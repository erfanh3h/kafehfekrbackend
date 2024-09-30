import asyncio
import threading
import time

from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import MSweeper_game_Time, Join_Game_Limit_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.MSweeper import MSweeperGameClass
from Controllers.GameSession import BaseGameSession


class MSweeperGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = MSweeperGameClass(send_data_function=self.send_command,
                                                 send_private_data_function=self.send_private_command)
        self.game_type = GameTypesEnum.MSweeper

        def entrypoint():
            self.check_start_game()

        # self.timer.start(Join_Game_Limit_Time, self.join_game_limit_time)
        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_game(self):
        while True:
            if self.check_all_players_joined():
                time.sleep(3)
                self.is_game_running = True
                self.timer.stop()
                self.prepare_gamers()
                self.send_game_data(self.send_start_game)
                break
            time.sleep(2)

    def send_reconnect_data(self, socket_id):
        reconnect_data = {'gamers': []}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is not None:
            gamer_id = gamer_data.gamer_id
            reconnect_data['game_data'] = self.game_controller.get_game_data_msweeper(gamer_id)
        reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                                 socket_id=socket_id, game_id=self.game_id))

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_select_peace_authority(peace_id, gamer_id)
            if is_selection_correct:
                is_game_finished = await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                if is_game_finished:
                    self.timer.stop()
        elif data['id'] == commands.Select_Mine:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_select_mine_authority(peace_id, gamer_id)
            if is_selection_correct:
                is_game_finished = await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
                if is_game_finished:
                    self.timer.stop()

    def send_start_game(self):
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Start_Game, data=None), game_id=self.game_id))
        self.timer.start(MSweeper_game_Time, self.check_winner)

    def check_winner(self):
        self.game_controller.finish_game()
        winner = self.game_controller.get_game_winner()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                         game_id=self.game_id))
        self.finish_game(winner)
