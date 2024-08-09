from Entities.Games.Chess.Piece import PieceClass


class BishopPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.name = 'Bishop'

    def get_move_list(self) -> list:
        result = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
        return result