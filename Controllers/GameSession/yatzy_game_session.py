import asyncio

from Entities.Games.Yatzy import YatzyGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Yatzy_Turn_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class YatzyGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_score_type):
        super().__init__(game_id, game_score_type)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        elif command_id == commands.Finish_Round:
            pass
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = YatzyGameClass(send_data_function=self.send_command,
                                              send_private_data_function=self.send_private_command)
        self.game_type = GameTypesEnum.YATZY
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

    def send_current_turn(self):
        if self.game_controller.is_game_finished:
            winner_id = self.game_controller.get_game_winner()
            self.finish_game(winner_id)
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_private_command
        gamer1_data = self.find_gamer_from_gamer_id(1)
        gamer2_data = self.find_gamer_from_gamer_id(2)
        if gamer1_data is not None:
            asyncio.new_event_loop().run_until_complete(send_private_command(
                command=make_command_json(id=commands.Current_Turn,
                                          data={"current_turn": self.game_controller.current_turn,
                                                "dices": self.game_controller.player1_current_dices}),
                game_id=self.game_id, socket_id=gamer1_data.socket_id))
        if gamer2_data is not None:
            asyncio.new_event_loop().run_until_complete(send_private_command(
                command=make_command_json(id=commands.Current_Turn,
                                          data={"current_turn": self.game_controller.current_turn,
                                                "dices": self.game_controller.player2_current_dices}),
                game_id=self.game_id, socket_id=gamer2_data.socket_id))
        self.timer.start(Yatzy_Turn_Time, self.send_current_turn)
