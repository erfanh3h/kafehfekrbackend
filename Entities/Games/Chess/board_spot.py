class BoardSpotClass:
    def __init__(self, r_index, c_index):
        self.position = (r_index, c_index)
        self.piece_index = None
        self.gamer_id = 0

    def set_data(self, piece_id: int, position: tuple, gamer_id: int):
        self.piece_index = piece_id
        self.gamer_id = gamer_id
        self.position = position

    def set_gamer_id(self, gamer_id: int, piece_id: int = None):
        self.gamer_id = gamer_id
        self.piece_index = piece_id

    def remove_pawn_gamer(self):
        self.piece_index = None

    def to_json(self):
        return {"gamer_id": self.gamer_id, "piece_index": self.piece_index, "position": self.position}

    def __str__(self):
        return self.gamer_id.__str__()
