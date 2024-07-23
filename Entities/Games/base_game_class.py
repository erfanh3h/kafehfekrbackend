class BaseGameClass:
    def __init__(self, send_data_function):
        self.current_turn = 1
        self.send_data_function = send_data_function
        self.is_game_finished = False
        self.is_round_finished = False

    def get_game_data(self):
        pass

    def start_game(self):
        pass

    def play_round(self):
        pass

    async def recieve_data(self, command_id, data, gamer_id):
        pass

    def check_end(self):
        pass

    def change_turn(self):
        pass

    def create_board_map(self):
        pass

    async def surrender(self , gamer_id):
        pass
