import asyncio
import threading
import time

from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import RPC_Turn_Round_Time, RPC_Sleep_Round_Time, RPC_Sleep_Turn_Round_Time, \
    Join_Game_Limit_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.RPC import RPCGameClass
from Controllers.GameSession import BaseGameSession


class RPCGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = RPCGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.RPC

        def entrypoint():
            self.check_start_game()

        self.timer.start(Join_Game_Limit_Time, self.join_game_limit_time)
        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_game(self):
        while True:
            if self.is_game_terminated:
                break
            if self.check_all_players_joined():
                self.is_game_running = True
                self.timer.stop()
                self.prepare_gamers()
                self.send_game_data(self.start_new_turn_round)
                break
            time.sleep(2)

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            peace_name = data['data']
            is_selection_correct = self.game_controller.check_authority(peace_name, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], peace_name, gamer_id)

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command
        self.game_controller.check_turn_round_winner()
        if self.game_controller.is_game_finished:
            def function2():
                winner_id = self.game_controller.get_game_winner()
                asyncio.new_event_loop().run_until_complete(
                    send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner_id}),
                                 game_id=self.game_id))
                self.finish_game(winner_id)

            def function1():
                self.check_and_send_round_winner()
                self.timer.start(3, function2)

            self.check_and_send_turn_round_winner()
            self.timer.start(3, function1)

        elif self.game_controller.is_round_finished:
            def function():
                self.check_and_send_round_winner()
                self.timer.start(RPC_Sleep_Round_Time, self.start_new_turn_round)
                self.game_controller.change_round()

            self.check_and_send_turn_round_winner()
            self.timer.start(RPC_Sleep_Round_Time, function)
            #print("end round ", self.game_controller.current_round)

        elif self.game_controller.is_turn_round_finished:
            #print("end turn round ", self.game_controller.current_turn_round)
            self.check_and_send_turn_round_winner()
            self.timer.start(RPC_Sleep_Turn_Round_Time, self.start_new_turn_round)
            self.game_controller.change_turn_round()
        else:
            self.start_new_turn_round()

    def start_new_turn_round(self):
        #print("start turn round ", self.game_controller.current_turn_round)
        from Entities.SocketIOManagerClass import send_command
        self.timer.start(RPC_Turn_Round_Time, self.send_current_turn)
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.New_Turn_Round, data=None), game_id=self.game_id))

    def check_and_send_turn_round_winner(self):
        from Entities.SocketIOManagerClass import send_command
        turn_round_winner = self.game_controller.turn_round_winner
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Finish_Turn_Round, data={
                "Winner": turn_round_winner,
                "P1_selection": self.game_controller.gamer1_round_selection.value,
                "P2_selection": self.game_controller.gamer2_round_selection.value}
                                                   ), game_id=self.game_id))

    def check_and_send_round_winner(self):
        if self.game_controller.is_round_finished:
            from Entities.SocketIOManagerClass import send_command
            round_winner = self.game_controller.get_round_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Round, data={"Winner": round_winner}),
                             game_id=self.game_id))
