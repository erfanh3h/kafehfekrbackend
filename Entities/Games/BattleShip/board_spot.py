class boardSpot(object):

    def __init__(self):
        self.is_selected = False
        self.number = 0

    def select(self):
        self.is_selected = True

    def set_number(self, number):
        self.number = number

    def __str__(self):
        return str(self.number)

    def is_ship(self):
        if self.number != 0:
            return True
        return False

    def to_json(self, show_ship=False):
        if self.is_selected or show_ship:
            return {"is_selected": self.is_selected, "number": self.number}
        else:
            return {"is_selected": False, "number": 0}
