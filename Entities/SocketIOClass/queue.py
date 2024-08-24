import socketio

from Commons import static_functions
from Controllers.QueueSession import BaseQueueSession
from Entities.ScoreManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel

queue_session = BaseQueueSession(GameScoreTypesEnum.NORMAL)
queue_session.start_timer()


class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        print('connect ', socket_id)
        print(environ)
        if auth is not None:
            try:
                user_id = auth['user_id']
            except:
                user_id = return_random_id()
        else:
            user_id = return_random_id()
        queuer_data = QueuerModel(user_id, "test", socket_id=socket_id)
        queue_session.join_queuer(queuer_data)

    async def on_disconnect(self, socket_id):
        # game_id = return_gameid_from_socketid(socket_id)
        # if game_id is not None:
        #     from Entities.SocketIOClass import Socket_Server
        #     await Socket_Server.leave_room(socket_id, current_game_id, namespace="/game")
        #     games[game_id].disconnect_user(socket_id)
        #     del socketid_gameid_pairs[socket_id]
        print('disconnect ', socket_id)
        queue_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        # game_id = return_gameid_from_socketid(socket_id)
        # if game_id is not None:
        #     await games[game_id].command_received(data, socket_id)
        #     print('User Sended command ', data)
        print('User Sended command ', data)


def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id
