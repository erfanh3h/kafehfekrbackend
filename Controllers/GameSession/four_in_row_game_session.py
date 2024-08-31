import asyncio
import time

from Entities.Games.FourInRow import FourInRowGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Four_In_Row_Turn_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class FourInRowGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = FourInRowGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.FOURINROW
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            piece_data = data['data']
            is_selection_authorized = self.game_controller.check_authority(piece_data, gamer_id)
            if is_selection_authorized:
                await self.game_controller.recieve_data(data['id'], piece_data, gamer_id)
                self.timer.stop()

    def send_current_turn(self):
        if self.check_finish_game():
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                         game_id=self.game_id))
        self.timer.start(Four_In_Row_Turn_Time, self.send_current_turn)
