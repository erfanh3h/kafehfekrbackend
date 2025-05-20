import asyncio

from Entities.Games.Ludo import LudoGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Ludo_Turn_Time, Ludo_Out_Of_Move_time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


class LudoGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def start_game_timer(self):
        self.game_controller = LudoGameClass(send_data_function=self.send_command, players_count=len(self.gamers))
        self.game_type = GameTypesEnum.LUDO
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        if not self.is_game_running:
            return None
        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is None:
            return None
        else:
            gamer_id = gamer_data.gamer_id
        if gamer_id is None:
            return
        if data['id'] == commands.Surrender:
            should_timer_stop = await self.game_controller.surrender(gamer_id)
            await self.send_command(commands.Surrender, {"gamer_id": gamer_id})
            if should_timer_stop:
                self.timer.stop()
            return None
        if data['id'] == commands.Roll_Dice:
            is_selection_correct = self.game_controller.check_authority(data, gamer_id)
            if not is_selection_correct:
                return
            have_move = await self.game_controller.recieve_data(data['id'], data['data'], gamer_id)
            if have_move:
                self.send_dice()
            if not have_move:
                self.pass_turn()
        if data['id'] == commands.Select_Peace:
            is_selection_correct = self.game_controller.check_authority(data, gamer_id)
            if not is_selection_correct:
                return
            await self.game_controller.recieve_data(data['id'], data['data'], gamer_id)
            if self.game_controller.is_game_finished:
                self.timer.stop()
                # self.send_current_turn()
            elif not self.game_controller.has_more_dice:
                self.timer.stop()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command
        print("new turn")
        if self.game_controller.is_game_finished:
            winner = self.game_controller.get_game_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                             game_id=self.game_id))
            self.finish_game(winner)
            return True
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data={'turn': self.game_controller.current_turn}),
                game_id=self.game_id))
        self.timer.start(Ludo_Turn_Time, self.send_current_turn)

    def send_dice(self):
        from Entities.SocketIOManagerClass import send_command
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Roll_Result, data={'dice': self.game_controller.current_dice}),
                game_id=self.game_id))

    def pass_turn(self):
        from Entities.SocketIOManagerClass import send_command
        self.timer.stop(False)
        asyncio.new_event_loop().run_until_complete(
            send_command(
                command=make_command_json(id=commands.Out_Of_Move, data={'turn': self.game_controller.current_turn,
                                                                         'dice': self.game_controller.current_dice}),
                game_id=self.game_id))
        self.game_controller.is_current_turn_played = True
        self.timer.start(Ludo_Out_Of_Move_time, self.send_current_turn)

    def finish_game(self, winner_gamer_id):
        if self.is_game_finished:
            return
        self.is_game_finished = True
        user_idis = [g.user_id for g in self.gamers],
        from Entities.Database import game_database
        game_database.game_history_manager.create_game_history(self.game_history_id, self.game_id, user_idis,
                                                               str(self.game_type.value), self.game_score_type.value,
                                                               self.game_controller.rank1)
        from Entities.SocketIOClass.game import finish_multiplayer_game
        rank1_id = self.gamer_id_to_user_id(self.game_controller.rank1)
        rank2_id = self.gamer_id_to_user_id(self.game_controller.rank2)
        finish_multiplayer_game(self.game_id, rank1_id, rank2_id)

    def gamer_id_to_user_id(self, gamer_id):
        for gamer in self.gamers:
            if gamer.gamer_id == gamer_id:
                return gamer.user_id
        return None
