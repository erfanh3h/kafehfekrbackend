import random

from Entities.Games.Yinsh.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class YinshGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [BoardSpotClass() for i in range(85)]
        self.is_setup_ring_phase = True
        self.is_ring_setuped = False
        self.player1_score = 0
        self.player2_score = 0
        self.player1_rings = 2
        self.player2_rings = 2
        self.last_selected_piece_id = -1
        self.disk_count = 51
        self.current_round = 0

    def get_game_data(self):
        board_data = []
        for i in range(85):
            board_data.append(self.board[i].to_json())
        data = {"board": board_data, "player1_score": self.player1_score, "player2_score": self.player2_score,
                "player1_rings": self.player1_rings, "player2_rings": self.player2_rings,
                "last_selected_piece_id": self.last_selected_piece_id, "current_turn": self.current_turn,
                "is_setup_ring_phase": self.is_setup_ring_phase, }
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Submit_Ring:
            self.submit_ring(gamer_id, data)
            await self.send_data_function(commands.Ring_Submited, {'gamer_id': gamer_id, 'piece_id': data})
        elif command_id == commands.Select_Peace:
            self.select_piece(gamer_id, data)
            await self.send_data_function(commands.Peace_Selected, {'gamer_id': gamer_id, 'piece_id': data})
        elif command_id == commands.Move_Ring:
            self.move_ring(gamer_id, data['target_id'], data['rotations_list'])
            self.last_selected_piece_id = -1
            await self.send_data_function(commands.Ring_Moved, {'gamer_id': gamer_id, 'target_id': data['target_id'],
                                                                'rotations_list': data['rotations_list']})
        return False

    def change_turn(self):
        self.is_ring_setuped = False
        self.is_current_turn_played = False
        self.current_round += 1
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1
        if self.player2_rings == 0 and self.player1_rings == 0:
            self.is_setup_ring_phase = False

    def check_game_ended(self):
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        return winner

    def finish_game(self):
        self.is_game_finished = True

    def check_setup_ring_authority(self, data, gamer_id: int):
        if not self.is_setup_ring_phase:
            return False
        if self.is_ring_setuped:
            return False
        return True

    def check_select_piece_authority(self, data, gamer_id: int):
        if self.is_setup_ring_phase:
            return False
        return True

    def check_move_ring_authority(self, data, gamer_id: int):
        if self.is_setup_ring_phase:
            return False
        return True

    def check_win_happened(self):
        return True

    def submit_ring(self, gamer_id, piece_id):
        self.board[piece_id].set_ring(gamer_id)
        if gamer_id == 1:
            self.player1_rings -= 1
        else:
            self.player2_rings -= 1
        self.is_ring_setuped = True

    def select_piece(self, gamer_id, piece_id):
        self.board[piece_id].set_disk(gamer_id)
        self.disk_count -= 1
        self.last_selected_piece_id = piece_id

    def move_ring(self, gamer_id, target_id, rotations_list):
        self.board[target_id].set_ring(gamer_id)
        self.board[self.last_selected_piece_id].set_ring(None)
        for piece_id in rotations_list:
            if self.board[piece_id].disk_user is not None and self.board[piece_id].disk_user == 1:
                self.board[piece_id].set_disk(2)
            elif self.board[piece_id].disk_user is not None and self.board[piece_id].disk_user == 2:
                self.board[piece_id].set_disk(1)
        if self.check_win_happened():
            pass

    def remove_disk(self, piece_id):
        self.board[piece_id].set_disk(None)

    def extract_random_piece_for_auto_ring(self):
        number = random.randint(0, 84)
        if self.board[number].ring_user is None:
            return number
        else:
            return self.extract_random_piece_for_auto_ring()
