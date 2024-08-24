import socketio

from Commons import static_functions
from Entities.ScoreManagerClass import GameScoreTypesEnum
from Models.Gamer import GamerModel

current_game_id = "gameId"


class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        print('connect ', socket_id)
        print(environ)
        if auth is not None:
            try:
                user_id = auth['user_id']
                user_game_id = auth['game_id']
            except:
                user_id, user_game_id = return_random_idies()
        else:
            user_id, user_game_id = return_random_idies()

        # from Entities.SocketIOClass import Socket_Server
        # if is_game_id_valid(user_game_id):
        #     if games[user_game_id].gamer_idies.__contains__(user_id):
        #         await Socket_Server.enter_room(socket_id, user_game_id, namespace="/game")
        #         games[user_game_id].join_gamer(user_id, socket_id)
        #         socketid_gameid_pairs[socket_id] = user_game_id
        #     else:
        #         await Socket_Server.disconnect(socket_id, namespace="/game")
        # else:
        #     await Socket_Server.disconnect(socket_id, namespace="/game")

    async def on_disconnect(self, socket_id):
        # game_id = return_gameid_from_socketid(socket_id)
        # if game_id is not None:
        #     from Entities.SocketIOClass import Socket_Server
        #     await Socket_Server.leave_room(socket_id, current_game_id, namespace="/game")
        #     games[game_id].disconnect_user(socket_id)
        #     del socketid_gameid_pairs[socket_id]
        print('disconnect ', socket_id)

    async def on_user_command(self, socket_id, data):
        # game_id = return_gameid_from_socketid(socket_id)
        # if game_id is not None:
        #     await games[game_id].command_received(data, socket_id)
        #     print('User Sended command ', data)
        print('User Sended command ', data)


def return_random_idies():
    user_id = static_functions.create_random_name()
    user_game_id = static_functions.create_random_name()
    return user_id, user_game_id
