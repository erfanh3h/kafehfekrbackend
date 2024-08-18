class BoardSpotClass:

    def __init__(self):
        self.value = 0
        self.equipped_user = 0

    def set_value(self, value: int, equipped_user: int):
        self.value = value
        self.equipped_user = equipped_user

    def __str__(self):
        return str(self.value)

    def to_json(self):
        return {"value": self.value, "equipped_user": self.equipped_user}