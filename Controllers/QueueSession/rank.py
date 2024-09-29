import asyncio
import threading
import time

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession import BaseQueueSession
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel


class RankQueueSession(BaseQueueSession):
    def __init__(self):
        super().__init__(GameScoreTypesEnum.RANK)
        self.queuers: list[QueuerModel] = []

    def find_gamer_from_user_id(self, user_id):
        for queuer in self.queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def start_new_game(self):
        queuers_idis = [self.queuers[0].user_id, self.queuers[1].user_id]
        queuers = []
        from Entities.SocketIOManagerClass import send_queue_command
        for queuer_id in queuers_idis:
            queuer_data = self.find_gamer_from_user_id(queuer_id)
            if queuer_data is None:
                return False
            queuers.append(queuer_data)
        game_id = static_functions.create_random_game_id()
        mix_game_type = []
        mix_game_type.extend(queuers[0].game_types)
        mix_game_type.extend(queuers[1].game_types)
        final_game_types = list(set(mix_game_type))
        # game_id = 'testgame'
        game_data = {'game_id': game_id}
        if len(queuers) == 2:
            for queuer_data in queuers:
                asyncio.new_event_loop().run_until_complete(
                    send_queue_command(command=make_command_json(id=commands.Start_Game, data=game_data),
                                       socket_id=queuer_data.socket_id))
                self.queuers.remove(queuer_data)
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

    def check_start_new_game(self):
        while True:
            if len(self.queuers) > 0:
                print(f"{self.game_score_type} queuer len : ", len(self.queuers))
            if len(self.queuers) >= 2:
                threading.Thread(target=self.start_new_game, daemon=True).start()
                time.sleep(2)
            else:
                time.sleep(4)

    def join_queuer(self, user_data: QueuerModel):
        self.queuers.append(user_data)

    def disconnect_user(self, socket_id):
        for user_data in self.queuers:
            if socket_id == user_data.socket_id:
                self.queuers.remove(user_data)
                break
