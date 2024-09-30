from Models.User import UserModel


class QueuerModel(UserModel):
    def __init__(self, user_id: str, username: str, user_image: int, user_coin: int, user_score: int, game_types,
                 socket_id='', ):
        super().__init__(user_id, username, user_image, user_coin, user_score)
        self.socket_id = socket_id
        self.user_score = user_score
        self.game_types = game_types

    def join_queue(self, socket_id):
        self.socket_id = socket_id

    def to_json(self):
        return {'name': self.username, 'user_id': self.user_id, 'image': self.user_image}
