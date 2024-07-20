class BaseGameClass:
    def __init__(self):
        self.symbol_1 = "1"
        self.symbol_2 = "2"
        self.symbol_3 = "3"
        self.symbol_4 = "4"
        self.current_turn = 0

    def start_game(self):
        pass

    def play_round(self):
        pass

    def recieve_data(self, data):
        pass

    def check_end(self):
        pass
