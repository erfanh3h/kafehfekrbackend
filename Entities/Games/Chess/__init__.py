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
        self.check_move_list = []
        self.init_board()
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
        board_data = []
        pieces_data = []
        for i in range(8):
            for j in range(8):
                board_data.append(self.board[i][j].to_json())
        data = {"board_data": board_data, "pieces_data": pieces_data,
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
            source_position = data['s_position']
            target_position = data['t_position']
            move_list = self.get_moves_list(source_position, gamer_id)
            if move_list.__contains__(target_position):
                self.move_piece(source_position, target_position, gamer_id)
                await self.send_data_function(commands.Peace_Selected, {
                    "select_data": {'s_position': source_position, 't_position': target_position,
                                    'gamer_id': gamer_id, 'type': 'move'}, })
                return True
            hit_list = self.get_hit_list(source_position, gamer_id)
            if hit_list.__contains__(target_position):
                self.hit_piece(source_position, target_position, gamer_id)
                await self.send_data_function(commands.Peace_Selected, {
                    "select_data": {'s_position': source_position, 't_position': target_position,
                                    'gamer_id': gamer_id, 'type': 'hit'}, })
                return True
            # is_move_correct = self.move_pawn(source_column_index, source_row_index, target_column_index,
            #                                  target_row_index, gamer_id)
            # if is_move_correct:
            #     await self.send_data_function(commands.Peace_Selected, {
            #         "select_data": {'s_c_index': source_column_index, 's_r_index': source_row_index,
            #                         't_c_index': target_column_index, 't_r_index': target_row_index,
            #                         'gamer_id': gamer_id}, })
            #     is_game_ended = self.check_game_ended()
            #     if is_game_ended:
            #         winner = self.get_game_winner()
            #         self.is_game_finished = True
            #         await self.send_data_function(commands.Finish_Game, {"Winner": winner})
            #     return True
        return False

    def get_game_winner(self):
        winner = 0
        # if self.player1_pawns <= 0:
        #     winner = self.symbol_2
        # elif self.player2_pawns <= 0:
        #     winner = self.symbol_1
        return winner

    def check_game_ended(self):
        # if self.player1_pawns <= 0:
        #     return True
        # elif self.player2_pawns <= 0:
        #     return True
        return False

    def finish_game(self):
        self.is_game_finished = True

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        if self.is_game_finished:
            return False
        source_position = data['s_position']
        if not self.is_target_piece_mine(source_position, gamer_id):
            return False
        return True

    def is_target_piece_empty(self, c_index, r_index):
        return self.board[c_index][r_index].piece.gamer_id == 0

    def is_target_piece_enemey(self, c_index, r_index, gamer_id):
        return self.board[c_index][r_index].piece.gamer_id == 0 and self.board[c_index][
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
        pieces_list.reverse()
        for piece_i in range(len(pieces_list)):
            self.board[7][piece_i].set_data(pieces_list[piece_i](2))
            index += 1

    def get_moves_list(self, position, gamer_id):
        result = []
        piece = self.board[position[0]][position[1]].piece
        if piece is not None:
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
                    if is_valid_coord(y, x) and self.is_target_piece_empty(y, x):
                        result.append((y, x))
        print(result)
        return result

    def get_hit_list(self, position, gamer_id):
        result = []
        piece = self.board[position[0]][position[1]].piece
        if piece is not None:
            piece_move_list = piece.get_hit_list()
            is_piece_multi_move = piece.is_multi_move
            if is_piece_multi_move:
                for move in piece_move_list:
                    i = 1
                    while True:
                        y = position[0] + move[0] * i
                        x = position[1] + move[1] * i
                        if is_valid_coord(x, y):
                            if self.is_target_piece_enemey(y, x, gamer_id):
                                result.append((y, x))
                                break
                            elif not self.is_target_piece_empty(y, x):
                                break
                            else:
                                i += 1
                        else:
                            break
            else:
                for move in piece_move_list:
                    y = position[0] + move[0]
                    x = position[1] + move[1]
                    if is_valid_coord(x, y):
                        if self.is_target_piece_enemey(y, x, gamer_id):
                            result.append((y, x))
        print(result)
        return result

    def move_piece(self, source_position, target_position, gamer_id):
        piece = self.board[source_position[0]][source_position[1]].piece
        piece.move()
        self.board[source_position[0]][source_position[1]].set_data(PieceClass(0))
        self.board[target_position[0]][target_position[1]].set_data(piece)

    def hit_piece(self, source_position, target_position, gamer_id):
        piece = self.board[source_position[0]][source_position[1]].piece
        piece.move()
        self.board[source_position[0]][source_position[1]].set_data(PieceClass(0))
        self.board[target_position[0]][target_position[1]].set_data(piece)
