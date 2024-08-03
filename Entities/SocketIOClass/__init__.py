import socketio

from Controllers.GameSession.checkers_game_session import CheckersGameSession
from Controllers.GameSession.mill_game_session import MillGameSession
from Controllers.GameSession.mnumbers_game_session import MNumbersGameSession
from Controllers.GameSession.msweeper_game_session import MSweeperGameSession
from Controllers.GameSession.rpc_game_session import RPCGameSession
from Controllers.GameSession.tictactoe_game_session import TicTacToeGameSession
from Models.Gamer import GamerModel
from Commons import static_functions

Socket_Server = socketio.AsyncServer(async_mode='asgi')

current_game_id = "gameId"
# gameSession = MillGameSession(game_id=current_game_id)
# gameSession = MNumbersGameSession(game_id=current_game_id)
gameSession = CheckersGameSession(game_id=current_game_id)
# gameSession = TicTacToeGameSession(game_id=current_game_id)
# gameSession = RPCGameSession(game_id=current_game_id)
# gameSession = MSweeperGameSession(game_id=current_game_id)

gameSession.add_gamer(GamerModel(user_id="0", username='test'))
gameSession.add_gamer(GamerModel(user_id="1", username='mobile'))
gameSession.start_game_timer()

games = {current_game_id: gameSession}
game_idies = [current_game_id]
socketid_gameid_pairs = {}


@Socket_Server.event
async def connect(socket_id, environ, auth):
    print('connect ', socket_id)
    if auth is not None:
        try:
            user_id = auth['user_id']
            user_game_id = auth['game_id']
        except:
            user_id, user_game_id = return_random_idies()
    else:
        user_id, user_game_id = return_random_idies()
    # print(Socket_Server.namespaces)
    #     await my_message(socket_id, {'Test': f'{socket_id}'})

    if is_game_id_valid(user_game_id):
        if games[user_game_id].gamer_idies.__contains__(user_id):
            await Socket_Server.enter_room(socket_id, user_game_id)
            games[user_game_id].join_gamer(user_id, socket_id)
            socketid_gameid_pairs[socket_id] = user_game_id
        else:
            await Socket_Server.disconnect(socket_id)
    else:
        await Socket_Server.disconnect(socket_id)


@Socket_Server.event
async def userReaction(socket_id, data):
    game_id = return_gameid_from_socketid(socket_id)
    if game_id is not None:
        await games[game_id].reaction_received(data, socket_id)
        print('User Sended command ', data)


@Socket_Server.event
async def userCommand(socket_id, data):
    game_id = return_gameid_from_socketid(socket_id)
    if game_id is not None:
        await games[game_id].command_received(data, socket_id)
        print('User Sended command ', data)


@Socket_Server.event
async def disconnect(socket_id):
    game_id = return_gameid_from_socketid(socket_id)
    if game_id is not None:
        await Socket_Server.leave_room(socket_id, current_game_id)
        games[game_id].disconnect_user(socket_id)
        del socketid_gameid_pairs[socket_id]
    print('disconnect ', socket_id)


def is_game_id_valid(recived_game_id):
    for game_id in game_idies:
        if game_id == recived_game_id:
            return True
    return False


def return_random_idies():
    user_id = static_functions.create_random_name()
    user_game_id = static_functions.create_random_name()
    return user_id, user_game_id


def return_gameid_from_socketid(socket_id):
    for raw_socket_id in socketid_gameid_pairs.keys():
        if raw_socket_id == socket_id:
            return socketid_gameid_pairs[raw_socket_id]
    return None
