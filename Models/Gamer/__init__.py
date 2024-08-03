import asyncio

from Entities.TimerClass.UserDisconnectTimerClass import UserDisconnectTimerClass
from Models.User import UserModel


class GamerModel(UserModel):
    def __init__(self, user_id: str, username: str, finish_reconnect_time_function=None, socket_id='',
                 team_id: int = 0):
        super().__init__(user_id, username)
        self.socket_id = socket_id
        self.gamer_id: int = 0
        self.user_id: str = user_id
        self.timer = UserDisconnectTimerClass(user_id=user_id)
        self.finish_reconnect_time_function = finish_reconnect_time_function
        self.is_alive: bool = True
        self.is_joined_game: bool = False
        self.is_disconnected: bool = False
        self.is_leaver: bool = False
        self.report_charge: int = 5
        self.reconnect_charge: int = 3
        self.team_id: int = team_id

    def set_finish_reconnect_time_function(self, finish_reconnect_time_function):
        self.finish_reconnect_time_function = finish_reconnect_time_function
        self.timer.set_finish_timer_function(finish_reconnect_time_function)

    def join_game(self, socket_id):
        self.is_joined_game = True
        self.socket_id = socket_id

    def reconnect(self, socket_id):
        self.is_disconnected = False
        self.socket_id = socket_id
        self.reconnect_charge -= 1
        self.timer.stop()

    def disconnect(self):
        self.is_disconnected = True
        self.socket_id = ""
        self.timer.start()

    def to_json(self):
        return {'gamer_id': self.gamer_id, 'name': self.username, 'user_id': self.user_id,
                'remain_dc_time': self.timer.max_time, 'is_disconnected': self.is_disconnected, }
