from Entities.Games.Yinsh.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class YinshGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [BoardSpotClass() for i in range(85)]
        self.is_setup_ring_phase = False
        self.player1_score = 0
        self.player2_score = 0

    def get_game_data_yinsh(self, gamer_id):
        data = {"board": self.board}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        # print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            pass
        elif command_id == commands.Remove_Peace:
            pass
        elif command_id == commands.Solve:
            pass
        return False

    def check_game_ended(self):
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        return winner

    def finish_game(self):
        self.is_game_finished = True

    def check_authority(self, data, gamer_id: int):
        return True
