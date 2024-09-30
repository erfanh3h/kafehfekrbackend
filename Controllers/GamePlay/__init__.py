import asyncio
import random
import threading
import time

from Commons import commands
from Commons.static_functions import make_command_json
from Controllers.GamePlay.game_type_class_pairs import game_type_class_pairs
from Entities.Games.wait_times import Join_Game_Limit_Time, Start_Game_Time , Game_Play_Round_Time
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
        self.gamer1_score = 0
        self.gamer2_score = 0
        self.current_game_index = 0
        self.game_winners = []
        self.is_gamers_join_game = {}
        self.is_game_started = False
        self.is_game_running = False
        self.is_game_terminated = False
        self.is_game_finished = False
        self.active_game_id = ""
        self.score_manager = RewardManagerClass(game_score_type, 'game_id', 'game_type')

    def select_random_games(self):
        if self.game_score_type == GameScoreTypesEnum.NORMAL:
            games_length = 1
            self.game_winners = [-1]
        else:
            games_length = 3
            self.game_winners = [-1, -1, -1]
        games_types = []
        for i in range(games_length):
            random_type = random.choice(self.game_types)
            games_types.append(random_type)
            self.game_types.remove(random_type)
        self.game_types = games_types
        random.shuffle(self.game_types)

    def join_game_limit_time(self):
        if not self.is_game_started:
            self.is_game_terminated = True

    def start_game_timer(self):
        self.is_gamers_join_game[self.gamers[0].user_id] = False
        self.is_gamers_join_game[self.gamers[1].user_id] = False

        def entrypoint():
            self.check_start_game()

        self.timer.start(Join_Game_Limit_Time, self.join_game_limit_time)
        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_all_players_joined(self):
        for is_gamer_joined in self.is_gamers_join_game:
            if not is_gamer_joined:
                return False
        return True

    def send_game_play_data(self, socket_id):
        game_data = {'gamers': [], 'games': self.game_types, 'game_score_type': self.game_score_type.value,
                     'current_game_index': self.current_game_index, 'winners': self.game_winners,
                     'gamer1_score': self.gamer1_score, 'gamer2_score': self.gamer2_score,
                     'is_game_finished': self.is_game_finished, }
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
        def function():
            for gamer_data in self.gamers:
                self.navigate_to_game(gamer_data.socket_id)
            self.start_current_game()

        while True:
            if self.is_game_terminated:
                break
            if self.check_all_players_joined():
                time.sleep(3)
                self.is_game_started = True
                self.timer.stop()
                self.select_random_games()
                for gamer in self.gamers:
                    self.send_game_play_data(gamer.socket_id)
                self.timer.start(Start_Game_Time, function)
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
        game_type = self.game_types[self.current_game_index]
        self.game_session = game_type_class_pairs[game_type](game_id=self.game_play_id, game_type=game_type,
                                                             game_score_type=self.game_score_type)
        self.game_session.add_gamer(
            GamerModel(user_id=self.gamers[0].user_id, username=self.gamers[0].username,
                       user_image=self.gamers[0].user_image,
                       user_score=self.gamers[0].user_score, user_coin=self.gamers[0].user_coin))
        self.game_session.join_gamer(self.gamers[0].user_id, self.gamers[0].socket_id)
        self.game_session.add_gamer(
            GamerModel(user_id=self.gamers[1].user_id, username=self.gamers[1].username,
                       user_image=self.gamers[1].user_image,
                       user_score=self.gamers[1].user_score, user_coin=self.gamers[1].user_coin))
        self.game_session.join_gamer(self.gamers[1].user_id, self.gamers[1].socket_id)
        self.game_session.start_game_timer()

    def is_user_id_valid(self, user_id):
        for user_data in self.gamers:
            if user_data.user_id == user_id:
                return True
        return False

    def finish_current_game(self, user_id):
        def function():
            for gamer_data in self.gamers:
                self.navigate_to_game(gamer_data.socket_id)
            self.start_current_game()

        if user_id == self.gamers[0].user_id:
            self.gamer1_score += 1
            self.game_winners[self.current_game_index] = 1
        elif user_id == self.gamers[1].user_id:
            self.gamer2_score += 1
            self.game_winners[self.current_game_index] = 2
        else:
            self.game_winners[self.current_game_index] = 0
        self.current_game_index += 1
        if self.current_game_index >= len(self.game_types):
            print("game finished")
            self.is_game_finished = True
            for gamer in self.gamers:
                self.send_game_play_data(gamer.socket_id)
            from Entities.SocketIOClass.game import delete_game
            delete_game(self.game_play_id)
        else:
            for gamer in self.gamers:
                self.send_game_play_data(gamer.socket_id)
            self.timer.start(Game_Play_Round_Time, function)
            for gamer in self.gamers:
                self.send_timer_value(gamer.socket_id)

    def change_gamer_socket_id(self, user_id, socket_id):
        for gamer in self.gamers:
            if gamer.user_id == user_id:
                gamer.socket_id = socket_id
                break
