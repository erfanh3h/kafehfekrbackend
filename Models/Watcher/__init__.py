from Models.User import UserModel
from fastapi import WebSocket


class WatcherModel(UserModel):
    def __init__(self, websocket: WebSocket, userId: int, username: str):
        super().__init__(userId, username)
        self.socket: WebSocket = websocket