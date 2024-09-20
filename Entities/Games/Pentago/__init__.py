from Entities.Games.base_game_class import BaseGameClass
from Commons import commands

win_conditions = [[0, 1, 2, 9, 10], [1, 2, 9, 10, 11], [3, 4, 5, 12, 13], [4, 5, 12, 13, 14], [6, 7, 8, 15, 16],
                  [7, 8, 15, 16, 17], [18, 19, 20, 27, 28], [19, 20, 27, 28, 29], [21, 22, 23, 30, 31],
                  [22, 23, 30, 31, 32], [24, 25, 26, 33, 34], [25, 26, 33, 34, 35], [0, 3, 6, 18, 21],
                  [3, 6, 18, 21, 24], [1, 4, 7, 19, 22], [4, 7, 19, 22, 25], [2, 5, 8, 20, 23], [5, 8, 20, 23, 26],
                  [9, 12, 15, 27, 30], [12, 15, 27, 30, 33], [10, 13, 16, 28, 31], [13, 16, 28, 31, 34],
                  [11, 14, 17, 29, 32], [14, 17, 29, 32, 35]]


class PentagoGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [0 for i in range(36)]
        self.gamer1_pawns = 18
        self.gamer2_pawns = 18
        self.selection_played = False
        self.rotation_played = False
        self.winner_id = 0
        self.current_round = 0

    def get_game_data(self):
        data = {"board": self.board, "pawns": [self.gamer1_pawns, self.gamer2_pawns],
                "rotation_played": self.rotation_played, "current_turn": self.current_turn,
                "selection_played": self.selection_played}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        # print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            if gamer_id == 1:
                self.board[data] = self.symbol_1
            else:
                self.board[data] = self.symbol_2
            await self.send_data_function(commands.Peace_Selected, {'user': gamer_id, 'target_peace': data})
            self.selection_played = True
            return False
        if command_id == commands.Rotate_Peace:
            self.rotate_piece(data)
            self.rotation_played = True
            self.is_game_finished = self.check_win_happened()
            await self.send_data_function(commands.Peace_Rotated, {'user': gamer_id, 'rotation_id': data})
            return True
        return False

    def rotate_piece(self, rotation_id):
        if rotation_id == 1:
            temp1, temp2, temp3 = self.board[0], self.board[1], self.board[2]
            self.board[0], self.board[1], self.board[2] = self.board[2], self.board[5], self.board[8]
            self.board[2], self.board[5], self.board[8] = self.board[8], self.board[7], self.board[6]
            self.board[8], self.board[7], self.board[6] = self.board[6], self.board[3], self.board[0]
            self.board[6], self.board[3], self.board[0] = temp1, temp2, temp3
        elif rotation_id == 2:
            temp1, temp2, temp3 = self.board[0], self.board[1], self.board[2]
            self.board[0], self.board[1], self.board[2] = self.board[6], self.board[3], self.board[0]
            self.board[6], self.board[3], self.board[0] = self.board[8], self.board[7], self.board[6]
            self.board[8], self.board[7], self.board[6] = self.board[2], self.board[5], self.board[8]
            self.board[2], self.board[5], self.board[8] = temp1, temp2, temp3
        elif rotation_id == 3:
            temp1, temp2, temp3 = self.board[9], self.board[10], self.board[11]
            self.board[9], self.board[10], self.board[11] = self.board[11], self.board[14], self.board[17]
            self.board[11], self.board[14], self.board[17] = self.board[17], self.board[16], self.board[15]
            self.board[17], self.board[16], self.board[15] = self.board[15], self.board[12], self.board[9]
            self.board[15], self.board[12], self.board[9] = temp1, temp2, temp3
        elif rotation_id == 4:
            temp1, temp2, temp3 = self.board[9], self.board[10], self.board[11]
            self.board[9], self.board[10], self.board[11] = self.board[15], self.board[12], self.board[9]
            self.board[15], self.board[12], self.board[9] = self.board[17], self.board[16], self.board[15]
            self.board[17], self.board[16], self.board[15] = self.board[11], self.board[14], self.board[17]
            self.board[11], self.board[14], self.board[17] = temp1, temp2, temp3

    def check_win_happened(self):
        def check_win(gamer_id, indexes) -> bool:
            for index in indexes:
                if self.board[index] != gamer_id:
                    return False
            return True

        for condition in win_conditions:
            is_player1_win = check_win(1, condition)
            is_player2_win = check_win(2, condition)
            if is_player1_win and not is_player2_win:
                self.winner_id = 1
                return True
            if is_player2_win and not is_player1_win:
                self.winner_id = 2
                return True
            if is_player1_win and is_player2_win:
                self.winner_id = 0
                return True
        return False

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            return False
        peace_number = data
        if peace_number < 0 or peace_number > 35:
            return False
        if (self.board[peace_number] == self.symbol_1) or (self.board[peace_number] == self.symbol_2):
            return False
        if self.is_game_finished:
            return False
        return True

    def check_rotate_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            return False
        rotate_id = data
        if rotate_id < 1 or rotate_id > 8:
            return False
        if self.is_game_finished:
            return False
        return True

    def check_game_ended(self):
        if self.is_game_finished:
            return True
        if self.gamer1_pawns == 0 and self.gamer2_pawns == 0:
            return True
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            winner = self.winner_id
        return winner

    def change_turn(self):
        self.current_round += 1
        self.selection_played = False
        self.rotation_played = False
        if self.current_turn == 1:
            self.current_turn = 2
            self.gamer2_pawns -= 1
        else:
            self.current_turn = 1
            self.gamer1_pawns -= 1
