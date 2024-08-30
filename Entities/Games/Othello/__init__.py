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


class OthelloGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [[0 for i in range(8)] for j in range(8)]
        self.player1_pawns = 30
        self.player2_pawns = 30
        self.current_move_list = []
        self.player1_score = 2
        self.player2_score = 2
        self.add_pawns_to_board()
        print(self)

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
                "current_turn": self.current_turn, 'scores': [self.player1_score, self.player2_score]}
        return data

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
            self.player2_pawns -= 1
        else:
            self.current_turn = self.symbol_1
            self.player1_pawns -= 1
        self.current_move_list = self.get_legal_moves(self.current_turn)

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            column_index = data['c_index']
            row_index = data['r_index']
            move = (column_index, row_index)
            self.flip_tiles(gamer_id, move)
            await self.send_data_function(commands.Peace_Selected, {
                "select_data": {'c_index': column_index, 'r_index': row_index, 'gamer_id': gamer_id},
                'scores': [self.player1_score, self.player2_score]})
            # is_game_finished = self.check_game_ended()
            # if is_game_finished:
            #     winner = self.get_game_winner()
            #     self.is_game_finished = True
            #     await self.send_data_function(commands.Finish_Game, {"Winner": winner})

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_score > self.player2_score:
                winner = self.symbol_1
            elif self.player2_score > self.player1_score:
                winner = self.symbol_2
        return winner

    def check_game_ended(self):
        if self.player1_pawns == 0 and self.player2_pawns == 0:
            self.is_game_finished = True
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
        move = (data['c_index'], data['r_index'])
        if not self.current_move_list.__contains__(move):
            return False
        return True

    def is_target_peace_empty(self, r_index, c_index):
        return self.board[r_index][c_index] == 0

    def is_target_peace_enemy(self, r_index, c_index, gamer_id):
        return self.board[r_index][c_index] != gamer_id

    def add_pawns_to_board(self):
        self.board[3][3] = 1
        self.board[4][4] = 1
        self.board[3][4] = 2
        self.board[4][3] = 2
        self.current_move_list = self.get_legal_moves(self.current_turn)

    def is_valid_coordinate(self, row, col):
        if 0 <= row < 8 and 0 <= col < 8:
            return True
        return False

    def has_tile_to_flip(self, move, direction, gamer_id):
        i = 1
        if self.is_valid_coordinate(move[0], move[1]):
            curr_tile = gamer_id
            while True:
                row = move[0] + direction[0] * i
                col = move[1] + direction[1] * i
                if not self.is_valid_coordinate(row, col) or \
                        self.is_target_peace_empty(row, col):
                    return False
                elif self.board[row][col] == curr_tile:
                    break
                else:
                    i += 1
        return i > 1

    def flip_tiles(self, gamer_id, move):
        self.board[move[0]][move[1]] = gamer_id
        if gamer_id == 1:
            self.player1_score += 1
        else:
            self.player2_score += 1
        for direction in MOVE_DIRS:
            if self.has_tile_to_flip(move, direction, gamer_id):
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
        if move != () and self.is_valid_coordinate(move[0], move[1]) \
                and self.is_target_peace_empty(move[0], move[1]):
            for direction in MOVE_DIRS:
                if self.has_tile_to_flip(move, direction, gamer_id):
                    return True
        return False
