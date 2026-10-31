import asyncio

from Commons import commands
from Commons.static_functions import make_command_json
from Controllers.GameSession import BaseGameSession
from Entities.RewardManagerClass import GameScoreTypesEnum


def safe_run_async(coro):
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


class BaseMultiplayerGameSession(BaseGameSession):

    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def check_finish_game_by_not_play_turn(self, current_turn):
        pass

    async def command_received(self, data, socket_id):
        if not self.is_game_running:
            return None
        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is None:
            return None
        else:
            gamer_id = gamer_data.gamer_id
        if gamer_id is None:
            return
        if data['id'] == commands.Surrender:
            should_timer_stop = await self.game_controller.surrender(gamer_id)
            await self.send_command(commands.Surrender, {"gamer_id": gamer_id})
            if should_timer_stop:
                self.timer.stop(False)
                self.send_current_turn()
            return None

        if data['id'] == commands.Exit_Game:
            if self.game_score_type == GameScoreTypesEnum.RANK:
                return
            from Entities.Database import game_database
            game_database.users_manager.update_user(gamer_data.user_id, open_game_id="")
        return gamer_id

    def check_finish_game(self):
        from Entities.SocketIOManagerClass import send_command
        if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
            self.game_controller.is_game_finished = True
            winner = self.game_controller.get_game_winner()
            safe_run_async(
                send_command(
                    command=make_command_json(
                        id=commands.Finish_Game,
                        data={
                            "rank1": self.game_controller.rank1,
                            "rank2": self.game_controller.rank2,
                            "Winner": self.game_controller.rank1 if self.game_controller.rank1 is not None else winner,
                        }
                    ),
                    game_id=self.game_id
                )
            )
            self.finish_game(winner)
            return True
        return False

    def finish_game(self, winner_gamer_id):
        if self.is_game_finished:
            return
        if self.game_score_type == GameScoreTypesEnum.RANK:  # 2 players rank game must end from there
            print("finish from rank")
            super().finish_game(self.game_controller.rank1)
            return
        print("finish from normal")
        self.is_game_finished = True
        user_idis = [g.user_id for g in self.gamers],
        from Entities.Database import game_database
        game_database.game_history_manager.create_game_history(self.game_history_id, self.game_id, user_idis,
                                                               str(self.game_type.value), self.game_score_type.value,
                                                               self.game_controller.rank1)
        from Entities.SocketIOClass.game import finish_multiplayer_game
        rank1_id = self.gamer_id_to_user_id(self.game_controller.rank1)
        rank2_id = self.gamer_id_to_user_id(self.game_controller.rank2)
        finish_multiplayer_game(self.game_id, rank1_id, rank2_id)

    def disconnect_user(self, socket_id):
        for gamer_index in range(0, len(self.gamers)):
            if self.gamers[gamer_index].socket_id == socket_id:
                if not self.game_controller.active_player_indexes.__contains__(
                        self.gamers[gamer_index].gamer_id):  # check user is one of active players
                    return
                user_data = self.find_gamer_from_socket(socket_id)
                if user_data is not None:
                    safe_run_async(
                        self.send_command(commands.User_Disconnected,
                                          {"user_id": user_data.user_id, "time": user_data.timer.max_time}))
                self.gamers[gamer_index].disconnect()
                self.timer.pause()
                break

    def join_gamer(self, user_id: int, socket_id):
        import time, threading

        def send_reconnect_data():  # used this like to give device change socket handler functions
            time.sleep(2)
            self.send_reconnect_data(socket_id)

        gamer_index = self.find_gamer_index_from_id(user_id)
        if gamer_index is not None:
            self.gamers[gamer_index].set_finish_reconnect_time_function(self.finish_reconnect_time)
            if self.gamers[gamer_index].is_joined_game:
                t = threading.Thread(target=send_reconnect_data, daemon=True)
                t.start()
                self.gamers[gamer_index].reconnect(socket_id)
                if not self.game_controller.active_player_indexes.__contains__(
                        self.gamers[gamer_index].gamer_id):  # check user is one of active players
                    return
                self.timer.resume()
                safe_run_async(
                    self.send_command(commands.User_Reconnected,
                                      {"user_id": user_id, 'time': self.timer.max_time - self.timer.counter}))
            else:
                self.gamers[gamer_index].join_game(socket_id)
