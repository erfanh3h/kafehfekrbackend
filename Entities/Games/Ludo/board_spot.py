class BoardSpotClass:

    def __init__(self):
        self.count = 0
        self.equipped_user = 0

    def __str__(self):
        return str(self.count)

    def add_piece(self, equipped_user, count=1):
        self.count += count
        self.equipped_user = equipped_user

    def remove_piece(self, count=1):
        self.count -= count
        if self.count == 0:
            self.equipped_user = 0

    def clear(self):
        self.count = 0
        self.equipped_user = 0

    def is_empty(self):
        return self.equipped_user == 0

    def is_gamer_id_spot(self, gamer_id):
        return self.equipped_user == gamer_id

    def is_enemy_spot(self, gamer_id):
        print(gamer_id , self.equipped_user)
        return self.equipped_user != 0 and self.equipped_user != gamer_id

    def to_json(self):
        return {"count": self.count, "equipped_user": self.equipped_user}
