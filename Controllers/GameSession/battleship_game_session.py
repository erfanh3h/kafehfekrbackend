import asyncio
import threading
import time

from Entities.Games.BattleShip import BattleShipGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import BattleShip_Turn_Time, BattleShip_Board_Time, BattleShip_Wait_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class BattleShipGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = BattleShipGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.BATTLESHIP

        def entrypoint():
            self.check_start_game()

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_game(self):
        while True:
            if self.check_all_players_joined():
                self.is_game_running = True
                self.prepare_gamers()
                self.send_game_data()
                self.send_start_game()
                break
            time.sleep(2)

    def send_reconnect_data(self, socket_id):
        reconnect_data = {'gamers': []}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is not None:
            gamer_id = gamer_data.gamer_id
            reconnect_data['game_data'] = self.game_controller.get_game_data_battleship(gamer_id)
        reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                                 socket_id=socket_id, game_id=self.game_id))

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Save_Board:
            board_data = data['data']
            is_selection_correct = self.game_controller.check_save_peace_authority(board_data, gamer_id)
            if is_selection_correct:
                is_game_rdy = await self.game_controller.recieve_data(data['id'], board_data, gamer_id)
                if is_game_rdy:
                    self.timer.stop()
        elif data['id'] == commands.Select_Peace:
            piece_id = data['data']
            is_selection_correct = self.game_controller.check_authority(piece_id, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], piece_id, gamer_id)
                self.timer.stop()

    def send_start_game(self):
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Start_Game, data=None), game_id=self.game_id))
        self.timer.start(BattleShip_Board_Time, self.send_current_turn)

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command

        def function():
            if self.game_controller.is_game_finished:
                winner_id = self.game_controller.get_game_winner()
                self.finish_game(winner_id)
                return
            self.game_controller.change_turn()
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                    game_id=self.game_id))
            self.timer.start(BattleShip_Turn_Time, self.send_current_turn)

        if self.game_controller.is_turn_win_happened:
            self.timer.start(BattleShip_Turn_Time, self.send_current_turn)
        else:
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Wait_Time, data=BattleShip_Wait_Time), game_id=self.game_id))
            self.timer.start(BattleShip_Wait_Time, function)
