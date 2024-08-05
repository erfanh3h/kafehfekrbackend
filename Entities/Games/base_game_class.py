from Commons import commands


class BaseGameClass:
    def __init__(self, send_data_function):
        self.current_turn = 1
        self.send_data_function = send_data_function
        self.is_game_finished = False
        self.is_round_finished = False
        self.is_turn_round_finished = False

    def get_game_data(self):
        pass

    def start_game(self):
        pass

    def play_round(self):
        pass

    async def recieve_data(self, command_id, data, gamer_id):
        pass

    def change_round(self):
        pass

    def change_turn(self):
        pass

    def create_board_map(self):
        pass

    def check_authority(self, data, gamer_id: int):
        pass

    def check_winner(self):
        pass

    def get_game_winner(self):
        pass

    def check_game_ended(self):
        pass

    async def surrender(self, gamer_id):
        self.is_game_finished = True
        await self.send_data_function(commands.Surrender, {"gamer_id": gamer_id})

    def finish_reconnect_time(self, user_id):
        self.is_game_finished = True
