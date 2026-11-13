import json
import os
import random
import time
from typing import Dict, List, Optional
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass

# In-memory global questions cache
_QUESTIONS_CACHE: Dict = {}
_QUESTIONS_BY_ID: Dict[int, Dict] = {}


def load_questions_cache() -> Dict:
    global _QUESTIONS_CACHE, _QUESTIONS_BY_ID
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
                _QUESTIONS_BY_ID = {
                    int(q["id"]): q
                    for q in _QUESTIONS_CACHE.get("all_questions", [])
                    if isinstance(q, dict) and "id" in q
                }
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
    _QUESTIONS_BY_ID = {int(q["id"]): q for q in _QUESTIONS_CACHE["all_questions"]}
    return _QUESTIONS_CACHE


def get_question_by_id(question_id: int) -> Optional[Dict]:
    load_questions_cache()
    return _QUESTIONS_BY_ID.get(int(question_id))


class QuizGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count: int = 2):
        super().__init__(send_data_function, players_count)
        self.total_questions = 10
        self.current_question_index = 0
        self.players_count = max(2, int(players_count))
        self.active_player_indexes = list(range(1, self.players_count + 1))
        self.surrendered_players: List[int] = []
        self.scores: Dict[int, int] = {i: 0 for i in self.active_player_indexes}
        self.correct_counts: Dict[int, int] = {i: 0 for i in self.active_player_indexes}
        self.total_answer_time: Dict[int, float] = {i: 0.0 for i in self.active_player_indexes}
        self.turn_answers: Dict[int, int] = {}
        self.turn_answer_times: Dict[int, float] = {}
        self.question_start_time: float = time.time()
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
            self.active_player_indexes = list(range(1, max(2, len(gamers)) + 1))
        self.players_count = len(self.active_player_indexes)
        self.surrendered_players = []
        self.scores = {gid: 0 for gid in self.active_player_indexes}
        self.correct_counts = {gid: 0 for gid in self.active_player_indexes}
        self.total_answer_time = {gid: 0.0 for gid in self.active_player_indexes}

    def mark_question_started(self):
        self.question_start_time = time.time()

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
                "scores": dict(self.scores),
            }
        return {}

    def get_current_question_full(self) -> Optional[Dict]:
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    def check_authority(self, data, gamer_id: int) -> bool:
        if self.is_game_finished or self.is_turn_round_finished:
            return False
        if gamer_id not in self.active_player_indexes:
            return False
        # Cannot answer twice in the same question turn
        if gamer_id in self.turn_answers:
            return False
        return True

    def all_active_answered(self) -> bool:
        if not self.active_player_indexes:
            return False
        return all(gid in self.turn_answers for gid in self.active_player_indexes)

    def submit_answer(self, gamer_id: int, option: int) -> bool:
        if self.is_game_finished or self.is_turn_round_finished:
            return False
        if gamer_id not in self.active_player_indexes or gamer_id in self.turn_answers:
            return False
        if option < 1 or option > 4:
            return False
        self.turn_answers[gamer_id] = option
        self.turn_answer_times[gamer_id] = max(0.0, time.time() - self.question_start_time)
        return self.all_active_answered()

    def resolve_turn_round(self) -> Dict:
        if self.is_turn_round_finished and self.last_turn_results:
            return self.last_turn_results

        q = self.get_current_question_full()
        correct_option = int(q["correct"]) if q else 1

        player_answers = {}
        for gid in list(self.active_player_indexes):
            if gid in self.turn_answers:
                chosen_opt = int(self.turn_answers[gid])
                if chosen_opt == correct_option:
                    delta = 1
                    is_correct = True
                    self.correct_counts[gid] = self.correct_counts.get(gid, 0) + 1
                    self.total_answer_time[gid] = self.total_answer_time.get(gid, 0.0) + self.turn_answer_times.get(gid, 15.0)
                else:
                    delta = -1
                    is_correct = False
            else:
                chosen_opt = 0
                delta = 0
                is_correct = False

            self.scores[gid] = self.scores.get(gid, 0) + delta
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
            "scores": dict(self.scores),
        }
        self.is_turn_round_finished = True
        return self.last_turn_results

    def _compute_final_rankings(self):
        active = list(self.active_player_indexes)
        if not active:
            self.rank1 = 0
            self.rank2 = 0
            return

        if len(active) == 1:
            self.rank1 = active[0]
            self.rank2 = self.surrendered_players[-1] if self.surrendered_players else active[0]
            return

        # Strict 2-player mode (ClassicRank / 2P Lobby / 2P Rank): equal scores -> Draw (winner = 0)
        if self.players_count == 2 and len(active) == 2:
            g1, g2 = active[0], active[1]
            s1, s2 = self.scores.get(g1, 0), self.scores.get(g2, 0)
            if s1 == s2:
                self.rank1 = None
                self.rank2 = None
            elif s1 > s2:
                self.rank1 = g1
                self.rank2 = g2
            else:
                self.rank1 = g2
                self.rank2 = g1
            return

        # 3-4 player mode: sort by (score DESC, correct_counts DESC, total_answer_time ASC)
        # If all active players have identical stats AND zero correct answers (all AFK / 0-0-0-0), return Draw (0)
        stats_tuples = {
            (self.scores.get(gid, 0), self.correct_counts.get(gid, 0), round(self.total_answer_time.get(gid, 0.0), 3))
            for gid in active
        }
        if len(stats_tuples) == 1 and all(self.correct_counts.get(gid, 0) == 0 and self.scores.get(gid, 0) == 0 for gid in active):
            self.rank1 = 0
            self.rank2 = 0
            return

        sorted_players = sorted(
            active,
            key=lambda gid: (
                -self.scores.get(gid, 0),
                -self.correct_counts.get(gid, 0),
                self.total_answer_time.get(gid, 0.0),
                gid,
            )
        )
        self.rank1 = sorted_players[0]
        self.rank2 = sorted_players[1] if len(sorted_players) > 1 else sorted_players[0]

    def advance_to_next_question(self) -> bool:
        self.current_question_index += 1
        self.turn_answers.clear()
        self.turn_answer_times.clear()
        self.is_turn_round_finished = False

        if self.current_question_index >= self.total_questions or self.current_question_index >= len(self.questions):
            self.is_game_finished = True
            self._compute_final_rankings()
            return False
        return True

    def _apply_surrender_sync(self, gamer_id):
        if gamer_id not in self.active_player_indexes:
            return False
        if gamer_id not in self.surrendered_players:
            self.surrendered_players.append(gamer_id)
        if len(self.active_player_indexes) == 2:
            if self.rank2 is None:
                self.rank2 = gamer_id
        self.active_player_indexes.remove(gamer_id)
        if len(self.active_player_indexes) == 1:
            last_survivor = self.active_player_indexes[0]
            if self.rank1 is None:
                self.rank1 = last_survivor
                if self.rank2 is None:
                    self.rank2 = gamer_id
            elif self.rank2 is None:
                self.rank2 = last_survivor
            self.is_game_finished = True
            return True
        # Quiz is simultaneous: remaining players keep answering current question without stopping turn timer
        return False

    def get_game_winner(self) -> int:
        if len(self.active_player_indexes) == 1:
            return self.active_player_indexes[0]
        if self.is_game_finished and self.players_count == 2 and len(self.active_player_indexes) == 2:
            g1, g2 = self.active_player_indexes[0], self.active_player_indexes[1]
            s1, s2 = self.scores.get(g1, 0), self.scores.get(g2, 0)
            if s1 > s2:
                return g1
            elif s2 > s1:
                return g2
            return 0  # Draw
        if self.rank1 is not None:
            return self.rank1
        if len(self.active_player_indexes) == 2:
            g1, g2 = self.active_player_indexes[0], self.active_player_indexes[1]
            s1, s2 = self.scores.get(g1, 0), self.scores.get(g2, 0)
            if s1 > s2:
                return g1
            elif s2 > s1:
                return g2
            return 0
        sorted_players = sorted(
            self.active_player_indexes,
            key=lambda gid: (
                -self.scores.get(gid, 0),
                -self.correct_counts.get(gid, 0),
                self.total_answer_time.get(gid, 0.0),
                gid,
            )
        )
        return sorted_players[0] if sorted_players else 0

    def get_game_data(self, viewer_gamer_id: Optional[int] = None) -> Dict:
        q_data = self.get_current_question_client_data()
        data = {
            "game_type": "Quiz",
            "current_turn": self.current_question_index + 1,
            "total_questions": self.total_questions,
            "scores": dict(self.scores),
            "current_question": q_data,
            "answers_count": len(self.turn_answers),
            "answered_players": [int(gid) for gid in self.turn_answers.keys()],
            "surrendered_players": [int(gid) for gid in self.surrendered_players],
            "players_count": self.players_count,
            "active_players": list(self.active_player_indexes),
            "is_turn_round_finished": self.is_turn_round_finished,
            "last_turn_results": self.last_turn_results,
        }
        if viewer_gamer_id is not None and viewer_gamer_id > 0:
            data["my_option"] = int(self.turn_answers.get(viewer_gamer_id, 0))
        return data
