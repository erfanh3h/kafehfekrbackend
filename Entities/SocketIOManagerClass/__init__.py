import socketio

from Entities.SocketIOClass import Socket_Server


# class SocketManager:
async def send_message(message, skip_ids=None):
    if skip_ids is None:
        skip_ids = []
    await Socket_Server.send(message, skip_sid=skip_ids)


async def send_private_message(message, socket_id):
    await Socket_Server.send(message, to=socket_id)


async def send_command(command, game_id, skip_ids=None):
    if skip_ids is None:
        skip_ids = []
    await Socket_Server.emit('command', command, skip_sid=skip_ids, room=game_id)


async def send_reaction(player_id, reaction_id, game_id, skip_ids=None):
    if skip_ids is None:
        skip_ids = []
    await Socket_Server.emit('reaction', {"playerId": player_id, "reactionId":reaction_id}, skip_sid=skip_ids, room=game_id)


async def send_private_command(command, socket_id, game_id):
    await Socket_Server.emit('command', command, to=socket_id, room=game_id)
