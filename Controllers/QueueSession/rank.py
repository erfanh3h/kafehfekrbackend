from Commons.static_functions import safe_run_async
import asyncio
import random
import sys
import threading
import time

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession import BaseQueueSession
from Controllers.QueueSession.pre_game import PreGameClass
from Entities.Database import game_database
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel


class RankQueueSession(BaseQueueSession):
    def __init__(self):
        super().__init__(GameScoreTypesEnum.RANK)
        self.queuers: list[QueuerModel] = []
        self.queuer_accept_pairs: dict[str, bool | None] = {}
        self.active_pre_games: dict[str, PreGameClass] = {}
        self.socket_id_pre_games_pairs: dict[str, str] = {}

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
        pre_game_id = data.get('pre_game_id', None)
        if pre_game_id is not None:  # commands received from pre game phase
            if pre_game_id not in self.active_pre_games.keys():
                return
            await self.active_pre_games[pre_game_id].command_received(data, socket_id)
            return
        # accept command
        user_id = data.get('user_id')
        if not user_id or user_id not in self.queuer_accept_pairs:
            return
        if data['id'] == commands.Accept:
            self.queuer_accept_pairs[user_id] = True
        if data['id'] == commands.Reject:
            self.queuer_accept_pairs[user_id] = False

    def delete_game(self, pre_game_id, dced_user, queuers):
        from Entities.SocketIOManagerClass import send_queue_command
        self.active_pre_games.pop(pre_game_id, None)
        for queuer_data in queuers:
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.Game_Canceled, data={}),
                                   socket_id=queuer_data.socket_id))

    def start_new_game(self, queuers, game_types, pre_game_id):
        if len(queuers) != 2:
            return
        self.socket_id_pre_games_pairs.pop(queuers[0].socket_id, None)
        self.socket_id_pre_games_pairs.pop(queuers[1].socket_id, None)
        from Entities.SocketIOManagerClass import send_queue_command
        game_id = static_functions.create_random_game_id()
        final_game_types = game_types
        # game_id = 'testgame'
        game_data = {'game_id': game_id}
        for queuer_data in queuers:
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.Start_Game, data=game_data),
                                   socket_id=queuer_data.socket_id))
            game_database.users_manager.update_user(queuer_data.user_id, open_game_id=game_id, open_pre_game_id="")
        self.active_pre_games.pop(pre_game_id, None)
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

    def start_new_pre_game(self, queuers):
        if len(queuers) != 2:
            return
        pre_game_id = static_functions.create_random_game_id()
        queurs_data = []
        for queuer_data in queuers:
            queurs_data.append(queuer_data.to_json())
        game_data = {'id': pre_game_id, 'queuers': queurs_data}
        from Entities.SocketIOManagerClass import enter_pre_game, send_queue_command
        for queuer_data in queuers:
            self.socket_id_pre_games_pairs[queuer_data.socket_id] = pre_game_id
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.Start_Pre_Game, data=game_data),
                                   socket_id=queuer_data.socket_id))
            safe_run_async(
                enter_pre_game(socket_id=queuer_data.socket_id, pre_game_id=pre_game_id))
        self.active_pre_games[pre_game_id] = PreGameClass(pre_game_id, queuers, self.start_new_game, self.delete_game)
        self.active_pre_games[pre_game_id].start_pre_game()

    def start_pre_game_timer(self, queuers):
        queuer1_id = queuers[0].user_id
        queuer2_id = queuers[1].user_id
        self.queuer_accept_pairs[queuer1_id] = None
        self.queuer_accept_pairs[queuer2_id] = None
        from Entities.SocketIOManagerClass import send_queue_command
        for user_data in queuers:
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.AcceptGame, data={}),
                                   socket_id=user_data.socket_id))

        def start_game():
            time.sleep(1)
            for queuer_data in queuers:
                self.queuer_accept_pairs.pop(queuer_data.user_id, None)
            threading.Thread(target=self.start_new_pre_game, args=(queuers,), daemon=True).start()

        def cancel_game():
            from Entities.SocketIOManagerClass import send_queue_command
            for queuer_data in queuers:
                safe_run_async(
                    send_queue_command(command=make_command_json(id=commands.Game_Canceled, data={}),
                                       socket_id=queuer_data.socket_id))
                self.queuer_accept_pairs.pop(queuer_data.user_id, None)

        def let_game_start():
            if self.queuer_accept_pairs.get(queuer1_id) and self.queuer_accept_pairs.get(queuer2_id):
                return True
            if self.queuer_accept_pairs.get(queuer1_id) == False or self.queuer_accept_pairs.get(queuer2_id) == False:
                return False
            return None

        def entrypoint():
            timer_counter = 0
            while True:
                start_game_status = let_game_start()
                if start_game_status:
                    start_game()
                    break
                elif start_game_status == False or timer_counter == 20:
                    cancel_game()
                    break
                time.sleep(1)
                timer_counter += 1

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_new_game(self):
        while True:
            if len(self.queuers) > 0:
                print(f"{self.game_score_type} queuer len : ", len(self.queuers))
            if len(self.queuers) >= 2:
                q1 = self.queuers.pop(0)
                q2 = self.queuers.pop(0)
                self.start_pre_game_timer([q1, q2])
                time.sleep(1.5)
            else:
                time.sleep(3)

    def join_queuer(self, user_data: QueuerModel):
        if user_data.user_id in self.queuer_accept_pairs:  # prevent join when waiting for user accept
            return
        self.queuers.append(user_data)

    def reconnect_queuer(self, pre_game_id, user_data: QueuerModel):
        from Entities.SocketIOManagerClass import send_queue_command, enter_pre_game
        if pre_game_id not in self.active_pre_games.keys():
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.Game_Finished, data={}),
                                   socket_id=user_data.socket_id))
            game_database.users_manager.update_user(user_data.user_id, open_pre_game_id="")
            return
        self.socket_id_pre_games_pairs[user_data.socket_id] = pre_game_id
        self.active_pre_games[pre_game_id].reconnect_user(user_data.socket_id, user_data.user_id)
        safe_run_async(
            enter_pre_game(socket_id=user_data.socket_id, pre_game_id=pre_game_id))
        data = self.active_pre_games[pre_game_id].get_reconnect_data()
        safe_run_async(
            send_queue_command(command=make_command_json(id=commands.Reconnect_Data, data=data),
                               socket_id=user_data.socket_id))

    async def disconnect_user(self, socket_id):
        if socket_id not in self.socket_id_pre_games_pairs:
            for user_data in list(self.queuers):
                if socket_id == user_data.socket_id:
                    self.queuers.remove(user_data)
                    break
            return
        game_id = self.socket_id_pre_games_pairs[socket_id]
        if game_id in self.active_pre_games:
            self.active_pre_games[game_id].disconnect_user(socket_id)
        for user_data in list(self.queuers):
            if socket_id == user_data.socket_id:
                self.queuers.remove(user_data)
                break
