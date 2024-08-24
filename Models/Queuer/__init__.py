from Models.User import UserModel


class QueuerModel(UserModel):
    def __init__(self, user_id: str, username: str, user_score: int = 0, socket_id='', ):
        super().__init__(user_id, username)
        self.socket_id = socket_id
        self.user_id: str = user_id
        self.nominate_for_game = False
        self.user_score = user_score

    def join_queue(self, socket_id):
        self.socket_id = socket_id

    def set_nominate_for_game(self, value):
        self.nominate_for_game = value

    def to_json(self):
        return {'name': self.username, 'user_id': self.user_id}
