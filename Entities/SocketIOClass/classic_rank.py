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
                if game_play.is_user_id_valid(user_id):
                    uid_str = str(user_id)
                    active_sid = getattr(game_play, "active_user_sockets", {}).get(uid_str, "")
                    if active_sid and uid_str not in getattr(game_play, "disconnected_user_ids", set()):
                        print(f"[ClassicRankSocket] User {user_id} already in active game {g_id}. Rejecting duplicate classic-rank start.")
                        await self.disconnect(socket_id, namespace="/classic-rank")
                        return

        await self.enter_room(socket_id, socket_id, namespace="/classic-rank")

        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id)
        if user_data is not None:
            username = user_data["username"]
            user_image = user_data.get("image", 0)
            user_coin = user_data.get("coin", 0)
            user_score = user_data.get("score", 0)
        else:
            username = auth.get("username", "کاربر")
            user_image = int(auth.get("user_image", 0))
            user_coin = 0
            user_score = 0

        queuer_data = QueuerModel(
            user_id=user_id,
            username=username,
            socket_id=socket_id,
            user_image=user_image,
            user_coin=user_coin,
            user_score=user_score,
            is_rdy=True,
        )
        await classic_rank_session.start_classic_rank_match(queuer_data, game_type, socket_id)

    async def on_disconnect(self, socket_id):
        pass

    async def on_user_command(self, socket_id, data):
        pass
