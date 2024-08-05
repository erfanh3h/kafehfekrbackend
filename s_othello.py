MOVE_DIRS = [(-1, -1), (-1, 0), (-1, +1),
             (0, -1), (0, +1),
             (+1, -1), (+1, 0), (+1, +1)]


class OthelloGameClass:
    def __init__(self):
        self.board = [[0 for i in range(8)] for j in range(8)]
        self.player1_pawns = 30
        self.player2_pawns = 30
        self.current_move_list = []
        self.player1_score = 2
        self.player2_score = 2

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

    def add_pawns_to_board(self):
        self.board[3][3] = 1
        self.board[4][4] = 1

        self.board[3][4] = 2
        self.board[4][3] = 2

    def check_win(self):
        winner = 0
        if self.player1_pawns <= 0:
            winner = 2
        elif self.player2_pawns <= 0:
            winner = 1
        return winner

    def is_valid_coord(self, row, col):
        if 0 <= row < 8 and 0 <= col < 8:
            return True
        return False

    def has_tile_to_flip(self, move, direction, gamer_id):
        i = 1
        if self.is_valid_coord(move[0], move[1]):
            curr_tile = gamer_id
            while True:
                row = move[0] + direction[0] * i
                col = move[1] + direction[1] * i
                if not self.is_valid_coord(row, col) or \
                        self.is_target_peace_empty(row, col):
                    return False
                elif self.board[row][col] == curr_tile:
                    break
                else:
                    i += 1
        return i > 1

    def flip_tiles(self, gamer_id, move):
        if self.current_move_list.__contains__(move):
            self.board[move[0]][move[1]] = gamer_id
            if gamer_id == 1:
                self.player1_score += 1
            else:
                self.player2_score += 1
            for direction in MOVE_DIRS:
                i = 1
                while True:
                    row = move[0] + direction[0] * i
                    col = move[1] + direction[1] * i
                    if self.board[row][col] == gamer_id:
                        break
                    else:
                        self.board[row][col] = gamer_id
                        if gamer_id == 1:
                            self.player1_score += 1
                            self.player2_score -= 1
                        else:
                            self.player2_score += 1
                            self.player1_score -= 1
                        i += 1

    def has_legal_move(self, gamer_id):
        for row in range(8):
            for col in range(8):
                move = (row, col)
                if self.is_legal_move(move, gamer_id):
                    return True
        return False

    def get_legal_moves(self, gamer_id):
        moves = []
        for row in range(8):
            for col in range(8):
                move = (row, col)
                if self.is_legal_move(move, gamer_id):
                    moves.append((row, col))
        return moves

    def is_legal_move(self, move, gamer_id):
        if move != () and self.is_valid_coord(move[0], move[1]) \
                and self.is_target_peace_empty(move[0], move[1]):
            for direction in MOVE_DIRS:
                if self.has_tile_to_flip(move, direction, gamer_id):
                    return True
        return False

    def play(self):
        self.add_pawns_to_board()
        print(checkers_game)
        self.current_move_list = self.get_legal_moves(1)
        print(self.current_move_list)
        self.flip_tiles(1, (3, 5))
        print(checkers_game)


checkers_game = OthelloGameClass()
checkers_game.play()
