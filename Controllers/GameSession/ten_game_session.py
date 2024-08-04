import asyncio
import time

from Entities.Games.Ten import TenGameClass
from Entities.Games.wait_times import Ten_Sleep_Round_Time, Ten_Round_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class TenGameSession(BaseGameSession):
    def __init__(self, game_id: str):
        super().__init__(game_id)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        elif command_id == commands.Finish_Round:
            pass
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = TenGameClass(send_data_function=self.send_command)
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Solve:
            is_selection_correct = self.game_controller.check_authority("", gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], data, gamer_id)
                if self.game_controller.is_round_finished:
                    self.timer.stop()
                    self.change_round()

    def finish_round_time(self):
        if self.game_controller.is_game_finished or self.game_controller.is_round_finished:
            return
        from Entities.SocketIOManagerClass import send_command
        self.game_controller.round_time_finished()
        if self.game_controller.is_round_finished:
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Finish_Round, data={"Winner": 0}), game_id=self.game_id))
        elif self.game_controller.is_game_finished:
            game_winner = self.game_controller.get_game_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Finish_Game, data={"Winner": game_winner}),
                    game_id=self.game_id))
        self.change_round()

    def send_current_turn(self):
        if self.game_controller.is_game_finished or self.game_controller.is_round_finished:
            return
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_round_numbers),
                game_id=self.game_id))
        self.timer.start(Ten_Round_Time, self.finish_round_time)

    def change_round(self):
        time.sleep(Ten_Sleep_Round_Time)
        self.game_controller.change_round()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.New_Round, data=self.game_controller.current_round),
                         game_id=self.game_id))
        self.send_current_turn()
