import asyncio
import threading
import time


class TimerClass:
    def __init__(self, max_time: int = 0, return_function=None):
        self.timerCounting = True
        self.max_time = max_time
        self.return_function = return_function
        self.is_canceled = False
        self.is_paused = False
        self.counter = 0
        self.is_user_turn = False
        self._run_id = 0
        self.timer = None

    def _cancel_timer_handle(self):
        if self.timer is not None:
            try:
                self.timer.cancel()
            except Exception:
                pass
            self.timer = None

    def start(self, max_time: int, return_function, is_user_turn=True):
        self._run_id += 1
        run_id = self._run_id
        self._cancel_timer_handle()
        self.counter = 0
        self.is_canceled = False
        self.is_paused = False
        self.max_time = max_time
        self.return_function = return_function
        self.is_user_turn = is_user_turn
        self.timer = threading.Timer(1, self.start_timer, args=(run_id,))
        self.timer.daemon = True
        self.timer.start()

    def stop(self, must_play_function=True):
        self._run_id += 1
        self._cancel_timer_handle()
        self.is_canceled = True
        self.is_user_turn = False
        fn = self.return_function
        if fn is not None and must_play_function:
            fn()

    # develop this like to keep track of time for reconnect data
    def start_timer(self, run_id=None):
        if run_id is not None and run_id != self._run_id:
            return
        if self.is_canceled or self.is_paused:
            return
        elif self.counter >= self.max_time:
            self._cancel_timer_handle()
            self.is_canceled = True
            self.is_user_turn = False
            fn = self.return_function
            if fn is not None:
                fn()
        else:
            self.counter += 1
            cur_id = self._run_id
            self.timer = threading.Timer(1, self.start_timer, args=(cur_id,))
            self.timer.daemon = True
            self.timer.start()

    def pause(self):
        self._run_id += 1
        self.is_paused = True
        self._cancel_timer_handle()

    def resume(self):
        if self.is_canceled:
            return
        self._run_id += 1
        run_id = self._run_id
        self.is_paused = False
        self._cancel_timer_handle()
        self.timer = threading.Timer(1, self.start_timer, args=(run_id,))
        self.timer.daemon = True
        self.timer.start()
