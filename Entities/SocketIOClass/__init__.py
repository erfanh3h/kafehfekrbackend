import socketio

from Controllers.GameSession.normal_game_session import NormalGameSession
from Entities.Games.game_types import GameTypesEnum
from Models.Gamer import GamerModel
from Controllers.GameSession import static_functions

gameSession = NormalGameSession()
gameSession.start_game_timer(game_type=GameTypesEnum.TIC_TAC_TOE)
Socket_Server = socketio.AsyncServer(async_mode='asgi')

user_sids = []


@Socket_Server.event
async def connect(sid, environ, auth):
    print('connect ', sid)
    if auth is not None:
        name = auth['name']
    else:
        name = static_functions.create_random_name()
    print(Socket_Server.namespaces)
    # Socket_Server.enter_room(sid,"1")
    await my_message(sid, {'Test': f'{sid}'})
    user_sids.append(sid)

    gameSession.add_gamer(GamerModel(user_id=sid, username=name, socket_id=sid))
    # print(Socket_Server.rooms(sid))


@Socket_Server.event
async def my_message(sid, data):
    await Socket_Server.send(data)
    print('Send message ', data)


@Socket_Server.event
async def userCommand(sid, data):
    await gameSession.command_received(data, sid)
    print('User Sended command ', data)


@Socket_Server.event
async def disconnect(sid):
    print('disconnect ', sid)
    user_sids.remove(sid)
