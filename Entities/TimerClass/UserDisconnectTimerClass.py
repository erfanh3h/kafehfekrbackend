import asyncio
import threading
import time


class UserDisconnectTimerClass:
    def __init__(self, max_time: int = 120, return_function=None):
        self.timerCounting = True
        self.max_time = max_time
        self.return_function = return_function
        self.is_canceled = False
        self.timer = threading.Timer(1, self.start_timer)

    def start(self, return_function=None):
        self.is_canceled = False
        self.return_function = return_function
        self.timer = threading.Timer(1, self.start_timer)
        self.timer.start()

    def stop(self):
        self.is_canceled = True

    def start_timer(self):
        if self.max_time <= 0 or self.is_canceled:
            self.timer.cancel()
            if self.return_function is not None:
                self.return_function()
        else:
            self.max_time -= 1
            print(self.max_time)
            self.timer = threading.Timer(1, self.start_timer)
            self.timer.start()
