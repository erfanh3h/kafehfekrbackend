import socketio

from Controllers.QueueSession.lobby import LobbySession
from Entities.Security import check_is_token_valid
from Models.Queuer import QueuerModel

lobby_session = LobbySession()


class LobbySocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        token_data = await check_is_token_valid(auth)
        if not token_data:
            await self.disconnect(socket_id, namespace="/lobby")
            return
        user_id = token_data['id']
        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id)
        queuer_data = QueuerModel(user_id, user_data["username"], socket_id=socket_id,
                                  user_image=user_data['image'], user_coin=user_data['coin'],
                                  user_score=user_data['score'], is_rdy=False)
        await lobby_session.join_queuers_list(queuer_data)
        # if user_data['coin'] < 5:  # check user coin
        #     await self.emit('command', {'id': commands.Not_Enough_Coin}, to=socket_id, namespace="/lobby")
        # else:
        #     lobby_session.create_lobby(queuer_data, game_types, lobby_name, lobby_password)

    async def on_disconnect(self, socket_id):
        await lobby_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print('User Sended command ', data)
        await lobby_session.command_received(data, socket_id)

    async def on_user_reaction(self, socket_id, data):
        await lobby_session.reaction_received(data, socket_id)
        print('User Sended command ', data)
