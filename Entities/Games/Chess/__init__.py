from Entities.Games.Chess.Piece import PieceClass
from Entities.Games.Chess.Piece.bishop import BishopPiece
from Entities.Games.Chess.Piece.king import KingPiece
from Entities.Games.Chess.Piece.knight import KnightPiece
from Entities.Games.Chess.Piece.pawn import PawnPiece
from Entities.Games.Chess.Piece.queen import QueenPiece
from Entities.Games.Chess.Piece.rook import RookPiece
from Entities.Games.Chess.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


def get_coordinate_of_peace(peace_number):
    x = peace_number % 8
    y = int(peace_number / 8)
    return x, y


def get_peace_of_coordinate(x, y):
    peace_number = y * 8 + x
    return peace_number


def is_valid_coord(col, row):
    if 0 <= row < 8 and 0 <= col < 8:
        return True
    return False


class ChessGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [[BoardSpotClass(i, j) for i in range(8)] for j in range(8)]
        self.king1_position = (0, 0)
        self.king2_position = (0, 0)
        self.current_moves = {}
        self.current_hits = {}
        self.player1_hitted_pawns = 0
        self.player2_hitted_pawns = 0
        self.init_board()
        self.is_player1_kish = False
        self.is_player2_kish = False

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
        board_data = []
        for i in range(8):
            for j in range(8):
                board_data.append(self.board[i][j].to_json())
        data = {"board_data": board_data, "current_turn": self.current_turn}
        return data

    def change_turn(self):
        self.current_hits.clear()
        self.current_moves.clear()
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1
        self.set_current_movements()
        self.is_game_finished = self.check_game_ended()

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            source_column_index = data['s_c_index']
            source_row_index = data['s_r_index']
            target_column_index = data['t_c_index']
            target_row_index = data['t_r_index']
            source_position = (source_column_index, source_row_index)
            target_position = (target_column_index, target_row_index)
            if (self.current_moves.keys().__contains__(source_position) and
                    self.current_moves[source_position].__contains__(target_position)):
                self.move_piece(source_position, target_position, gamer_id)
                await self.send_data_function(commands.Peace_Selected, {
                    "select_data": {'s_c_index': source_column_index, 's_r_index': source_row_index,
                                    't_c_index': target_column_index, 't_r_index': target_row_index,
                                    'gamer_id': gamer_id, 'type': 'move'}, })
                return True
            if (self.current_hits.keys().__contains__(source_position) and
                    self.current_hits[source_position].__contains__(target_position)):
                # this checks used for when user is check and become dc
                if gamer_id == 1 and target_position == self.king2_position:
                    self.king2_position = (-1, -1)
                if gamer_id == 2 and target_position == self.king1_position:
                    self.king1_position = (-1, -1)
                self.move_piece(source_position, target_position, gamer_id)
                await self.send_data_function(commands.Peace_Selected, {
                    "select_data": {'s_c_index': source_column_index, 's_r_index': source_row_index,
                                    't_c_index': target_column_index, 't_r_index': target_row_index,
                                    'gamer_id': gamer_id, 'type': 'hit'}, })
                return True
        return False

    def get_game_winner(self):
        winner = 0
        if self.leaver_id != 0:
            winner = self.get_opponent_id(self.leaver_id)
        elif self.player1_hitted_pawns == 15 and self.player2_hitted_pawns == 15:
            winner = 0
        # this is status when user could kill enemy king ( while he is check not move)
        elif self.king1_position == (-1, -1):
            winner = 2
        elif self.king2_position == (-1, -1):
            winner = 1
        elif self.current_turn == 1:
            winner = self.symbol_2
        else:
            winner = self.symbol_1
        return winner

    def check_game_ended(self):
        if len(self.current_moves.keys()) == 0 and len(self.current_hits.keys()) == 0:
            return True
        if self.player1_hitted_pawns == 15 and self.player2_hitted_pawns == 15:
            return True
        if self.king1_position == (-1, -1) or self.king2_position == (-1, -1):
            return True
        if self.leaver_id != 0 :
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
        source_column_index = data['s_c_index']
        source_row_index = data['s_r_index']
        source_position = (source_column_index, source_row_index)
        if not self.is_target_piece_mine(source_position, gamer_id):
            return False
        return True

    def is_target_piece_empty(self, c_index, r_index):
        return self.board[c_index][r_index].piece.gamer_id == 0

    def is_target_piece_enemey(self, c_index, r_index, gamer_id):
        return self.board[c_index][r_index].piece.gamer_id != 0 and self.board[c_index][
            r_index].piece.gamer_id != gamer_id

    def is_target_piece_mine(self, position: tuple, gamer_id: int):
        return self.board[position[0]][position[1]].piece.gamer_id == gamer_id

    def init_board(self):
        pieces_list = [RookPiece, KnightPiece, BishopPiece, QueenPiece, KingPiece, BishopPiece, KnightPiece, RookPiece]
        index = 0
        for piece in pieces_list:
            self.board[0][index].set_data(piece(1))
            index += 1
        for i in range(8):
            self.board[1][i].set_data(PawnPiece(1))
            index += 1
        for i in range(8):
            self.board[6][i].set_data(PawnPiece(2))
            index += 1
        for piece_i in range(len(pieces_list)):
            self.board[7][piece_i].set_data(pieces_list[piece_i](2))
            index += 1
        self.king1_position = (0, 4)
        self.king2_position = (7, 4)

    def get_moves_list(self, position, gamer_id):
        result = []
        piece = self.board[position[0]][position[1]].piece
        if piece.gamer_id != 0:
            piece_move_list = piece.get_move_list()
            is_piece_multi_move = piece.is_multi_move
            if is_piece_multi_move:
                for move in piece_move_list:
                    i = 1
                    while True:
                        y = position[0] + move[0] * i
                        x = position[1] + move[1] * i
                        if is_valid_coord(x, y):
                            if not self.is_target_piece_empty(y, x):
                                break
                            else:
                                result.append((y, x))
                                i += 1
                        else:
                            break
            else:
                for move in piece_move_list:
                    y = position[0] + move[0]
                    x = position[1] + move[1]
                    # check for castle move that king side must be empty
                    if (move[0], move[1]) == (0, 2) and not self.is_target_piece_empty(y, x - 1):
                        continue
                    # check for castle move that king side must be empty
                    if (move[0], move[1]) == (0, -2) and not self.is_target_piece_empty(y, x + 1):
                        continue
                    if is_valid_coord(y, x) and self.is_target_piece_empty(y, x):
                        result.append((y, x))
        return result

    def get_hit_list(self, position, gamer_id):
        result = []
        piece = self.board[position[0]][position[1]].piece
        if piece.gamer_id != 0:
            piece_move_list = piece.get_hit_list()
            is_piece_multi_move = piece.is_multi_move
            if is_piece_multi_move:
                for move in piece_move_list:
                    i = 1
                    while True:
                        y = position[0] + move[0] * i
                        x = position[1] + move[1] * i
                        if is_valid_coord(y, x):
                            if self.is_target_piece_enemey(y, x, gamer_id):
                                result.append((y, x))
                                break
                            elif self.is_target_piece_mine((y, x), gamer_id):
                                break
                            else:
                                i += 1
                        else:
                            break
            else:
                for move in piece_move_list:
                    y = position[0] + move[0]
                    x = position[1] + move[1]
                    if is_valid_coord(y, x):
                        if self.is_target_piece_enemey(y, x, gamer_id):
                            result.append((y, x))
        return result

    def get_hit_list_with_changed_position(self, position, gamer_id, source_changed_position, target_changed_position):
        result = []
        piece = self.board[position[0]][position[1]].piece
        if piece.gamer_id != 0:
            piece_move_list = piece.get_hit_list()
            is_piece_multi_move = piece.is_multi_move
            if is_piece_multi_move:
                for move in piece_move_list:
                    i = 1
                    while True:
                        y = position[0] + move[0] * i
                        x = position[1] + move[1] * i
                        if is_valid_coord(y, x):
                            if source_changed_position == (y, x):
                                i += 1
                            elif target_changed_position == (y, x):
                                result.append((y, x))
                                break
                            else:
                                if self.is_target_piece_enemey(y, x, gamer_id):
                                    result.append((y, x))
                                    break
                                elif self.is_target_piece_mine((y, x), gamer_id):
                                    break
                                else:
                                    i += 1
                        else:
                            break
            else:
                for move in piece_move_list:
                    y = position[0] + move[0]
                    x = position[1] + move[1]
                    if is_valid_coord(y, x):
                        if target_changed_position == (y, x):
                            result.append((y, x))
                        else:
                            if self.is_target_piece_enemey(y, x, gamer_id):
                                result.append((y, x))
        return result

    def add_possible_moves(self, position, enemy_id, king_position):
        result = []
        enemy_positions = self.get_enemy_positions(enemy_id)
        move_possible_list = self.get_moves_list(position, self.current_turn)
        for new_position in move_possible_list:
            can_selected = True
            for check_position in enemy_positions:
                raw_result = self.get_hit_list_with_changed_position(check_position, enemy_id, position, new_position)
                if king_position == position and raw_result.__contains__(new_position):
                    can_selected = False
                    break
                if raw_result.__contains__(king_position):
                    can_selected = False
                    break
            if can_selected:
                result.append(new_position)
        return result

    def add_possible_hits(self, position, enemy_id, king_position):
        result = []
        enemy_positions = self.get_enemy_positions(enemy_id)
        move_possible_list = self.get_hit_list(position, self.current_turn)
        for new_position in move_possible_list:
            can_selected = True
            for check_position in enemy_positions:
                raw_result = self.get_hit_list_with_changed_position(check_position, enemy_id, position, new_position)
                if king_position == position and raw_result.__contains__(new_position):
                    can_selected = False
                    break
                if raw_result.__contains__(king_position):
                    if new_position == check_position:
                        result.append(new_position)
                        break
                    can_selected = False
                    break
            if can_selected:
                result.append(new_position)
        return result

    def get_enemy_positions(self, enemy_id):
        result = []
        for i in range(8):
            for j in range(8):
                if self.board[i][j].piece.gamer_id == enemy_id:
                    result.append((i, j))
        return result

    def get_current_player_positions(self):
        result = []
        for i in range(8):
            for j in range(8):
                if self.board[i][j].piece.gamer_id == self.current_turn:
                    result.append((i, j))
        return result

    def set_current_movements(self):
        current_gamer_pieces = self.get_current_player_positions()
        if self.current_turn == 1:
            enemy_id = 2
        else:
            enemy_id = 1
        if enemy_id == 1:
            king_position = self.king2_position
        else:
            king_position = self.king1_position
        for position in current_gamer_pieces:
            moves = self.add_possible_moves(position, enemy_id, king_position)
            hits = self.add_possible_hits(position, enemy_id, king_position)
            if len(moves) != 0:
                self.current_moves[position] = moves
            if len(hits) != 0:
                self.current_hits[position] = hits

    def move_piece(self, source_position, target_position, gamer_id):
        # change pawn to queen when reach last col
        if (source_position[0] == 6 and target_position[0] == 7 and
                self.board[source_position[0]][source_position[1]].piece.name == 'Pawn'):
            gamer_id = self.board[source_position[0]][source_position[1]].piece.gamer_id
            self.board[source_position[0]][source_position[1]].set_data(QueenPiece(gamer_id))
        if (source_position[0] == 1 and target_position[0] == 0 and
                self.board[source_position[0]][source_position[1]].piece.name == 'Pawn'):
            gamer_id = self.board[source_position[0]][source_position[1]].piece.gamer_id
            self.board[source_position[0]][source_position[1]].set_data(QueenPiece(gamer_id))
        ##########
        # apply remove pawns count
        if not self.is_target_piece_empty(target_position[0], target_position[1]):
            if self.board[target_position[0]][target_position[1]].piece.gamer_id == 1:
                self.player1_hitted_pawns += 1
            else:
                self.player2_hitted_pawns += 1
        ##########
        # swap piece data
        piece = self.board[source_position[0]][source_position[1]].piece
        piece.move()
        self.board[source_position[0]][source_position[1]].set_data(PieceClass(0))
        self.board[target_position[0]][target_position[1]].set_data(piece)
        #########
        # chech king rook special move
        if source_position == (7, 4) and target_position == (7, 2):
            self.move_piece((7, 0), (7, 3), gamer_id)
        if source_position == (7, 4) and target_position == (7, 6):
            self.move_piece((7, 7), (7, 5), gamer_id)
        if source_position == (0, 4) and target_position == (0, 6):
            self.move_piece((0, 7), (0, 5), gamer_id)
        if source_position == (0, 4) and target_position == (0, 2):
            self.move_piece((0, 0), (0, 3), gamer_id)
        ##########
        # change king position
        if gamer_id == 1 and source_position == self.king1_position:
            self.king1_position = target_position
        if gamer_id == 2 and target_position == self.king2_position:
            self.king2_position = target_position
        ##########

    # def get_is_king_check(self, gamer_id: int):
    #     # self.king1_checks.clear()
    #     # self.king2_checks.clear()
    #     if gamer_id == 1:
    #         target_king_position = self.king1_position
    #     else:
    #         target_king_position = self.king2_position
    #     for i in range(8):
    #         for j in range(8):
    #             position = (i, j)
    #             if self.is_target_piece_enemey(position[0], position[1], gamer_id):
    #                 result_list = self.get_hit_list(position, gamer_id)
    #                 if result_list.__contains__(target_king_position):
    #                     return True
    #     return False
