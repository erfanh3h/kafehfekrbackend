from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class DotBoxGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.lines_board = [0 for i in range(60)]
        self.boxes_board = [0 for i in range(25)]
        self.counter = 0
        self.current_round = 1
        self.gamer1_score = 0
        self.gamer2_score = 0
        self.boxes_neighbors = {0: [1, 9], 1: [0, 2, 4], 2: [1, 14], 3: [4, 10], 4: [1, 3, 5, 7], 5: [4, 13],
                                6: [7, 11],
                                7: [4, 6, 8], 8: [7, 12], 9: [0, 10, 21], 10: [3, 9, 11, 18], 11: [6, 10, 15],
                                12: [8, 13, 17],
                                13: [5, 12, 14, 20], 14: [2, 13, 23], 15: [11, 16], 16: [15, 17, 19], 17: [12, 16],
                                18: [10, 19],
                                19: [16, 18, 20, 22], 20: [13, 19], 21: [9, 22], 22: [19, 21, 23], 23: [14, 22]}

    def get_game_data(self):
        data = {"lines_board": self.lines_board, "boxes_board": self.boxes_board,
                "scores": [self.gamer1_score, self.gamer2_score],
                "current_round": self.current_round, "current_turn": self.current_turn}
        return data

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = 2
        else:
            self.current_turn = 1

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        peace_number = data
        self.counter += 1
        if gamer_id == 1:
            self.lines_board[peace_number] = self.symbol_1
        else:
            self.lines_board[peace_number] = self.symbol_2
        await self.send_data_function(commands.Peace_Selected, {'user': gamer_id, 'target_peace': peace_number})
        if self.check_game_ended():
            self.is_game_finished = True
            game_winner = self.get_game_winner()
            await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
            return False
        else:
            is_win_happen = self.check_box_win_happen(peace_number)
            return is_win_happen

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        peace_number = data
        if peace_number < 0 or peace_number > 8:
            return False
        if (self.lines_board[peace_number] == self.symbol_1) or (self.lines_board[peace_number] == self.symbol_2):
            return False
        if self.is_game_finished:
            return False
        return True

    def get_game_winner(self):
        winner = 0
        if self.gamer1_score > self.gamer2_score:
            winner = self.gamer1_score
        elif self.gamer2_score > self.gamer1_score:
            winner = self.gamer2_score
        return winner

    def check_game_ended(self):
        for peace in self.lines_board:
            if peace != 0:
                return False

    def check_box_win_happen(self, peace_number):
        return True
