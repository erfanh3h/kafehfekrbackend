import asyncio
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Stub socketio/pymongo if needed in lightweight environments
if "socketio" not in sys.modules:
    sys.modules["socketio"] = types.SimpleNamespace(
        AsyncNamespace=type("AsyncNamespace", (), {}),
        AsyncServer=MagicMock,
        AsyncClient=MagicMock,
    )

from Entities.RewardManagerClass import RewardManagerClass, GameScoreTypesEnum
from Entities.RewardManagerClass.reward_data import (
    CLASSIC_RANK_DEFAULT_AI_LEVEL,
    CLASSIC_RANK_REWARDS_TABLE,
    calculate_classic_rank_rewards,
    normalize_ai_level,
)
from Entities.Database.game_play_history_collection import create_game_play_history_json
from Entities.Database.user_history_collection import UserHistoryCollectionManager


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = {str(d["_id"]): dict(d) for d in (docs or [])}
        self.last_update = None

    def find_one(self, query):
        return self.docs.get(str(query.get("_id")))

    def insert_one(self, doc):
        self.docs[str(doc["_id"])] = dict(doc)

    def delete_one(self, query):
        self.docs.pop(str(query.get("_id")), None)

    def find_one_and_update(self, query, update_doc, upsert=False):
        self.last_update = (query, update_doc, upsert)
        uid = str(query.get("_id"))
        doc = self.docs.get(uid)
        if doc is None:
            if not upsert:
                return None
            doc = {"_id": uid}
            for k, v in update_doc.get("$setOnInsert", {}).items():
                doc[k] = v
            self.docs[uid] = doc
        for k, v in update_doc.get("$set", {}).items():
            doc[k] = v
        for k, v in update_doc.get("$inc", {}).items():
            doc[k] = doc.get(k, 0) + v
        return doc


class TestClassicRankAILevels(unittest.TestCase):
    def test_normalize_ai_level_defaults_to_2(self):
        self.assertEqual(CLASSIC_RANK_DEFAULT_AI_LEVEL, 2)
        self.assertEqual(normalize_ai_level(None), 2)
        self.assertEqual(normalize_ai_level(0), 2)
        self.assertEqual(normalize_ai_level(99), 2)
        self.assertEqual(normalize_ai_level(True), 2)
        self.assertEqual(normalize_ai_level("invalid"), 2)
        self.assertEqual(normalize_ai_level(1), 1)
        self.assertEqual(normalize_ai_level("easy"), 1)
        self.assertEqual(normalize_ai_level(2), 2)
        self.assertEqual(normalize_ai_level("medium"), 2)
        self.assertEqual(normalize_ai_level(3), 3)
        self.assertEqual(normalize_ai_level("hard"), 3)

    def test_rewards_scale_strictly_with_ai_level_and_game_difficulty(self):
        for g_type in ("TicTacToe", "FourInRow", "Chess", "Risk"):
            w1, c1 = calculate_classic_rank_rewards(g_type, ai_level=1, outcome="win")
            w2, c2 = calculate_classic_rank_rewards(g_type, ai_level=2, outcome="win")
            w3, c3 = calculate_classic_rank_rewards(g_type, ai_level=3, outcome="win")
            self.assertLess(w1, w2)
            self.assertLess(w2, w3)
            self.assertLess(c1, c2)
            self.assertLess(c2, c3)

            d1, dc1 = calculate_classic_rank_rewards(g_type, ai_level=1, outcome="draw")
            d2, dc2 = calculate_classic_rank_rewards(g_type, ai_level=2, outcome="draw")
            d3, dc3 = calculate_classic_rank_rewards(g_type, ai_level=3, outcome="draw")
            self.assertLess(d1, d2)
            self.assertLess(d2, d3)
            self.assertLessEqual(dc1, dc2)
            self.assertLess(dc2, dc3)

            self.assertEqual(calculate_classic_rank_rewards(g_type, ai_level=3, outcome="win", is_afk_or_dc=True), (0, 0))

    def test_reward_manager_awards_xp_coins_and_level_history(self):
        users_col = _FakeCollection([
            {"_id": "u_human", "username": "Ali", "score": 500, "xp": 100, "coin": 50},
        ])
        history_col = _FakeCollection()
        fake_users_mgr = MagicMock()
        fake_users_mgr.read_user.side_effect = lambda uid: users_col.find_one({"_id": uid})
        fake_users_mgr.update_user.side_effect = lambda uid, **kw: users_col.find_one_and_update({"_id": uid}, {"$set": kw})
        fake_hist_mgr = UserHistoryCollectionManager(history_col)
        fake_db = types.SimpleNamespace(users_manager=fake_users_mgr, user_history_manager=fake_hist_mgr)

        with patch.dict("sys.modules", {"Entities.Database": types.SimpleNamespace(game_database=fake_db)}):
            for ai_lvl in (1, 2, 3):
                before_xp = users_col.find_one({"_id": "u_human"})["xp"]
                before_coin = users_col.find_one({"_id": "u_human"})["coin"]

                rm = RewardManagerClass(GameScoreTypesEnum.CLASSIC_RANK, ai_level=ai_lvl)
                rm.set_user_data(["u_human", "bot_abc"])
                rm.finish_game(1, ["Chess"], [1])

                expected_xp, expected_coin = calculate_classic_rank_rewards("Chess", ai_level=ai_lvl, outcome="win")
                self.assertEqual(rm.last_awarded_xp["u_human"], expected_xp)
                self.assertEqual(rm.last_awarded_coin["u_human"], expected_coin)
                self.assertEqual(rm.last_awarded_score["u_human"], 0)

                after = users_col.find_one({"_id": "u_human"})
                self.assertEqual(after["xp"] - before_xp, expected_xp)
                self.assertEqual(after["coin"] - before_coin, expected_coin)
                self.assertEqual(after["score"], 500)

                hdoc = history_col.find_one({"_id": "u_human"})
                self.assertEqual(hdoc[f"win_classic_rank_lvl{ai_lvl}"], 1)

    def test_reward_manager_multiplayer_classic_rank_uses_ai_level(self):
        users_col = _FakeCollection([
            {"_id": "u_human", "username": "Sara", "score": 300, "xp": 20, "coin": 10},
        ])
        history_col = _FakeCollection()
        fake_users_mgr = MagicMock()
        fake_users_mgr.read_user.side_effect = lambda uid: users_col.find_one({"_id": uid})
        fake_users_mgr.update_user.side_effect = lambda uid, **kw: users_col.find_one_and_update({"_id": uid}, {"$set": kw})
        fake_hist_mgr = UserHistoryCollectionManager(history_col)
        fake_db = types.SimpleNamespace(users_manager=fake_users_mgr, user_history_manager=fake_hist_mgr)

        with patch.dict("sys.modules", {"Entities.Database": types.SimpleNamespace(game_database=fake_db)}):
            rm = RewardManagerClass(GameScoreTypesEnum.CLASSIC_RANK, ai_level=3)
            rm.set_user_data(["u_human", "bot_ludo"])
            # Human loses to Hard Ludo bot -> should receive Level 3 lose reward, not rank2 win reward
            rm.finish_multiplayer_game("bot_ludo", "u_human", ["Ludo"], game_id="g_ludo")
            exp_xp, exp_coin = calculate_classic_rank_rewards("Ludo", ai_level=3, outcome="lose")
            self.assertEqual(rm.last_awarded_xp["u_human"], exp_xp)
            self.assertEqual(rm.last_awarded_coin["u_human"], exp_coin)

    def test_game_play_history_records_ai_level(self):
        doc = create_game_play_history_json("g1", ["u1", "bot_1"], ["Chess"], "ClassicRank", ai_level=3)
        self.assertEqual(doc["ai_level"], 3)

    def test_classic_rank_session_passes_selected_ai_level(self):
        from Controllers.QueueSession.classic_rank import ClassicRankSession
        from Models.Queuer import QueuerModel

        session = ClassicRankSession()
        human = QueuerModel("u1", "Erfan", 1, 100, 500, socket_id="sid_1")

        captured = {}

        class _FakeBot:
            def __init__(self, **kwargs):
                captured["bot_kwargs"] = kwargs

            async def start(self):
                return None

        def _fake_add_new_game(game_id, queuers, game_types, score_type, ai_level=None):
            captured["add_new_game"] = {
                "game_id": game_id,
                "score_type": score_type,
                "ai_level": ai_level,
            }

        fake_sio_server = MagicMock()
        fake_sio_server.emit = AsyncMock()
        fake_game_mod = types.SimpleNamespace(add_new_game=_fake_add_new_game)
        fake_sio_pkg = types.SimpleNamespace(Socket_Server=fake_sio_server)

        async def _run():
            with patch("Controllers.QueueSession.classic_rank.ClassicRankBot", _FakeBot), \
                 patch.dict("sys.modules", {
                     "Entities.SocketIOClass.game": fake_game_mod,
                     "Entities.SocketIOClass": fake_sio_pkg,
                 }):
                await session.start_classic_rank_match(human, "Chess", "sid_1", ai_level=3)
                await asyncio.sleep(0.08)

        asyncio.run(_run())
        self.assertEqual(captured["bot_kwargs"]["level"], 3)
        self.assertEqual(captured["add_new_game"]["ai_level"], 3)
        emitted_cmd = fake_sio_server.emit.call_args.args[1]
        self.assertEqual(emitted_cmd["data"]["ai_level"], 3)

    def test_all_25_games_accept_all_3_levels_and_differentiate_monopoly_sudoku_msweeper(self):
        from Bots.games import get_game_logic, list_supported_games
        from Bots.games.monopoly import MonopolyGameLogic
        from Bots.games.sudoku import SudokuGameLogic
        from Bots.games.msweeper import MSweeperGameLogic

        supported = list_supported_games()
        self.assertEqual(len(supported), 25)
        for game_name in supported:
            for lvl in (1, 2, 3):
                logic = get_game_logic(game_name, level=lvl)
                self.assertEqual(logic.level, lvl)

        # Monopoly: Level 2 accepts even-value trade; Level 3 rejects trade that lacks margin / helps opponent
        for lvl, expected_action in ((1, "accept"), (2, "accept"), (3, "reject")):
            m = MonopolyGameLogic(level=lvl)
            m.is_game_active = True
            m.my_player_num = 2
            m.phase = "trade"
            m.players = [
                {"gamer_id": 1, "cash": 500, "alive": True},
                {"gamer_id": 2, "cash": 500, "alive": True},
            ]
            m.pending_trade = {
                "to_player": 2,
                "offer_cash": 60,
                "request_cash": 60,
                "offer_tiles": [],
                "request_tiles": [],
            }
            move = m.compute_next_move()
            self.assertEqual(move["action"], expected_action)

        # Sudoku: Level 3 prioritizes naked single (cell with 1 local candidate)
        s = SudokuGameLogic(level=3)
        s.is_board_initialized = True
        # Fill row 0 cols 1..8 with 2..9 so cell 0 has only candidate 1
        for c in range(1, 9):
            s.board_values[c] = c + 1
            s.is_base_number[c] = True
        move = s.compute_next_move()
        self.assertEqual(move, (0, 1))

        # MSweeper: Level 3 deterministically flags obvious 1-cell mine clue
        ms = MSweeperGameLogic(level=3)
        ms.selected[0] = True
        ms.values[0] = 3  # corner cell (0,0) has 3 neighbors: 1, 8, 9 -> all 3 must be mines
        cmd, target = ms.compute_next_move()
        self.assertEqual(cmd, "SelectMine")
        self.assertIn(target, (1, 8, 9))

    def test_chess_level_3_avoids_hanging_queen_and_finds_checkmate(self):
        from Bots.games.chess import ChessGameLogic

        # 1. Level 3 detects immediate checkmate (White K@(0,7), Black K@(2,5), Black Q@(2,6) -> Q to (1,6)#)
        c = ChessGameLogic(level=3)
        c.board = [{"gamer_id": 0, "name": "", "is_first_move": False} for _ in range(64)]
        c.board[0 * 8 + 7] = {"gamer_id": 1, "name": "King", "is_first_move": False}
        c.king1_pos = (0, 7)
        c.board[2 * 8 + 5] = {"gamer_id": 2, "name": "King", "is_first_move": False}
        c.king2_pos = (2, 5)
        c.board[2 * 8 + 6] = {"gamer_id": 2, "name": "Queen", "is_first_move": False}
        c.my_player_num = 2
        mv = c.compute_next_move()
        self.assertEqual(mv, ((2, 6), (1, 6)))

        # 2. Level 3 never moves Queen into square attacked by Pawn just for center bonus
        c2 = ChessGameLogic(level=3)
        c2.board = [{"gamer_id": 0, "name": "", "is_first_move": False} for _ in range(64)]
        c2.board[0 * 8 + 4] = {"gamer_id": 1, "name": "King", "is_first_move": False}
        c2.king1_pos = (0, 4)
        c2.board[2 * 8 + 2] = {"gamer_id": 1, "name": "Pawn", "is_first_move": False}  # attacks (3,3)
        c2.board[7 * 8 + 4] = {"gamer_id": 2, "name": "King", "is_first_move": False}
        c2.king2_pos = (7, 4)
        c2.board[5 * 8 + 3] = {"gamer_id": 2, "name": "Queen", "is_first_move": False}
        c2.my_player_num = 2
        mv2 = c2.compute_next_move()
        self.assertNotEqual(mv2[1], (3, 3))

    def test_dotbox_and_yinsh_level_3_helpers_work_cleanly(self):
        from Bots.games.dotbox import DotBoxGameLogic
        from Bots.games.yinsh import YinshGameLogic

        d = DotBoxGameLogic(level=3)
        d.my_player_num = 2
        mv = d.compute_next_move()
        self.assertIsInstance(mv, int)

        y = YinshGameLogic(level=3)
        y.my_player_num = 2
        y.is_setup_ring_phase = True
        ymv = y.compute_next_move()
        self.assertEqual(ymv[0], "SubmitRing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
