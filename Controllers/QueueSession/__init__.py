import asyncio
import threading
import time

from Commons import commands
from Commons.static_functions import make_command_json
from Entities.Games.game_types import GameTypesEnum
from Entities.TimerClass import TimerClass
from Models.Queuer import QueuerModel


class BaseQueueSession:
    def __init__(self, game_score_type):
        self.queuers: list[QueuerModel] = []
        self.timer = TimerClass()
        self.game_type = game_score_type
        self.queue_must_run = True

    def start_timer(self):
        def check_start_new_game():
            while True:
                print("queuer len : ", len(self.queuers))
                time.sleep(2)

        t = threading.Thread(target=check_start_new_game, daemon=True)
        t.start()

    def find_gamer_from_socket(self, socket_id):
        for queuer in self.queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def add_queuer(self, queuer: QueuerModel):
        self.queuers.append(queuer)

    def join_queuer(self, user_data: QueuerModel):
        self.queuers.append(user_data)

    def send_game_data(self):
        game_data = {'gamers': []}
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Game_Data, data=game_data), game_id='self.game_id'))

        # self.gamers.reverse()

    async def send_command(self, command_id, command_data):
        from Entities.SocketIOManagerClass import send_command
        await send_command(command=make_command_json(id=command_id, data=command_data), game_id='self.game_id')

    async def send_private_command(self, command_id, command_data, gamer_id):
        queuer_data = self.find_gamer_from_socket(gamer_id)
        if queuer_data is not None:
            socket_id = queuer_data.socket_id
            from Entities.SocketIOManagerClass import send_private_command
            asyncio.new_event_loop().run_until_complete(
                send_private_command(command=make_command_json(id=command_id, data=command_data),
                                     socket_id=socket_id, game_id='self.game_id'))

    async def command_received(self, data, socket_id):
        queuer_data = self.find_gamer_from_socket(socket_id)
        if queuer_data is None:
            return None
        else:
            user_id = queuer_data.user_id
        return user_id

    def disconnect_user(self, socket_id):
        queuer_data = self.find_gamer_from_socket(socket_id)
        if queuer_data is not None:
            self.queuers.remove(queuer_data)
        # self.queuers[gamer_index].disconnect()
