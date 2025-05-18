import socketio

from Commons import static_functions
from Controllers.QueueSession.chat import ChatSession
from Controllers.QueueSession.lobby import LobbySession
from Models.Chat_User import ChatUserModel
from Models.Queuer import QueuerModel
from Commons import commands

chat_session = ChatSession()


class ChatSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if auth is not None:
            try:
                from Entities.Security import extract_token
                # user_id = auth['user_id']
                token_data = await extract_token(auth['token'])
                if token_data is not None:
                    user_id = token_data['id']
                else:
                    await self.disconnect(socket_id, namespace="/lobby")
                    return
            except:
                await self.disconnect(socket_id, namespace="/lobby")
                return
        else:
            await self.disconnect(socket_id, namespace="/lobby")
            return
        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id)
        user_dt = ChatUserModel(user_id, user_data["username"], socket_id=socket_id,
                                user_image=user_data['image'], user_coin=user_data['coin'],
                                user_score=user_data['score'])
        chat_session.join_user(user_dt)

    async def on_disconnect(self, socket_id):
        await chat_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print('User Sended command ', data)
        await chat_session.command_received(data, socket_id)
