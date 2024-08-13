class boardSpot:
    def __init__(self, index, gamer_id):
        self.index = index
        self.gamer_id = gamer_id
        self.is_selected = False
        self.score = 0

    def __str__(self):
        return str(self.score)

    def select(self, score):
        self.score = score
        self.is_selected = True

    def to_json(self):
        return {"is_selected": self.is_selected, "score": self.score, "gamer_id": self.gamer_id, }
