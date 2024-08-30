import random

from Entities.Games.Checkers.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


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


class CheckersGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [[BoardSpotClass(i, j) for i in range(8)] for j in range(8)]
        self.player1_pawns = 12
        self.player2_pawns = 12
        self.check_move_list = []
        self.add_pawns_to_board()

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
                board_peaces_data.append(self.board[i][j].to_json())
        data = {"board": board_peaces_data, "pawns_count": [self.player1_pawns, self.player2_pawns],
                "current_turn": self.current_turn}
        return data

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            source_column_index = data['s_c_index']
            source_row_index = data['s_r_index']
            target_column_index = data['t_c_index']
            target_row_index = data['t_r_index']
            is_move_correct = self.move_pawn(source_column_index, source_row_index, target_column_index,
                                             target_row_index, gamer_id)
            if is_move_correct:
                await self.send_data_function(commands.Peace_Selected, {
                    "select_data": {'s_c_index': source_column_index, 's_r_index': source_row_index,
                                    't_c_index': target_column_index, 't_r_index': target_row_index,
                                    'gamer_id': gamer_id}, })
                is_game_ended = self.check_game_ended()
                if is_game_ended:
                    # winner = self.get_game_winner()
                    self.is_game_finished = True
                    # await self.send_data_function(commands.Finish_Game, {"Winner": winner})
                return True
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_pawns <= 0:
                winner = self.symbol_2
            elif self.player2_pawns <= 0:
                winner = self.symbol_1
        return winner

    def check_game_ended(self):
        if self.player1_pawns <= 0:
            return True
        elif self.player2_pawns <= 0:
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

    def is_target_peace_empty(self, r_index, c_index):
        return self.board[c_index][r_index].pawn_gamer_id == 0

    def is_target_peace_enemy(self, r_index, c_index, gamer_id):
        return self.board[c_index][r_index].pawn_gamer_id != 0 and self.board[c_index][
            r_index].pawn_gamer_id != gamer_id

    def add_pawns_to_board(self):
        self.board[0][0].set_pawn_gamer_id(1)
        self.board[0][2].set_pawn_gamer_id(1)
        self.board[0][4].set_pawn_gamer_id(1)
        self.board[0][6].set_pawn_gamer_id(1)
        self.board[1][1].set_pawn_gamer_id(1)
        self.board[1][3].set_pawn_gamer_id(1)
        self.board[1][5].set_pawn_gamer_id(1)
        self.board[1][7].set_pawn_gamer_id(1)
        self.board[2][0].set_pawn_gamer_id(1)
        self.board[2][2].set_pawn_gamer_id(1)
        self.board[2][4].set_pawn_gamer_id(1)
        self.board[2][6].set_pawn_gamer_id(1)
        self.board[5][1].set_pawn_gamer_id(2)
        self.board[5][3].set_pawn_gamer_id(2)
        self.board[5][5].set_pawn_gamer_id(2)
        self.board[5][7].set_pawn_gamer_id(2)
        self.board[6][0].set_pawn_gamer_id(2)
        self.board[6][2].set_pawn_gamer_id(2)
        self.board[6][4].set_pawn_gamer_id(2)
        self.board[6][6].set_pawn_gamer_id(2)
        self.board[7][1].set_pawn_gamer_id(2)
        self.board[7][3].set_pawn_gamer_id(2)
        self.board[7][5].set_pawn_gamer_id(2)
        self.board[7][7].set_pawn_gamer_id(2)

    def move_peace(self, s_r_index, s_c_index, t_r_index, t_c_index, gamer_id):
        self.board[s_r_index][s_c_index].remove_pawn_gamer()
        self.board[t_r_index][t_c_index].set_pawn_gamer_id(gamer_id)

    def get_direction1_right_pawn_move(self, r_index, c_index, gamer_id, is_multi_move=False):
        new_r_index = r_index - 1
        new_c_index = c_index + 1
        if new_r_index < 0 or new_r_index > 7 or new_c_index < 0 or new_c_index > 7:
            return None, None, None, False
        if self.is_target_peace_empty(new_r_index, new_c_index) and not is_multi_move:
            return (new_r_index, new_c_index), None, None, False
        else:
            if self.is_target_peace_enemy(new_r_index, new_c_index, gamer_id):
                new_r1_index = new_r_index - 1
                new_c1_index = new_c_index + 1
                if is_valid_coordinate(new_c1_index, new_r1_index) and self.is_target_peace_empty(new_r1_index,
                                                                                                  new_c1_index):
                    self.check_move_list.append(
                        ((new_r1_index, new_c1_index), (new_r_index, new_c_index), (r_index, c_index), True))
                return None, None, None, False
            else:
                return None, None, None, False

    def get_direction1_left_pawn_move(self, r_index, c_index, gamer_id, is_multi_move=False):
        new_r_index = r_index + 1
        new_c_index = c_index + 1
        if new_r_index < 0 or new_r_index > 7 or new_c_index < 0 or new_c_index > 7:
            return None, None, None, False
        if self.is_target_peace_empty(new_r_index, new_c_index) and not is_multi_move:
            return (new_r_index, new_c_index), None, None, False
        else:
            if self.is_target_peace_enemy(new_r_index, new_c_index, gamer_id):
                new_r1_index = new_r_index + 1
                new_c1_index = new_c_index + 1
                if is_valid_coordinate(new_c1_index, new_r1_index) and self.is_target_peace_empty(new_r1_index,
                                                                                                  new_c1_index):
                    self.check_move_list.append(
                        ((new_r1_index, new_c1_index), (new_r_index, new_c_index), (r_index, c_index), True))
                return None, None, None, False
            else:
                return None, None, None, False

    def get_direction2_right_pawn_move(self, r_index, c_index, gamer_id, is_multi_move=False):
        new_r_index = r_index + 1
        new_c_index = c_index - 1
        if new_r_index < 0 or new_r_index > 7 or new_c_index < 0 or new_c_index > 7:
            return None, None, None, False
        if self.is_target_peace_empty(new_r_index, new_c_index) and not is_multi_move:
            return (new_r_index, new_c_index), None, None, False
        else:
            if self.is_target_peace_enemy(new_r_index, new_c_index, gamer_id):
                new_r1_index = new_r_index + 1
                new_c1_index = new_c_index - 1
                if is_valid_coordinate(new_c1_index, new_r1_index) and self.is_target_peace_empty(new_r1_index,
                                                                                                  new_c1_index):
                    self.check_move_list.append(
                        ((new_r1_index, new_c1_index), (new_r_index, new_c_index), (r_index, c_index), True))
                return None, None, None, False
            else:
                return None, None, None, False

    def get_direction2_left_pawn_move(self, r_index, c_index, gamer_id, is_multi_move=False):
        new_r_index = r_index - 1
        new_c_index = c_index - 1
        if new_r_index < 0 or new_r_index > 7 or new_c_index < 0 or new_c_index > 7:
            return None, None, None, False
        if self.is_target_peace_empty(new_r_index, new_c_index) and not is_multi_move:
            return (new_r_index, new_c_index), None, None, False
        else:
            if self.is_target_peace_enemy(new_r_index, new_c_index, gamer_id):
                new_r1_index = new_r_index - 1
                new_c1_index = new_c_index - 1
                if is_valid_coordinate(new_c1_index, new_r1_index) and self.is_target_peace_empty(new_r1_index,
                                                                                                  new_c1_index):
                    self.check_move_list.append(
                        ((new_r1_index, new_c1_index), (new_r_index, new_c_index), (r_index, c_index), True))
                return None, None, None, False
            else:
                return None, None, None, False

    def get_possible_moves_of_peace(self, r_index, c_index, gamer_id):
        def get_direction1_moves(r_index, c_index, gamer_id):
            temp_list = []
            right_result = self.get_direction1_right_pawn_move(r_index, c_index, gamer_id)
            left_result = self.get_direction1_left_pawn_move(r_index, c_index, gamer_id)
            temp_list.append([right_result[0], right_result[1], right_result[2]])
            temp_list.append([left_result[0], left_result[1], left_result[2]])
            while len(self.check_move_list) != 0:
                indexes, removed_peace, source_start, is_multi_move = self.check_move_list[0]
                temp_list.append([indexes, removed_peace, source_start])
                if removed_peace is not None:
                    right_result = self.get_direction1_right_pawn_move(indexes[0], indexes[1], gamer_id, is_multi_move)
                    left_result = self.get_direction1_left_pawn_move(indexes[0], indexes[1], gamer_id, is_multi_move)
                    self.check_move_list.append(right_result)
                    self.check_move_list.append(left_result)
                del self.check_move_list[0]
            return temp_list

        def get_direction2_moves(r_index, c_index, gamer_id):
            temp_list = []
            right_result = self.get_direction2_right_pawn_move(r_index, c_index, gamer_id)
            left_result = self.get_direction2_left_pawn_move(r_index, c_index, gamer_id)
            temp_list.append([right_result[0], right_result[1], right_result[2]])
            temp_list.append([left_result[0], left_result[1], left_result[2]])
            while len(self.check_move_list) != 0:
                indexes, removed_peace, source_start, is_multi_move = self.check_move_list[0]
                temp_list.append([indexes, removed_peace, source_start])
                if removed_peace is not None:
                    right_result = self.get_direction2_right_pawn_move(indexes[0], indexes[1], gamer_id, is_multi_move)
                    left_result = self.get_direction2_left_pawn_move(indexes[0], indexes[1], gamer_id, is_multi_move)
                    self.check_move_list.append(right_result)
                    self.check_move_list.append(left_result)
                del self.check_move_list[0]
            return temp_list

        moves = []
        if self.board[c_index][r_index].is_super_pawn:
            list1 = get_direction1_moves(r_index, c_index, gamer_id)
            list2 = get_direction2_moves(r_index, c_index, gamer_id)
            temp_move_list = list1 + list2
        elif gamer_id == 1:
            temp_move_list = get_direction1_moves(r_index, c_index, gamer_id)
        else:
            temp_move_list = get_direction2_moves(r_index, c_index, gamer_id)
        print(temp_move_list)
        for move in temp_move_list:
            if move[0] is not None:
                moves.append(move)
        return moves

    def check_is_last_peace(self, c_index, gamer_id):
        if gamer_id == 1:
            if c_index == 7:
                return True
            return False
        else:
            if c_index == 0:
                return True
            return False

    def remove_pawn(self, c_index, r_index, gamer_id):
        self.board[r_index][c_index].remove_pawn_gamer()
        if gamer_id == 1:
            self.player2_pawns -= 1
        else:
            self.player1_pawns -= 1

    def move_pawn(self, s_c_index, s_r_index, t_c_index, t_r_index, gamer_id):
        moves = self.get_possible_moves_of_peace(s_r_index, s_c_index, gamer_id)
        print(moves)
        for move_data in moves:
            if move_data[0] == (t_r_index, t_c_index):
                if self.check_is_last_peace(t_c_index, gamer_id) or self.board[s_c_index][s_r_index].is_super_pawn:
                    self.board[t_c_index][t_r_index].set_pawn_gamer_id(gamer_id, True)
                else:
                    self.board[t_c_index][t_r_index].set_pawn_gamer_id(gamer_id, False)
                self.board[s_c_index][s_r_index].remove_pawn_gamer()
                if move_data[1] is not None:
                    remove_point = move_data[1]
                    source_peace_index = move_data[2]
                    while remove_point is not None:
                        self.remove_pawn(remove_point[0], remove_point[1], gamer_id)
                        remove_point = None
                        if source_peace_index is not None and source_peace_index != (s_r_index, s_c_index):
                            for raw_move_data in moves:
                                if raw_move_data[0] == (source_peace_index[0], source_peace_index[1]):
                                    source_peace_index = raw_move_data[2]
                                    remove_point = raw_move_data[1]
                                    break
                return True
        return False
