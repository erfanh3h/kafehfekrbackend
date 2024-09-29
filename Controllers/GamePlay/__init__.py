from Controllers.GamePlay.game_type_class_pairs import game_type_class_pairs
from Entities.RewardManagerClass import RewardManagerClass
from Models.Gamer import GamerModel


class BaseGamePlayClass:
    def __init__(self, game_play_id, gamers, game_types, game_score_type):
        self.game_play_id = game_play_id
        self.gamers = gamers
        self.game_types = game_types
        self.game_score_type = game_score_type
        self.game_session = None
        self.gamer1_score = 0
        self.gamer2_score = 0
        self.current_game_index = 0
        self.game_winners = []
        self.is_game_running = False
        self.active_game_id = ""
        self.score_manager = RewardManagerClass(game_score_type, 'game_id', 'game_type')
        self.select_random_games()

    def select_random_games(self):
        pass

    def join_gamer(self, user_id: int, socket_id):
        if self.game_session is not None:
            self.game_session.join_gamer(user_id, socket_id)

    async def command_received(self, data, socket_id):
        if self.game_session is not None:
            self.game_session.command_received(data, socket_id)

    def disconnect_user(self, socket_id):
        if self.game_session is not None:
            self.game_session.disconnect_user(socket_id)

    async def reaction_received(self, data, socket_id):
        self.game_session.reaction_received(data, socket_id)

    def start_current_game(self):
        game_type = self.game_types[self.current_game_index]
        self.game_session = game_type_class_pairs[game_type.value](game_id=self.game_play_id, game_type=game_type,
                                                                   game_score_type=self.game_score_type)
        self.game_session.add_gamer(
            GamerModel(user_id=self.gamers[0].user_id, username=self.gamers[0].username,
                       user_image=self.gamers[0].user_image,
                       user_score=self.gamers[0].user_score, user_coin=self.gamers[0].user_coin))
        self.game_session.add_gamer(
            GamerModel(user_id=self.gamers[1].user_id, username=self.gamers[1].username,
                       user_image=self.gamers[1].user_image,
                       user_score=self.gamers[1].user_score, user_coin=self.gamers[1].user_coin))
        self.game_session.start_game_timer()

    def finish_current_game(self, winner_id):
        pass
