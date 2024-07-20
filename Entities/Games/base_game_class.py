
class BaseGameClass:
    def __init__(self, send_data_function):
        self.symbol_1 = "0"
        self.symbol_2 = "1"
        self.symbol_3 = "2"
        self.symbol_4 = "3"
        self.current_turn = 0
        self.send_data_function = send_data_function

    def start_game(self):
        pass

    def play_round(self):
        pass

    async def recieve_data(self, command_id, data, gamer_id):
        pass

    def check_end(self):
        pass
