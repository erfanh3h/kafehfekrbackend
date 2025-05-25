import asyncio

from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession
from Entities.Games.Risk import RiskGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Risk_Turn_Time, Ludo_Out_Of_Move_time, Start_Game_Time
from Commons.static_functions import make_command_json
from Commons import commands


class RiskGameSession(BaseMultiplayerGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = RiskGameClass(send_data_function=self.send_command, players_count=len(self.gamers))
        self.game_type = GameTypesEnum.RISK
        super().start_game_timer()

    def send_game_data(self, function):
        print("send game data")
        game_data = {'gamers': [], 'game_data': self.game_controller.get_game_data()}
        for gamer in self.gamers:
            game_data['gamers'].append(gamer.to_json())
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Game_Data, data=game_data), game_id=self.game_id))
        self.timer.start(Start_Game_Time, function)

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Draw_Card:
            is_selection_correct = self.game_controller.check_authority(data, gamer_id)
            if not is_selection_correct:
                return
            await self.game_controller.recieve_data(data['id'], data, gamer_id)
            await self.send_command(commands.Draw_Result, {'gamer_id': gamer_id, 'draw_type': data['draw_type'],
                                                         "new_data": self.game_controller.players_data[
                                                             self.game_controller.current_turn - 1].to_global_json()})
            await self.send_private_command(commands.User_Data, {"data": self.game_controller.players_data[
                self.game_controller.current_turn - 1].to_private_json()}, socket_id)
        if data['id'] == commands.Pass_Turn:
            is_selection_correct = self.game_controller.check_authority(data, gamer_id)
            if not is_selection_correct:
                return
            await self.game_controller.recieve_data(data['id'], data, gamer_id)
            await self.send_command(commands.Draw_Result, {'gamer_index': self.game_controller.current_turn - 1,
                                                         'draw_type': data['draw_type'],
                                                         "new_data": self.game_controller.players_data[
                                                             self.game_controller.current_turn - 1].to_global_json()})
            await self.send_private_command(commands.User_Data, self.game_controller.players_data[
                self.game_controller.current_turn - 1].to_private_json(), socket_id)
            self.send_current_turn()
            # self.timer.stop()
            # if self.game_controller.is_game_finished:
            #     self.timer.stop()
            #     # self.send_current_turn()
            # elif not self.game_controller.has_more_dice:
            #     self.timer.stop()

    def send_current_turn(self):
        print("new turn")
        if self.check_finish_game():
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Draw_Card, data={'turn': self.game_controller.current_turn}),
                game_id=self.game_id))
        self.timer.start(Risk_Turn_Time, self.send_current_turn)

    def send_dice(self):
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Roll_Result, data={'dice': self.game_controller.current_dice}),
                game_id=self.game_id))

    def pass_turn(self):
        from Entities.SocketIOManagerClass import send_command
        self.timer.stop(False)
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Out_Of_Move, data={'turn': self.game_controller.current_turn,
                                                                         'dice': self.game_controller.current_dice}),
                game_id=self.game_id))
        self.game_controller.is_current_turn_played = True
        self.timer.start(Ludo_Out_Of_Move_time, self.send_current_turn)
