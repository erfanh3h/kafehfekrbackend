import asyncio

from Commons import commands
from Commons.static_functions import make_command_json
from Controllers.GameSession import BaseGameSession

class BaseMultiplayerGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def check_finish_game_by_not_play_turn(self, current_turn):
        pass

    def check_finish_game(self):
        from Entities.SocketIOManagerClass import send_command
        if self.game_controller.is_game_finished:
            winner = self.game_controller.get_game_winner()
            asyncio.new_event_loop().run_until_complete(
                send_command(command=make_command_json(id=commands.Finish_Game,
                                                       data={"rank1": self.game_controller.rank1,
                                                             "rank2": self.game_controller.rank2}),
                             game_id=self.game_id))
            self.finish_game(winner)
            return True
        return False

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
