import asyncio

from Models.User import UserModel


class GamerModel(UserModel):
    def __init__(self, user_id: str, username: str, socket_id='', team_id: int = 0):
        super().__init__(user_id, username)
        self.socket_id = socket_id
        self.gamer_id: int = 0
        self.user_id: str = user_id
        self.is_alive: bool = True
        self.is_joined_game: bool = False
        self.is_disconnected: bool = False
        self.is_leaver: bool = False
        self.report_charge: int = 5
        self.reconnect_charge: int = 3
        self.team_id: int = team_id

    def join_game(self, socket_id):
        self.is_joined_game = True
        self.socket_id = socket_id

    def reconnect(self, socket_id):
        self.is_disconnected = False
        self.socket_id = socket_id
        self.reconnect_charge -= 1

    def disconnect(self):
        self.is_disconnected = True
        self.socket_id = ""

    def to_json(self):
        return {'gamer_id': self.gamer_id, 'name': self.username, 'user_id': self.user_id}
