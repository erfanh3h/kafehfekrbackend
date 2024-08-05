import asyncio
import time

from Entities.Games.Mill import MillGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Mill_Remove_Time, Mill_Select_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.TicTacToe import TicTacToeGameClass
from Controllers.GameSession import BaseGameSession


class MillGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_score_type):
        super().__init__(game_id, game_score_type)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = MillGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.MILL
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_select_authority(peace_id, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                self.timer.stop()
        elif data['id'] == commands.Swap_Peace:
            is_selection_correct = self.game_controller.check_swap_authority(data['data'], gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], data, gamer_id)
                self.timer.stop()
        elif data['id'] == commands.Select_Remove_Peace:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_remove_authority(peace_id, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                self.timer.stop()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command
        if self.game_controller.is_game_finished:
            return
        if self.game_controller.current_remover == 0:
            self.game_controller.change_turn()
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                    game_id=self.game_id))
            self.timer.start(Mill_Select_Time, self.send_current_turn)
        else:
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Select_Remove_Peace,
                                              data=self.game_controller.current_remover),
                    game_id=self.game_id))
            self.timer.start(Mill_Remove_Time, self.call_after_wait_for_remove_peace)

    def call_after_wait_for_remove_peace(self):
        self.game_controller.current_remover = 0
        self.send_current_turn()
