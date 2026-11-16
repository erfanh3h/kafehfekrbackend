class UserModel:
    def __init__(self, user_id: str, username: str, user_image: int, user_coin: int, user_score: int, profile_frame: int = 1):
        self.user_id: str = user_id
        self.username: str = username
        self.user_image: int = user_image
        self.user_coin: int = user_coin
        self.user_score: int = user_score
        f_val = int(profile_frame) if profile_frame is not None else 1
        self.profile_frame: int = max(1, min(20, f_val)) if f_val > 0 else 1
        self.avatar_frame: int = self.profile_frame
        # self.letGame: bool = True
