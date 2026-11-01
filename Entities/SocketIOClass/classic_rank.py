"""
Socket.IO Namespace for Classic Rank Matchmaking (/classic-rank).
"""

import socketio

from Controllers.QueueSession.classic_rank import ClassicRankSession
from Entities.Security import extract_token
from Models.Queuer import QueuerModel

classic_rank_session = ClassicRankSession()


class ClassicRankSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if auth is None:
            await self.disconnect(socket_id, namespace="/classic-rank")
            return

        try:
            token = auth.get("token", "")
            token_data = await extract_token(token)
            if token_data is None:
                await self.disconnect(socket_id, namespace="/classic-rank")
                return

            user_id = token_data["id"]
            game_type = auth.get("game_type", "TicTacToe")
            await self.enter_room(socket_id, socket_id, namespace="/classic-rank")
        except Exception as e:
            print(f"[ClassicRankSocket] Auth error: {e}")
            await self.disconnect(socket_id, namespace="/classic-rank")
            return

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
