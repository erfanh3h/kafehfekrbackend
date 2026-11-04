from Commons.static_functions import safe_run_async
import asyncio
import threading
import time

from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import RPC_Turn_Round_Time, RPC_Sleep_Round_Time, RPC_Sleep_Turn_Round_Time
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

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_game(self):
        while not self.is_game_finished:
            if self.check_all_players_joined():
                time.sleep(0.8)
                self.is_game_running = True
                self.timer.stop(False)
                self.prepare_gamers()
                self.send_game_data(self.start_new_turn_round)
                break
            time.sleep(0.3)

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
        self.timer.stop(False)
        if self.is_game_finished:
            return
        self.game_controller.check_turn_round_winner()
        if self.game_controller.is_game_finished:
            def finish_after_clash():
                if self.is_game_finished:
                    return
                self.check_finish_game()

            self.check_and_send_turn_round_winner()
            self.timer.start(RPC_Sleep_Turn_Round_Time, finish_after_clash, is_user_turn=False)

        elif self.game_controller.is_round_finished:
            self.check_and_send_turn_round_winner()
            self.check_and_send_round_winner()
            self.game_controller.change_round()

            def start_next_round():
                if self.is_game_finished or self.game_controller.is_game_finished:
                    return
                safe_run_async(
                    send_command(command=make_command_json(id=commands.New_Round, data=self.game_controller.current_round),
                                 game_id=self.game_id))
                self.start_new_turn_round()

            self.timer.start(RPC_Sleep_Round_Time, start_next_round, is_user_turn=False)

        elif self.game_controller.is_turn_round_finished:
            self.check_and_send_turn_round_winner()
            self.game_controller.change_turn_round()
            self.timer.start(RPC_Sleep_Turn_Round_Time, self.start_new_turn_round, is_user_turn=False)
        else:
            self.start_new_turn_round()

    def start_new_turn_round(self):
        if self.is_game_finished or self.game_controller.is_game_finished:
            return
        from Entities.SocketIOManagerClass import send_command
        self.timer.start(RPC_Turn_Round_Time, self.send_current_turn, is_user_turn=True)
        safe_run_async(
            send_command(command=make_command_json(id=commands.New_Turn_Round, data=None), game_id=self.game_id))

    def check_and_send_turn_round_winner(self):
        from Entities.SocketIOManagerClass import send_command
        turn_round_winner = self.game_controller.turn_round_winner
        safe_run_async(
            send_command(command=make_command_json(id=commands.Finish_Turn_Round, data={
                "Winner": turn_round_winner,
                "P1_selection": self.game_controller.gamer1_round_selection.value,
                "P2_selection": self.game_controller.gamer2_round_selection.value}
                                                   ), game_id=self.game_id))

    def check_and_send_round_winner(self):
        if self.game_controller.is_round_finished:
            from Entities.SocketIOManagerClass import send_command
            round_winner = self.game_controller.get_round_winner()
            safe_run_async(
                send_command(command=make_command_json(id=commands.Finish_Round, data={"Winner": round_winner}),
                             game_id=self.game_id))
