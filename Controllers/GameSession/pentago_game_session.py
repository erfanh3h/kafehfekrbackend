import asyncio
import random

from Entities.Games.Pentago import PentagoGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Pentago_Turn_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


def safe_run_async(coro):
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


class PentagoGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = PentagoGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.PENTAGO
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            peace_id = data['data']
            if isinstance(peace_id, dict):
                peace_id = peace_id.get('target_peace', peace_id.get('piece_id', -1))
            is_selection_authorized = self.game_controller.check_authority(peace_id, gamer_id)
            if is_selection_authorized:
                await self.game_controller.recieve_data(data['id'], int(peace_id), gamer_id)
        elif data['id'] == commands.Rotate_Peace:
            rotate_id = data['data']
            if isinstance(rotate_id, dict):
                rotate_id = rotate_id.get('rotation_id', rotate_id.get('rotate_id', -1))
            is_rotation_authorized = self.game_controller.check_rotate_authority(rotate_id, gamer_id)
            if is_rotation_authorized:
                self.timer.stop(False)
                await self.game_controller.recieve_data(data['id'], int(rotate_id), gamer_id)
                self.send_current_turn()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command
        # Auto-rotate if user timed out before rotating
        if self.game_controller.current_round != 0 and not self.game_controller.rotation_played:
            random_index = random.randint(1, 8)
            self.game_controller.rotate_piece(random_index)
            self.game_controller.rotation_played = True
            self.game_controller.is_game_finished = self.game_controller.check_win_happened()
            safe_run_async(send_command(
                command=make_command_json(
                    id=commands.Peace_Rotated,
                    data={
                        'user': self.game_controller.current_turn,
                        'rotation_id': random_index,
                        'board': list(self.game_controller.board)
                    }
                ),
                game_id=self.game_id))
        if self.game_controller.check_game_ended():
            winner = self.game_controller.get_game_winner()
            safe_run_async(
                send_command(
                    command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                    game_id=self.game_id))
            self.finish_game(winner)
            return

        self.game_controller.change_turn()

        def function():
            safe_run_async(
                send_command(
                    command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                    game_id=self.game_id))
            self.timer.start(Pentago_Turn_Time, self.send_current_turn)

        if self.game_controller.current_round == 1:
            function()
        else:
            self.timer.start(2, function)

    def send_reconnect_data(self, socket_id):
        reconnect_data = {'gamers': [], 'game_type': 'Pentago'}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        reconnect_data['game_data'] = self.game_controller.get_game_data()
        reconnect_data['game_data']['game_type'] = 'Pentago'
        if self.timer.is_user_turn:
            reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}
        else:
            reconnect_data['timer_data'] = {'is_user_turn': False, 'time': 0}
        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(
                command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                socket_id=socket_id,
                game_id=self.game_id
            )
        )
