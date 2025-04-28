import random

from Commons import commands
from Commons.static_functions import make_command_json
from Entities.Games.game_types import GameTypesEnum
from Entities.TimerClass import TimerClass
from Models.Queuer import QueuerModel


class PreGameClass:
    def __init__(self, pre_game_id: str, queuers, start_game_function):
        self.timer = TimerClass()
        self.start_game_function = start_game_function
        self.pre_game_id: str = pre_game_id
        self.active_game_types = []
        self.game_types = []
        self.queuers: list[QueuerModel] = queuers
        self.pre_bans: list[GameTypesEnum] = []
        self.system_selected_game: GameTypesEnum = None
        self.select_turn_index = 0

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

    def to_json(self):
        data = {'pre_game_id': self.pre_game_id, 'pre_game_name': self.pre_game_name, 'creator_id': self.creator_id,
                'game_types': self.game_types, 'queuers_length': len(self.queuers)}
        return data

    def to_complete_json(self):
        data = {'pre_game_id': self.pre_game_id, 'pre_game_name': self.pre_game_name, 'creator_id': self.creator_id,
                'game_types': self.game_types, }
        queuer_data = []
        # for queuer in self.queuers:
        #     queuer_data.append(queuer.to_pre_game_json())
        data['queuers'] = queuer_data
        return data

    def start_pre_game(self):
        self.pre_bans = random.sample(list(GameTypesEnum), 3)  # randomly ban 3 games
        self.active_game_types = [game for game in GameTypesEnum if game not in self.pre_bans]
        self.timer.start(5, self.send_current_turn)

    async def command_received(self, data, socket_id):
        from Entities.SocketIOManagerClass import send_pre_game_command
        gamer_data = self.find_gamer_from_socket_id(socket_id)
        user_id = gamer_data.user_id
        if data['id'] == commands.Select_Game:
            if gamer_data.selected_game is not None:
                return
            if self.select_turn_index == 3 and self.queuers[0].selected_game is not None:
                return
            if self.select_turn_index == 4 and self.queuers[1].selected_game is not None:
                return
            gamer_data.selected_game = data['game_type']
            await send_pre_game_command(command=make_command_json(id=commands.Select_Game,
                                                                  data={'user_id': user_id,
                                                                        'game_type': data['game_type']}),
                                        pre_game_id=self.pre_game_id)
            self.timer.stop()
        if data['id'] == commands.Ban_Game:
            if len(gamer_data.banned_games) > 2:
                return
            if self.select_turn_index == 1 and len(self.queuers[0].banned_games) != 0:
                return
            if self.select_turn_index == 2 and len(self.queuers[1].banned_games) != 0:
                return
            if self.select_turn_index == 5 and len(self.queuers[0].banned_games) != 1:
                return
            if self.select_turn_index == 6 and len(self.queuers[1].banned_games) != 1:
                return
            gamer_data.banned_games.append(data['game_type'])
            await send_pre_game_command(command=make_command_json(id=commands.Ban_Game,
                                                                  data={'user_id': user_id,
                                                                        'game_type': data['game_type']}),
                                        pre_game_id=self.pre_game_id)
            self.timer.stop()

    def send_current_turn(self):
        if self.select_turn_index == 0:
            self.select_turn_index += 1
            self.timer.start(25, self.send_current_turn)
        elif self.select_turn_index == 6:  # last turn
            self.start_game_function(self.queuers, [self.queuers[0].selected_game, self.queuers[1].selected_game,
                                                    self.system_selected_game])

        else:
            self.select_turn_index += 1
            self.timer.start(25, self.send_current_turn)
