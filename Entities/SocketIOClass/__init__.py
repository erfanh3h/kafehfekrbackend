import socketio

from Entities.Database import game_database
from Entities.SocketIOClass.chat import ChatSocketNameSpace
from Entities.SocketIOClass.game import GameSocketNameSpace
from Entities.SocketIOClass.lobby import LobbySocketNameSpace
from Entities.SocketIOClass.multi_queue import MultiQueueSocketNameSpace
from Entities.SocketIOClass.queue import QueueSocketNameSpace

Socket_Server = socketio.AsyncServer(async_mode='asgi',
                                     namespaces=['/game', '/queue', '/multi-queue', '/lobby', '/chat'])
Socket_Server.register_namespace(GameSocketNameSpace('/game'))
Socket_Server.register_namespace(QueueSocketNameSpace('/queue'))
Socket_Server.register_namespace(MultiQueueSocketNameSpace('/multi-queue'))
Socket_Server.register_namespace(LobbySocketNameSpace('/lobby'))
Socket_Server.register_namespace(ChatSocketNameSpace('/chat'))
