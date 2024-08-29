import asyncio
import threading
import time

from Commons import commands
from Commons.static_functions import make_command_json
from Entities.Games.base_game_class import BaseGameClass
from Entities.Games.wait_times import Start_Game_Time, Join_Game_Limit_Time
from Entities.RewardManagerClass import RewardManagerClass
from Entities.TimerClass import TimerClass
from Models.Gamer import GamerModel


class BaseGameSession:
    def __init__(self, game_id: str, game_type, game_score_type):
        # self.temp_gamers: list[GamerModel] = [GamerModel(user_id=i, username=str(i)) for i in range(2)]
        self.gamers: list[GamerModel] = []
        self.timer = TimerClass()
        self.game_controller: BaseGameClass = BaseGameClass(None)
        self.game_id = game_id
        self.is_game_running = False
        self.gamer_idies = []
        self.game_type = game_type
        self.game_score_type = game_score_type
        self.score_manager = RewardManagerClass(game_score_type, game_id, game_type)
        self.is_game_terminated = False

    # this use to close game if didnt started in last 20 sec
    def join_game_limit_time(self):
        if not self.is_game_running:
            self.is_game_terminated = True
            self.finish_game(-1)

    def start_game_timer(self):
        def entrypoint():
            self.check_start_game()

        self.timer.start(Join_Game_Limit_Time, self.join_game_limit_time)
        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_all_players_joined(self):
        for gamer in self.gamers:
            if not gamer.is_joined_game:
                return False
        return True

    def check_start_game(self):
        while True:
            if self.is_game_terminated:
                break
            if self.check_all_players_joined():
                self.is_game_running = True
                self.timer.stop()
                self.prepare_gamers()
                self.send_game_data(self.send_current_turn)
                break
            time.sleep(2)

    def find_gamer_from_socket(self, socket_id):
        for gamer in self.gamers:
            if gamer.socket_id == socket_id:
                return gamer
        return None

    def find_gamer_from_gamer_id(self, gamer_id):
        for gamer in self.gamers:
            if gamer.gamer_id == gamer_id:
                return gamer
        return None

    def find_gamer_index_from_id(self, user_id):
        for index in range(0, len(self.gamers)):
            if self.gamers[index].user_id == user_id:
                return index
        return None

    def find_gamer_id_from_user_id(self, user_id):
        for index in range(0, len(self.gamers)):
            if self.gamers[index].user_id == user_id:
                return self.gamers[index].gamer_id
        return 0

    def add_gamer(self, gamer: GamerModel):
        self.gamers.append(gamer)
        self.gamer_idies.append(gamer.user_id)

    def join_gamer(self, user_id: int, socket_id):
        gamer_index = self.find_gamer_index_from_id(user_id)
        if gamer_index is not None:
            self.gamers[gamer_index].set_finish_reconnect_time_function(self.finish_reconnect_time)
            if self.gamers[gamer_index].is_joined_game:
                self.gamers[gamer_index].reconnect(socket_id)
                self.send_reconnect_data(socket_id)
                asyncio.new_event_loop().run_until_complete(
                    self.send_command(commands.User_Reconnected, {"user_id": user_id}))
            else:
                self.gamers[gamer_index].join_game(socket_id)

    def send_game_data(self, function):
        game_data = {'gamers': []}
        for gamer in self.gamers:
            game_data['gamers'].append(gamer.to_json())
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Game_Data, data=game_data), game_id=self.game_id))
        self.timer.start(Start_Game_Time, function)

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
        self.score_manager.set_user_data(self.gamers[0].user_id, self.gamers[1].user_id)
        from Entities.Database import game_database
        game_database.game_history_manager.create_game_history(self.game_id, self.gamers[0].user_id,
                                                               self.gamers[1].user_id,
                                                               str(self.game_type.value),
                                                               str(self.game_score_type.value))
        game_database.users_manager.update_user(self.gamers[0].user_id, open_game_id=self.game_id, )
        game_database.users_manager.update_user(self.gamers[1].user_id, open_game_id=self.game_id, )

    async def send_command(self, command_id, command_data):
        from Entities.SocketIOManagerClass import send_command
        await send_command(command=make_command_json(id=command_id, data=command_data), game_id=self.game_id)

    async def send_private_command(self, command_id, command_data, gamer_id):
        data = self.find_gamer_from_gamer_id(gamer_id)
        if data is not None:
            socket_id = data.socket_id
            from Entities.SocketIOManagerClass import send_private_command
            asyncio.new_event_loop().run_until_complete(
                send_private_command(command=make_command_json(id=command_id, data=command_data),
                                     socket_id=socket_id, game_id=self.game_id))

    async def command_received(self, data, socket_id):
        if not self.is_game_running:
            print("game not started yet")
            return None
        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is None:
            return None
        else:
            gamer_id = gamer_data.gamer_id
        if data['id'] == commands.Surrender:
            await self.game_controller.surrender(gamer_id)
            self.timer.stop()
            return None
        return gamer_id

    async def reaction_received(self, data, socket_id):
        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is not None:
            gamer_id = gamer_data.gamer_id
            from Entities.SocketIOManagerClass import send_reaction
            await send_reaction(reaction_id=data, player_id=gamer_id, game_id=self.game_id)

    def send_current_turn(self):
        pass

    def disconnect_user(self, socket_id):
        for gamer_index in range(0, len(self.gamers)):
            if self.gamers[gamer_index].socket_id == socket_id:
                user_data = self.find_gamer_from_socket(socket_id)
                if user_data is not None:
                    asyncio.new_event_loop().run_until_complete(
                        self.send_command(commands.User_Disconnected,
                                          {"user_id": user_data.user_id, "time": user_data.timer.max_time}))
                self.gamers[gamer_index].disconnect()
                break

    def finish_reconnect_time(self, user_id):
        asyncio.new_event_loop().run_until_complete(
            self.send_command(commands.Finish_Reconnect_Time, {"user_id": user_id}))
        gamer_id = self.find_gamer_id_from_user_id(user_id)
        self.game_controller.finish_reconnect_time(gamer_id)
        self.timer.stop()

    def finish_game(self, winner_gamer_id):
        self.score_manager.finish_game(winner_gamer_id)
        from Entities.SocketIOClass.game import delete_game
        delete_game(self.game_id)
