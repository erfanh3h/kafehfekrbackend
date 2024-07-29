class boardSpot(object):
    value = 0
    selected = False
    correctly_selected_mine = False
    wrongly_selected_mine = False
    hitted_mine = False
    mine = False

    def __init__(self):
        self.selected = False

    def __str__(self):
        return str(self.value)

    def is_mine(self):
        if self.value == -1:
            return True
        return False

    def to_json(self):
        return {"selected": self.selected, "correctly_selected_mine": self.correctly_selected_mine,
                "wrongly_selected_mine": self.wrongly_selected_mine, "hitted_mine": self.hitted_mine, "mine": self.mine,
                "value": self.value}
