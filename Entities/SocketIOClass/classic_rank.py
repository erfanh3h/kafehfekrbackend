"""
Socket.IO Namespace for Classic Rank Matchmaking (/classic-rank).
"""

import socketio
from Commons import commands
from Controllers.QueueSession.classic_rank import ClassicRankSession
from Entities.Security import check_is_token_valid
from Models.Queuer import QueuerModel

classic_rank_session = ClassicRankSession()


class ClassicRankSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if not isinstance(auth, dict):
            await self.disconnect(socket_id, namespace="/classic-rank")
            return
        try:
            token_data = await check_is_token_valid(auth)
            if token_data is None:
                await self.emit("command", {"id": commands.Logout}, to=socket_id, namespace="/classic-rank")
                await self.disconnect(socket_id, namespace="/classic-rank")
                return
            user_id = token_data["id"]
            game_type = auth.get("game_type", "TicTacToe")
        except Exception as e:
            print(f"[ClassicRankSocket] Auth error: {e}")
            await self.disconnect(socket_id, namespace="/classic-rank")
            return

        # Reject if user already has a live active ongoing game in memory
        from Entities.SocketIOClass.game import games
        for g_id, game_play in list(games.items()):
            if not getattr(game_play, "is_game_finished", False) and not getattr(game_play, "is_game_terminated", False):
                is_active_fn = getattr(game_play, "is_user_active_in_game", game_play.is_user_id_valid)
                if is_active_fn(user_id):
                    uid_str = str(user_id)
                    active_sid = getattr(game_play, "active_user_sockets", {}).get(uid_str, "")
                    if active_sid and uid_str not in getattr(game_play, "disconnected_user_ids", set()):
                        print(f"[ClassicRankSocket] User {user_id} already in active game {g_id}. Rejecting duplicate classic-rank start.")
                        await self.disconnect(socket_id, namespace="/classic-rank")
                        return

        await self.enter_room(socket_id, socket_id, namespace="/classic-rank")

        from Entities.Database import game_database
        from Commons.static_functions import (
            check_ban_and_auto_unban,
            get_maintenance_block,
            is_queue_closed,
            is_version_allowed,
        )
        is_bot = bool(token_data.get('is_bot')) or str(user_id).startswith("bot_")
        user_data = None
        if not is_bot:
            user_data = game_database.users_manager.read_user(user_id)
            if user_data is None or check_ban_and_auto_unban(user_data, game_database.users_manager):
                await self.emit("command", {"id": commands.Logout, "data": {"reason": "banned", "message": "حساب کاربری شما توسط مدیریت مسدود شده است."}}, to=socket_id, namespace="/classic-rank")
                await self.disconnect(socket_id, namespace="/classic-rank")
                return

            config_data = game_database.config_manager.read_config() or {}
            maint_msg = get_maintenance_block(config_data)
            if maint_msg:
                await self.emit("command", {"id": commands.Logout, "data": {"reason": "maintenance", "message": maint_msg}}, to=socket_id, namespace="/classic-rank")
                await self.disconnect(socket_id, namespace="/classic-rank")
                return

            client_ver = str(auth.get("version", "")).strip() if isinstance(auth, dict) else ""
            if client_ver:
                allowed_ver = str(config_data.get("allowed_version", "")).strip()
                if allowed_ver and not is_version_allowed(client_ver, allowed_ver):
                    await self.emit("command", {"id": commands.Logout, "data": {"reason": "force_update", "message": f"نسخه بازی شما ({client_ver}) قدیمی است. حداقل نسخه مجاز {allowed_ver} می‌باشد."}}, to=socket_id, namespace="/classic-rank")
                    await self.disconnect(socket_id, namespace="/classic-rank")
                    return

            if is_queue_closed(config_data):
                await self.emit("command", {"id": getattr(commands, "Queue_Closed", "QueueClosed"), "data": {"message": "صف مسابقات در حال حاضر توسط مدیریت بسته شده است."}}, to=socket_id, namespace="/classic-rank")
                await self.disconnect(socket_id, namespace="/classic-rank")
                return

        if user_data is not None:
            username = user_data["username"]
            user_image = user_data.get("image", 0)
            user_coin = user_data.get("coin", 0)
            user_score = user_data.get("score", 0)
            profile_frame = int(user_data.get("profile_frame", user_data.get("avatar_frame", 1)) or 1)
        else:
            username = auth.get("username", "کاربر")
            user_image = int(auth.get("user_image", 0))
            user_coin = 0
            user_score = 0
            profile_frame = int(auth.get("profile_frame", auth.get("avatar_frame", 1)) or 1)

        queuer_data = QueuerModel(
            user_id=user_id,
            username=username,
            socket_id=socket_id,
            user_image=user_image,
            user_coin=user_coin,
            user_score=user_score,
            is_rdy=True,
            profile_frame=profile_frame,
        )
        await classic_rank_session.start_classic_rank_match(queuer_data, game_type, socket_id)

    async def on_disconnect(self, socket_id):
        pass

    async def on_user_command(self, socket_id, data):
        pass
