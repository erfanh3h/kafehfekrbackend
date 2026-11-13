import random
from typing import Any, List, Optional
from .base_game import BaseGameLogic


class QuizGameLogic(BaseGameLogic):
    # Knowledge accuracy calibrated by bot level: Level 1 ~45%, Level 2 ~65%, Level 3 ~82%
    ACCURACY_BY_LEVEL = {
        1: 0.45,
        2: 0.65,
        3: 0.82,
    }

    def __init__(self, level: int = 1):
        super().__init__(
            game_type="Quiz",
            game_type_aliases=["quiz", "کوییز", "مسابقه", "اطلاعات عمومی"],
            level=level,
        )
        self.current_turn: int = 1
        self.total_questions: int = 10
        self.current_question_id: int = 0
        self.current_question_text: str = ""
        self.has_answered_current_turn: bool = False
        self.is_turn_round_finished: bool = False

    def reset(self):
        self.current_turn = 1
        self.current_question_id = 0
        self.current_question_text = ""
        self.has_answered_current_turn = False
        self.is_turn_round_finished = False

    def _apply_question_payload(self, q_dict: dict):
        self.current_turn = int(q_dict.get("turn", q_dict.get("current_turn", self.current_turn)))
        self.total_questions = int(q_dict.get("total_questions", self.total_questions or 10))
        self.current_question_id = int(q_dict.get("question_id", q_dict.get("id", 0)) or 0)
        self.current_question_text = str(q_dict.get("question", "") or "")

    def handle_server_command(self, cmd_id: str, payload: Any) -> bool:
        if cmd_id == "CurrentTurn":
            if isinstance(payload, dict):
                self._apply_question_payload(payload)
            self.is_turn_round_finished = False
            self.has_answered_current_turn = False
            return True
        elif cmd_id == "FinishTurnRound":
            self.has_answered_current_turn = True
            self.is_turn_round_finished = True
            return True
        elif cmd_id == "ReconnectData" and isinstance(payload, dict):
            gd = payload.get("game_data") if isinstance(payload.get("game_data"), dict) else payload
            if isinstance(gd, dict):
                cur_q = gd.get("current_question")
                if isinstance(cur_q, dict) and cur_q:
                    self._apply_question_payload(cur_q)
                elif "turn" in gd or "question" in gd:
                    self._apply_question_payload(gd)
                self.is_turn_round_finished = bool(
                    gd.get("is_turn_round_finished", payload.get("is_turn_round_finished", False))
                )
                answered_list = gd.get("answered_players", [])
                my_gid = self.my_player_num or 0
                already_answered = (
                    (isinstance(answered_list, list) and my_gid in [int(x) for x in answered_list if str(x).isdigit()])
                    or int(gd.get("my_option", 0) or 0) > 0
                )
                self.has_answered_current_turn = self.is_turn_round_finished or already_answered
            return True
        return False

    def should_act_on_reconnect(self) -> bool:
        return (
            not self.is_turn_round_finished
            and not self.has_answered_current_turn
            and (self.current_question_id > 0 or bool(self.current_question_text))
        )

    def get_legal_moves(self) -> List[int]:
        if self.has_answered_current_turn or self.is_turn_round_finished:
            return []
        return [1, 2, 3, 4]

    def _lookup_correct_option(self) -> Optional[int]:
        try:
            from Entities.Games.Quiz import get_question_by_id, load_questions_cache

            if self.current_question_id > 0:
                q_obj = get_question_by_id(self.current_question_id)
                if q_obj and 1 <= int(q_obj.get("correct", 0)) <= 4:
                    return int(q_obj["correct"])

            if self.current_question_text:
                cache = load_questions_cache()
                target = self.current_question_text.strip()
                for q_obj in cache.get("all_questions", []):
                    if isinstance(q_obj, dict) and str(q_obj.get("question", "")).strip() == target:
                        corr = int(q_obj.get("correct", 0))
                        if 1 <= corr <= 4:
                            return corr
        except Exception:
            pass
        return None

    def compute_next_move(self) -> Optional[int]:
        if self.has_answered_current_turn or self.is_turn_round_finished:
            return None
        self.has_answered_current_turn = True

        correct_opt = self._lookup_correct_option()
        if correct_opt is not None:
            accuracy = self.ACCURACY_BY_LEVEL.get(int(self.level or 2), 0.65)
            if random.random() < accuracy:
                return correct_opt
            wrong_options = [opt for opt in (1, 2, 3, 4) if opt != correct_opt]
            return random.choice(wrong_options)

        return random.choice([1, 2, 3, 4])

    def build_move_command(self, move: Any) -> dict:
        return {"id": "SelectPeace", "data": {"option": move}}
