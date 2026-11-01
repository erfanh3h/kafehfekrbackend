import asyncio

from Commons import commands
from Commons.static_functions import make_command_json, safe_run_async
from Controllers.GameSession import BaseGameSession
from Entities.RewardManagerClass import GameScoreTypesEnum


class BaseMultiplayerGameSession(BaseGameSession):

    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)

    def check_finish_game_by_not_play_turn(self, current_turn):
        pass

    async def command_received(self, data, socket_id):
        if isinstance(data, dict) and data.get('id') in [commands.Reconnect_Data, "RequestReconnectData", "reconnect_data"]:
            self.send_reconnect_data(socket_id)
            return None

        cmd_id = data.get('id') if isinstance(data, dict) else None
        if not self.is_game_running and cmd_id not in (commands.Surrender, commands.Exit_Game):
            return None

        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is None:
            return None
        if any(g.gamer_id == 0 for g in self.gamers):
            self.prepare_gamers()
        if not self.is_game_running and cmd_id == commands.Surrender:
            self.is_game_running = True

        gamer_id = gamer_data.gamer_id
        if gamer_id is None or gamer_id == 0:
            return None

        if cmd_id == commands.Surrender:
            if self.game_score_type != GameScoreTypesEnum.RANK and not str(gamer_data.user_id).startswith("bot_"):
                try:
                    from Entities.Database import game_database
                    game_database.users_manager.update_user(gamer_data.user_id, open_game_id="")
                except Exception as e:
                    print(f"[BaseMultiplayerGameSession] Error clearing open_game_id on surrender: {e}")

            should_timer_stop = await self.game_controller.surrender(gamer_id)
            await self.send_command(commands.Surrender, {"gamer_id": gamer_id})

            # If all remaining active players are bots (e.g. human surrendered vs bots), finish immediately
            remaining_active = getattr(self.game_controller, 'active_player_indexes', [])
            has_remaining_human = False
            for active_gid in remaining_active:
                g_obj = self.find_gamer_from_gamer_id(active_gid)
                if g_obj is not None and not str(g_obj.user_id).startswith("bot_"):
                    has_remaining_human = True
                    break
            if not has_remaining_human and len(remaining_active) > 0:
                if self.game_controller.rank1 is None:
                    self.game_controller.rank1 = remaining_active[0]
                if self.game_controller.rank2 is None and len(remaining_active) > 1:
                    self.game_controller.rank2 = remaining_active[1]
                self.game_controller.is_game_finished = True

            if self.check_finish_game():
                self.timer.stop(False)
                return None

            if should_timer_stop:
                self.timer.stop(False)
                self.send_current_turn()
            return None

        if cmd_id == commands.Exit_Game:
            if self.game_score_type == GameScoreTypesEnum.RANK:
                return None
            if not str(gamer_data.user_id).startswith("bot_"):
                try:
                    from Entities.Database import game_database
                    game_database.users_manager.update_user(gamer_data.user_id, open_game_id="")
                except Exception:
                    pass
            return None

        return gamer_id

    def check_finish_game(self):
        from Entities.SocketIOManagerClass import send_command
        if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
            self.game_controller.is_game_finished = True
            winner = self.game_controller.get_game_winner()
            final_winner = self.game_controller.rank1 if self.game_controller.rank1 is not None else winner
            if self.game_score_type not in (GameScoreTypesEnum.RANK, GameScoreTypesEnum.CLASSIC_RANK):
                safe_run_async(
                    send_command(
                        command=make_command_json(
                            id=commands.Finish_Game,
                            data={
                                "rank1": self.game_controller.rank1,
                                "rank2": self.game_controller.rank2,
                                "Winner": final_winner,
                            }
                        ),
                        game_id=self.game_id
                    )
                )
            self.finish_game(final_winner)
            return True
        return False

    def finish_game(self, winner_gamer_id):
        if self.is_game_finished:
            return
        if self.game_score_type in (GameScoreTypesEnum.RANK, GameScoreTypesEnum.CLASSIC_RANK):
            print("finish from rank/classic_rank")
            super().finish_game(self.game_controller.rank1 if self.game_controller.rank1 is not None else winner_gamer_id)
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
        gamer_index = self.find_gamer_index_from_id(user_id)
        if gamer_index is not None:
            self.gamers[gamer_index].set_finish_reconnect_time_function(self.finish_reconnect_time)
            if self.gamers[gamer_index].is_joined_game:
                self.gamers[gamer_index].reconnect(socket_id)
                self.send_reconnect_data(socket_id)
                if not self.game_controller.active_player_indexes.__contains__(
                        self.gamers[gamer_index].gamer_id):  # check user is one of active players
                    return
                self.timer.resume()
                safe_run_async(
                    self.send_command(commands.User_Reconnected,
                                      {"user_id": user_id, 'time': max(0, self.timer.max_time - self.timer.counter)}))
            else:
                self.gamers[gamer_index].join_game(socket_id)
                if self.is_game_running:
                    self.send_reconnect_data(socket_id)
