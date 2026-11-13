import threading
import time
from typing import Optional

from Commons import commands
from Commons.static_functions import make_command_json, safe_run_async
from Controllers.GameSession import BaseGameSession
from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession
from Entities.Games.Quiz import QuizGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Quiz_Turn_Time, Quiz_Sleep_Turn_Time, Start_Game_Time


class QuizGameSession(BaseMultiplayerGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)
        self.game_controller: Optional[QuizGameClass] = None
        self._round_lock = threading.RLock()

    def start_game_timer(self):
        self.game_controller = QuizGameClass(
            send_data_function=self.send_command,
            players_count=max(2, len(self.gamers)),
        )
        self.game_type = GameTypesEnum.QUIZ

        def entrypoint():
            self.check_start_game()

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_start_game(self):
        while not self.is_game_finished:
            if self.check_all_players_joined():
                time.sleep(0.8)
                with self._round_lock:
                    if self.is_game_finished or self.game_controller is None:
                        break
                    self.is_game_running = True
                    self.timer.stop(False)
                    self.prepare_gamers()
                    self.game_controller.setup_players(self.gamers)
                self.send_game_data(self._start_first_turn)
                break
            time.sleep(0.3)

    def send_game_data(self, function):
        if self.game_controller is None:
            super().send_game_data(function)
            return
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
        self.timer.start(Start_Game_Time, function, is_user_turn=False)

    def _start_first_turn(self):
        with self._round_lock:
            if self.is_game_finished or self.game_controller is None or self.game_controller.is_game_finished:
                return
            from Entities.SocketIOManagerClass import send_command

            safe_run_async(
                send_command(
                    command=make_command_json(
                        id=commands.Start_Game,
                        data={
                            "turn": 1,
                            "total_questions": self.game_controller.total_questions,
                        },
                    ),
                    game_id=self.game_id,
                )
            )
            self.start_question_turn()

    def send_current_turn(self):
        self.start_question_turn()

    def start_question_turn(self):
        with self._round_lock:
            if self.is_game_finished or self.game_controller is None or self.game_controller.is_game_finished:
                return
            from Entities.SocketIOManagerClass import send_command

            q_data = self.game_controller.get_current_question_client_data()
            turn_num = self.game_controller.current_question_index + 1
            self.game_controller.mark_question_started()

            payload = {
                "turn": turn_num,
                "total_questions": self.game_controller.total_questions,
                "question_id": q_data.get("id", turn_num),
                "category_id": q_data.get("category_id", 0),
                "category_title": q_data.get("category_title", ""),
                "question": q_data.get("question", ""),
                "options": q_data.get("options", []),
                "scores": dict(self.game_controller.scores),
                "active_players": list(self.game_controller.active_player_indexes),
                "time": Quiz_Turn_Time,
            }

            safe_run_async(
                send_command(
                    command=make_command_json(id=commands.Current_Turn, data=payload),
                    game_id=self.game_id,
                )
            )
            self.timer.start(Quiz_Turn_Time, self.on_turn_timer_expired, is_user_turn=True)

    async def command_received(self, data, socket_id):
        cmd_id = data.get("id") if isinstance(data, dict) else None
        gamer_id = await super().command_received(data, socket_id)

        if cmd_id == commands.Surrender:
            # In 3-4P Quiz, remaining active players might have all already answered this question
            with self._round_lock:
                if (
                    not self.is_game_finished
                    and self.game_controller is not None
                    and not self.game_controller.is_game_finished
                    and not self.game_controller.is_turn_round_finished
                    and self.game_controller.all_active_answered()
                ):
                    self.timer.stop(False)
                    self.reveal_turn_results()
            return

        if gamer_id is None:
            return

        if cmd_id == commands.Select_Peace:
            raw_data = data.get("data", {})
            if isinstance(raw_data, dict):
                raw_opt = raw_data.get("option", raw_data.get("target_peace", raw_data.get("index", 0)))
            else:
                raw_opt = raw_data
            try:
                option = int(raw_opt)
            except Exception:
                option = 0

            if option < 1 or option > 4:
                return

            with self._round_lock:
                if self.is_game_finished or self.game_controller is None:
                    return
                if not self.game_controller.check_authority(data, gamer_id):
                    return

                all_answered = self.game_controller.submit_answer(gamer_id, option)
                from Entities.SocketIOManagerClass import send_command

                # Broadcast that this player locked in their answer (never expose chosen option)
                safe_run_async(
                    send_command(
                        command=make_command_json(
                            id=commands.Peace_Selected,
                            data={"gamer_id": gamer_id, "has_answered": True},
                        ),
                        game_id=self.game_id,
                    )
                )

                if all_answered:
                    self.timer.stop(False)
                    self.reveal_turn_results()

    def on_turn_timer_expired(self):
        self.reveal_turn_results()

    def reveal_turn_results(self):
        with self._round_lock:
            if self.is_game_finished or self.game_controller is None or self.game_controller.is_game_finished:
                return
            if self.game_controller.is_turn_round_finished:
                return
            results = self.game_controller.resolve_turn_round()
            from Entities.SocketIOManagerClass import send_command

            safe_run_async(
                send_command(
                    command=make_command_json(id=commands.Finish_Turn_Round, data=results),
                    game_id=self.game_id,
                )
            )
            self.timer.start(Quiz_Sleep_Turn_Time, self.on_reveal_timer_expired, is_user_turn=False)

    def on_reveal_timer_expired(self):
        with self._round_lock:
            if self.is_game_finished or self.game_controller is None:
                return
            has_more = self.game_controller.advance_to_next_question()
            if has_more:
                self.start_question_turn()
            else:
                self.check_finish_game()

    def finish_reconnect_time(self, user_id):
        with self._finish_lock, self._round_lock:
            if self.is_game_finished or self.game_controller is None:
                return
            self.dc_timeout_user_id = user_id
            safe_run_async(self.send_command(commands.Finish_Reconnect_Time, {"user_id": user_id}))
            gamer_id = self.find_gamer_id_from_user_id(user_id)

            if len(self.gamers) <= 2:
                self.timer.stop(False)
                from Entities.Games.base_game_class import get_opponent_id

                opponent_id = get_opponent_id(gamer_id)
                opponent = self.find_gamer_from_gamer_id(opponent_id)
                if opponent is not None and getattr(opponent, "is_disconnected", False):
                    self.game_controller.finish_reconnect_time(gamer_id)
                    self.game_controller.leaver_id = 0
                    self.game_controller.is_game_finished = True
                    self.finish_game(0)
                    return
                self.game_controller.finish_reconnect_time(gamer_id)
                if gamer_id > 0:
                    safe_run_async(self.send_command(commands.Surrender, {"gamer_id": gamer_id}))
                self.check_finish_game()
                return

            self.game_controller.finish_reconnect_time(gamer_id)
            if gamer_id > 0:
                safe_run_async(self.send_command(commands.Surrender, {"gamer_id": gamer_id}))
            if self.check_finish_game():
                self.timer.stop(False)
                return
            if not self.game_controller.is_turn_round_finished and self.game_controller.all_active_answered():
                self.timer.stop(False)
                self.reveal_turn_results()
            else:
                self.timer.resume()

    def check_finish_game(self):
        with self._round_lock:
            if self.game_controller is None:
                return False
            if self.game_controller.is_game_finished or self.game_controller.check_game_ended():
                self.game_controller.is_game_finished = True
                winner = self.game_controller.get_game_winner()
                final_winner = self.game_controller.rank1 if self.game_controller.rank1 is not None else winner
                from Entities.SocketIOManagerClass import send_command
                from Entities.SocketIOClass.game import games
                from Entities.RewardManagerClass import GameScoreTypesEnum

                if self.game_score_type not in (GameScoreTypesEnum.RANK, GameScoreTypesEnum.CLASSIC_RANK) and self.game_id not in games:
                    safe_run_async(
                        send_command(
                            command=make_command_json(
                                id=commands.Finish_Game,
                                data={
                                    "rank1": self.game_controller.rank1,
                                    "rank2": self.game_controller.rank2,
                                    "Winner": final_winner,
                                },
                            ),
                            game_id=self.game_id,
                        )
                    )
                self.finish_game(final_winner)
                return True
            return False

    def finish_game(self, winner_gamer_id):
        if len(self.gamers) <= 2:
            # 2-player Quiz (RANK / CLASSIC_RANK / LOBBY) routes through BaseGameSession -> finish_single_game
            # so draws (winner_gamer_id == 0), wins, losses, and multi-game RANK series all score properly.
            BaseGameSession.finish_game(self, winner_gamer_id)
        else:
            super().finish_game(winner_gamer_id)

    def send_reconnect_data(self, socket_id):
        if not self.is_game_running or self.game_controller is None:
            return
        with self._round_lock:
            gamer_data = self.find_gamer_from_socket(socket_id)
            viewer_gid = gamer_data.gamer_id if gamer_data is not None else 0
            g_data = self.game_controller.get_game_data(viewer_gamer_id=viewer_gid)
            rem_time = max(0, self.timer.max_time - self.timer.counter)
            reconnect_data = {
                "gamers": [g.to_json() for g in self.gamers],
                "game_data": g_data,
                "game_type": GameTypesEnum.QUIZ.value,
                "timer_data": (
                    {"is_user_turn": True, "time": self.timer.counter + 1}
                    if self.timer.is_user_turn
                    else {"is_user_turn": False, "time": 0}
                ),
                "time": rem_time,
                "is_turn_round_finished": self.game_controller.is_turn_round_finished,
            }
        from Entities.SocketIOManagerClass import send_private_command

        safe_run_async(
            send_private_command(
                command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                socket_id=socket_id,
                game_id=self.game_id,
            )
        )
