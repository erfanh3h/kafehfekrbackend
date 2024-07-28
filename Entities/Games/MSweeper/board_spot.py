class boardSpot(object):
    value = 0
    selected = False
    select_mine = False
    mine = False

    def __init__(self):
        self.selected = False

    def __str__(self):
        return str(self.value)

    def is_mine(self):
        if self.value == -1:
            return True
        return False
