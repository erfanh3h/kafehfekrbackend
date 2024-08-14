from Entities.Games.base_game_class import BaseGameClass
from Commons import commands

MOVE_DIRS = [(-1, -1), (-1, 0), (-1, +1),
             (0, -1), (0, +1),
             (+1, -1), (+1, 0), (+1, +1)]


def get_coordinate_of_peace(peace_number):
    x = peace_number % 8
    y = int(peace_number / 8)
    return x, y


def get_peace_of_coordinate(x, y):
    peace_number = y * 8 + x
    return peace_number


def is_valid_coordinate(col, row):
    if 0 <= row < 8 and 0 <= col < 8:
        return True
    return False


class FourInRowGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [[0 for i in range(8)] for j in range(8)]
        self.player1_pawns = 32
        self.player2_pawns = 32
        self.player2_score = 2
        self.game_winner = 0

    def __str__(self):
        board = """"""
        board += '____0___1___2___3___4___5___6___7__\n'
        for i in range(8):
            board += f'{i} |'
            for j in range(8):
                board += f' {self.board[i][j]} '
                if j != 7:
                    board += '|'
            board += '|'
            board += '\n'
            if i != 7:
                board += '____________________________________\n'
        board += '___________________________________\n'
        return board

    def get_game_data(self):
        board_peaces_data = []
        for i in range(8):
            for j in range(8):
                board_peaces_data.append(self.board[i][j])
        data = {"board": board_peaces_data, "pawns_count": [self.player1_pawns, self.player2_pawns],
                "current_turn": self.current_turn, }
        return data

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            row_index = data['r_index']
            column_index = self.get_possible_piece_column(row_index)
            if column_index == -1:
                self.submit_piece(column_index, row_index, gamer_id)
                await self.send_data_function(commands.Peace_Selected, {
                    "select_data": {'c_index': column_index, 'r_index': row_index, 'gamer_id': gamer_id}, })
                if gamer_id == 1:
                    self.player1_pawns -= 1
                else:
                    self.player2_pawns -= 1
                position = (column_index, row_index)
                is_game_finished = self.is_win_happen(gamer_id, position)
                if is_game_finished:
                    self.game_winner = gamer_id
                    self.is_game_finished = True
                    await self.send_data_function(commands.Finish_Game, {"Winner": self.game_winner})
                is_game_finished = self.check_game_ended()
                if is_game_finished:
                    self.game_winner = 0
                    self.is_game_finished = True
                    await self.send_data_function(commands.Finish_Game, {"Winner": self.game_winner})

    def get_game_winner(self):
        winner = self.game_winner
        if self.leaver_id != 0:
            winner = self.get_opponent_id(self.leaver_id)
        return winner

    def check_game_ended(self):
        if self.player1_pawns == 0 and self.player2_pawns == 0:
            return True
        return False

    def finish_game(self):
        self.is_game_finished = True

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        if self.is_game_finished:
            return False
        return True

    def is_win_happen(self, gamer_id, position):
        result = False
        for direction in MOVE_DIRS:
            if result:
                break
            i = 1
            while True:
                if i == 4:
                    result = True
                    break
                col = position[0] + direction[0] * i
                row = position[1] + direction[1] * i
                if is_valid_coordinate(col, row) and self.board[col][row] == gamer_id:
                    i += 1
                else:
                    break
        return result

    def get_possible_piece_column(self, row_index):
        result_col = -1
        for col in range(7, -1, -1):
            if self.board[col][row_index] == 0:
                result_col = col
                break
        return result_col

    def submit_piece(self, col, row, gamer_id):
        self.board[col][row] = gamer_id
