import asyncio
import random
import threading
import time

from Commons import commands
from Commons.static_functions import make_command_json
from Controllers.GamePlay.game_type_class_pairs import game_type_class_pairs
from Entities.Games.wait_times import Join_Game_Limit_Time, Start_Game_Time, Game_Play_Round_Time
from Entities.RewardManagerClass import RewardManagerClass, GameScoreTypesEnum
from Entities.TimerClass import TimerClass
from Models.Gamer import GamerModel


class BaseGamePlayClass:
    def __init__(self, game_play_id, gamers, game_types, game_score_type):
        self.timer = TimerClass()
        self.game_play_id = game_play_id
        self.gamers = gamers
        self.game_types = game_types
        self.game_score_type = game_score_type
        self.game_session = None
        self.gamer_scores = [0 for g in gamers]
        # self.gamer1_score = 0
        # self.gamer2_score = 0
        self.current_game_index = 0
        self.game_winners = []
        self.is_gamers_join_game = {}
        self.is_game_started = False
        self.is_game_running = False
        self.is_game_terminated = False
        self.is_game_finished = False
        self.active_game_id = ""
        self.game_winner_id = None
        self.score_manager = RewardManagerClass(game_score_type)

    def select_random_games(self):
        if self.game_score_type == GameScoreTypesEnum.RANK:
            games_length = 3
            self.game_winners = [-1, -1, -1]
        else:
            games_length = 1
            self.game_winners = [-1]
        games_types = []
        for i in range(games_length):
            random_type = random.choice(self.game_types)
            games_types.append(random_type)
            self.game_types.remove(random_type)
        self.game_types = games_types
        random.shuffle(self.game_types)

    def prepare_database(self):
        from Entities.Database import game_database
        user_idis = [g.user_id for g in self.gamers]
        self.score_manager.set_user_data(user_idis)
        game_database.game_play_history_manager.delete_game_play_history(self.game_play_id)
        game_database.game_play_history_manager.create_game_play_history(self.game_play_id, user_idis, self.game_types,
                                                                         str(self.game_score_type.value))
        for user_id in user_idis:
            game_database.users_manager.update_user(user_id, open_game_id=self.game_play_id, )
        # if self.game_score_type == GameScoreTypesEnum.RANK: #TODO : return this for coin
        #     game_database.users_manager.update_user(self.gamers[0].user_id, open_game_id=self.game_play_id,
        #                                             coin=self.gamers[0].user_coin - rank_coin_cost)
        #     game_database.users_manager.update_user(self.gamers[1].user_id, open_game_id=self.game_play_id,
        #                                             coin=self.gamers[1].user_coin - rank_coin_cost)
        # else:
        #     game_database.users_manager.update_user(self.gamers[0].user_id, open_game_id=self.game_play_id, )
        #     game_database.users_manager.update_user(self.gamers[1].user_id, open_game_id=self.game_play_id, )

    def join_game_limit_time(self):
        if not self.is_game_started:
            self.is_game_terminated = True

    def start_game_timer(self):
        user_idis = [g.user_id for g in self.gamers]
        for user_id in user_idis:
            if str(user_id).startswith("bot_"):
                self.is_gamers_join_game[user_id] = True
            else:
                self.is_gamers_join_game[user_id] = False

        def entrypoint():
            self.check_start_game()

        self.timer.start(Join_Game_Limit_Time, self.join_game_limit_time)
        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_all_players_joined(self):
        for is_gamer_joined in self.is_gamers_join_game.values():
            if not is_gamer_joined:
                return False
        return True

    def send_game_play_data(self, socket_id, xp_gained: int = 0):
        game_data = {'gamers': [], 'games': self.game_types, 'game_score_type': self.game_score_type.value,
                     'current_game_index': self.current_game_index, 'winners': self.game_winners,
                     'is_game_finished': self.is_game_finished, 'scores': self.gamer_scores,
                     'game_winner_id': self.game_winner_id, 'xp_gained': xp_gained}
        for gamer in self.gamers:
            game_data['gamers'].append(gamer.to_json())
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=commands.Game_Play_Data, data=game_data),
                                 game_id=self.game_play_id, socket_id=socket_id))

    def navigate_to_game(self, socket_id):
        game_data = {'current_game_index': self.current_game_index}
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=commands.Game_Play_Navigate, data=game_data),
                                 game_id=self.game_play_id, socket_id=socket_id))

    def send_timer_value(self, socket_id):
        data = {'time': self.timer.counter + 1}
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=commands.Game_Play_Time, data=data),
                                 game_id=self.game_play_id, socket_id=socket_id))

    def check_start_game(self):
        def start_new_game_function():
            for gamer_data in self.gamers:
                self.navigate_to_game(gamer_data.socket_id)
            self.start_current_game()

        while True:
            if self.is_game_terminated:
                self.is_game_finished = True
                from Entities.SocketIOClass.game import delete_game
                delete_game(self.game_play_id)
                break
            if self.check_all_players_joined():
                time.sleep(3)
                self.is_game_started = True
                self.timer.stop()
                self.select_random_games()
                self.prepare_database()
                for gamer in self.gamers:
                    self.send_game_play_data(gamer.socket_id)
                self.timer.start(Start_Game_Time, start_new_game_function)
                for gamer in self.gamers:
                    self.send_timer_value(gamer.socket_id)
                break
            time.sleep(2)

    def join_gamer(self, user_id, socket_id):
        self.change_gamer_socket_id(user_id, socket_id)
        if self.is_game_started:
            self.send_game_play_data(socket_id)
            if self.game_session is not None:
                self.navigate_to_game(socket_id)
                self.game_session.join_gamer(user_id, socket_id)
        else:
            self.is_gamers_join_game[user_id] = True

    async def command_received(self, data, socket_id):
        if self.game_session is not None:
            await self.game_session.command_received(data, socket_id)

    def disconnect_user(self, socket_id):
        if self.game_session is not None:
            self.game_session.disconnect_user(socket_id)

    async def reaction_received(self, data, socket_id):
        await self.game_session.reaction_received(data, socket_id)

    def start_current_game(self):
        if self.is_game_finished or self.current_game_index >= len(self.game_types):
            return
        game_type = self.game_types[self.current_game_index]
        self.game_session = game_type_class_pairs[game_type](game_id=self.game_play_id, game_type=game_type,
                                                             game_score_type=self.game_score_type)
        for gamer in self.gamers:
            self.game_session.add_gamer(
                GamerModel(user_id=gamer.user_id, username=gamer.username, user_image=gamer.user_image,
                           user_score=gamer.user_score, user_coin=gamer.user_coin))
            self.game_session.join_gamer(gamer.user_id, gamer.socket_id)
        if self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            from Entities.Bots.bot_controller import BotController
            bot_gamer = None
            for g in self.game_session.gamers:
                if str(g.user_id).startswith("bot_"):
                    bot_gamer = g
                    break
            if bot_gamer:
                self.game_session.bot_controller = BotController(
                    game_session=self.game_session,
                    bot_user_id=bot_gamer.user_id,
                    bot_gamer_id=bot_gamer.gamer_id if hasattr(bot_gamer, "gamer_id") else 2,
                    game_type=game_type,
                    level=2
                )
        self.game_session.start_game_timer()

    def is_user_id_valid(self, user_id):
        for user_data in self.gamers:
            if user_data.user_id == user_id:
                return True
        return False

    def check_is_game_finished(self):
        for index, gamer_score in enumerate(self.gamer_scores):
            if len(self.game_types) == 1 and gamer_score == 1:
                return True, self.gamers[index].user_id
            if len(self.game_types) == 3 and gamer_score >= 2:
                return True, self.gamers[index].user_id
        if self.current_game_index >= len(self.game_types):
            if len(self.gamer_scores) >= 2:
                if self.gamer_scores[0] > self.gamer_scores[1]:
                    return True, self.gamers[0].user_id
                elif self.gamer_scores[1] > self.gamer_scores[0]:
                    return True, self.gamers[1].user_id
            return True, 0
        return False, None

    def finish_current_game(self, currnet_game_winner_id):
        if self.is_game_finished:
            return

        def start_new_game_function():
            if self.is_game_finished or self.current_game_index >= len(self.game_types):
                return
            for gamer_data in self.gamers:
                self.navigate_to_game(gamer_data.socket_id)
            self.start_current_game()

        winner_index = self.user_id_to_index(currnet_game_winner_id)
        if self.current_game_index < len(self.game_winners):
            if winner_index != -1:  # prevent drow
                self.gamer_scores[winner_index] += 1
                self.game_winners[self.current_game_index] = winner_index + 1
            else:
                self.game_winners[self.current_game_index] = 0
        self.current_game_index += 1
        is_game_finished, winner_id = self.check_is_game_finished()
        if is_game_finished:
            self.finish_game_play(winner_id)
        else:
            for gamer in self.gamers:
                self.send_game_play_data(gamer.socket_id)
            self.timer.start(Game_Play_Round_Time, start_new_game_function)
            for gamer in self.gamers:
                self.send_timer_value(gamer.socket_id)

    def finish_multiplayer_game(self, rank1_id, rank2_id):
        self.game_winners = []
        rank1_index = self.user_id_to_index(rank1_id)
        if rank1_index != -1:
            self.gamer_scores[rank1_index] = 2
            self.game_winners.append(rank1_index + 1)
        rank2_index = self.user_id_to_index(rank2_id)
        if rank2_index != -1:
            self.gamer_scores[rank2_index] = 1
            self.game_winners.append(rank2_index + 1)
        from Entities.Database import game_database
        finished_game_types = [self.game_types[0]]
        xp_gained = self.score_manager.finish_multiplayer_game(rank1_id, rank2_id, finished_game_types) or 0
        game_database.game_play_history_manager.update_game_play_history(self.game_play_id, self.game_winners,
                                                                         self.gamer_scores)
        self.is_game_finished = True
        for gamer in self.gamers:
            self.send_game_play_data(gamer.socket_id, xp_gained=xp_gained)
        from Entities.SocketIOClass.game import delete_game
        delete_game(self.game_play_id)

    def change_gamer_socket_id(self, user_id, socket_id):
        for gamer in self.gamers:
            if gamer.user_id == user_id:
                gamer.socket_id = socket_id
                break

    def finish_game_play(self, winner_id):
        from Entities.Database import game_database
        finished_game_types = []
        finished_game_winners = []
        for index, item in enumerate(self.game_types):
            if self.game_winners[index] != -1:
                finished_game_types.append(item)
                finished_game_winners.append(self.game_winners[index])
        xp_gained = self.score_manager.finish_game(winner_id, finished_game_types, finished_game_winners) or 0
        game_database.game_play_history_manager.update_game_play_history(self.game_play_id, self.game_winners,
                                                                         self.gamer_scores)
        self.is_game_finished = True
        self.game_winner_id = winner_id
        for gamer in self.gamers:
            self.send_game_play_data(gamer.socket_id, xp_gained=xp_gained)
        from Entities.SocketIOClass.game import delete_game
        delete_game(self.game_play_id)

    def user_id_to_index(self, user_id):
        for index, gamer in enumerate(self.gamers):
            if gamer.user_id == user_id:
                return index
        return -1  # -1 for draw
