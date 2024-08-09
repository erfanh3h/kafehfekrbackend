class PieceClass:
    def __init__(self, index):
        self.position: tuple = (0, 0)
        self.index = index
        self.is_removed = False
        self.gamer_id = 0
        self.move_list: list[tuple] = []
        self.is_multi_move = True
        self.is_first_move = True
        self.name = ""

    def set_data(self, position: tuple, gamer_id: int):
        self.position = position
        self.gamer_id = gamer_id

    def remove_piece(self):
        self.is_removed = True
        self.position = None

    def get_move_list(self) -> list:
        result = []
        return result

    def get_hit_list(self) -> list:
        return self.get_move_list()

    def move_to_position(self, position: tuple):
        self.position = position
        self.is_first_move = False

    def to_json(self):
        return {"index": self.index, "is_removed": self.is_removed, "gamer_id": self.gamer_id,
                "is_first_move": self.is_first_move, "name": self.name}

    def __str__(self):
        return f""
