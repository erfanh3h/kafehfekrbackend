from Entities.Games.Chess.Piece import PieceClass


class QueenPiece(PieceClass):
    def __init__(self, index):
        super().__init__(index)

    def get_move_list(self) -> list:
        result = [(1, 0), (-1, 0), (0, 1), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]
        return result