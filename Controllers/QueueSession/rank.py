import asyncio
import threading
import time

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession import BaseQueueSession
from Controllers.QueueSession.pre_game import PreGameClass
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel


class RankQueueSession(BaseQueueSession):
    def __init__(self):
        super().__init__(GameScoreTypesEnum.RANK)
        self.queuers: list[QueuerModel] = []
        self.active_pre_games: dict[str, PreGameClass] = {}

    def find_gamer_from_user_id(self, user_id):
        for queuer in self.queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def find_gamer_from_socket_id(self, socket_id):
        for queuer in self.queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    async def command_received(self, data, socket_id):
        pre_game_id = data['pre_game_id']
        if pre_game_id is None:
            return
        if pre_game_id not in self.active_pre_games.keys():
            return
        await self.active_pre_games[pre_game_id].command_received(data, socket_id)

    def start_new_game(self, queuers, game_types):
        if len(queuers) != 2:
            return
        from Entities.SocketIOManagerClass import send_queue_command
        game_id = static_functions.create_random_game_id()
        final_game_types = game_types
        # game_id = 'testgame'
        game_data = {'game_id': game_id}
        for queuer_data in queuers:
            asyncio.new_event_loop().run_until_complete(
                send_queue_command(command=make_command_json(id=commands.Start_Game, data=game_data),
                                   socket_id=queuer_data.socket_id))
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

    def start_new_pre_game(self):
        queuers_idis = [self.queuers[0].user_id, self.queuers[1].user_id]
        queuers = []
        for queuer_id in queuers_idis:
            queuer_data = self.find_gamer_from_user_id(queuer_id)
            if queuer_data is None:
                return False
            queuers.append(queuer_data)
        if len(queuers) != 2:
            return
        pre_game_id = static_functions.create_random_game_id()
        queurs_data = []
        for queuer_data in queuers:
            queurs_data.append(queuer_data.to_json())
        game_data = {'id': pre_game_id, 'queuers': queurs_data}
        from Entities.SocketIOManagerClass import enter_pre_game, send_queue_command
        for queuer_data in queuers:
            print(queuer_data.socket_id)
            asyncio.new_event_loop().run_until_complete(
                send_queue_command(command=make_command_json(id=commands.Start_Pre_Game, data=game_data),
                                   socket_id=queuer_data.socket_id))
            asyncio.new_event_loop().run_until_complete(
                enter_pre_game(socket_id=queuer_data.socket_id, pre_game_id=pre_game_id))
            self.queuers.remove(queuer_data)
        self.active_pre_games[pre_game_id] = PreGameClass(pre_game_id, queuers, self.start_new_game)
        self.active_pre_games[pre_game_id].start_pre_game()

    def check_start_new_game(self):
        while True:
            if len(self.queuers) > 0:
                print(f"{self.game_score_type} queuer len : ", len(self.queuers))
            if len(self.queuers) >= 2:
                threading.Thread(target=self.start_new_pre_game, daemon=True).start()
                time.sleep(1.5)
            else:
                time.sleep(4)

    def join_queuer(self, user_data: QueuerModel):
        self.queuers.append(user_data)

    def reconnect_queuer(self, pre_game_id, user_data: QueuerModel):
        print(pre_game_id)

    def disconnect_user(self, socket_id):
        for user_data in self.queuers:
            if socket_id == user_data.socket_id:
                self.queuers.remove(user_data)
                break
