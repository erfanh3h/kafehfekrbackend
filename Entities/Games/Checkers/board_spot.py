class BoardSpotClass:
    def __init__(self, r_index, c_index):
        self.r_index = r_index
        self.c_index = c_index
        self.pawn_gamer_id = 0
        self.is_super_pawn = False

    def set_pawn_gamer_id(self, pawn_gamer_id, is_super_pawn=False):
        self.pawn_gamer_id = pawn_gamer_id
        self.is_super_pawn = is_super_pawn

    def remove_pawn_gamer(self):
        self.pawn_gamer_id = 0
        self.is_super_pawn = False

    def __str__(self):
        return self.pawn_gamer_id.__str__()

    def to_json(self):
        return {"pawn_gamer_id": self.pawn_gamer_id, "is_super_pawn": self.is_super_pawn}
