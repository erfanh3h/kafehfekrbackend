import asyncio
import threading
import time

from Commons import commands
from Commons.static_functions import make_command_json
from Entities.Games.game_types import GameTypesEnum
from Entities.TimerClass import TimerClass
from Models.Queuer import QueuerModel
from Commons import static_functions


class GameQueueSessionDetails:
    def __init__(self, game_type, game_score_type):
        self.queuers: list[QueuerModel] = []
        self.game_type = game_type
        self.game_score_type = game_score_type
        self.queue_must_run = True

    def queuers_length(self) -> int:
        return len(self.queuers)

    def find_gamer_from_socket(self, socket_id):
        for queuer in self.queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def find_gamer_from_user_id(self, user_id):
        for queuer in self.queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def add_queuer(self, queuer: QueuerModel):
        self.queuers.append(queuer)

    def join_queuer(self, user_data: QueuerModel):
        self.queuers.append(user_data)

    def start_game(self):
        queuers_idis = [self.queuers[0].user_id, self.queuers[1].user_id]
        queuers = []
        from Entities.SocketIOManagerClass import send_queue_command
        for queuer_id in queuers_idis:
            queuer_data = self.find_gamer_from_user_id(queuer_id)
            if queuer_data is None:
                return False
            queuers.append(queuer_data)
        game_id = static_functions.create_random_game_id()
        # game_id = 'testgame'
        game_data = {'game_id': game_id}
        if len(queuers) == 2:
            for queuer_data in queuers:
                asyncio.new_event_loop().run_until_complete(
                    send_queue_command(command=make_command_json(id=commands.Start_Game, data=game_data),
                                       socket_id=queuer_data.socket_id))
                self.queuers.remove(queuer_data)
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, self.game_type, self.game_score_type)

    def command_received(self, data, socket_id):
        queuer_data = self.find_gamer_from_socket(socket_id)
        if queuer_data is None:
            return None
        else:
            user_id = queuer_data.user_id
        return user_id

    def disconnect_user(self, socket_id):
        queuer_data = self.find_gamer_from_socket(socket_id)
        if queuer_data is not None:
            self.queuers.remove(queuer_data)
