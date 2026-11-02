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
        user_data = game_database.users_manager.read_user(user_id)
        if not user_data:
            await self.disconnect(socket_id, namespace="/lobby")
            return
        await self.enter_room(socket_id, socket_id, namespace="/lobby")
        queuer_data = QueuerModel(
            user_id,
            user_data.get("username", "کاربر"),
            socket_id=socket_id,
            user_image=user_data.get("image", 0),
            user_coin=user_data.get("coin", 0),
            user_score=user_data.get("score", 0),
            is_rdy=False,
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
