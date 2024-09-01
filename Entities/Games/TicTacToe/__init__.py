from Entities.Games.base_game_class import BaseGameClass
from Commons import commands
from Entities.Games.game_rounds import TicTacToe_Round_Count


class TicTacToeGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [0 for i in range(9)]
        self.win_conditions = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]
        self.counter = 0
        self.round_count = TicTacToe_Round_Count
        self.current_round = 1
        self.gamer1_score = 0
        self.gamer2_score = 0
        self.round_winner = 0

    def get_game_data(self):
        data = {"board": self.board, "scores": [self.gamer1_score, self.gamer2_score],
                "current_round": self.current_round, "current_turn": self.current_turn}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        peace_number = data
        self.counter += 1
        if gamer_id == 1:
            self.board[peace_number] = self.symbol_1
        else:
            self.board[peace_number] = self.symbol_2
        await self.send_data_function(commands.Peace_Selected, {'user': gamer_id, 'target_peace': peace_number})
        winner = self.check_winner()
        if winner is not None or self.counter == 9:
            if self.check_game_ended():
                # game_winner = self.get_game_winner()
                # await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
                self.is_game_finished = True
            else:
                self.is_round_finished = True
                # await self.send_data_function(commands.Finish_Round, {"Winner": winner})

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            return False
        peace_number = data
        # Check if players' selection is out of range
        if peace_number < 0 or peace_number > 8:
            return False
            # Check if the square is already filled
        if (self.board[peace_number] == self.symbol_1) or (self.board[peace_number] == self.symbol_2):
            return False

        if self.is_game_finished or self.is_round_finished:
            return False
        return True

    def check_winner(self):
        winner = None
        for condition in self.win_conditions:
            if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_1:
                winner = self.symbol_1
                self.gamer1_score += 1
                self.round_winner = winner
                break
            if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_2:
                winner = self.symbol_2
                self.gamer2_score += 1
                self.round_winner = winner
                break
        return winner

    def check_game_ended(self):
        if self.current_round == self.round_count:
            return True
        if self.gamer1_score == 3 or self.gamer2_score == 3:
            return True
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.gamer1_score > self.gamer2_score:
                winner = self.symbol_1
            elif self.gamer2_score > self.gamer1_score:
                winner = self.symbol_2
        return winner

    def is_game_finished(self):
        pass

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = 2
        else:
            self.current_turn = 1

    def change_round(self):
        self.current_round += 1
        self.is_round_finished = False
        self.round_winner = 0
        self.board = [0 for i in range(9)]
        self.counter = 0
