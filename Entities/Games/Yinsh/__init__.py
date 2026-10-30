import random

from Entities.Games.Yinsh.board_spot import BoardSpotClass
from Entities.Games.Yinsh.directions import all_piece_directions, all_directions_list, dooz_directions_list
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
        self.player1_rings = 5
        self.player2_rings = 5
        self.last_selected_piece_id = -1
        self.disk_count = 51
        self.current_round = 0
        self.removed_rings = []
        self.win_happens_data = []
        self.pending_ring_removals = []
        self.current_remover = 0
        self.init_directions()

    def init_directions(self):
        for i in range(85):
            self.board[i].set_direction(all_piece_directions[i])

    def get_game_data(self):
        board_data = []
        for i in range(85):
            board_data.append(self.board[i].to_json())
        data = {"board": board_data, "player1_score": self.player1_score, "player2_score": self.player2_score,
                "player1_rings": self.player1_rings, "player2_rings": self.player2_rings,
                "last_selected_piece_id": self.last_selected_piece_id, "current_turn": self.current_turn,
                "is_setup_ring_phase": self.is_setup_ring_phase, 'disk_count': self.disk_count,
                "current_remover": self.current_remover}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        # print(command_id, data, gamer_id)
        if command_id == commands.Submit_Ring:
            piece_id = int(data)
            self.submit_ring(gamer_id, piece_id)
            await self.send_data_function(commands.Ring_Submited, {'gamer_id': gamer_id, 'piece_id': piece_id})
        elif command_id == commands.Select_Peace:
            piece_id = int(data)
            self.select_piece(gamer_id, piece_id)
            await self.send_data_function(commands.Peace_Selected, {'gamer_id': gamer_id, 'piece_id': piece_id})
        elif command_id == commands.Move_Ring:
            target_id = int(data['target_id']) if isinstance(data, dict) else int(data)
            rotation_list = self.get_list_of_rotations(target_id)
            self.move_ring(gamer_id, target_id, rotation_list)
            self.removed_rings = []
            self.win_happens_data = self.check_win_happened(rotation_list)
            await self.send_data_function(commands.Ring_Moved,
                                          {'gamer_id': gamer_id, 'source_id': self.last_selected_piece_id,
                                           'target_id': target_id, 'rotations_list': rotation_list})
            self.last_selected_piece_id = -1
            if len(self.win_happens_data) > 0:
                for win_data in self.win_happens_data:
                    for piece_id in win_data['data']:
                        self.remove_disk(piece_id)
                    self.pending_ring_removals.append(int(win_data['gamer_id']))
                self.current_remover = self.pending_ring_removals[0]
                await self.send_data_function(commands.Win_Happened,
                                              {'win_data': list(self.win_happens_data),
                                               'removed_rings': [],
                                               'current_remover': self.current_remover})
                self.win_happens_data.clear()
        elif command_id == commands.Select_Remove_Peace:
            ring_id = int(data['piece_id']) if isinstance(data, dict) and 'piece_id' in data else int(data)
            self.remove_gamer_ring(gamer_id, ring_id)
            if len(self.pending_ring_removals) > 0:
                if self.pending_ring_removals[0] == gamer_id:
                    self.pending_ring_removals.pop(0)
                elif gamer_id in self.pending_ring_removals:
                    self.pending_ring_removals.remove(gamer_id)
            self.current_remover = self.pending_ring_removals[0] if len(self.pending_ring_removals) > 0 else 0
            await self.send_data_function(commands.Win_Happened,
                                          {'win_data': [],
                                           'removed_rings': [ring_id],
                                           'gamer_id': gamer_id,
                                           'current_remover': self.current_remover})
        return False

    def change_turn(self):
        self.removed_rings = []
        self.win_happens_data = []
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
        if self.is_game_finished:
            return True
        if self.player1_score >= 3 or self.player2_score >= 3:
            return True
        if self.disk_count == 0:
            return True
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_score >= 3 and self.player1_score > self.player2_score:
                winner = 1
            elif self.player2_score >= 3 and self.player2_score > self.player1_score:
                winner = 2
            elif self.player1_score > self.player2_score:
                winner = 1
            elif self.player2_score > self.player1_score:
                winner = 2
            else:
                winner = 0
        return winner

    def finish_game(self):
        self.is_game_finished = True

    def check_setup_ring_authority(self, data, gamer_id: int):
        if not self.is_setup_ring_phase:
            return False
        if self.is_ring_setuped:
            return False
        if gamer_id != self.current_turn:
            return False
        if not isinstance(data, (int, float)):
            return False
        piece_id = int(data)
        if piece_id < 0 or piece_id >= 85:
            return False
        if self.board[piece_id].ring_user is not None or self.board[piece_id].disk_user is not None:
            return False
        return True

    def check_select_piece_authority(self, data, gamer_id: int):
        if self.is_setup_ring_phase or self.current_remover != 0:
            return False
        if gamer_id != self.current_turn:
            return False
        if self.last_selected_piece_id != -1:
            return False
        if not isinstance(data, (int, float)):
            return False
        piece_id = int(data)
        if piece_id < 0 or piece_id >= 85:
            return False
        if self.board[piece_id].ring_user != gamer_id:
            return False
        return True

    def check_move_ring_authority(self, data, gamer_id: int):
        if self.is_setup_ring_phase or self.current_remover != 0:
            return False
        if gamer_id != self.current_turn:
            return False
        if self.last_selected_piece_id == -1:
            return False
        raw_target = data.get('target_id') if isinstance(data, dict) else data
        if not isinstance(raw_target, (int, float)):
            return False
        target_id = int(raw_target)
        if target_id < 0 or target_id >= 85:
            return False
        if self.board[target_id].ring_user is not None or self.board[target_id].disk_user is not None:
            return False
        return True

    def check_remove_ring_authority(self, data, gamer_id: int):
        if self.is_setup_ring_phase:
            return False
        if self.current_remover != gamer_id and gamer_id not in self.pending_ring_removals:
            return False
        raw_id = data.get('piece_id') if isinstance(data, dict) else data
        if not isinstance(raw_id, (int, float)):
            return False
        piece_id = int(raw_id)
        if piece_id < 0 or piece_id >= 85:
            return False
        if self.board[piece_id].ring_user != gamer_id:
            return False
        return True

    def remove_gamer_ring(self, gamer_id, ring_id):
        if 0 <= ring_id < 85 and self.board[ring_id].ring_user == gamer_id:
            self.board[ring_id].set_ring(None)
        if gamer_id == 1:
            self.player1_score += 1
        else:
            self.player2_score += 1

    def get_random_gamer_ring(self, gamer_id):
        gamer_rings = []
        for i in range(85):
            if self.board[i].ring_user == gamer_id:
                gamer_rings.append(i)
        if not gamer_rings:
            if gamer_id == 1:
                self.player1_score += 1
            else:
                self.player2_score += 1
            return 0
        random_id = random.choice(gamer_rings)
        self.board[random_id].set_ring(None)
        if gamer_id == 1:
            self.player1_score += 1
        else:
            self.player2_score += 1
        return random_id

    def apply_win_happen(self, data):
        piece_idis = data['data']
        gamer_id = data['gamer_id']
        for piece_id in piece_idis:
            self.remove_disk(piece_id)
        random_ring_id = self.get_random_gamer_ring(gamer_id)
        return random_ring_id

    def check_win_happened(self, rotation_list):
        result = {}
        final_result = []

        def check_piece_id_counted_before(piece):
            # this function use to prevent cross dooz condition
            for data in final_result:
                if piece in data['data']:
                    return True
            return False

        result[self.last_selected_piece_id] = self.get_list_of_possible_dooz(self.last_selected_piece_id)
        for piece_id in rotation_list:
            result[piece_id] = self.get_list_of_possible_dooz(piece_id)
        for piece_id in result.keys():
            for direction_id in result[piece_id]:
                if len(result[piece_id][direction_id]) >= 5 and not check_piece_id_counted_before(piece_id):
                    result_data = {'data': result[piece_id][direction_id], 'gamer_id': self.board[piece_id].disk_user}
                    final_result.append(result_data)
        return final_result

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

    def remove_disk(self, piece_id):
        self.board[piece_id].set_disk(None)
        self.disk_count += 1

    def extract_random_piece_for_auto_ring(self):
        number = random.randint(0, 84)
        if self.board[number].ring_user is None:
            return number
        else:
            return self.extract_random_piece_for_auto_ring()

    def check_piece_have_same_disk_in_direction(self, direction_id, start_piece_id):
        result = None
        for direction in self.board[start_piece_id].directions:
            if direction[0] == direction_id:
                if (self.board[direction[1]].disk_user is not None and
                        self.board[direction[1]].disk_user == self.board[start_piece_id].disk_user):
                    result = direction
                else:
                    result = None
                break
        return result

    def check_piece_have_neighbour_in_direction(self, direction_id, start_piece_id):
        result = None, False
        for direction in self.board[start_piece_id].directions:
            if direction[0] == direction_id:
                if self.board[direction[1]].ring_user is not None:
                    result = None, False
                else:
                    result = direction, (self.board[direction[1]].disk_user is not None)
                break
        return result

    def get_dooz_idies(self, direction_id, start_piece_id):
        check_move_list = []
        result = []
        have_neighbour = self.check_piece_have_same_disk_in_direction(direction_id, start_piece_id)
        if have_neighbour is not None:
            result.append(have_neighbour[1])
            check_move_list.append(have_neighbour[1])
        while len(check_move_list) > 0:
            have_neighbour = self.check_piece_have_same_disk_in_direction(direction_id, check_move_list[0])
            if have_neighbour is not None:
                result.append(have_neighbour[1])
                check_move_list.append(have_neighbour[1])
            check_move_list.pop(0)
        return result

    def get_direction_idies(self, direction_id, start_piece_id):
        check_move_list = []
        result = []

        def disk_func(piece_id):
            next_neighbour_data, next_is_disk = self.check_piece_have_neighbour_in_direction(direction_id, piece_id)
            if next_neighbour_data is not None:
                result.append(next_neighbour_data[1])
                if next_is_disk:
                    disk_func(next_neighbour_data[1])

        neighbour_data, is_disk = self.check_piece_have_neighbour_in_direction(direction_id, start_piece_id)
        if neighbour_data is not None:
            result.append(neighbour_data[1])
            if is_disk:
                disk_func(neighbour_data[1])
            else:
                check_move_list.append(neighbour_data[1])
        while len(check_move_list) > 0:
            neighbour_data, is_disk = self.check_piece_have_neighbour_in_direction(direction_id, check_move_list[0])
            if neighbour_data is not None:
                result.append(neighbour_data[1])
                if is_disk:
                    disk_func(neighbour_data[1])
                else:
                    check_move_list.append(neighbour_data[1])
            check_move_list.pop(0)
        return result

    def get_list_of_possible_dooz(self, piece_id):
        result = {}
        for direction_list in dooz_directions_list:
            index = 0
            result[direction_list[0]] = []
            for direction_id in direction_list:
                result[direction_list[0]].extend(self.get_dooz_idies(direction_id, piece_id))
                index += 1
                if index == 1:  # each piece is center of neighbours list and must added
                    result[direction_list[0]].append(piece_id)
        return result

    def get_list_of_rotations(self, piece_id):
        result = {}
        for direction_id in all_directions_list:
            result[direction_id] = self.get_direction_idies(direction_id, self.last_selected_piece_id)
        target_direction_id = None
        for direction_id in result.keys():
            for pId in result[direction_id]:
                if pId == piece_id:
                    target_direction_id = direction_id
                    break
        if target_direction_id is None:
            return []
        final_result = []
        for pId in result[target_direction_id]:
            if self.board[pId].disk_user is not None:
                final_result.append(pId)
            if pId == piece_id:
                break
        return final_result
