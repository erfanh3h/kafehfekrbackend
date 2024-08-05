import asyncio
import time

from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import TicTacToe_Turn_Time, TicTacToe_Sleep_Round_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.TicTacToe import TicTacToeGameClass
from Controllers.GameSession import BaseGameSession


class TicTacToeGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_score_type):
        super().__init__(game_id, game_score_type)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        elif command_id == commands.Finish_Round:
            pass
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = TicTacToeGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.TIC_TAC_TOE
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_authority(peace_id, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                self.timer.stop()
                if self.game_controller.is_round_finished:
                    self.change_round()

    def send_current_turn(self):
        if self.game_controller.is_game_finished or self.game_controller.is_round_finished:
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                         game_id=self.game_id))
        self.timer.start(TicTacToe_Turn_Time, self.send_current_turn)

    def change_round(self):
        time.sleep(TicTacToe_Sleep_Round_Time)
        self.game_controller.change_round()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.New_Round, data=self.game_controller.current_round),
                         game_id=self.game_id))
        self.send_current_turn()
