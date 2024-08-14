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
        self.boxes_neighbors = {0: [0, 5, 6, 11], 1: [1, 6, 7, 12], 2: [2, 7, 8, 13], 3: [3, 8, 9, 14],
                                4: [4, 9, 10, 15], 5: [11, 16, 17, 22], 6: [12, 17, 18, 23], 7: [13, 18, 19, 24],
                                8: [14, 19, 20, 25], 9: [15, 20, 21, 26], 10: [22, 27, 28, 33], 11: [23, 28, 29, 34],
                                12: [24, 29, 30, 35], 13: [25, 30, 31, 36], 14: [26, 31, 32, 37], 15: [33, 38, 39, 44],
                                16: [34, 39, 40, 45], 17: [35, 40, 41, 46], 18: [36, 41, 42, 47], 19: [37, 42, 43, 48],
                                20: [44, 49, 50, 55], 21: [45, 50, 51, 56], 22: [46, 51, 52, 57], 23: [47, 52, 53, 58],
                                24: [48, 53, 54, 59]}

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
            is_win_happen, win_list = self.check_box_win_happen(peace_number)
            if is_win_happen:
                for index in win_list:
                    self.boxes_board[index] = gamer_id
                if gamer_id == 1:
                    self.gamer1_score += len(win_list)
                else:
                    self.gamer2_score += len(win_list)
            return is_win_happen

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        peace_number = data
        if peace_number < 0 or peace_number > 63:
            return False
        if (self.lines_board[peace_number] == self.symbol_1) or (self.lines_board[peace_number] == self.symbol_2):
            return False
        if self.is_game_finished:
            return False
        return True

    def get_game_winner(self):
        winner = 0
        if self.leaver_id != 0:
            winner = self.get_opponent_id(self.leaver_id)
        elif self.gamer1_score > self.gamer2_score:
            winner = self.gamer1_score
        elif self.gamer2_score > self.gamer1_score:
            winner = self.gamer2_score
        return winner

    def check_game_ended(self):
        for peace in self.lines_board:
            if peace != 0:
                return False
        return True

    def check_each_box_in_raw_happen(self, neighbors: list):
        for neighbor_index in range(len(neighbors)):
            if self.lines_board[neighbors[neighbor_index]] == 0:
                return False
        return True

    def check_box_win_happen(self, peace_number):
        lines_list_to_check = {}
        is_win_happen = False
        win_results = []
        for key, value in self.boxes_neighbors.items():
            if value.__contains__(peace_number):
                lines_list_to_check[key] = self.boxes_neighbors[key]
        for key, value in lines_list_to_check.items():
            if self.check_each_box_in_raw_happen(value):
                is_win_happen = True
                win_results.append(key)
        return is_win_happen, win_results
