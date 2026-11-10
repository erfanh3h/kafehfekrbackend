from Commons import commands
from Commons.static_functions import make_command_json, safe_run_async
from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession
from Entities.Games.Uno import UnoGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Start_Game_Time, Uno_Turn_Time
from Entities.RewardManagerClass import GameScoreTypesEnum


class UnoGameSession(BaseMultiplayerGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)
        self._first_turn_started: bool = False

    def start_game_timer(self):
        if self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            count = 2
        else:
            count = max(2, min(4, len(self.gamers)))
        self.game_controller = UnoGameClass(
            send_data_function=self.send_command,
            players_count=count,
        )
        self.game_type = GameTypesEnum.UNO
        super().start_game_timer()

    async def send_private_command(self, command_id, command_data, gamer_id: int):
        data = self.find_gamer_from_gamer_id(gamer_id)
        if data is not None and data.socket_id:
            from Entities.SocketIOManagerClass import send_private_command
            await send_private_command(
                command=make_command_json(id=command_id, data=command_data),
                socket_id=data.socket_id,
                game_id=self.game_id,
            )

    async def _sync_all_private_user_data_async(self):
        from Entities.SocketIOManagerClass import send_private_command
        for index, gamer in enumerate(self.gamers):
            if gamer.socket_id:
                gid = gamer.gamer_id if gamer.gamer_id > 0 else (index + 1)
                await send_private_command(
                    command=make_command_json(
                        id=commands.User_Data,
                        data=self.game_controller.get_user_private_game_data(gid),
                    ),
                    socket_id=gamer.socket_id,
                    game_id=self.game_id,
                )

    def _sync_all_private_user_data(self):
        safe_run_async(self._sync_all_private_user_data_async())

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
        self._sync_all_private_user_data()
        self.timer.start(Start_Game_Time, self._start_first_turn)

    def _build_turn_payload(self) -> dict:
        deck_rem = len(self.game_controller.draw_pile)
        return {
            "turn": self.game_controller.current_turn,
            "direction": self.game_controller.direction,
            "current_color": self.game_controller.current_color,
            "current_value": self.game_controller.current_value,
            "top_card": self.game_controller.get_top_card(),
            "hands_count": self.game_controller.get_hands_count(),
            "draw_pile_count": deck_rem,
            "deck_remaining": deck_rem,
            "has_drawn_this_turn": self.game_controller.has_drawn_this_turn,
            "uno_called": self.game_controller.get_uno_called_dict(),
        }

    def _start_first_turn(self):
        if self.is_game_finished or self.check_finish_game():
            return
        if self._first_turn_started:
            return
        self._first_turn_started = True
        from Entities.SocketIOManagerClass import send_command
        turn_payload = self._build_turn_payload()
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Start_Game, data=turn_payload),
                game_id=self.game_id,
            )
        )
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data=turn_payload),
                game_id=self.game_id,
            )
        )
        self._sync_all_private_user_data()
        self.timer.start(Uno_Turn_Time, self.on_turn_timeout)

    def send_current_turn(self):
        if self.is_game_finished or self.check_finish_game():
            return
        from Entities.SocketIOManagerClass import send_command
        turn_payload = self._build_turn_payload()
        self._sync_all_private_user_data()
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data=turn_payload),
                game_id=self.game_id,
            )
        )
        self.timer.start(Uno_Turn_Time, self.on_turn_timeout)

    def send_reconnect_data(self, socket_id):
        if not self.is_game_running:
            return
        gamer_data = self.find_gamer_from_socket(socket_id)
        gid = (
            gamer_data.gamer_id
            if (gamer_data is not None and gamer_data.gamer_id > 0)
            else self.game_controller.current_turn
        )
        user_priv = self.game_controller.get_user_private_game_data(gid)
        g_data = self.game_controller.get_game_data()
        g_data["game_type"] = GameTypesEnum.UNO.value
        g_data["my_hand"] = user_priv.get("hand", [])
        g_data["hand"] = user_priv.get("hand", [])
        reconnect_data = {
            "gamers": [g.to_json() for g in self.gamers],
            "game_data": g_data,
            "game_type": GameTypesEnum.UNO.value,
            "user_data": user_priv,
        }
        if self.timer.is_user_turn:
            reconnect_data["timer_data"] = {
                "is_user_turn": True,
                "time": self.timer.counter + 1,
            }
        else:
            reconnect_data["timer_data"] = {"is_user_turn": False, "time": 0}

        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(
                command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                socket_id=socket_id,
                game_id=self.game_id,
            )
        )
        safe_run_async(
            send_private_command(
                command=make_command_json(
                    id=commands.User_Data,
                    data=user_priv,
                ),
                socket_id=socket_id,
                game_id=self.game_id,
            )
        )

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return

        if not self.game_controller.check_authority(data, gamer_id):
            return

        cmd_id = data.get("id")
        if cmd_id == commands.Call_Uno:
            res = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if res:
                await self.send_command(commands.Uno_Called, res)
            return

        self.game_controller.is_current_turn_played = True

        if cmd_id in (commands.Play_Card, commands.Select_Peace):
            self._first_turn_started = True
            self.timer.stop(False)
            res = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if not res:
                self.timer.start(Uno_Turn_Time, self.on_turn_timeout)
                return

            deck_rem = len(self.game_controller.draw_pile)
            payload = dict(res)
            payload["player"] = gamer_id
            payload["hands_count"] = self.game_controller.get_hands_count()
            payload["draw_pile_count"] = deck_rem
            payload["deck_remaining"] = deck_rem
            payload["top_card"] = self.game_controller.get_top_card()

            await self._sync_all_private_user_data_async()
            await self.send_command(commands.Card_Played, payload)

            if self.game_controller.is_game_finished:
                await self.send_command(
                    commands.Win_Happened,
                    {
                        "Winner": self.game_controller.rank1,
                        "winner_id": self.game_controller.rank1,
                        "rank1": self.game_controller.rank1,
                        "rank2": self.game_controller.rank2,
                    },
                )
                self.timer.start(1, self.check_finish_game)
                return

            await self.send_command(commands.Current_Turn, self._build_turn_payload())
            self.timer.start(Uno_Turn_Time, self.on_turn_timeout)

        elif cmd_id == commands.Draw_Card:
            self._first_turn_started = True
            self.timer.stop(False)
            res = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if not res:
                self.timer.start(Uno_Turn_Time, self.on_turn_timeout)
                return

            await self._sync_all_private_user_data_async()
            user_priv = self.game_controller.get_user_private_game_data(gamer_id)
            deck_rem = len(self.game_controller.draw_pile)
            can_play_drawn = bool(res.get("drawn_is_playable", False)) and not bool(res.get("turn_passed", False))
            await self.send_private_command(
                commands.Draw_Result_Private,
                {
                    "gamer_id": gamer_id,
                    "player": gamer_id,
                    "drawn_card": res.get("drawn_card"),
                    "drawn_is_playable": res.get("drawn_is_playable", False),
                    "playable": can_play_drawn,
                    "playable_uids": res.get("playable_uids", []),
                    "has_drawn_this_turn": res.get("has_drawn_this_turn", False),
                    "turn_passed": res.get("turn_passed", False),
                    "my_hand": user_priv.get("hand", []),
                    "hand": user_priv.get("hand", []),
                    "user_data": user_priv,
                },
                gamer_id,
            )
            await self.send_command(
                commands.Draw_Result,
                {
                    "gamer_id": gamer_id,
                    "player": gamer_id,
                    "drawn_count": 1,
                    "has_drawn_this_turn": res.get("has_drawn_this_turn", False),
                    "turn_passed": res.get("turn_passed", False),
                    "next_turn": self.game_controller.current_turn,
                    "direction": self.game_controller.direction,
                    "hands_count": self.game_controller.get_hands_count(),
                    "draw_pile_count": deck_rem,
                    "deck_remaining": deck_rem,
                },
            )
            if res.get("turn_passed"):
                await self.send_command(commands.Current_Turn, self._build_turn_payload())
            self.timer.start(Uno_Turn_Time, self.on_turn_timeout)

        elif cmd_id == commands.Pass_Turn:
            self._first_turn_started = True
            self.timer.stop(False)
            res = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if not res:
                self.timer.start(Uno_Turn_Time, self.on_turn_timeout)
                return

            deck_rem = len(self.game_controller.draw_pile)
            await self._sync_all_private_user_data_async()
            await self.send_command(
                commands.Pass_Turn,
                {
                    "gamer_id": gamer_id,
                    "player": gamer_id,
                    "next_turn": self.game_controller.current_turn,
                    "direction": self.game_controller.direction,
                    "hands_count": self.game_controller.get_hands_count(),
                    "draw_pile_count": deck_rem,
                    "deck_remaining": deck_rem,
                },
            )
            await self.send_command(commands.Current_Turn, self._build_turn_payload())
            self.timer.start(Uno_Turn_Time, self.on_turn_timeout)

    def on_turn_timeout(self):
        if self.is_game_finished or self.check_finish_game():
            return
        self._first_turn_started = True
        cur_turn = self.game_controller.current_turn

        if not self.game_controller.has_drawn_this_turn:
            res = self.game_controller.draw_card_for_turn(cur_turn, force_pass=True)
            self._sync_all_private_user_data()
            user_priv = self.game_controller.get_user_private_game_data(cur_turn)
            deck_rem = len(self.game_controller.draw_pile)
            safe_run_async(
                self.send_private_command(
                    commands.Draw_Result_Private,
                    {
                        "gamer_id": cur_turn,
                        "player": cur_turn,
                        "drawn_card": res.get("drawn_card"),
                        "drawn_is_playable": False,
                        "playable": False,
                        "playable_uids": [],
                        "has_drawn_this_turn": False,
                        "turn_passed": True,
                        "my_hand": user_priv.get("hand", []),
                        "hand": user_priv.get("hand", []),
                        "user_data": user_priv,
                    },
                    cur_turn,
                )
            )
            safe_run_async(
                self.send_command(
                    commands.Draw_Result,
                    {
                        "gamer_id": cur_turn,
                        "player": cur_turn,
                        "drawn_count": 1,
                        "has_drawn_this_turn": False,
                        "turn_passed": True,
                        "next_turn": self.game_controller.current_turn,
                        "direction": self.game_controller.direction,
                        "hands_count": self.game_controller.get_hands_count(),
                        "draw_pile_count": deck_rem,
                        "deck_remaining": deck_rem,
                    },
                )
            )
        else:
            self.game_controller.pass_turn(cur_turn)
            self._sync_all_private_user_data()
            deck_rem = len(self.game_controller.draw_pile)
            safe_run_async(
                self.send_command(
                    commands.Pass_Turn,
                    {
                        "gamer_id": cur_turn,
                        "player": cur_turn,
                        "next_turn": self.game_controller.current_turn,
                        "direction": self.game_controller.direction,
                        "hands_count": self.game_controller.get_hands_count(),
                        "draw_pile_count": deck_rem,
                        "deck_remaining": deck_rem,
                    },
                )
            )

        self.send_current_turn()
