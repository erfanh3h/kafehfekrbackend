import random

from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.Risk.models import RiskContinentModel, RiskStrategyModel
from Entities.Games.Risk.user_spot import UserSpotClass
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass


def roll_dice(dice_count):
    result = []
    for i in range(dice_count):
        result.append(random.randint(1, 6))
    return result


class RiskGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count=2):
        super().__init__(send_data_function, players_count)
        self.strategies: list[RiskStrategyModel] = []
        self.continents: list[RiskContinentModel] = []
        self.tokens: list[RiskContinentModel] = []
        self.init_cards()
        self.players_data: list[UserSpotClass] = []
        self.init_game()
        self.current_turn = 1

    def init_cards(self):
        for _ in range(18):
            self.strategies.append(RiskStrategyModel.ARMY)
        for _ in range(4):
            self.strategies.append(RiskStrategyModel.BACKUP)
            self.strategies.append(RiskStrategyModel.BOMB)
            self.strategies.append(RiskStrategyModel.DESTROY)
        for _ in range(3):
            self.strategies.append(RiskStrategyModel.CANCEL)
            self.strategies.append(RiskStrategyModel.CANON)
        for _ in range(2):
            self.strategies.append(RiskStrategyModel.EXPAND)
            self.strategies.append(RiskStrategyModel.SPY)
        for _ in range(12):
            self.continents.append(RiskContinentModel.ASIA)
        for _ in range(9):
            self.continents.append(RiskContinentModel.ASIA)
        for _ in range(7):
            self.continents.append(RiskContinentModel.EUROPE)
        for _ in range(6):
            self.continents.append(RiskContinentModel.AFRICA)
        for _ in range(4):
            self.continents.append(RiskContinentModel.AUSTRALIA)
            self.continents.append(RiskContinentModel.SOUTHAMERICA)
        for continent in RiskContinentModel.all():
            self.tokens.append(continent.value)
        for _ in range(5):
            random.shuffle(self.strategies)
            random.shuffle(self.continents)

    def init_game(self):
        for index in range(self.players_count):
            self.players_data.append(UserSpotClass(index + 1))
            self.active_player_indexes.append(index + 1)
        for index, player_data in enumerate(self.players_data):
            for _ in range(3):
                continent = self.continents.pop()
                strategy = self.strategies.pop()
                player_data.add_continent(continent)
                player_data.add_strategy(strategy)
            if index != 0:
                strategy = self.strategies.pop()
                player_data.add_strategy(strategy)
        for index, player_data in enumerate(self.players_data):
            print(index, player_data.continents, player_data.strategies)

    def get_game_data(self):
        players_data = []
        for player_data in self.players_data:
            players_data.append(player_data.to_global_json())

        data = {"current_turn": self.current_turn, "active_player_indexes": self.active_player_indexes,
                'rank1': self.rank1, 'strategies': len(self.strategies), 'continents': len(self.continents),
                'players_data': players_data, 'tokens': len(self.tokens)}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        # print("here",command_id, data, gamer_id)
        if command_id == commands.Draw_Card:
            self.draw_card(data['draw_type'])

        elif command_id == commands.Pass_Turn:
            self.draw_card(4)
        return True

    def change_turn(self):
        self.is_current_turn_played = False
        super().change_turn()

    def get_game_winner(self):
        return 0

    def draw_card(self, draw_type):
        if draw_type == 1:
            continent = self.continents.pop()
            self.players_data[self.current_turn - 1].add_continent(continent)
            continent = self.continents.pop()
            self.players_data[self.current_turn - 1].add_continent(continent)
        elif draw_type == 2:
            strategy = self.strategies.pop()
            self.players_data[self.current_turn - 1].add_strategy(strategy)
            strategy = self.strategies.pop()
            self.players_data[self.current_turn - 1].add_strategy(strategy)
        elif draw_type == 3:
            continent = self.continents.pop()
            self.players_data[self.current_turn - 1].add_continent(continent)
            strategy = self.strategies.pop()
            self.players_data[self.current_turn - 1].add_strategy(strategy)
        elif draw_type == 4:  # for pass turn
            strategy = self.strategies.pop()
            self.players_data[self.current_turn - 1].add_strategy(strategy)

    def check_authority(self, data, gamer_id: int):
        # if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2) or (
        #         self.current_turn == 3 and gamer_id != 3) or (self.current_turn == 4 and gamer_id != 4):
        #     print("not turn of : ", gamer_id)
        #     return False
        # if self.is_game_finished:
        #     return False
        return True
