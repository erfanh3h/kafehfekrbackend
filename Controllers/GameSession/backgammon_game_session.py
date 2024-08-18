import asyncio

from Entities.Games.BackGammon import BackGammonGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import BackGammon_Turn_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class BackGammonGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_score_type):
        super().__init__(game_id, game_score_type)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = BackGammonGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.BACKGAMMON
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
        if self.game_controller.is_game_finished:
            winner_id = self.game_controller.get_game_winner()
            self.finish_game(winner_id)
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data={'turn': self.game_controller.current_turn,
                                                                          'dices': self.game_controller.current_dices}),
                game_id=self.game_id))
        self.timer.start(BackGammon_Turn_Time, self.send_current_turn)
