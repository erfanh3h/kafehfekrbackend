import asyncio
import threading
import time
from typing import Optional

from Commons import commands
from Commons.static_functions import make_command_json, safe_run_async
from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession
from Entities.Games.Quiz import QuizGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Quiz_Turn_Time, Quiz_Sleep_Turn_Time
from Entities.RewardManagerClass import GameScoreTypesEnum


class QuizGameSession(BaseMultiplayerGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)
        self.game_controller: Optional[QuizGameClass] = None

    def start_game_timer(self):
        self.game_controller = QuizGameClass(
            send_data_function=self.send_command,
            players_count=len(self.gamers)
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
                self.is_game_running = True
                self.timer.stop(False)
                self.prepare_gamers()
                self.game_controller.setup_players(self.gamers)
                time.sleep(0.5)
                self.start_question_turn()
                break
            time.sleep(0.3)

    def start_question_turn(self):
        if self.is_game_finished or self.game_controller.is_game_finished:
            return
        from Entities.SocketIOManagerClass import send_command
        q_data = self.game_controller.get_current_question_client_data()
        turn_num = self.game_controller.current_question_index + 1

        payload = {
            "turn": turn_num,
            "total_questions": self.game_controller.total_questions,
            "question_id": q_data.get("id", turn_num),
            "question": q_data.get("question", ""),
            "options": q_data.get("options", []),
            "scores": self.game_controller.scores,
            "time": Quiz_Turn_Time,
        }

        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Current_Turn, data=payload),
                game_id=self.game_id
            )
        )
        self.timer.start(Quiz_Turn_Time, self.on_turn_timer_expired, is_user_turn=True)

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return

        cmd_id = data.get("id")
        if cmd_id == commands.Select_Peace:
            if not self.game_controller.check_authority(data, gamer_id):
                return
            raw_data = data.get("data", {})
            if isinstance(raw_data, dict):
                option = int(raw_data.get("option", raw_data.get("target_peace", raw_data.get("index", 0))))
            else:
                try:
                    option = int(raw_data)
                except Exception:
                    option = 0

            if option < 1 or option > 4:
                return

            all_answered = self.game_controller.submit_answer(gamer_id, option)
            from Entities.SocketIOManagerClass import send_command
            # Broadcast that this player locked in their answer (hidden option)
            safe_run_async(
                send_command(
                    command=make_command_json(
                        id=commands.Peace_Selected,
                        data={"gamer_id": gamer_id, "has_answered": True}
                    ),
                    game_id=self.game_id
                )
            )

            if all_answered:
                # All players answered before timer expired - transition early!
                self.timer.stop(False)
                self.reveal_turn_results()

    def on_turn_timer_expired(self):
        self.reveal_turn_results()

    def reveal_turn_results(self):
        if self.is_game_finished:
            return
        results = self.game_controller.resolve_turn_round()
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Finish_Turn_Round, data=results),
                game_id=self.game_id
            )
        )
        self.timer.start(Quiz_Sleep_Turn_Time, self.on_reveal_timer_expired, is_user_turn=False)

    def on_reveal_timer_expired(self):
        if self.is_game_finished:
            return
        has_more = self.game_controller.advance_to_next_question()
        if has_more:
            self.start_question_turn()
        else:
            self.check_finish_game()

    def send_reconnect_data(self, socket_id):
        if self.game_controller is None:
            return
        from Entities.SocketIOManagerClass import send_private_command
        data = self.game_controller.get_game_data()
        rem_time = max(0, self.timer.max_time - self.timer.counter)
        data["time"] = rem_time
        safe_run_async(
            send_private_command(
                command=make_command_json(id=commands.Reconnect_Data, data=data),
                socket_id=socket_id,
                game_id=self.game_id
            )
        )
