import asyncio
import threading
import time


class UserDisconnectTimerClass:
    def __init__(self, user_id: str, max_time: int = 20000,):
        self.timerCounting = True
        self.max_time = max_time
        self.finish_timer_function = None
        self.is_canceled = False
        self.timer = threading.Timer(1, self.start_timer)
        self.user_id = user_id

    def set_finish_timer_function(self, finish_timer_function):
        self.finish_timer_function = finish_timer_function

    def start(self):
        self.is_canceled = False
        self.timer = threading.Timer(1, self.start_timer)
        self.timer.start()

    def stop(self):
        self.is_canceled = True

    def start_timer(self):
        if self.max_time <= 0:
            self.timer.cancel()
            if self.finish_timer_function is not None:
                self.finish_timer_function(self.user_id)
        elif self.is_canceled:
            self.timer.cancel()
        else:
            self.max_time -= 1
            # print(self.user_id, self.max_time)
            self.timer = threading.Timer(1, self.start_timer)
            self.timer.start()
