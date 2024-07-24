from Entities.Games.RPC.rpc_model import RPCModel, string_to_rpc_enum
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class RPCGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [0 for i in range(9)]
        self.win_conditions = [[RPCModel.Rock, RPCModel.Cutter], [RPCModel.Cutter, RPCModel.Paper],
                               [RPCModel.Paper, RPCModel.Rock]]
        self.round_count = 2
        self.turn_round_count = 5
        self.current_round = 1
        self.current_turn_round = 1
        self.gamer1_round_score = 0
        self.gamer2_round_score = 0
        self.gamer1_total_score = 0
        self.gamer2_total_score = 0
        self.gamer1_round_selection = RPCModel.Rock
        self.gamer2_round_selection = RPCModel.Rock

    def get_game_data(self):
        data = {"round_scores": [self.gamer1_round_score, self.gamer2_round_score],
                "total_scores": [self.gamer1_total_score, self.gamer2_total_score],
                "current_round": self.current_round, "currentturn__round": self.current_turn_round, }
        return data

    def change_round(self):
        self.is_turn_round_finished = False
        self.is_round_finished = False
        self.gamer1_round_selection = RPCModel.Rock
        self.gamer2_round_selection = RPCModel.Rock
        self.gamer1_round_score = 0
        self.gamer2_round_score = 0
        self.current_round += 1
        self.current_turn_round = 1

    def change_turn_round(self):
        self.is_turn_round_finished = False
        self.current_turn_round += 1
        self.gamer1_round_selection = RPCModel.Rock
        self.gamer2_round_selection = RPCModel.Rock

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if gamer_id == 1:
            self.gamer1_round_selection = string_to_rpc_enum(string=data)
        else:
            self.gamer2_round_selection = string_to_rpc_enum(string=data)

    def check_turn_round_winner(self):
        winner = self.check_winner()
        if self.current_turn_round == self.turn_round_count:
            if self.current_round != self.round_count:
                self.is_round_finished = True
                if self.gamer1_round_score > self.gamer2_round_score:
                    self.gamer1_total_score +=1
                elif self.gamer2_round_score > self.gamer1_round_score:
                    self.gamer2_total_score +=1
            else:
                self.is_game_finished = True
        else:
            self.is_turn_round_finished = True
        return winner

    def check_authority(self, data, gamer_id: int):
        print("akbar")
        return True

    def check_winner(self):
        winner = 0
        for condition in self.win_conditions:
            if self.gamer1_round_selection == condition[0] and self.gamer2_round_selection == condition[1]:
                winner = self.symbol_1
                self.gamer1_round_score += 1
                break
            if self.gamer2_round_selection == condition[0] and self.gamer1_round_selection == condition[1]:
                winner = self.symbol_2
                self.gamer1_round_score += 1
                break
        return winner

    def get_round_winner(self):
        if self.gamer1_round_score > self.gamer2_round_score:
            return self.symbol_1
        elif self.gamer2_round_score > self.gamer1_round_score:
            return self.symbol_2
        else:
            return 0

    def get_game_winner(self):
        if self.gamer1_total_score > self.gamer2_total_score:
            return self.symbol_1
        elif self.gamer2_total_score > self.gamer1_total_score:
            return self.symbol_2
        else:
            return None

    def change_turn(self):
        pass

    async def surrender(self, gamer_id):
        self.is_game_finished = True
        if gamer_id == 1:
            game_winner = 2
        else:
            game_winner = 1
        await self.send_data_function(commands.Surrender, {"gamer_id": gamer_id})
