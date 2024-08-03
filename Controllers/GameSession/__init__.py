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
    def __init__(self, game_id: str):
        # self.temp_gamers: list[GamerModel] = [GamerModel(user_id=i, username=str(i)) for i in range(2)]
        self.gamers: list[GamerModel] = []
        self.timer = TimerClass()
        self.game_controller: BaseGameClass = BaseGameClass(None)
        self.game_id = game_id
        self.is_game_running = False
        self.gamer_idies = []

    def start_game_timer(self):
        def entrypoint():
            self.check_start_game()

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_all_players_joined(self):
        for gamer in self.gamers:
            if not gamer.is_joined_game:
                return False
        return True

    def check_start_game(self):
        while True:
            if self.check_all_players_joined():
                self.is_game_running = True
                self.prepare_gamers()
                self.send_game_data()
                self.game_controller.change_turn()
                self.send_current_turn()
                break
            time.sleep(2)

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
        self.gamer_idies.append(gamer.user_id)

    def join_gamer(self, user_id: int, socket_id):
        for gamer_index in range(0, len(self.gamers)):
            if self.gamers[gamer_index].user_id == user_id:
                self.gamers[gamer_index].set_finish_reconnect_time_function(self.finish_reconnect_time)
                if self.gamers[gamer_index].is_joined_game:
                    self.gamers[gamer_index].reconnect(socket_id)
                    self.send_reconnect_data(socket_id)
                else:
                    self.gamers[gamer_index].join_game(socket_id)
                break

    def send_game_data(self):
        game_data = {'gamers': []}
        for gamer in self.gamers:
            game_data['gamers'].append(gamer.to_json())
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Game_Data, data=game_data), game_id=self.game_id))

    def send_reconnect_data(self, socket_id):
        reconnect_data = {'gamers': []}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        reconnect_data['game_data'] = self.game_controller.get_game_data()
        if self.timer.is_user_turn:
            reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}
        else:
            reconnect_data['timer_data'] = {'is_user_turn': False, 'time': 0}
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                                 socket_id=socket_id, game_id=self.game_id))

    def prepare_gamers(self):
        for gamer_id in range(0, len(self.gamers)):
            self.gamers[gamer_id].gamer_id = gamer_id + 1
            self.gamers[gamer_id].team_id = gamer_id + 1
        # self.gamers.reverse()

    async def send_command(self, command_id, command_data):
        from Entities.SocketIOManagerClass import send_command
        await send_command(command=make_command_json(id=command_id, data=command_data), game_id=self.game_id)

    async def send_private_command(self, command_id, command_data, gamer_id):
        socket_id = self.find_gamer_from_id(gamer_id).socket_id
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=command_id, data=command_data),
                                 socket_id=socket_id, game_id=self.game_id))

    async def command_received(self, data, socket_id):
        pass

    async def reaction_received(self, data, socket_id):
        gamer_id = self.find_gamer_from_socket(socket_id).gamer_id
        from Entities.SocketIOManagerClass import send_reaction
        await send_reaction(reaction_id=data, player_id=gamer_id, game_id=self.game_id)

    def send_current_turn(self):
        pass

    def disconnect_user(self, socket_id):
        for gamer_index in range(0, len(self.gamers)):
            if self.gamers[gamer_index].socket_id == socket_id:
                self.gamers[gamer_index].disconnect()
                break

    def finish_reconnect_time(self, gamer_id):
        pass

        # from Entities.SocketIOManagerClass import send_command
        # if data['id'] == commands.Game_Data:
        #     gamer_id = self.find_gamer_from_socket(socket_id).gamer_id
        #     self.timer.stop()
