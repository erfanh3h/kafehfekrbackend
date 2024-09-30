import asyncio
import time

from Entities.Games.FekrBekr import FekrBekrGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import FekrBekr_Round_Time, FekrBekr_Board_Time, FekrBekr_Round_Wait_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class FekrBekrGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = FekrBekrGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.FEKRBEKR
        super().start_game_timer()

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
            reconnect_data['game_data'] = self.game_controller.get_game_data_fekrbekr(gamer_id)
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
                is_round_done = await self.game_controller.recieve_data(data['id'], piece_id, gamer_id)
                if is_round_done:
                    self.timer.stop()

    def send_start_game(self):
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(command=make_command_json(id=commands.Start_Game, data=None), game_id=self.game_id))
        self.timer.start(FekrBekr_Board_Time, self.send_current_turn)

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command

        def auto_select_round():
            empty_data = [0, 0, 0, 0]
            if not self.game_controller.player1_played_turn:
                self.game_controller.player1_choices.append(empty_data)
                self.game_controller.player1_results.append(empty_data)
                asyncio.new_event_loop().run_until_complete(send_command(
                    command=make_command_json(id=commands.Peace_Selected,
                                              data={'gamer_id': 1, 'data': empty_data, "result": empty_data}),
                    game_id=self.game_id, ))
            if not self.game_controller.player2_played_turn:
                self.game_controller.player2_choices.append(empty_data)
                self.game_controller.player2_results.append(empty_data)
                asyncio.new_event_loop().run_until_complete(send_command(
                    command=make_command_json(id=commands.Peace_Selected,
                                              data={'gamer_id': 2, 'data': empty_data, "result": empty_data}),
                    game_id=self.game_id, ))

        def auto_select_board():
            default_board = [1, 2, 3, 4]
            if not self.game_controller.player1_board_rdy:
                self.game_controller.save_board(default_board, 1)
            if not self.game_controller.player2_board_rdy:
                self.game_controller.save_board(default_board, 2)

        # check to if user didn't select this turn , automattically select first piece of him
        if self.game_controller.current_round != 0 and not self.game_controller.is_game_finished:
            auto_select_round()
        elif self.game_controller.current_round == 0:
            auto_select_board()
        self.game_controller.change_round()
        if self.game_controller.check_game_ended():
            winner = self.game_controller.get_game_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                             game_id=self.game_id))
            self.finish_game(winner)
            return

        def function():
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Current_Turn,
                                                       data={"current_round": self.game_controller.current_round}),
                             game_id=self.game_id))
            self.timer.start(FekrBekr_Round_Time, self.send_current_turn)

        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Wait_Time, data=FekrBekr_Round_Wait_Time),
                game_id=self.game_id))
        self.timer.start(FekrBekr_Round_Wait_Time, function)
