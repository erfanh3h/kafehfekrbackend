import threading
from Controllers.QueueSession.game_queue_session_details import GameQueueSessionDetails
from Entities.TimerClass import TimerClass
from Models.Queuer import QueuerModel


class BaseQueueSession:
    def __init__(self, game_score_type):
        self.timer = TimerClass()
        self.game_score_type = game_score_type

    def check_start_new_game(self):
        pass

    def init_session(self):
        t = threading.Thread(target=self.check_start_new_game, daemon=True)
        t.start()

    def join_queuer(self, user_data: QueuerModel):
        return True

    def disconnect_user(self, socket_id):
        pass
