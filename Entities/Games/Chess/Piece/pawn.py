from Entities.Games.Chess.Piece import PieceClass


class PawnPiece(PieceClass):
    def __init__(self, gamer_id):
        super().__init__(gamer_id)
        self.is_multi_move = False
        self.name = 'Pawn'

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