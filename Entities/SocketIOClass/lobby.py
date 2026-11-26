import socketio

from Controllers.QueueSession.lobby import LobbySession
from Entities.SocketIOClass._auth_guard import authenticate_namespace_user
from Models.Queuer import QueuerModel

lobby_session = LobbySession()


class LobbySocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        auth_res = await authenticate_namespace_user(
            self,
            socket_id,
            auth,
            "/lobby",
            require_dict_auth=False,
            check_maintenance=True,
            check_version=True,
        )
        if auth_res is None:
            return
        token_data, user_data, _is_bot = auth_res
        user_id = token_data["id"]
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
