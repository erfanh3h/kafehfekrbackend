from Commons.static_functions import safe_run_async
from Entities.Games.base_game_class import BaseGameClass


class BaseMultiPlayerGameClass(BaseGameClass):
    def __init__(self, send_data_function, players_count):
        super().__init__(send_data_function)
        self.active_player_indexes = []
        self.rank1 = None
        self.rank2 = None
        self.players_count = players_count

    def change_turn(self):
        if not self.active_player_indexes:
            self.current_turn = (self.current_turn % max(1, self.players_count)) + 1
            return
        if self.current_turn <= 0:
            self.current_turn = self.active_player_indexes[0]
            return
        for step in range(1, self.players_count + 1):
            candidate = ((self.current_turn - 1 + step) % self.players_count) + 1
            if candidate in self.active_player_indexes:
                self.current_turn = candidate
                return
        self.current_turn = self.active_player_indexes[0]

    def check_game_ended(self):
        if self.rank1 is not None and self.rank2 is not None:
            return True
        return False

    def _apply_surrender_sync(self, gamer_id):
        if gamer_id not in self.active_player_indexes:
            return False
        if len(self.active_player_indexes) == 2:
            if self.rank2 is None:
                self.rank2 = gamer_id
        self.active_player_indexes.remove(gamer_id)
        if len(self.active_player_indexes) == 1:
            self.rank1 = self.active_player_indexes[0]
            self.is_game_finished = True
            return True
        if self.current_turn == gamer_id:
            return True
        return False

    async def surrender(self, gamer_id):
        return self._apply_surrender_sync(gamer_id)

    def finish_reconnect_time(self, gamer_id):
        self._apply_surrender_sync(gamer_id)
