from Entities.RewardManagerClass import GameScoreTypesEnum
from Entities.Games.Quoridor import QuoridorGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Quoridor_Turn_Time
from Commons.static_functions import make_command_json, safe_run_async
from Commons import commands
from Controllers.GameSession import BaseGameSession


class QuoridorGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = QuoridorGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.QUORIDOR
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Select_Peace:
            move_data = data.get('data')
            is_authorized = self.game_controller.check_authority(move_data, gamer_id)
            if is_authorized:
                accepted = await self.game_controller.recieve_data(data['id'], move_data, gamer_id)
                if accepted:
                    self.timer.stop(False)
                    self.send_current_turn()

    def send_current_turn(self):
        if (
            self.game_controller.current_round != 0
            and not self.game_controller.is_current_turn_played
            and not self.game_controller.is_game_finished
            and self.check_finish_game_by_not_play_turn(self.game_controller.current_turn)
        ):
            return

        from Entities.SocketIOManagerClass import send_command

        if self.game_controller.check_game_ended():
            winner = self.game_controller.get_game_winner()

            def finish_after_delay():
                from Entities.SocketIOClass.game import games
                if self.game_score_type != GameScoreTypesEnum.RANK and self.game_id not in games:
                    safe_run_async(
                        send_command(
                            command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                            game_id=self.game_id,
                        )
                    )
                self.finish_game(winner)

            # Allow client 2.2s to finish final pawn hop and goal celebration VFX
            self.timer.start(2.2, finish_after_delay)
            return

        self.game_controller.change_turn()
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data=self.game_controller.current_turn),
                game_id=self.game_id,
            )
        )
        self.timer.start(Quoridor_Turn_Time, self.send_current_turn)

    def send_reconnect_data(self, socket_id):
        if not self.is_game_running:
            return
        reconnect_data = {'gamers': [], 'game_type': 'Quoridor'}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        reconnect_data['game_data'] = self.game_controller.get_game_data()
        reconnect_data['game_data']['game_type'] = 'Quoridor'
        if self.timer.is_user_turn:
            reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}
        else:
            reconnect_data['timer_data'] = {'is_user_turn': False, 'time': 0}

        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(
                command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                socket_id=socket_id,
                game_id=self.game_id,
            )
        )
