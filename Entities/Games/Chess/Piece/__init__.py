class PieceClass:
    def __init__(self, gamer_id):
        self.gamer_id = gamer_id
        self.is_multi_move = True
        self.is_first_move = True

    def get_move_list(self) -> list:
        result = []
        return result

    def get_hit_list(self) -> list:
        return self.get_move_list()

    def move(self):
        self.is_first_move = False

    def to_json(self):
        return {}
        # return {"index": self.index, "is_removed": self.is_removed, "gamer_id": self.gamer_id,
        #         "is_first_move": self.is_first_move, "name": self.name}

    def __str__(self):
        return self.gamer_id.__str__()
