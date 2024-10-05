import socketio

from Entities.SocketIOClass.game import GameSocketNameSpace
from Entities.SocketIOClass.lobby import LobbySocketNameSpace
from Entities.SocketIOClass.queue import QueueSocketNameSpace

Socket_Server = socketio.AsyncServer(async_mode='asgi', namespaces=['/game', '/queue', '/lobby'])
Socket_Server.register_namespace(GameSocketNameSpace('/game'))
Socket_Server.register_namespace(QueueSocketNameSpace('/queue'))
Socket_Server.register_namespace(LobbySocketNameSpace('/lobby'))
