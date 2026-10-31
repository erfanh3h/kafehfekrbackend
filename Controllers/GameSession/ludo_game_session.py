from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession, safe_run_async
from Entities.Games.Ludo import LudoGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Ludo_Turn_Time, Ludo_Out_Of_Move_time
from Commons.static_functions import make_command_json
from Commons import commands


class LudoGameSession(BaseMultiplayerGameSession):

    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = LudoGameClass(send_data_function=self.send_command, players_count=len(self.gamers))
        self.game_type = GameTypesEnum.LUDO
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data['id'] == commands.Roll_Dice:
            is_selection_correct = self.game_controller.check_authority(data, gamer_id)
            if not is_selection_correct:
                return
            have_move = await self.game_controller.recieve_data(data['id'], data.get('data', {}), gamer_id)
            if have_move:
                self.send_dice()
            else:
                self.pass_turn()
        elif data['id'] == commands.Select_Peace:
            is_selection_correct = self.game_controller.check_authority(data, gamer_id)
            if not is_selection_correct:
                return
            await self.game_controller.recieve_data(data['id'], data.get('data', {}), gamer_id)
            self.timer.stop(False)
            if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
                self.game_controller.is_game_finished = True
                # Wait 2.5 seconds so players see the final piece reaching home and podium VFX
                self.timer.start(3, self.check_finish_game)
            elif (
                self.game_controller.has_more_dice
                and gamer_id in self.game_controller.active_player_indexes
            ):
                # Player rolled a 6 and gets a bonus roll
                self.game_controller.has_more_dice = False
                self.game_controller.current_dice = 0
                self.game_controller.current_turn_player_rolled = False
                self.game_controller.current_available_indexes.clear()
                self.send_bonus_turn()
            else:
                self.send_current_turn()

    def send_bonus_turn(self):
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(
                    id=commands.Current_Turn,
                    data={'turn': self.game_controller.current_turn, 'bonus': True}
                ),
                game_id=self.game_id
            )
        )
        self.timer.start(Ludo_Turn_Time, self.send_current_turn)

    def send_current_turn(self):
        print("new turn")
        if self.check_finish_game():
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data={'turn': self.game_controller.current_turn}),
                game_id=self.game_id
            )
        )
        self.timer.start(Ludo_Turn_Time, self.send_current_turn)

    def send_dice(self):
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(
                    id=commands.Roll_Result,
                    data={
                        'dice': self.game_controller.current_dice,
                        'turn': self.game_controller.current_turn,
                        'available_moves': list(self.game_controller.current_available_indexes),
                    }
                ),
                game_id=self.game_id
            )
        )

    def pass_turn(self):
        from Entities.SocketIOManagerClass import send_command
        self.timer.stop(False)
        safe_run_async(
            send_command(
                command=make_command_json(
                    id=commands.Out_Of_Move,
                    data={
                        'turn': self.game_controller.current_turn,
                        'dice': self.game_controller.current_dice
                    }
                ),
                game_id=self.game_id
            )
        )
        self.game_controller.is_current_turn_played = True
        self.timer.start(Ludo_Out_Of_Move_time, self.send_current_turn)

    def send_reconnect_data(self, socket_id):
        reconnect_data = {'gamers': [], 'game_type': 'Ludo'}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        reconnect_data['game_data'] = self.game_controller.get_game_data()
        reconnect_data['game_data']['game_type'] = 'Ludo'
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
