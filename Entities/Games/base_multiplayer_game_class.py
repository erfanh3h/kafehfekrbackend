from Entities.Games.base_game_class import BaseGameClass


class BaseMultiPlayerGameClass(BaseGameClass):
    def __init__(self, send_data_function, players_count):
        super().__init__(send_data_function)
        self.active_player_indexes = []
        self.rank1 = None
        self.rank2 = None
        self.players_count = players_count

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = 2
        else:
            if self.players_count == 4:
                if self.current_turn == 2:
                    self.current_turn = 3
                elif self.current_turn == 3:
                    self.current_turn = 4
                else:
                    self.current_turn = 1
            if self.players_count == 3:
                if self.current_turn == 2:
                    self.current_turn = 3
                else:
                    self.current_turn = 1
            else:
                self.current_turn = 1
        if len(self.active_player_indexes) != 0 and not self.active_player_indexes.__contains__(self.current_turn):
            self.change_turn()

    def check_game_ended(self):
        if self.rank1 is not None and self.rank2 is not None:
            return True
        return False

    async def surrender(self, gamer_id):
        if not self.active_player_indexes.__contains__(gamer_id):
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

    def finish_reconnect_time(self, gamer_id):
        import asyncio
        asyncio.new_event_loop().run_until_complete(self.surrender(gamer_id))
