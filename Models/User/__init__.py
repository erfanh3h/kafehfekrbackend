class UserModel:
    def __init__(self, user_id: str, username: str, user_image: int, user_coin: int, user_score: int):
        self.user_id: str = user_id
        self.username: str = username
        self.user_image: int = user_image
        self.user_coin: int = user_coin
        self.user_score: int = user_score
        # self.letGame: bool = True
