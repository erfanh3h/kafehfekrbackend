from Entities.Games.Chess.Piece import PieceClass


class RookPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.name = 'Rook'

    def get_move_list(self) -> list:
        result = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        return result
