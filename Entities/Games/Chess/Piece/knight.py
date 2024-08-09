from Entities.Games.Chess.Piece import PieceClass


class KnightPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)
        self.is_multi_move = False

    def get_move_list(self) -> list:
        result = [(-2, 1), (-1, 2), (1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1)]
        return result