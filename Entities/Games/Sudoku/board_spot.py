class BoardSpotClass:
    def __init__(self, number=0):
        self.number = number
        self.is_base_number = True

    def set_number(self, number):
        self.number = number

    def clear_number(self):
        self.number = 0
        self.is_base_number = False

    def __str__(self):
        return self.number.__str__()

    def to_json(self):
        return {"is_base_number": self.is_base_number, "number": self.number,}
