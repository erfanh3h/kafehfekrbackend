import asyncio
import threading
import time

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
        if pre_game_id is not None:  # commands recieed from pre game phase
            if pre_game_id not in self.active_pre_games.keys():
                return
            await self.active_pre_games[pre_game_id].command_received(data, socket_id)
            return
        # accept command
        user_id = data['user_id']
        if not self.queuer_accept_pairs.keys().__contains__(user_id):
            return
        if data['id'] == commands.Accept:
            self.queuer_accept_pairs[user_id] = True
        if data['id'] == commands.Reject:
            self.queuer_accept_pairs[user_id] = False

    def start_new_game(self, queuers, game_types):
        if len(queuers) != 2:
            return
        del self.socket_id_pre_games_pairs[queuers[0].socket_id]
        del self.socket_id_pre_games_pairs[queuers[1].socket_id]
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
            asyncio.new_event_loop().run_until_complete(
                send_queue_command(command=make_command_json(id=commands.Start_Pre_Game, data=game_data),
                                   socket_id=queuer_data.socket_id))
            asyncio.new_event_loop().run_until_complete(
                enter_pre_game(socket_id=queuer_data.socket_id, pre_game_id=pre_game_id))
        self.active_pre_games[pre_game_id] = PreGameClass(pre_game_id, queuers, self.start_new_game)
        self.active_pre_games[pre_game_id].start_pre_game()

    def start_pre_game_timer(self, queuers):
        queuer1_id = queuers[0].user_id
        queuer2_id = queuers[1].user_id
        self.queuer_accept_pairs[queuer1_id] = None
        self.queuer_accept_pairs[queuer2_id] = None
        from Entities.SocketIOManagerClass import send_queue_command
        for user_data in queuers:
            asyncio.new_event_loop().run_until_complete(
                send_queue_command(command=make_command_json(id=commands.AcceptGame, data={}),
                                   socket_id=user_data.socket_id))

        def start_game():
            time.sleep(1)
            for queuer_data in queuers:
                del self.queuer_accept_pairs[queuer_data.user_id]
            threading.Thread(target=self.start_new_pre_game, args=(queuers,), daemon=True).start()

        def cancel_game():
            from Entities.SocketIOManagerClass import send_queue_command
            for queuer_data in queuers:
                asyncio.new_event_loop().run_until_complete(
                    send_queue_command(command=make_command_json(id=commands.Game_Canceled, data={}),
                                       socket_id=queuer_data.socket_id))
                del self.queuer_accept_pairs[queuer_data.user_id]

        def let_game_start():
            if self.queuer_accept_pairs[queuer1_id] and self.queuer_accept_pairs[queuer2_id]:
                return True
            if self.queuer_accept_pairs[queuer1_id] == False or self.queuer_accept_pairs[queuer2_id] == False:
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
                self.start_pre_game_timer(self.queuers[0:2])
                self.queuers.pop(0)
                self.queuers.pop(0)
                time.sleep(1.5)
            else:
                time.sleep(4)

    def join_queuer(self, user_data: QueuerModel):
        if self.queuer_accept_pairs.keys().__contains__(user_data.user_id):  # prevent join when waiting for user accept
            return
        self.queuers.append(user_data)

    def reconnect_queuer(self, pre_game_id, user_data: QueuerModel):
        from Entities.SocketIOManagerClass import send_queue_command, enter_pre_game
        if pre_game_id not in self.active_pre_games.keys():
            asyncio.new_event_loop().run_until_complete(
                send_queue_command(command=make_command_json(id=commands.Game_Finished, data={}),
                                   socket_id=user_data.socket_id))
            game_database.users_manager.update_user(user_data.user_id, open_pre_game_id="")
            return
        self.socket_id_pre_games_pairs[user_data.socket_id] = pre_game_id
        self.active_pre_games[pre_game_id].reconnect_user(user_data.socket_id, user_data.user_id)
        asyncio.new_event_loop().run_until_complete(
            enter_pre_game(socket_id=user_data.socket_id, pre_game_id=pre_game_id))
        data = self.active_pre_games[pre_game_id].get_reconnect_data()
        asyncio.new_event_loop().run_until_complete(
            send_queue_command(command=make_command_json(id=commands.Reconnect_Data, data=data),
                               socket_id=user_data.socket_id))

    async def disconnect_user(self, socket_id):
        if not self.socket_id_pre_games_pairs.keys().__contains__(socket_id):
            for user_data in self.queuers:
                if socket_id == user_data.socket_id:
                    self.queuers.remove(user_data)
                    break
            return
        game_id = self.socket_id_pre_games_pairs[socket_id]
        self.active_pre_games[game_id].disconnect_user(socket_id)
        for user_data in self.queuers:
            if socket_id == user_data.socket_id:
                self.queuers.remove(user_data)
                break
