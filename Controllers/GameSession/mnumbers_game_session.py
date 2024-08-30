import asyncio
import time

from Entities.Games.MNumbers import MNumbersGameClass
from Entities.Games.Mill import MillGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import MNumbers_Turn_Time, MNumbers_Show_Result_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.TicTacToe import TicTacToeGameClass
from Controllers.GameSession import BaseGameSession


class MNumbersGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = MNumbersGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.MNUMBERS
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            selection_data = data['data']
            is_selection_correct = self.game_controller.check_authority(selection_data, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], selection_data, gamer_id)
                self.timer.stop()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command
        def wait_get_data():
            self.game_controller.change_turn()
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                    game_id=self.game_id))
            self.timer.start(MNumbers_Turn_Time, self.send_current_turn)

        if self.game_controller.is_game_finished:
            winner_id = self.game_controller.get_game_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner_id}),
                             game_id=self.game_id))
            self.finish_game(winner_id)
            return
        self.timer.start(MNumbers_Show_Result_Time, wait_get_data)
