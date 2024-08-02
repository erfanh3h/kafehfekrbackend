import asyncio
import time

from Entities.Games.Checkers import CheckersGameClass
from Entities.Games.wait_times import Checkers_Turn_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class CheckersGameSession(BaseGameSession):
    def __init__(self, game_id: str):
        super().__init__(game_id)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        elif command_id == commands.Finish_Round:
            pass
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = CheckersGameClass(send_data_function=self.send_command)
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        if not self.is_game_running:
            print("game not started yet")
            return
        gamer_id = self.find_gamer_from_socket(socket_id).gamer_id
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            is_selection_authorized = self.game_controller.check_authority(peace_id, gamer_id)
            if is_selection_authorized:
                is_selection_correct = await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                if is_selection_correct:
                    self.timer.stop()
        elif data['id'] == commands.Surrender:
            await self.game_controller.surrender(gamer_id)
            self.timer.stop()

    def send_current_turn(self):
        if self.game_controller.is_game_finished or self.game_controller.is_round_finished:
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                         game_id=self.game_id))
        self.timer.start(Checkers_Turn_Time, self.send_current_turn)

