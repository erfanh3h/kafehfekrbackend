import threading
import time

from Controllers.QueueSession import BaseQueueSession
from Controllers.QueueSession.normal_queue_session_details import NormalQueueSessionDetails
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel

all_game_types = [game.value for game in GameTypesEnum]


class NormalQueueSession(BaseQueueSession):
    def __init__(self):
        super().__init__(GameScoreTypesEnum.NORMAL)
        self.queues: dict[str, NormalQueueSessionDetails] = {}
        self.user_id_game_type_pair = {}

    def check_start_new_game(self):
        while True:
            for key in self.queues.keys():
                if self.queues[key].queuers_length() >= 2:
                    threading.Thread(target=self.queues[key].start_game, daemon=True).start()
                    # self.queues[key].start_game()
                if len(self.queues[key].queuers) > 0:
                    print(f"{self.game_score_type} {self.queues[key].game_type.value} queuer len : ",
                          len(self.queues[key].queuers))
            # print("---------------------")
            time.sleep(4)

    def init_session(self):
        games_values = [game.value for game in GameTypesEnum]
        games_enums = [game for game in GameTypesEnum]
        for index, item in enumerate(games_values):
            self.queues[games_values[index]] = NormalQueueSessionDetails(games_enums[index], self.game_score_type)
        super().init_session()

    def join_queuer(self, user_data: QueuerModel):
        game_type = user_data.game_types[0]
        if game_type in all_game_types:
            self.queues[game_type].add_queuer(user_data)
            self.user_id_game_type_pair[user_data.socket_id] = game_type
            return True
        return False

    def disconnect_user(self, user_socket_id):
        for socket_id in self.user_id_game_type_pair.keys():
            if socket_id == user_socket_id:
                self.queues[self.user_id_game_type_pair[socket_id]].disconnect_user(socket_id)
                del self.user_id_game_type_pair[socket_id]
                break
