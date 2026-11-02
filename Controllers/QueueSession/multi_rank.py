from Commons.static_functions import safe_run_async
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
            if str(queuer.user_id) == str(user_id):
                return queuer
        return None

    def find_gamer_from_socket_id(self, socket_id):
        for queuer in self.ludo_queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def can_user_join_queue(self, user_id) -> bool:
        if self.find_gamer_from_user_id(user_id) is not None:
            return False
        try:
            from Entities.SocketIOClass.game import games
            for g_id, game_play in list(games.items()):
                if not getattr(game_play, "is_game_finished", False) and not getattr(game_play, "is_game_terminated", False):
                    if game_play.is_user_id_valid(user_id):
                        return False
        except Exception:
            pass
        return True

    async def command_received(self, data, socket_id):
        from Entities.SocketIOManagerClass import send_global_command
        if isinstance(data, dict) and data.get('id') == commands.Message:
            gamer = self.find_gamer_from_socket_id(socket_id)
            if gamer is None:
                return
            send_data = {'name': gamer.username, 'content': data.get('content', ''), 'id': gamer.user_id}
            await send_global_command(command=make_command_json(id=commands.Message, data=send_data))

    def start_new_game(self, queuers, game_type):
        from Entities.SocketIOManagerClass import send_queue_command
        game_id = static_functions.create_random_game_id()
        final_game_types = [game_type]
        game_data = {'game_id': game_id}
        for queuer_data in queuers:
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.Start_Game, data=game_data),
                                   socket_id=queuer_data.socket_id, namespace='/multi-queue'))
            if queuer_data in self.ludo_queuers:
                self.ludo_queuers.remove(queuer_data)
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

    def check_start_new_game(self):
        while True:
            if len(self.ludo_queuers) > 0:
                print(f"ludo queuer len : ", len(self.ludo_queuers))
            distinct_queuers = []
            seen_uids = set()
            for q in list(self.ludo_queuers):
                uid_s = str(q.user_id)
                if uid_s not in seen_uids:
                    seen_uids.add(uid_s)
                    distinct_queuers.append(q)
                if len(distinct_queuers) == 3:
                    break
            if len(distinct_queuers) >= 3:
                for q in distinct_queuers:
                    if q in self.ludo_queuers:
                        self.ludo_queuers.remove(q)
                threading.Thread(target=self.start_new_game, args=(distinct_queuers, GameTypesEnum.LUDO.value), daemon=True).start()
                time.sleep(1.5)
            else:
                time.sleep(4)

    def join_user(self, user_data: QueuerModel, game_type) -> bool:
        if not self.can_user_join_queue(user_data.user_id):
            return False
        if game_type == GameTypesEnum.LUDO.value:
            self.ludo_queuers.append(user_data)
            return True
        return False

    async def disconnect_user(self, socket_id):
        for user_data in list(self.ludo_queuers):
            if socket_id == user_data.socket_id:
                self.ludo_queuers.remove(user_data)
                break
