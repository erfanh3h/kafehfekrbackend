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

    @staticmethod
    def _is_bot_user(user_id) -> bool:
        return str(user_id).startswith("bot_")

    def _is_player_active(self, gamer_id: int) -> bool:
        if gamer_id is None or gamer_id <= 0 or self.game_controller is None:
            return False
        active = getattr(self.game_controller, "active_player_indexes", None)
        if active is None:
            return True
        return gamer_id in active

    def _has_any_active_disconnected_player(self) -> bool:
        if self.game_controller is None:
            return any(getattr(g, "is_disconnected", False) for g in self.gamers)
        active = getattr(self.game_controller, "active_player_indexes", None)
        for g in self.gamers:
            if not getattr(g, "is_disconnected", False):
                continue
            if active is None or g.gamer_id == 0 or g.gamer_id in active:
                return True
        return False

    def _sync_timer_pause_state(self):
        if self.is_game_finished:
            return
        if self._has_any_active_disconnected_player():
            self.timer.pause()
        elif getattr(self.timer, "is_paused", False) and not getattr(self.timer, "is_canceled", True):
            self.timer.resume()

    def _clear_user_open_game_id(self, user_id):
        if self.game_score_type == GameScoreTypesEnum.RANK or self._is_bot_user(user_id):
            return
        try:
            from Entities.Database import game_database
            user_doc = game_database.users_manager.read_user(user_id)
            if user_doc is None or user_doc.get("open_game_id", "") in ("", self.game_id):
                game_database.users_manager.update_user(user_id, open_game_id="")
        except Exception as e:
            print(f"[BaseMultiplayerGameSession] Error clearing open_game_id for {user_id}: {e}")

    def _check_and_finish_if_no_humans_left(self) -> bool:
        if self.game_controller is None:
            return False
        remaining_active = list(getattr(self.game_controller, "active_player_indexes", []))
        if len(remaining_active) == 0:
            self.game_controller.is_game_finished = True
            return True
        has_remaining_human = False
        for active_gid in remaining_active:
            g_obj = self.find_gamer_from_gamer_id(active_gid)
            if g_obj is not None and not self._is_bot_user(g_obj.user_id):
                has_remaining_human = True
                break
        if not has_remaining_human:
            if self.game_controller.rank1 is None:
                self.game_controller.rank1 = remaining_active[0]
            if self.game_controller.rank2 is None and len(remaining_active) > 1:
                for gid in remaining_active:
                    if gid != self.game_controller.rank1:
                        self.game_controller.rank2 = gid
                        break
            self.game_controller.is_game_finished = True
            return True
        return False

    def _build_surrender_payload(self, gamer_id: int, reason: str = "surrender") -> dict:
        return {"gamer_id": gamer_id}

    def _on_player_eliminated(self, gamer_id: int, reason: str, state_changed: bool, was_turn: bool):
        if was_turn or state_changed:
            self.timer.stop(False)
            self.send_current_turn()
        self._sync_timer_pause_state()

    def _eliminate_player_locked(self, gamer_data, reason: str = "surrender", pre_apply_fn=None) -> bool:
        with self._finish_lock:
            if self.is_game_finished or self.game_controller is None or gamer_data is None:
                return False
            if any(g.gamer_id == 0 for g in self.gamers):
                self.prepare_gamers()
            gamer_id = gamer_data.gamer_id
            if gamer_id is None or gamer_id == 0:
                return False
            if not self._is_player_active(gamer_id):
                try:
                    gamer_data.timer.stop()
                except Exception:
                    pass
                gamer_data.is_disconnected = False
                return False

            try:
                gamer_data.timer.stop()
            except Exception:
                pass
            gamer_data.is_disconnected = False

            if reason == "disconnect_timeout":
                self.dc_timeout_user_id = gamer_data.user_id
                self.dc_timeout_user_ids.add(str(gamer_data.user_id))
            elif reason == "afk":
                self.afk_user_id = gamer_data.user_id
                self.afk_user_ids.add(str(gamer_data.user_id))
            elif reason == "surrender":
                self.surrender_user_ids.add(str(gamer_data.user_id))

            self._clear_user_open_game_id(gamer_data.user_id)

            was_turn = (getattr(self.game_controller, "current_turn", 0) == gamer_id)
            prev_rank1 = getattr(self.game_controller, "rank1", None)
            active_before = list(getattr(self.game_controller, "active_player_indexes", []))
            other_active_gids = [gid for gid in active_before if gid != gamer_id]

            if pre_apply_fn is not None:
                pre_apply_fn(gamer_id)

            if reason == "disconnect_timeout" and hasattr(self.game_controller, "finish_reconnect_time"):
                state_changed = bool(self.game_controller.finish_reconnect_time(gamer_id))
            elif hasattr(self.game_controller, "_apply_surrender_sync"):
                state_changed = bool(self.game_controller._apply_surrender_sync(gamer_id))
            else:
                state_changed = bool(self.game_controller.finish_reconnect_time(gamer_id))

            # If disconnect timeout leaves only 1 active player who is ALSO disconnected, end as draw (unless rank1 was already legitimately won)
            if reason == "disconnect_timeout" and len(other_active_gids) == 1:
                survivor = self.find_gamer_from_gamer_id(other_active_gids[0])
                if survivor is not None and getattr(survivor, "is_disconnected", False):
                    try:
                        survivor.timer.stop()
                    except Exception:
                        pass
                    survivor.is_disconnected = False
                    self.dc_timeout_user_ids.add(str(survivor.user_id))
                    if prev_rank1 is None:
                        self.game_controller.rank1 = 0
                        self.game_controller.rank2 = 0
                    else:
                        self.game_controller.rank1 = prev_rank1
                        self.game_controller.rank2 = 0
                    self.game_controller.is_game_finished = True

            surrender_payload = self._build_surrender_payload(gamer_id, reason)
            safe_run_async(self.send_command(commands.Surrender, surrender_payload))

            self._check_and_finish_if_no_humans_left()

            if self.check_finish_game():
                self.timer.stop(False)
                return True

            self._on_player_eliminated(gamer_id, reason, state_changed, was_turn)
            return True

    async def command_received(self, data, socket_id):
        if not isinstance(data, dict) or "id" not in data:
            return None
        data.setdefault("data", None)
        if data.get('id') in [commands.Reconnect_Data, "RequestReconnectData", "reconnect_data"]:
            self.send_reconnect_data(socket_id)
            return None

        if self.is_game_finished:
            return None

        cmd_id = data.get('id')
        if not self.is_game_running and cmd_id not in (commands.Surrender, commands.Exit_Game):
            return None

        gamer_data = self.find_gamer_from_socket(socket_id)
        if gamer_data is None:
            return None
        if any(g.gamer_id == 0 for g in self.gamers):
            self.prepare_gamers()
        if not self.is_game_running and cmd_id == commands.Surrender:
            self.is_game_running = True
        if self.started_monotonic <= 0.0:
            import time as _time
            self.started_monotonic = _time.monotonic()

        gamer_id = gamer_data.gamer_id
        if gamer_id is None or gamer_id == 0:
            return None

        if cmd_id == commands.Surrender:
            self.surrender_user_ids.add(str(gamer_data.user_id))
            self._eliminate_player_locked(gamer_data, reason="surrender")
            return None

        if cmd_id == commands.Exit_Game:
            self._clear_user_open_game_id(gamer_data.user_id)
            return None

        # Reject gameplay commands from already-eliminated / surrendered players
        if not self._is_player_active(gamer_id):
            return None

        uid_key = str(gamer_data.user_id)
        self.player_actions_count[uid_key] = self.player_actions_count.get(uid_key, 0) + 1
        return gamer_id

    def finish_reconnect_time(self, user_id):
        with self._finish_lock:
            if self.is_game_finished:
                return
            gamer_index = self.find_gamer_index_from_id(user_id)
            if gamer_index is None:
                return
            gamer_data = self.gamers[gamer_index]
            if not getattr(gamer_data, "is_disconnected", False):
                return
            if self.game_controller is not None and gamer_data.gamer_id > 0 and not self._is_player_active(gamer_data.gamer_id):
                gamer_data.is_disconnected = False
                return
            safe_run_async(self.send_command(commands.Finish_Reconnect_Time, {"user_id": user_id}))
            self._eliminate_player_locked(gamer_data, reason="disconnect_timeout")

    def check_finish_game(self):
        from Entities.SocketIOManagerClass import send_command
        if self.game_controller is None:
            return False
        if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
            self.game_controller.is_game_finished = True
            winner = self.game_controller.get_game_winner()
            final_winner = self.game_controller.rank1 if self.game_controller.rank1 is not None else winner
            from Entities.SocketIOClass.game import games
            if self.game_score_type not in (GameScoreTypesEnum.RANK, GameScoreTypesEnum.CLASSIC_RANK) and self.game_id not in games:
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
        with self._finish_lock:
            if self.is_game_finished:
                return
            if self.game_score_type in (GameScoreTypesEnum.RANK, GameScoreTypesEnum.CLASSIC_RANK):
                print("finish from rank/classic_rank")
                super().finish_game(self.game_controller.rank1 if self.game_controller.rank1 is not None else winner_gamer_id)
                return
            print("finish from normal")
            self.is_game_finished = True
            self.timer.stop(False)
        for g in self.gamers:
            try:
                g.timer.stop()
            except Exception:
                pass
        user_idis = [g.user_id for g in self.gamers]
        from Entities.Database import game_database
        try:
            game_type_val = self.game_type.value if hasattr(self.game_type, "value") else str(self.game_type)
            game_score_val = self.game_score_type.value if hasattr(self.game_score_type, "value") else str(self.game_score_type)
            users_info = []
            for g in self.gamers:
                users_info.append({
                    "user_id": str(g.user_id),
                    "username": getattr(g, "username", getattr(g, "name", "")),
                    "image": int(getattr(g, "user_image", getattr(g, "image", 0))),
                })
            game_database.game_history_manager.create_game_history(self.game_history_id, self.game_id, user_idis,
                                                                   str(game_type_val), game_score_val,
                                                                   self.game_controller.rank1, users_info=users_info)
        except Exception as e:
            print(f"[BaseMultiplayerGameSession] Error creating game history: {e}")
        from Entities.SocketIOClass.game import finish_multiplayer_game
        raw_r1 = self.game_controller.rank1
        raw_r2 = self.game_controller.rank2
        rank1_id = 0 if raw_r1 == 0 else self.gamer_id_to_user_id(raw_r1)
        rank2_id = 0 if raw_r2 == 0 else self.gamer_id_to_user_id(raw_r2)
        if rank1_id not in (None, 0) and rank2_id is not None and str(rank2_id) == str(rank1_id):
            rank2_id = None
        finish_multiplayer_game(self.game_id, rank1_id, rank2_id)

    def disconnect_user(self, socket_id):
        with self._finish_lock:
            if self.is_game_finished:
                return
            for gamer in self.gamers:
                if gamer.socket_id == socket_id:
                    if self.game_controller is not None and gamer.gamer_id > 0:
                        if not self._is_player_active(gamer.gamer_id):
                            return
                    if gamer.is_disconnected:
                        return
                    safe_run_async(
                        self.send_command(commands.User_Disconnected,
                                          {"user_id": gamer.user_id, "time": gamer.timer.max_time}))
                    gamer.disconnect()
                    self.timer.pause()
                    break

    def join_gamer(self, user_id: int, socket_id):
        with self._finish_lock:
            gamer_index = self.find_gamer_index_from_id(user_id)
            if gamer_index is None:
                return
            gamer = self.gamers[gamer_index]
            gamer.set_finish_reconnect_time_function(self.finish_reconnect_time)
            if gamer.is_joined_game:
                if not gamer.is_disconnected and gamer.socket_id not in ("", socket_id):
                    return
                was_disconnected = gamer.is_disconnected
                gamer.reconnect(socket_id)
                self.send_reconnect_data(socket_id)
                if self.is_game_finished:
                    return
                if self.game_controller is not None and gamer.gamer_id > 0 and not self._is_player_active(gamer.gamer_id):
                    return
                self._sync_timer_pause_state()
                if was_disconnected:
                    safe_run_async(
                        self.send_command(commands.User_Reconnected,
                                          {"user_id": user_id, 'time': max(0, self.timer.max_time - self.timer.counter)}))
            else:
                gamer.join_game(socket_id)
                if self.is_game_running:
                    self.send_reconnect_data(socket_id)
