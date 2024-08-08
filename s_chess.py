"""CONVENTIONS:
positions are done row-column from the bottom left and are both numbers. This corresponds to the alpha-number system in traditional chess while being computationally useful. they are specified as tuples
"""
import itertools

WHITE = "white"
BLACK = "black"


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
        # if self.piece_index is None:
        #     return self.gamer_id.__str__()
        # else:
        #     return self.piece_index.__str__()


def get_piece_of_coordinate(x, y):
    piece_number = y * 8 + x
    return piece_number


class PieceClass:
    def __init__(self, index):
        self.position = None
        self.index = index
        self.is_removed = False
        self.gamer_id = 0

    def set_data(self, position: tuple, gamer_id: int):
        self.position = position
        self.gamer_id = gamer_id

    def remove_piece(self):
        self.is_removed = True
        self.position = None

    def get_move_list(self) -> list:
        return []

    def move_to_position(self, position: tuple):
        self.position = position

    def __str__(self):
        return f""


class PawnPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)


class RookPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)


class KnightPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)


class BishopPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)


class QueenPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)


class KingPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)


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

    def play(self):
        self.init_board()


chess_game = ChessGameClass()
chess_game.play()
print(chess_game)
