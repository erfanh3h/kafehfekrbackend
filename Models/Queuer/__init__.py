from Models.User import UserModel


class QueuerModel(UserModel):
    def __init__(self, user_id: str, username: str, user_image: int, user_coin: int, user_score: int, socket_id='',
                 is_rdy=True):
        super().__init__(user_id, username, user_image, user_coin, user_score)
        self.socket_id = socket_id
        self.user_score = user_score
        self.is_rdy = is_rdy
        self.selected_game = None
        self.banned_games = []
        self.queuer_index = 0

    def set_index(self, queuer_index):
        self.queuer_index = queuer_index

    def join_queue(self, socket_id):
        self.socket_id = socket_id

    def to_json(self):
        return {'name': self.username, 'user_id': self.user_id, 'image': self.user_image}

    def to_lobby_json(self):
        return {'name': self.username, 'user_id': self.user_id, 'image': self.user_image, 'is_rdy': self.is_rdy}

    def to_queue_json(self):
        return {'name': self.username, 'user_id': self.user_id, 'image': self.user_image,
                'selected_game': self.selected_game, 'banned_games': self.banned_games}
