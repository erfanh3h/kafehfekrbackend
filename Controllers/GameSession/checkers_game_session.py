import asyncio
import time

from Entities.Games.Checkers import CheckersGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Checkers_Turn_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class CheckersGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = CheckersGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.CHECKERS
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            is_selection_authorized = self.game_controller.check_authority(peace_id, gamer_id)
            if is_selection_authorized:
                is_selection_correct = await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                if is_selection_correct:
                    self.timer.stop()

    def send_current_turn(self):
        # checking player not played his turn
        if (self.game_controller.current_round != 0 and not self.game_controller.is_current_turn_played and
                self.check_finish_game_by_not_play_turn(self.game_controller.current_turn)):
            return
        from Entities.SocketIOManagerClass import send_command
        if self.game_controller.is_game_finished:
            winner_id = self.game_controller.get_game_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner_id}),
                             game_id=self.game_id))
            self.finish_game(winner_id)
            return
        if self.game_controller.is_round_finished:
            return
        self.game_controller.change_turn()
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                         game_id=self.game_id))
        self.timer.start(Checkers_Turn_Time, self.send_current_turn)
