import socketio

from Entities.SocketIOClass import Socket_Server


# class SocketManager:
async def send_message(message, namespace="/game", skip_ids=None):
    if skip_ids is None:
        skip_ids = []
    await Socket_Server.send(message, skip_sid=skip_ids, namespace=namespace)


async def send_private_message(message, socket_id, namespace="/game"):
    await Socket_Server.send(message, to=socket_id, namespace=namespace)


async def send_command(command, game_id, namespace="/game", skip_ids=None):
    if skip_ids is None:
        skip_ids = []
    await Socket_Server.emit('command', command, skip_sid=skip_ids, room=game_id, namespace=namespace)


async def send_reaction(player_id, reaction_id, game_id, namespace="/game", skip_ids=None):
    if skip_ids is None:
        skip_ids = []
    await Socket_Server.emit('reaction', {"playerId": player_id, "reactionId": reaction_id}, skip_sid=skip_ids,
                             room=game_id, namespace=namespace)


async def send_private_command(command, socket_id, game_id, namespace="/game"):
    await Socket_Server.emit('command', command, to=socket_id, room=game_id, namespace=namespace)


async def send_queue_command(command, socket_id, namespace="/queue"):
    await Socket_Server.emit('command', command, to=socket_id, namespace=namespace)


async def enter_pre_game(socket_id, pre_game_id, namespace="/queue"):
    await Socket_Server.enter_room(sid=socket_id, room=pre_game_id, namespace=namespace)

async def send_pre_game_command(command, pre_game_id, namespace="/queue"):
    await Socket_Server.emit('command', command, room=pre_game_id, namespace=namespace)

async def enter_lobby(socket_id, lobby_id, namespace="/lobby"):
    await Socket_Server.enter_room(sid=socket_id, room=lobby_id, namespace=namespace)


async def leave_lobby(socket_id, lobby_id, namespace="/lobby"):
    await Socket_Server.leave_room(socket_id, lobby_id, namespace=namespace)


async def send_lobby_command(command, lobby_id, namespace="/lobby"):
    await Socket_Server.emit('command', command, room=lobby_id, namespace=namespace)


async def send_private_lobby_command(command, socket_id, namespace="/lobby"):
    await Socket_Server.emit('command', command, to=socket_id, namespace=namespace)


async def send_global_lobby_command(command, namespace="/lobby"):
    await Socket_Server.emit('command', command, namespace=namespace)


async def send_lobby_reaction(player_id, reaction_id, lobby_id, namespace="/lobby"):
    await Socket_Server.emit('reaction', {"playerId": player_id, "reactionId": reaction_id}, room=lobby_id,
                             namespace=namespace)
