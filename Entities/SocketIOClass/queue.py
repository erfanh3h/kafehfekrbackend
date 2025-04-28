import socketio

from Commons import static_functions
from Controllers.QueueSession.rank import RankQueueSession
from Models.Queuer import QueuerModel
from Commons import commands

# normal_queue_session = NormalQueueSession()
# normal_queue_session.init_session()
rank_queue_session = RankQueueSession()
rank_queue_session.init_session()


class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if auth is not None:
            try:
                from Entities.Security import extract_token
                # user_id = auth['user_id']
                token_data = await extract_token(auth['token'])
                if token_data is not None:
                    user_id = token_data['id']
                    # game_types = auth['game_types']
                    # game_score_type = auth['game_score_type']
                else:
                    await self.disconnect(socket_id, namespace="/queue")
                    return
            except:
                await self.disconnect(socket_id, namespace="/queue")
                return
        else:
            await self.disconnect(socket_id, namespace="/queue")
            return
        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id)
        queuer_data = QueuerModel(user_id, user_data["username"], socket_id=socket_id,
                                  user_image=user_data['image'], user_coin=user_data['coin'],
                                  user_score=user_data['score'])
        if user_data['coin'] < 15:  # check user coin
            await self.emit('command', {'id': commands.Not_Enough_Coin}, to=socket_id, namespace="/queue")
        else:
            rank_queue_session.join_queuer(queuer_data)

    async def on_disconnect(self, socket_id):
        rank_queue_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print('User Sended command ', data)
        await rank_queue_session.command_received(data, socket_id)


def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id
