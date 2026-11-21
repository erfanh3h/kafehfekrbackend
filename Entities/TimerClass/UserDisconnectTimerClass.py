import threading


class UserDisconnectTimerClass:
    def __init__(self, user_id: str, max_time: int = 60):
        self.timerCounting = True
        self.max_time = max_time
        self.finish_timer_function = None
        self.is_canceled = False
        self._run_id = 0
        self._lock = threading.RLock()
        self.timer = None
        self.user_id = user_id

    def set_finish_timer_function(self, finish_timer_function):
        with self._lock:
            self.finish_timer_function = finish_timer_function

    def _cancel_handle(self):
        if self.timer is not None:
            try:
                self.timer.cancel()
            except Exception:
                pass
            self.timer = None

    def start(self):
        with self._lock:
            self._run_id += 1
            run_id = self._run_id
            self._cancel_handle()
            self.is_canceled = False
            self.timer = threading.Timer(1, self.start_timer, args=(run_id,))
            self.timer.daemon = True
            self.timer.start()

    def stop(self):
        with self._lock:
            self._run_id += 1
            self.is_canceled = True
            self._cancel_handle()

    def start_timer(self, run_id=None):
        fn = None
        uid = self.user_id
        with self._lock:
            if self.is_canceled or (run_id is not None and run_id != self._run_id):
                self._cancel_handle()
                return
            if self.max_time <= 0:
                self._cancel_handle()
                self.is_canceled = True
                fn = self.finish_timer_function
            else:
                self.max_time -= 1
                cur_id = self._run_id
                self.timer = threading.Timer(1, self.start_timer, args=(cur_id,))
                self.timer.daemon = True
                self.timer.start()
        if fn is not None:
            fn(uid)
