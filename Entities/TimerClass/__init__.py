import asyncio
import threading
import time

class TimerClass:
    def __init__(self, max_time: int = 0, return_function = None):
        self.timerCounting = True
        self.max_time = max_time
        # self.start_function = start_function
        self.return_function = return_function
        self.is_canceled = False
        self.counter = 0
        self.timer = threading.Timer(1, self.start_timer)
        # asyncio.get_running_loop().create_task(self.start_timer())

    def start(self , max_time: int , return_function):
        self.counter = 0
        self.is_canceled = False
        self.max_time = max_time
        self.return_function = return_function
        self.timer = threading.Timer(1, self.start_timer)
        self.timer.start()
    def stop(self):
        self.is_canceled = True

    def start_timer(self):
        print(self.counter)
        if self.counter > self.max_time or self.is_canceled:
            self.timer.cancel()
            if self.return_function is not None:
                self.return_function()
        else :
            self.counter += 1
            self.timer = threading.Timer(1, self.start_timer)
            self.timer.start()
