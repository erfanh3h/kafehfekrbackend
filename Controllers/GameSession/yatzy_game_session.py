import asyncio

from Entities.Games.Yatzy import YatzyGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Yatzy_Turn_Time, Yatzy_Turn_Wait_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class YatzyGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = YatzyGameClass(send_data_function=self.send_command,
                                              send_private_data_function=self.send_private_command)
        self.game_type = GameTypesEnum.YATZY
        super().start_game_timer()

    def send_reconnect_data(self, socket_id):
        reconnect_data = {'gamers': []}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is not None:
            gamer_id = gamer_data.gamer_id
            reconnect_data['game_data'] = self.game_controller.get_game_data_yatzy(gamer_id)
        reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}
        from Entities.SocketIOManagerClass import send_private_command
        asyncio.new_event_loop().run_until_complete(
            send_private_command(command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                                 socket_id=socket_id, game_id=self.game_id))

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        peace_id = data['data']
        is_selection_correct = self.game_controller.check_authority(peace_id, gamer_id)
        if is_selection_correct:
            is_round_done = await self.game_controller.recieve_data(data['id'], peace_id, gamer_id)
            if is_round_done:
                self.timer.stop()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_private_command, send_command
        def auto_select_turn():
            check_player1_index = self.game_controller.check_player_played_this_round(1)
            if check_player1_index != -1:
                asyncio.new_event_loop().run_until_complete(send_command(
                    command=make_command_json(id=commands.Peace_Selected,
                                              data={'gamer_id': 1, 'selected_index': check_player1_index,
                                                    'score': 0, 'player1_score': self.game_controller.player1_score,
                                                    'player2_score': self.game_controller.player2_score}),
                    game_id=self.game_id, ))
            check_player2_index = self.game_controller.check_player_played_this_round(2)
            if check_player2_index != -1:
                asyncio.new_event_loop().run_until_complete(send_command(
                    command=make_command_json(id=commands.Peace_Selected,
                                              data={'gamer_id': 2, 'selected_index': check_player2_index,
                                                    'score': 0, 'player1_score': self.game_controller.player1_score,
                                                    'player2_score': self.game_controller.player2_score}),
                    game_id=self.game_id, ))

        # check to if user didn't select this turn , automattically select first piece of him
        if self.game_controller.current_round != 0 and not self.game_controller.is_game_finished:
            auto_select_turn()
        self.game_controller.change_turn()
        if self.check_finish_game():
            return

        def function():
            gamer1_data = self.find_gamer_from_gamer_id(1)
            gamer2_data = self.find_gamer_from_gamer_id(2)
            if gamer1_data is not None:
                asyncio.new_event_loop().run_until_complete(send_private_command(
                    command=make_command_json(id=commands.Current_Turn,
                                              data={"current_turn": self.game_controller.current_round,
                                                    "dices": self.game_controller.player1_current_dices}),
                    game_id=self.game_id, socket_id=gamer1_data.socket_id))
            if gamer2_data is not None:
                asyncio.new_event_loop().run_until_complete(send_private_command(
                    command=make_command_json(id=commands.Current_Turn,
                                              data={"current_turn": self.game_controller.current_round,
                                                    "dices": self.game_controller.player2_current_dices}),
                    game_id=self.game_id, socket_id=gamer2_data.socket_id))
            self.timer.start(Yatzy_Turn_Time, self.send_current_turn)

        if self.game_controller.current_round != 1:
            asyncio.new_event_loop().run_until_complete(
                send_command(
                    command=make_command_json(id=commands.Wait_Time, data=Yatzy_Turn_Wait_Time), game_id=self.game_id))
            self.timer.start(Yatzy_Turn_Wait_Time, function)
        else:
            function()
