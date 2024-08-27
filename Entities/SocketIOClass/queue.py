import socketio

from Commons import static_functions
from Controllers.QueueSession import BaseQueueSession
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel

queue_session = BaseQueueSession(GameScoreTypesEnum.NORMAL)
queue_session.init_session()
game_types = [game.value for game in GameTypesEnum]
socketid_game_type_pairs: dict[str, str] = {}


class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        print('connect ', socket_id)
        print(environ)
        if auth is not None:
            try:
                user_id = auth['user_id']
                if auth['game_type'] in game_types:
                    game_type = auth['game_type']
                else:
                    game_type = None
            except:
                user_id = return_random_id()
                game_type = None
        else:
            user_id = return_random_id()
            game_type = None
        if game_type is None:
            await self.disconnect(socket_id, namespace="/queue")
        else:
            queuer_data = QueuerModel(user_id, "test", socket_id=socket_id)
            queue_session.join_queuer(queuer_data, game_type)
            socketid_game_type_pairs[socket_id] = game_type

    async def on_disconnect(self, socket_id):
        game_type = return_game_type_from_socketid(socket_id)
        if game_type is not None:
            queue_session.disconnect_user(socket_id, game_type)
            del socketid_game_type_pairs[socket_id]
        print('disconnect ', socket_id)

    async def on_user_command(self, socket_id, data):
        # game_id = return_gameid_from_socketid(socket_id)
        # if game_id is not None:
        #     await games[game_id].command_received(data, socket_id)
        #     print('User Sended command ', data)
        print('User Sended command ', data)


def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id


def return_game_type_from_socketid(socket_id):
    for raw_socket_id in socketid_game_type_pairs.keys():
        if raw_socket_id == socket_id:
            return socketid_game_type_pairs[raw_socket_id]
    return None
