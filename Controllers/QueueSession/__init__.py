import asyncio
import threading
import time

from Commons import commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession.game_queue_session_details import GameQueueSessionDetails
from Entities.Games.game_types import GameTypesEnum
from Entities.TimerClass import TimerClass
from Models.Queuer import QueuerModel
from Commons import static_functions


class BaseQueueSession:
    def __init__(self, game_score_type):
        self.queues: dict[str, GameQueueSessionDetails] = {}
        self.timer = TimerClass()
        self.game_score_type = game_score_type
        self.queue_must_run = True

    def init_session(self):
        games_values = [game.value for game in GameTypesEnum]
        games_enums = [game for game in GameTypesEnum]
        for index,item in enumerate(games_values):
            self.queues[games_values[index]] = GameQueueSessionDetails(games_enums[index], self.game_score_type)

        def check_start_new_game():
            while True:
                for key in self.queues.keys():
                    if self.queues[key].queuers_length() >= 2:
                        self.queues[key].start_game()
                    if len(self.queues[key].queuers) > 0:
                        print(f"{self.queues[key].game_type.value} queuer len : ", len(self.queues[key].queuers))
                print("---------------------")
                time.sleep(5)

        t = threading.Thread(target=check_start_new_game, daemon=True)
        t.start()

    def join_queuer(self, user_data: QueuerModel, gamer_type: str):
        self.queues[gamer_type].add_queuer(user_data)

    def disconnect_user(self, socket_id, gamer_type: str):
        self.queues[gamer_type].disconnect_user(socket_id)
