import asyncio
import threading
import time

from Commons.wait_times import RPC_Turn_Round_Time, RPC_Sleep_Round_Time, RPC_Sleep_Turn_Round_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.RPC import RPCGameClass
from Controllers.GameSession import BaseGameSession


class RPCGameSession(BaseGameSession):
    def __init__(self, game_id: str):
        super().__init__(game_id)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        elif command_id == commands.Finish_Round:
            pass
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = RPCGameClass(send_data_function=self.send_command)

        def entrypoint():
            self.check_start_game()

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_game(self):
        while True:
            if self.check_all_players_joined():
                self.is_game_running = True
                self.prepare_gamers()
                self.send_game_data()
                self.start_new_turn_round()
                break
            time.sleep(2)

    async def command_received(self, data, socket_id):
        if not self.is_game_running:
            print("game not started yet")
            return
        gamer_id = self.find_gamer_from_socket(socket_id).gamer_id
        if data['id'] == commands.Select_Peace:
            peace_name = data['data']
            is_selection_correct = self.game_controller.check_authority(peace_name, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], peace_name, gamer_id)
        elif data['id'] == commands.Surrender:
            await self.game_controller.surrender(gamer_id)
            self.timer.stop()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command
        self.game_controller.check_turn_round_winner()
        if self.game_controller.is_game_finished:
            print("end game ")
            game_winner = self.game_controller.get_game_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": game_winner}),
                             game_id=self.game_id))
        elif self.game_controller.is_round_finished:
            print("end round ", self.game_controller.current_round)
            round_winner = self.game_controller.get_round_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Round, data={"Winner": round_winner}),
                             game_id=self.game_id))
            self.timer.start(RPC_Sleep_Round_Time, self.send_current_turn)
            self.game_controller.change_round()
        elif self.game_controller.is_turn_round_finished:
            print("end turn round ", self.game_controller.current_turn_round)
            turn_round_winner = self.game_controller.check_winner()
            self.game_controller.change_turn_round()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Round, data={
                    "Winner": turn_round_winner,
                    "P1_selection": self.game_controller.gamer1_round_selection,
                    "P2_selection": self.game_controller.gamer2_round_selection}
                                                       ), game_id=self.game_id))
            self.timer.start(RPC_Sleep_Turn_Round_Time, self.send_current_turn)
            self.game_controller.change_turn_round()
        else:
            self.start_new_turn_round()

    def start_new_turn_round(self):
        print("start turn round ", self.game_controller.current_turn_round)
        from Entities.SocketIOManagerClass import send_command
        self.timer.start(RPC_Turn_Round_Time, self.send_current_turn)
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.New_Turn_Round, data=None), game_id=self.game_id))
