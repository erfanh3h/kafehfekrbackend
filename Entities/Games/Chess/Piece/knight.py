from Entities.Games.Chess.Piece import PieceClass


class KnightPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.is_multi_move = False
        self.name = 'knight'

    def get_move_list(self) -> list:
        result = [(-2, 1), (-1, 2), (1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1)]
        return result