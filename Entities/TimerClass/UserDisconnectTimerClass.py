import threading


class UserDisconnectTimerClass:
    def __init__(self, user_id: str, max_time: int = 60):
        self.timerCounting = True
        self.max_time = max_time
        self.finish_timer_function = None
        self.is_canceled = False
        self._run_id = 0
        self.timer = threading.Timer(1, self.start_timer, args=(self._run_id,))
        self.timer.daemon = True
        self.user_id = user_id

    def set_finish_timer_function(self, finish_timer_function):
        self.finish_timer_function = finish_timer_function

    def start(self):
        self._run_id += 1
        try:
            self.timer.cancel()
        except Exception:
            pass
        self.is_canceled = False
        self.timer = threading.Timer(1, self.start_timer, args=(self._run_id,))
        self.timer.daemon = True
        self.timer.start()

    def stop(self):
        self._run_id += 1
        self.is_canceled = True
        try:
            self.timer.cancel()
        except Exception:
            pass

    def start_timer(self, run_id=None):
        if self.is_canceled or (run_id is not None and run_id != self._run_id):
            try:
                self.timer.cancel()
            except Exception:
                pass
            return
        if self.max_time <= 0:
            try:
                self.timer.cancel()
            except Exception:
                pass
            if self.finish_timer_function is not None:
                self.finish_timer_function(self.user_id)
        else:
            self.max_time -= 1
            self.timer = threading.Timer(1, self.start_timer, args=(self._run_id,))
            self.timer.daemon = True
            self.timer.start()
