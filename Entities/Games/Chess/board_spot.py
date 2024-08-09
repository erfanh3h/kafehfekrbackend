from Entities.Games.Chess import PieceClass


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

    def to_json(self):
        return {}
        # return {"gamer_id": self.gamer_id, "piece_index": self.piece_index, "position": self.position}