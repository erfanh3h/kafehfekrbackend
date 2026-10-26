import asyncio

from Entities.Games.BackGammon import BackGammonGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import BackGammon_Turn_Time, BackGammon_Out_Of_Move_time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class BackGammonGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = BackGammonGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.BACKGAMMON
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Roll_Dice:
            have_selection = await self.game_controller.recieve_data(data['id'], data['data'], gamer_id)
            if have_selection:
                self.send_dices()
            else:
                self.pass_turn()
        if data['id'] == commands.Select_Peace:
            selection_data = data['data']
            is_selection_correct = self.game_controller.check_authority(selection_data, gamer_id)
            if is_selection_correct:
                is_turn_finished = await self.game_controller.recieve_data(data['id'], selection_data, gamer_id)
                if is_turn_finished or self.game_controller.is_game_finished:
                    self.timer.stop()


    def send_current_turn(self):
        # checking player not played his turn
        if (self.game_controller.current_round != 0 and not self.game_controller.is_current_turn_played and
                self.check_finish_game_by_not_play_turn(self.game_controller.current_turn)):
            return
        if self.check_finish_game():
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data={'turn': self.game_controller.current_turn}),
                game_id=self.game_id))
        self.timer.start(BackGammon_Turn_Time, self.send_current_turn)

    def send_dices(self):
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Roll_Result, data={'dices': self.game_controller.current_dices}),
                game_id=self.game_id))

    def pass_turn(self):
        from Entities.SocketIOManagerClass import send_command
        self.timer.stop(False)
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Out_Of_Move, data={'turn': self.game_controller.current_turn,
                                                                         'dices': self.game_controller.current_dices}),
                game_id=self.game_id))
        self.game_controller.is_current_turn_played = True
        self.timer.start(BackGammon_Out_Of_Move_time, self.send_current_turn)
