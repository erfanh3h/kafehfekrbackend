from Entities.RewardManagerClass import GameScoreTypesEnum
from Commons.static_functions import safe_run_async
import asyncio

from Entities.Games.DotBox import DotBoxGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import DotBox_Turn_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class DotBoxGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = DotBoxGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.DOTBOX
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_authority(peace_id, gamer_id)
            if is_selection_correct:
                self.game_controller.is_current_turn_played = True
                is_win_box_happened = await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                if not is_win_box_happened or self.game_controller.check_game_ended():
                    self.timer.stop()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command
        if self.is_game_finished:
            self.timer.stop(False)
            return
        if self.game_controller.check_game_ended():
            winner = self.game_controller.get_game_winner()
            from Entities.SocketIOClass.game import games
            if self.game_score_type != GameScoreTypesEnum.RANK and self.game_id not in games:
                safe_run_async(
                    send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                                 game_id=self.game_id))
            self.finish_game(winner)
            return
        if self.check_afk_turn():
            return
        self.game_controller.change_turn()
        safe_run_async(
            send_command(command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                         game_id=self.game_id))
        self.timer.start(DotBox_Turn_Time, self.send_current_turn)
