import socketio

from Controllers.QueueSession.chat import ChatSession
from Entities.SocketIOClass._auth_guard import authenticate_namespace_user
from Models.Chat_User import ChatUserModel

chat_session = ChatSession()


class ChatSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        auth_res = await authenticate_namespace_user(
            self,
            socket_id,
            auth,
            "/chat",
            require_dict_auth=False,
            disconnect_bot=True,
        )
        if auth_res is None:
            return
        token_data, user_data, _is_bot = auth_res
        user_id = token_data['id']
        user_dt = ChatUserModel(user_id, user_data["username"], socket_id=socket_id,
                                user_image=user_data['image'], user_coin=user_data['coin'],
                                user_score=user_data['score'])
        chat_session.join_user(user_dt)

    async def on_disconnect(self, socket_id):
        await chat_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print('User Sended command ', data)
        await chat_session.command_received(data, socket_id)
