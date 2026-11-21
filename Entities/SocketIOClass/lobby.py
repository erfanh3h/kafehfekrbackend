import socketio

from Controllers.QueueSession.lobby import LobbySession
from Entities.Security import check_is_token_valid
from Models.Queuer import QueuerModel

lobby_session = LobbySession()


class LobbySocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        from Commons import commands
        token_data = await check_is_token_valid(auth)
        if not token_data:
            await self.emit("command", {"id": commands.Logout}, to=socket_id, namespace="/lobby")
            await self.disconnect(socket_id, namespace="/lobby")
            return
        user_id = token_data["id"]
        from Entities.Database import game_database
        from Commons.static_functions import is_user_banned, is_version_allowed
        is_bot = bool(token_data.get('is_bot')) or str(user_id).startswith("bot_")
        user_data = None
        if not is_bot:
            user_data = game_database.users_manager.read_user(user_id)
            if not user_data or is_user_banned(user_data):
                await self.emit("command", {"id": commands.Logout, "data": {"reason": "banned", "message": "حساب کاربری شما توسط مدیریت مسدود شده است."}}, to=socket_id, namespace="/lobby")
                await self.disconnect(socket_id, namespace="/lobby")
                return

            client_ver = str(auth.get("version", "")).strip() if isinstance(auth, dict) else ""
            if client_ver:
                config_data = game_database.config_manager.read_config() or {}
                allowed_ver = str(config_data.get("allowed_version", "")).strip()
                if allowed_ver and not is_version_allowed(client_ver, allowed_ver):
                    await self.emit("command", {"id": commands.Logout, "data": {"reason": "force_update", "message": f"نسخه بازی شما ({client_ver}) قدیمی است. حداقل نسخه مجاز {allowed_ver} می‌باشد."}}, to=socket_id, namespace="/lobby")
                    await self.disconnect(socket_id, namespace="/lobby")
                    return
        if not user_data:
            user_data = {"username": "کاربر", "image": 0, "coin": 0, "score": 0, "profile_frame": 1}
        await self.enter_room(socket_id, socket_id, namespace="/lobby")
        queuer_data = QueuerModel(
            user_id,
            user_data.get("username", "کاربر"),
            socket_id=socket_id,
            user_image=user_data.get("image", 0),
            user_coin=user_data.get("coin", 0),
            user_score=user_data.get("score", 0),
            is_rdy=False,
            profile_frame=int(user_data.get("profile_frame", user_data.get("avatar_frame", 1)) or 1),
        )
        await lobby_session.join_queuers_list(queuer_data)

    async def on_disconnect(self, socket_id):
        await lobby_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print("User Sended command ", data)
        await lobby_session.command_received(data, socket_id)

    async def on_user_reaction(self, socket_id, data):
        await lobby_session.reaction_received(data, socket_id)
        print("User Sended command ", data)
