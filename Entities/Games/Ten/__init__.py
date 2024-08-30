import random

from Entities.Games.Ten.ten_games import ten_games_list
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands
from Entities.Games.game_rounds import Ten_Round_Count


class TenGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.rounds_list = []
        self.current_round_numbers = []
        self.round_count = Ten_Round_Count
        self.current_round = 1
        self.max_round = 3
        self.gamer1_score = 0
        self.gamer2_score = 0
        self.init_games()

    def init_games(self):
        indexes = []
        for i in range(3):
            random_number = random.randint(0, len(ten_games_list))
            if random_number not in indexes:
                indexes.append(random_number)
        for i in range(3):
            self.rounds_list.append(ten_games_list[indexes[i]])
        self.current_round_numbers = self.rounds_list[0]

    def get_game_data(self):
        data = {"scores": [self.gamer1_score, self.gamer2_score], "current_round": self.current_round,
                "current_numbers": self.current_round_numbers}
        return data

    def change_round(self):
        self.is_round_finished = False
        self.current_round_numbers = self.rounds_list[self.current_round]
        self.current_round += 1

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if gamer_id == 1:
            self.gamer1_score += 1
        else:
            self.gamer2_score += 1
        winner = gamer_id
        if self.check_game_ended():
            game_winner = self.get_game_winner()
            await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
            self.is_game_finished = True
        else:
            self.is_round_finished = True
            await self.send_data_function(commands.Finish_Round, {"Winner": winner})

    def round_time_finished(self):
        if self.current_round == self.round_count:
            self.is_game_finished = True
        else:
            self.is_round_finished = True

    def check_game_ended(self):
        if self.current_round == self.round_count:
            return True
        # if self.gamer1_score.__float__() >= self.round_count / 2
        return False

    def check_authority(self, data, gamer_id: int):
        # if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
        #     print("not turn of : ", gamer_id)
        #     return False
        # peace_number = data
        # # Check if players' selection is out of range
        # if peace_number < 0 or peace_number > 8:
        #     return False
        # Check if the square is already filled
        # if (self.board[peace_number] == self.symbol_1) or (self.board[peace_number] == self.symbol_2):
        #     return False

        if self.is_game_finished or self.is_round_finished:
            return False
        return True

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.gamer1_score > self.gamer2_score:
                winner = self.symbol_1
            elif self.gamer2_score > self.gamer1_score:
                winner = self.symbol_2
        return winner
