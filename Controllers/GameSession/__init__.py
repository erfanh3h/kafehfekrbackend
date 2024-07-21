import asyncio
import threading
import time

from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.TicTacToe import TicTacToeGameClass
from Entities.TimerClass import TimerClass
from Models.Gamer import GamerModel
from Entities.Games.base_game_class import BaseGameClass


class BaseGameSession:
    def __init__(self):
        # self.temp_gamers: list[GamerModel] = [GamerModel(user_id=i, username=str(i)) for i in range(2)]
        self.gamers: list[GamerModel] = []
        self.timer = TimerClass()
        self.game_controller: BaseGameClass

    def start_game_timer(self):
        def entrypoint():
            self.check_start_game()

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_game(self):
        while True:
            if len(self.gamers) == 2:
                self.prepare_gamers()
                self.send_game_data()
                self.game_controller.change_turn()
                self.send_current_turn()
                break
            time.sleep(3)

    def find_gamer_from_socket(self, socket_id) -> GamerModel:
        for gamer in self.gamers:
            if gamer.socket_id == socket_id:
                return gamer
        return self.gamers[0]

    def find_gamer_from_id(self, user_id) -> GamerModel:
        for gamer in self.gamers:
            if gamer.gamer_id == user_id:
                return gamer
        return self.gamers[0]

    def add_gamer(self, gamer: GamerModel):
        self.gamers.append(gamer)

    def send_game_data(self):
        game_data = {'gamers': []}
        for gamer in self.gamers:
            game_data['gamers'].append({'id': gamer.gamer_id, 'name': gamer.username})
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Game_Data, data=game_data)))

    def prepare_gamers(self):
        for gamer_id in range(0, len(self.gamers)):
            self.gamers[gamer_id].gamer_id = gamer_id
            self.gamers[gamer_id].team_id = gamer_id + 1
        self.gamers.reverse()

    async def send_command(self, command_id, command_data):
        from Entities.SocketIOManagerClass import send_command
        await send_command(command=make_command_json(id=command_id, data=command_data))

    async def command_received(self, data, socket_id):
        pass

    def send_current_turn(self):
        pass

        # from Entities.SocketIOManagerClass import send_command
        # if data['id'] == commands.Game_Data:
        #     gamer_id = self.find_gamer_from_socket(socket_id).gamer_id
        #     self.timer.stop()
