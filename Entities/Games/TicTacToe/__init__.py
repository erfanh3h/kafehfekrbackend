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

    def get_game_data(self):
        data = {"board": self.board, "scores": [self.gamer1_score, self.gamer2_score],
                "current_round": self.current_round, "current_turn": self.current_turn}
        return data

    def change_round(self):
        self.board = [0 for i in range(9)]
        self.counter = 0
        self.is_round_finished = False
        self.current_round += 1
        if self.current_round % 2 == 0:
            self.current_turn = 1
        else:
            self.current_turn = 2

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
            if self.current_round == self.round_count:
                game_winner = self.get_game_winner()
                await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
                self.is_game_finished = True
            else:
                self.is_round_finished = True
                await self.send_data_function(commands.Finish_Round, {"Winner": winner})

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
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
                break
            if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_2:
                winner = self.symbol_2
                self.gamer2_score += 1
                break
        return winner

    def get_game_winner(self):
        if self.gamer1_score > self.gamer2_score:
            return self.symbol_1
        elif self.gamer2_score > self.gamer1_score:
            return self.symbol_2
        else:
            return None

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = 2
        else:
            self.current_turn = 1

    async def surrender(self, gamer_id):
        self.is_game_finished = True
        if gamer_id == 1:
            game_winner = 2
        else:
            game_winner = 1
        await self.send_data_function(commands.Surrender, {"gamer_id": gamer_id})
