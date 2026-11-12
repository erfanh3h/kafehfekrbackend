import json
import os
import random
import time
from typing import Dict, List, Optional
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass

# In-memory global questions cache
_QUESTIONS_CACHE: Dict = {}


def load_questions_cache() -> Dict:
    global _QUESTIONS_CACHE
    if _QUESTIONS_CACHE:
        return _QUESTIONS_CACHE
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "questions.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "questions_by_category" in data:
                    _QUESTIONS_CACHE = data
                elif isinstance(data, list):
                    # legacy list format
                    by_cat = {}
                    for q in data:
                        cid = str(q.get("category_id", 0))
                        by_cat.setdefault(cid, []).append(q)
                    _QUESTIONS_CACHE = {
                        "categories": {},
                        "questions_by_category": by_cat,
                        "all_questions": data
                    }
                else:
                    _QUESTIONS_CACHE = data
                cats_count = len(_QUESTIONS_CACHE.get("questions_by_category", {}))
                total_q = len(_QUESTIONS_CACHE.get("all_questions", []))
                print(f"[QuizGameClass] Loaded questions cache: {total_q} questions across {cats_count} categories.")
                return _QUESTIONS_CACHE
        except Exception as e:
            print(f"[QuizGameClass] Error loading questions.json: {e}")
    # Fallback
    _QUESTIONS_CACHE = {
        "categories": {"1": "اطلاعات عمومی 📚"},
        "questions_by_category": {
            "1": [
                {"id": 1, "category_id": 1, "category_title": "اطلاعات عمومی 📚", "question": "پایتخت ایران کدام شهر است؟", "options": ["شیراز", "تهران", "اصفهان", "مشهد"], "correct": 2},
                {"id": 2, "category_id": 1, "category_title": "اطلاعات عمومی 📚", "question": "خلیج فارس در کدام سمت ایران قرار دارد؟", "options": ["شمال", "شرق", "جنوب", "غرب"], "correct": 3},
            ]
        },
        "all_questions": [
            {"id": 1, "category_id": 1, "category_title": "اطلاعات عمومی 📚", "question": "پایتخت ایران کدام شهر است؟", "options": ["شیراز", "تهران", "اصفهان", "مشهد"], "correct": 2},
            {"id": 2, "category_id": 1, "category_title": "اطلاعات عمومی 📚", "question": "خلیج فارس در کدام سمت ایران قرار دارد؟", "options": ["شمال", "شرق", "جنوب", "غرب"], "correct": 3},
        ]
    }
    return _QUESTIONS_CACHE


class QuizGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count: int = 2):
        super().__init__(send_data_function, players_count)
        self.total_questions = 10
        self.current_question_index = 0
        self.players_count = players_count
        self.active_player_indexes = list(range(1, players_count + 1))
        self.scores: Dict[int, int] = {i: 0 for i in self.active_player_indexes}
        self.turn_answers: Dict[int, int] = {}
        self.turn_answer_times: Dict[int, float] = {}
        self.last_turn_results: Dict = {}
        self.is_turn_round_finished: bool = False
        self.is_game_finished: bool = False
        self.rank1: Optional[int] = None
        self.rank2: Optional[int] = None

        cache = load_questions_cache()
        by_cat = cache.get("questions_by_category", {})
        valid_cats = [cid for cid, q_list in by_cat.items() if len(q_list) > 0]

        self.questions = []
        if len(valid_cats) >= self.total_questions:
            # Pick 10 distinct categories with ZERO repetition
            selected_cats = random.sample(valid_cats, self.total_questions)
            for cid in selected_cats:
                q = random.choice(by_cat[cid])
                self.questions.append(q)
            # Shuffle question sequence so category order is randomized
            random.shuffle(self.questions)
        else:
            # Fallback if fewer than 10 categories available
            for cid in valid_cats:
                q = random.choice(by_cat[cid])
                self.questions.append(q)
            all_q = cache.get("all_questions", [])
            chosen_ids = {q.get("id") for q in self.questions if "id" in q}
            remaining = [q for q in all_q if q.get("id") not in chosen_ids]
            needed = self.total_questions - len(self.questions)
            if needed > 0 and remaining:
                self.questions.extend(random.sample(remaining, min(needed, len(remaining))))
            random.shuffle(self.questions)

    def setup_players(self, gamers):
        self.active_player_indexes = [g.gamer_id for g in gamers if getattr(g, "gamer_id", 0) > 0]
        if not self.active_player_indexes:
            self.active_player_indexes = list(range(1, len(gamers) + 1))
        self.players_count = len(self.active_player_indexes)
        self.scores = {gid: 0 for gid in self.active_player_indexes}

    def get_current_question_client_data(self) -> Dict:
        if 0 <= self.current_question_index < len(self.questions):
            q = self.questions[self.current_question_index]
            return {
                "id": q.get("id", self.current_question_index + 1),
                "category_id": q.get("category_id", 0),
                "category_title": q.get("category_title", "اطلاعات عمومی"),
                "question": q["question"],
                "options": q["options"],
                "turn": self.current_question_index + 1,
                "total_questions": self.total_questions,
                "scores": self.scores,
            }
        return {}

    def get_current_question_full(self) -> Optional[Dict]:
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    def check_authority(self, data, gamer_id: int) -> bool:
        if self.is_game_finished:
            return False
        if gamer_id not in self.active_player_indexes:
            return False
        # Cannot answer twice in the same question turn
        if gamer_id in self.turn_answers:
            return False
        return True

    def submit_answer(self, gamer_id: int, option: int) -> bool:
        if option < 1 or option > 4:
            return False
        self.turn_answers[gamer_id] = option
        self.turn_answer_times[gamer_id] = time.time()
        # Returns True if all active players have submitted their answers
        all_answered = all(gid in self.turn_answers for gid in self.active_player_indexes)
        return all_answered

    def resolve_turn_round(self) -> Dict:
        q = self.get_current_question_full()
        correct_option = q["correct"] if q else 1

        player_answers = {}
        for gid in self.active_player_indexes:
            if gid in self.turn_answers:
                chosen_opt = self.turn_answers[gid]
                if chosen_opt == correct_option:
                    delta = 1
                    is_correct = True
                else:
                    delta = -1
                    is_correct = False
            else:
                chosen_opt = 0
                delta = 0
                is_correct = False

            self.scores[gid] += delta
            player_answers[str(gid)] = {
                "gamer_id": gid,
                "option": chosen_opt,
                "score_delta": delta,
                "total_score": self.scores[gid],
                "is_correct": is_correct,
            }

        self.last_turn_results = {
            "turn": self.current_question_index + 1,
            "total_questions": self.total_questions,
            "category_title": q.get("category_title", "") if q else "",
            "correct_option": correct_option,
            "player_answers": player_answers,
            "scores": self.scores,
        }
        self.is_turn_round_finished = True
        return self.last_turn_results

    def advance_to_next_question(self) -> bool:
        self.current_question_index += 1
        self.turn_answers.clear()
        self.turn_answer_times.clear()
        self.is_turn_round_finished = False

        if self.current_question_index >= self.total_questions:
            self.is_game_finished = True
            # Rank players by score descending
            sorted_players = sorted(
                self.active_player_indexes,
                key=lambda gid: self.scores.get(gid, 0),
                reverse=True
            )
            if sorted_players:
                self.rank1 = sorted_players[0]
                if len(sorted_players) > 1:
                    self.rank2 = sorted_players[1]
                else:
                    self.rank2 = sorted_players[0]
            return False
        return True

    def get_game_winner(self) -> int:
        if self.players_count == 2 and len(self.active_player_indexes) >= 2:
            s1 = self.scores.get(1, 0)
            s2 = self.scores.get(2, 0)
            if s1 > s2:
                return 1
            elif s2 > s1:
                return 2
            else:
                return 0  # Draw
        if self.rank1 is not None:
            return self.rank1
        sorted_players = sorted(
            self.active_player_indexes,
            key=lambda gid: self.scores.get(gid, 0),
            reverse=True
        )
        return sorted_players[0] if sorted_players else 0

    def get_game_data(self) -> Dict:
        q_data = self.get_current_question_client_data()
        return {
            "game_type": "Quiz",
            "current_turn": self.current_question_index + 1,
            "total_questions": self.total_questions,
            "scores": self.scores,
            "current_question": q_data,
            "answers_count": len(self.turn_answers),
            "players_count": self.players_count,
            "active_players": self.active_player_indexes,
            "is_turn_round_finished": self.is_turn_round_finished,
            "last_turn_results": self.last_turn_results,
        }
