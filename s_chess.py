"""CONVENTIONS:
positions are done row-column from the bottom left and are both numbers. This corresponds to the alpha-number system in traditional chess while being computationally useful. they are specified as tuples
"""
WHITE = "white"
BLACK = "black"


def is_valid_coord(col, row):
    if 0 <= row < 8 and 0 <= col < 8:
        return True
    return False


class PieceClass:
    def __init__(self, gamer_id):
        self.gamer_id = gamer_id
        self.move_list: list[tuple] = []
        self.is_removed = False
        self.is_multi_move = True
        self.is_first_move = True

    def remove_piece(self):
        self.is_removed = True

    def get_move_list(self) -> list:
        result = []
        return result

    def get_hit_list(self) -> list:
        return self.get_move_list()

    def move(self):
        self.is_first_move = False

    def __str__(self):
        return self.gamer_id.__str__()


class BoardSpotClass:
    def __init__(self, r_index, c_index):
        self.position = (r_index, c_index)
        self.piece: PieceClass = PieceClass(0)

    def set_data(self, piece: PieceClass):
        self.piece = piece

    def __str__(self):
        if self.piece is not None:
            return self.piece.__str__()
        else:
            return ""


def get_piece_of_coordinate(x, y):
    piece_number = y * 8 + x
    return piece_number


class PawnPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.is_multi_move = False

    def get_move_list(self) -> list:
        result = []
        if self.gamer_id == 1:
            result.append((1, 0))
        else:
            result.append((-1, 0))
        return result

    def get_hit_list(self) -> list:
        result = []
        if self.gamer_id == 1:
            result = [(1, -1), (1, 1)]
        else:
            result = [(-1, -1), (-1, 1)]
        return result


class RookPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)

    def get_move_list(self) -> list:
        result = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        return result


class KnightPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.is_multi_move = False

    def get_move_list(self) -> list:
        result = [(-2, 1), (-1, 2), (1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1)]
        return result


class BishopPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)

    def get_move_list(self) -> list:
        result = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
        return result


class QueenPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)

    def get_move_list(self) -> list:
        result = [(1, 0), (-1, 0), (0, 1), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]
        return result


class KingPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.is_multi_move = False

    def get_move_list(self) -> list:
        result = [(1, 0), (-1, 0), (0, 1), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]
        return result


class ChessGameClass:
    def __init__(self):
        self.board = [[BoardSpotClass(i, j) for i in range(8)] for j in range(8)]

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

    def is_target_piece_empty(self, c_index, r_index):
        return self.board[c_index][r_index].piece.gamer_id == 0

    def is_target_piece_enemey(self, c_index, r_index, gamer_id):
        return self.board[c_index][r_index].piece.gamer_id == 0 and self.board[c_index][
            r_index].piece.gamer_id != gamer_id

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

    def play(self):
        self.init_board()
        print(self)
        move_result = self.get_moves_list((0, 0), 1)
        self.get_hit_list((0, 7), 1)
        self.move_piece((1, 7), (2, 7), 1)
        print(self)


chess_game = ChessGameClass()
chess_game.play()
# print(chess_game)
