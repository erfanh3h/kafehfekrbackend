import asyncio
import threading
import time

from Entities.Games.wait_times import MSweeper_game_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.MSweeper import MSweeperGameClass
from Controllers.GameSession import BaseGameSession


class MSweeperGameSession(BaseGameSession):
    def __init__(self, game_id: str):
        super().__init__(game_id)

    async def send_command(self, command_id, command_data):
        if command_id == commands.Finish_Game:
            self.timer.stop()
        await super().send_command(command_id, command_data)

    def start_game_timer(self):
        self.game_controller = MSweeperGameClass(send_data_function=self.send_command,
                                                 send_private_data_function=self.send_private_command)

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

    async def command_received(self, data, socket_id):
        if not self.is_game_running:
            print("game not started yet")
            return
        gamer_id = self.find_gamer_from_socket(socket_id).gamer_id
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_select_peace_authority(peace_id, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
        elif data['id'] == commands.Select_Mine:
            peace_id = data['data']
            is_selection_correct = self.game_controller.check_select_mine_authority(peace_id, gamer_id)
            if is_selection_correct:
                await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
        elif data['id'] == commands.Surrender:
            await self.game_controller.surrender(gamer_id)
            self.timer.stop()

    def send_start_game(self):
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Start_Game, data=None), game_id=self.game_id))
        self.timer.start(MSweeper_game_Time, self.check_winner)

    def check_winner(self):
        if self.game_controller.is_game_finished:
            return
        time.sleep(2)
        self.game_controller.finish_game()
        winner = self.game_controller.get_game_winner()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                         game_id=self.game_id))
