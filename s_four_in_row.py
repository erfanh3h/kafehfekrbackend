MOVE_DIRS = [(-1, -1), (-1, 0), (-1, +1),
             (0, -1), (0, +1),
             (+1, -1), (+1, 0), (+1, +1)]


def is_valid_coord(col, row):
    if 0 <= row < 8 and 0 <= col < 8:
        return True
    return False


class OthelloGameClass:
    def __init__(self):
        self.board = [[0 for i in range(8)] for j in range(8)]
        self.player1_pawns = 32
        self.player2_pawns = 32

    def is_target_peace_empty(self, r_index, c_index):
        return self.board[r_index][c_index] == 0

    def is_target_peace_enemy(self, r_index, c_index, gamer_id):
        return self.board[r_index][c_index] != gamer_id

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

    def check_win(self):
        winner = 0
        if self.player1_pawns <= 0:
            winner = 2
        elif self.player2_pawns <= 0:
            winner = 1
        return winner

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
                if is_valid_coord(col, row) and self.board[col][row] == gamer_id:
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

    def play(self):
        print(checkers_game)
        col = self.get_possible_piece_column(6)
        if col != -1:
            self.submit_piece(col, 6, 1)
        col = self.get_possible_piece_column(6)
        if col != -1:
            self.submit_piece(col, 6, 1)
        col = self.get_possible_piece_column(6)
        if col != -1:
            self.submit_piece(col, 6, 1)
        col = self.get_possible_piece_column(6)
        if col != -1:
            self.submit_piece(col, 6, 1)
        print(checkers_game)
        print(self.is_win_happen(1, (4, 6)))

        # self.flip_tiles(1, (3, 5))
        # print(checkers_game)


checkers_game = OthelloGameClass()
checkers_game.play()
