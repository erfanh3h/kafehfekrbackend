import asyncio
import threading
import time

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession import BaseQueueSession
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel


class MultiRankQueueSession(BaseQueueSession):
    def __init__(self):
        super().__init__(GameScoreTypesEnum.MultiRANK)
        self.ludo_queuers: list[QueuerModel] = []

    def find_gamer_from_user_id(self, user_id):
        for queuer in self.ludo_queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def find_gamer_from_socket_id(self, socket_id):
        for queuer in self.ludo_queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    async def command_received(self, data, socket_id):
        from Entities.SocketIOManagerClass import send_global_command
        if data['id'] == commands.Message:
            gamer = self.find_gamer_from_socket_id(socket_id)
            send_data = {'name': gamer.username, 'content': data['content'], 'id': gamer.user_id}
            await send_global_command(command=make_command_json(id=commands.Message, data=send_data))

    def start_new_game(self, queuers, game_type):
        from Entities.SocketIOManagerClass import send_queue_command
        game_id = static_functions.create_random_game_id()
        final_game_types = [game_type]
        game_data = {'game_id': game_id}
        for queuer_data in queuers:
            asyncio.new_event_loop().run_until_complete(
                send_queue_command(command=make_command_json(id=commands.Start_Game, data=game_data),
                                   socket_id=queuer_data.socket_id, namespace='/multi-queue'))
            self.ludo_queuers.remove(queuer_data)
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

    def check_start_new_game(self):
        def start_ludo():
            self.start_new_game(self.ludo_queuers[0: 3], GameTypesEnum.LUDO.value)

        while True:
            if len(self.ludo_queuers) > 0:
                print(f"ludo queuer len : ", len(self.ludo_queuers))
            if len(self.ludo_queuers) >= 3:
                threading.Thread(target=start_ludo, daemon=True).start()
                time.sleep(1.5)
            else:
                time.sleep(4)

    def join_user(self, user_data: QueuerModel, game_type):
        if game_type == GameTypesEnum.LUDO.value:
            self.ludo_queuers.append(user_data)

    async def disconnect_user(self, socket_id):
        for user_data in self.ludo_queuers:
            if socket_id == user_data.socket_id:
                self.ludo_queuers.remove(user_data)
                break
