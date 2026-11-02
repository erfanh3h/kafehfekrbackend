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
        self.accept_phase_sockets: dict[str, str] = {}
        self.active_pre_games: dict[str, PreGameClass] = {}
        self.socket_id_pre_games_pairs: dict[str, str] = {}

    def find_gamer_from_user_id(self, user_id):
        for queuer in self.queuers:
            if str(queuer.user_id) == str(user_id):
                return queuer
        return None

    def find_gamer_from_socket_id(self, socket_id):
        if not socket_id:
            return None
        for queuer in self.queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def find_active_pre_game_for_user(self, user_id):
        for pg_id, pg in list(self.active_pre_games.items()):
            q = pg.find_gamer_from_user_id(user_id)
            if q is not None:
                return pg_id, pg, q
        return None, None, None

    def is_user_in_accept_phase(self, user_id) -> bool:
        return any(str(uid) == str(user_id) for uid in self.queuer_accept_pairs.keys())

    def has_active_ongoing_game(self, user_id) -> bool:
        try:
            from Entities.SocketIOClass.game import games
            for g_id, game_play in list(games.items()):
                if not getattr(game_play, "is_game_finished", False) and not getattr(game_play, "is_game_terminated", False):
                    if game_play.is_user_id_valid(user_id):
                        return True
        except Exception:
            pass
        return False

    def can_user_join_queue(self, user_id) -> bool:
        # Reject if already in queue
        if self.find_gamer_from_user_id(user_id) is not None:
            return False
        # Reject if waiting for match accept
        if self.is_user_in_accept_phase(user_id):
            return False
        # Reject if in an active pre-game draft
        pg_id, pg, q = self.find_active_pre_game_for_user(user_id)
        if pg is not None:
            return False
        # Reject if in an active ongoing game
        if self.has_active_ongoing_game(user_id):
            return False
        return True

    def can_user_reconnect_pre_game(self, pre_game_id, user_id, socket_id) -> bool:
        if not pre_game_id or pre_game_id not in self.active_pre_games:
            return False
        pg = self.active_pre_games[pre_game_id]
        return pg.can_user_reconnect(user_id, socket_id)

    async def command_received(self, data, socket_id):
        if not isinstance(data, dict):
            return
        pre_game_id = data.get('pre_game_id', None)
        if pre_game_id is not None:  # commands received from pre game phase
            if pre_game_id not in self.active_pre_games.keys():
                return
            if self.socket_id_pre_games_pairs.get(socket_id) != pre_game_id:
                return
            await self.active_pre_games[pre_game_id].command_received(data, socket_id)
            return
        # accept command: verify that socket_id matches the player in the accept phase
        matched_uid = None
        for uid_key, expected_sid in list(self.accept_phase_sockets.items()):
            if expected_sid == socket_id:
                matched_uid = uid_key
                break
        if matched_uid is None or matched_uid not in self.queuer_accept_pairs:
            return
        if data.get('id') == commands.Accept:
            self.queuer_accept_pairs[matched_uid] = True
        if data.get('id') == commands.Reject:
            self.queuer_accept_pairs[matched_uid] = False

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
        self.accept_phase_sockets[queuer1_id] = queuers[0].socket_id
        self.accept_phase_sockets[queuer2_id] = queuers[1].socket_id
        from Entities.SocketIOManagerClass import send_queue_command
        for user_data in queuers:
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.AcceptGame, data={}),
                                   socket_id=user_data.socket_id))

        def start_game():
            time.sleep(1)
            for queuer_data in queuers:
                self.queuer_accept_pairs.pop(queuer_data.user_id, None)
                self.accept_phase_sockets.pop(queuer_data.user_id, None)
            threading.Thread(target=self.start_new_pre_game, args=(queuers,), daemon=True).start()

        def cancel_game():
            from Entities.SocketIOManagerClass import send_queue_command
            for queuer_data in queuers:
                safe_run_async(
                    send_queue_command(command=make_command_json(id=commands.Game_Canceled, data={}),
                                       socket_id=queuer_data.socket_id))
                self.queuer_accept_pairs.pop(queuer_data.user_id, None)
                self.accept_phase_sockets.pop(queuer_data.user_id, None)

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
                q2 = None
                for idx, candidate in enumerate(self.queuers):
                    if str(candidate.user_id) != str(q1.user_id):
                        q2 = self.queuers.pop(idx)
                        break
                if q2 is not None:
                    self.start_pre_game_timer([q1, q2])
                    time.sleep(1.0)
                else:
                    self.queuers.insert(0, q1)
                    time.sleep(1.0)
            else:
                time.sleep(1.0)

    def join_queuer(self, user_data: QueuerModel) -> bool:
        if not self.can_user_join_queue(user_data.user_id):
            return False
        self.queuers.append(user_data)
        return True

    def reconnect_queuer(self, pre_game_id, user_data: QueuerModel) -> bool:
        from Entities.SocketIOManagerClass import send_queue_command, enter_pre_game
        if pre_game_id not in self.active_pre_games.keys():
            safe_run_async(
                send_queue_command(command=make_command_json(id=commands.Game_Finished, data={}),
                                   socket_id=user_data.socket_id))
            game_database.users_manager.update_user(user_data.user_id, open_pre_game_id="")
            return False
        pg = self.active_pre_games[pre_game_id]
        if not pg.can_user_reconnect(user_data.user_id, user_data.socket_id):
            return False
        # Remove any stale socket mapping for this user in this pre-game
        existing_q = pg.find_gamer_from_user_id(user_data.user_id)
        if existing_q is not None and existing_q.socket_id and existing_q.socket_id != user_data.socket_id:
            self.socket_id_pre_games_pairs.pop(existing_q.socket_id, None)
        self.socket_id_pre_games_pairs[user_data.socket_id] = pre_game_id
        pg.reconnect_user(user_data.socket_id, user_data.user_id)
        safe_run_async(
            enter_pre_game(socket_id=user_data.socket_id, pre_game_id=pre_game_id))
        data = pg.get_reconnect_data()
        safe_run_async(
            send_queue_command(command=make_command_json(id=commands.Reconnect_Data, data=data),
                               socket_id=user_data.socket_id))
        return True

    async def disconnect_user(self, socket_id):
        # If disconnecting during accept phase, mark as rejected so opponent does not hang
        for uid_key, expected_sid in list(self.accept_phase_sockets.items()):
            if expected_sid == socket_id:
                if uid_key in self.queuer_accept_pairs:
                    self.queuer_accept_pairs[uid_key] = False
                self.accept_phase_sockets.pop(uid_key, None)
        if socket_id not in self.socket_id_pre_games_pairs:
            for user_data in list(self.queuers):
                if socket_id == user_data.socket_id:
                    self.queuers.remove(user_data)
                    break
            return
        game_id = self.socket_id_pre_games_pairs.pop(socket_id, None)
        if game_id in self.active_pre_games:
            self.active_pre_games[game_id].disconnect_user(socket_id)
        for user_data in list(self.queuers):
            if socket_id == user_data.socket_id:
                self.queuers.remove(user_data)
                break
