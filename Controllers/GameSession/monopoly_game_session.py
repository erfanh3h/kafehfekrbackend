from Commons import commands
from Commons.static_functions import make_command_json, safe_run_async
from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession
from Entities.Games.Monopoly import MonopolyGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import (
    Monopoly_Manage_Time,
    Monopoly_Response_Time,
    Monopoly_Turn_Time,
    Start_Game_Time,
)
from Entities.RewardManagerClass import GameScoreTypesEnum


class MonopolyGameSession(BaseMultiplayerGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)
        self._first_turn_started: bool = False

    def start_game_timer(self):
        if self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            count = 2
        else:
            count = max(2, min(4, len(self.gamers)))
        self.game_controller = MonopolyGameClass(
            send_data_function=self.send_command,
            players_count=count,
        )
        self.game_type = GameTypesEnum.MONOPOLY
        super().start_game_timer()

    def _get_phase_time_limit(self) -> int:
        phase = getattr(self.game_controller, "phase", "roll")
        if phase in ("auction", "trade"):
            return Monopoly_Response_Time
        if phase in ("buy_or_auction", "manage", "debt"):
            return Monopoly_Manage_Time
        return Monopoly_Turn_Time

    def _start_phase_timer(self):
        if self.is_game_finished or self.game_controller.is_game_finished:
            return
        self.timer.start(self._get_phase_time_limit(), self.on_turn_timeout)

    def _build_turn_payload(self) -> dict:
        payload = self.game_controller.get_game_data()
        payload["time_limit"] = self._get_phase_time_limit()
        return payload

    def send_game_data(self, function):
        self._first_turn_started = False
        game_data = {
            "gamers": [gamer.to_json() for gamer in self.gamers],
            "game_data": self.game_controller.get_game_data(),
        }
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Game_Data, data=game_data),
                game_id=self.game_id,
            )
        )
        self.timer.start(Start_Game_Time, self._start_first_turn)

    def _start_first_turn(self):
        if self.is_game_finished or self.check_finish_game():
            return
        if self._first_turn_started:
            return
        self._first_turn_started = True
        from Entities.SocketIOManagerClass import send_command
        state_payload = self._build_turn_payload()
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Start_Game, data=state_payload),
                game_id=self.game_id,
            )
        )
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data=state_payload),
                game_id=self.game_id,
            )
        )
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Monopoly_State, data=state_payload),
                game_id=self.game_id,
            )
        )
        self._start_phase_timer()

    def send_current_turn(self):
        if self.is_game_finished or self.check_finish_game():
            return
        from Entities.SocketIOManagerClass import send_command
        state_payload = self._build_turn_payload()
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data=state_payload),
                game_id=self.game_id,
            )
        )
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Monopoly_State, data=state_payload),
                game_id=self.game_id,
            )
        )
        self._start_phase_timer()

    def send_reconnect_data(self, socket_id):
        if not self.is_game_running:
            return
        gamer_data = self.find_gamer_from_socket(socket_id)
        gid = (
            gamer_data.gamer_id
            if (gamer_data is not None and gamer_data.gamer_id > 0)
            else self.game_controller.current_turn
        )
        g_data = self._build_turn_payload()
        g_data["game_type"] = GameTypesEnum.MONOPOLY.value
        reconnect_data = {
            "gamers": [g.to_json() for g in self.gamers],
            "game_data": g_data,
            "game_type": GameTypesEnum.MONOPOLY.value,
            "user_data": self.game_controller.get_user_private_game_data(gid),
        }
        remaining = max(0, self.timer.max_time - self.timer.counter)
        reconnect_data["timer_data"] = {
            "is_user_turn": (self.game_controller.current_turn == gid),
            "time": remaining if remaining > 0 else self._get_phase_time_limit(),
        }
        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(
                command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                socket_id=socket_id,
                game_id=self.game_id,
            )
        )

    async def _reset_gamer_missed_turns_async(self, gamer_id: int):
        gamer_obj = self.find_gamer_from_gamer_id(gamer_id)
        if gamer_obj is not None:
            prev_missed = int(getattr(gamer_obj, "not_played_turns", 0))
            if hasattr(gamer_obj, "reset_not_played_turns"):
                gamer_obj.reset_not_played_turns()
            if prev_missed > 0:
                await self.send_command(
                    commands.Not_played_Turns,
                    {"gamer_id": gamer_id, "count": 0, "max_turns": 3},
                )

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if not self.game_controller.check_authority(data, gamer_id):
            return
        cmd_id = data.get("id")
        if cmd_id not in (
            commands.Monopoly_Roll,
            commands.Monopoly_Action,
            commands.Monopoly_Auction,
            commands.Monopoly_Trade,
        ):
            return

        self._first_turn_started = True
        self.game_controller.is_current_turn_played = True
        self.timer.stop(False)

        prev_turn = self.game_controller.current_turn
        ev = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
        if not ev:
            self._start_phase_timer()
            return

        if cmd_id in (commands.Monopoly_Roll, commands.Monopoly_Action):
            await self._reset_gamer_missed_turns_async(gamer_id)

        state_payload = self._build_turn_payload()
        event_payload = dict(ev)
        event_payload["state"] = state_payload
        await self.send_command(commands.Monopoly_Event, event_payload)

        if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
            self.game_controller.is_game_finished = True
            await self.send_command(commands.Monopoly_State, state_payload)
            await self.send_command(
                commands.Win_Happened,
                {
                    "Winner": self.game_controller.rank1,
                    "winner_id": self.game_controller.rank1,
                    "rank1": self.game_controller.rank1,
                    "rank2": self.game_controller.rank2,
                },
            )
            self.timer.start(2, self.check_finish_game)
            return

        if self.game_controller.current_turn != prev_turn or self.game_controller.phase == "roll":
            await self.send_command(commands.Current_Turn, state_payload)
        await self.send_command(commands.Monopoly_State, state_payload)
        self._start_phase_timer()

    def _eliminate_afk_player(self, target_gid: int, gamer):
        self.afk_user_id = gamer.user_id
        if self.game_score_type != GameScoreTypesEnum.RANK and not str(gamer.user_id).startswith("bot_"):
            try:
                from Entities.Database import game_database
                game_database.users_manager.update_user(gamer.user_id, open_game_id="")
            except Exception as e:
                print(f"[MonopolyGameSession] Error clearing open_game_id on AFK forfeit: {e}")

        self.game_controller._apply_surrender_sync(target_gid)
        remaining_active = getattr(self.game_controller, "active_player_indexes", [])
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
            self.game_controller.phase = "finished"

        safe_run_async(
            self.send_command(
                commands.Surrender,
                {"gamer_id": target_gid, "reason": "afk"},
            )
        )
        state_payload = self._build_turn_payload()
        safe_run_async(self.send_command(commands.Monopoly_State, state_payload))

        if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
            self.game_controller.is_game_finished = True
            safe_run_async(
                self.send_command(
                    commands.Win_Happened,
                    {
                        "Winner": self.game_controller.rank1,
                        "winner_id": self.game_controller.rank1,
                        "rank1": self.game_controller.rank1,
                        "rank2": self.game_controller.rank2,
                    },
                )
            )
            self.check_finish_game()
            return
        self.send_current_turn()

    def on_turn_timeout(self):
        if self.is_game_finished or self.check_finish_game():
            return
        self._first_turn_started = True
        phase = self.game_controller.phase
        prev_turn = self.game_controller.current_turn

        if phase in ("roll", "buy_or_auction", "manage", "debt"):
            afk_gid = (
                int(self.game_controller.debt["player_id"])
                if (phase == "debt" and self.game_controller.debt)
                else self.game_controller.current_turn
            )
            gamer = self.find_gamer_from_gamer_id(afk_gid)
            if gamer is not None:
                gamer.not_played_turn()
                safe_run_async(
                    self.send_command(
                        commands.Not_played_Turns,
                        {
                            "gamer_id": afk_gid,
                            "count": gamer.not_played_turns,
                            "max_turns": 3,
                        },
                    )
                )
                if gamer.not_played_turns >= 3:
                    self._eliminate_afk_player(afk_gid, gamer)
                    return

        ev = self.game_controller.auto_resolve_timeout()
        state_payload = self._build_turn_payload()
        if ev:
            ev_payload = dict(ev)
            ev_payload["state"] = state_payload
            ev_payload["timeout_resolved"] = True
            safe_run_async(self.send_command(commands.Monopoly_Event, ev_payload))

        if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
            self.game_controller.is_game_finished = True
            safe_run_async(self.send_command(commands.Monopoly_State, state_payload))
            safe_run_async(
                self.send_command(
                    commands.Win_Happened,
                    {
                        "Winner": self.game_controller.rank1,
                        "winner_id": self.game_controller.rank1,
                        "rank1": self.game_controller.rank1,
                        "rank2": self.game_controller.rank2,
                    },
                )
            )
            self.check_finish_game()
            return

        if self.game_controller.current_turn != prev_turn or self.game_controller.phase == "roll":
            safe_run_async(self.send_command(commands.Current_Turn, state_payload))
        safe_run_async(self.send_command(commands.Monopoly_State, state_payload))
        self._start_phase_timer()
