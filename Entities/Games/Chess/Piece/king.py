from Entities.Games.Chess.Piece import PieceClass


class KingPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.is_multi_move = False
        self.name = 'King'

    def get_move_list(self) -> list:
        result = [(1, 0), (-1, 0), (0, 1), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]
        if self.is_first_move:
            result.append((0, 2))
            result.append((0, -2))
        return result
