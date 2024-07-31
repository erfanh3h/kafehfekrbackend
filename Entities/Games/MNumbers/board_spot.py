class boardSpot:

    def __init__(self):
        self.value = 0
        self.equipped_user = 0

    def __str__(self):
        return str(self.value)

    def to_json(self):
        return {"value": self.value, "equipped_user": self.equipped_user}

    def to_empty_json(self):
        return {"value": 0, "equipped_user": 0}
