"""CONVENTIONS:
positions are done row-column from the bottom left and are both numbers. This corresponds to the alpha-number system in traditional chess while being computationally useful. they are specified as tuples
"""
import itertools

WHITE = "white"
BLACK = "black"


def is_valid_coord(row, col):
    if 0 <= row < 8 and 0 <= col < 8:
        return True
    return False


class BoardSpotClass:
    def __init__(self, r_index, c_index):
        self.position = (r_index, c_index)
        self.piece_index = None
        self.gamer_id = 0

    def set_data(self, piece_id: int, position: tuple, gamer_id: int):
        self.piece_index = piece_id
        self.gamer_id = gamer_id
        self.position = position

    def remove_pawn_gamer(self):
        self.piece_index = None

    def __str__(self):
        return self.gamer_id.__str__()


def get_piece_of_coordinate(x, y):
    piece_number = y * 8 + x
    return piece_number


class PieceClass:
    def __init__(self, index):
        self.position: tuple = (0, 0)
        self.index = index
        self.is_removed = False
        self.gamer_id = 0
        self.move_list: list[tuple] = []
        self.is_multi_move = True
        self.is_first_move = True

    def set_data(self, position: tuple, gamer_id: int):
        self.position = position
        self.gamer_id = gamer_id

    def remove_piece(self):
        self.is_removed = True
        self.position = None

    def get_move_list(self) -> list:
        result = []
        return result

    def move_to_position(self, position: tuple):
        self.position = position
        self.is_first_move = False

    def __str__(self):
        return f""


class PawnPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)
        self.is_multi_move = False

    def get_move_list(self) -> list:
        result = []
        if self.gamer_id == 1:
            result.append((0, 1))
        else:
            result.append((0, +1))
        return result


class RookPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)

    def get_move_list(self) -> list:
        result = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        return result


class KnightPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)
        self.is_multi_move = False
    def get_move_list(self) -> list:
        result = [(-2, 1), (-1, 2), (1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1)]
        return result


class BishopPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)

    def get_move_list(self) -> list:
        result = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        return result


class QueenPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)

    def get_move_list(self) -> list:
        result = [(1, 1), (1, -1), (-1, 1), (-1, -1), (0, 1), (0, -1), (1, 0), (-1, 0)]
        return result


class KingPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)
        self.is_multi_move = False

    def get_move_list(self) -> list:
        result = [(1, 1), (1, -1), (-1, 1), (-1, -1), (0, 1), (0, -1), (1, 0), (-1, 0)]
        return result


class ChessGameClass:
    def __init__(self):
        self.board = [[BoardSpotClass(i, j) for i in range(8)] for j in range(8)]
        self.pieces: list[PieceClass] = []

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

    def init_board(self):
        pieces_list = [RookPiece, KnightPiece, BishopPiece, QueenPiece, KingPiece, BishopPiece, KnightPiece, RookPiece]
        index = 0
        for piece in pieces_list:
            self.pieces.append(piece(index))
            self.board[0][index].set_data(index, (0, index), 1)
            self.pieces[index].set_data((0, index), 1)
            index += 1
        for i in range(8):
            self.pieces.append(PawnPiece(index))
            self.board[1][i].set_data(index, (1, i), 1)
            self.pieces[index].set_data((1, i), 1)
            index += 1
        for i in range(8):
            self.pieces.append(PawnPiece(index))
            self.board[6][i].set_data(index, (6, i), 2)
            self.pieces[index].set_data((6, i), 2)
            index += 1
        pieces_list.reverse()
        for piece_i in range(len(pieces_list)):
            self.pieces.append(pieces_list[piece_i](index))
            self.board[7][piece_i].set_data(index, (7, piece_i), 2)
            self.pieces[index].set_data((7, piece_i), 2)
            index += 1

    def is_target_peace_empty(self, r_index, c_index):
        # print(c_index, r_index)
        return self.board[c_index][r_index].gamer_id == 0

    def get_moves_list(self, position, gamer_id):
        result = []
        piece_index = self.board[position[0]][position[1]].piece_index
        if piece_index is not None:
            piece_move_list = self.pieces[piece_index].get_move_list()
            is_piece_multi_move = self.pieces[piece_index].is_multi_move
            if is_piece_multi_move:
                for move in piece_move_list:
                    i = 1
                    while True:
                        x = position[0] + move[1] * i
                        y = position[1] + move[0] * i
                        if is_valid_coord(x, y):
                            # if self.is_target_peace_empty(x, y):
                            result.append((x, y))
                            i += 1
                            # else:
                            #     break
                        else:
                            break
            else:
                for move in piece_move_list:
                    x = position[0] + move[1]
                    y = position[1] + move[0]
                    if is_valid_coord(x, y):
                        result.append((x, y))
        print(result)

    def play(self):
        self.init_board()
        self.get_moves_list((0, 3), 1)


chess_game = ChessGameClass()
chess_game.play()
print(chess_game)
