import asyncio
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

# Ensure backend root is on sys.path
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


def _install_stubs():
    """Install lightweight deterministic stubs for DB, SocketIO, and external deps."""
    # Stub socketio so Bots.bot_controller can import cleanly
    if "socketio" not in sys.modules:
        sio_mod = types.ModuleType("socketio")

        class _DummyAsyncClient:
            def __init__(self, *args, **kwargs):
                self.namespaces = {}
                self.connected = False

            def on(self, *args, **kwargs):
                def _dec(fn):
                    return fn
                return _dec

            async def emit(self, *args, **kwargs):
                pass

            async def disconnect(self):
                self.connected = False

        sio_mod.AsyncClient = _DummyAsyncClient
        sio_mod.AsyncServer = MagicMock
        sio_mod.AsyncNamespace = object
        sys.modules["socketio"] = sio_mod

    # Shared recording log for emitted commands
    emitted_public = []
    emitted_private = []
    finished_multiplayer_calls = []
    deleted_games = []

    # Stub Entities.SocketIOManagerClass
    sio_mgr_mod = types.ModuleType("Entities.SocketIOManagerClass")

    async def _send_command(command, game_id=""):
        emitted_public.append({"game_id": game_id, "command": command})

    async def _send_private_command(command, socket_id="", game_id=""):
        emitted_private.append({"game_id": game_id, "socket_id": socket_id, "command": command})

    class _DummySocketServer:
        class manager:
            @staticmethod
            def is_connected(sid, ns):
                return bool(sid)

    sio_mgr_mod.send_command = _send_command
    sio_mgr_mod.send_private_command = _send_private_command
    sio_mgr_mod.Socket_Server = _DummySocketServer
    sys.modules["Entities.SocketIOManagerClass"] = sio_mgr_mod

    # Stub Entities.SocketIOClass and Entities.SocketIOClass.game
    if "Entities.SocketIOClass" not in sys.modules:
        pkg = types.ModuleType("Entities.SocketIOClass")
        pkg.__path__ = []
        pkg.Socket_Server = _DummySocketServer
        sys.modules["Entities.SocketIOClass"] = pkg

    game_ns_mod = types.ModuleType("Entities.SocketIOClass.game")
    game_ns_mod.games = {}

    def _finish_multiplayer_game(game_id, rank1_id, rank2_id):
        finished_multiplayer_calls.append((game_id, rank1_id, rank2_id))

    def _finish_game(game_id, winner_id):
        finished_multiplayer_calls.append((game_id, winner_id, None))

    def _delete_game(game_id):
        deleted_games.append(game_id)
        game_ns_mod.games.pop(game_id, None)

    game_ns_mod.finish_multiplayer_game = _finish_multiplayer_game
    game_ns_mod.finish_game = _finish_game
    game_ns_mod.delete_game = _delete_game
    sys.modules["Entities.SocketIOClass.game"] = game_ns_mod

    # Stub Entities.Database with in-memory users store
    db_mod = types.ModuleType("Entities.Database")

    class _MockUsersManager:
        def __init__(self):
            self.users = {}
            self.updates = []

        def reset(self):
            self.users.clear()
            self.updates.clear()

        def read_user(self, user_id):
            return self.users.get(str(user_id))

        def update_user(self, user_id, **kwargs):
            self.updates.append((str(user_id), dict(kwargs)))
            u = self.users.setdefault(str(user_id), {"score": 100, "xp": 0, "coin": 0, "open_game_id": ""})
            u.update(kwargs)

    class _MockHistoryManager:
        def __init__(self):
            self.multi_calls = []
            self.single_calls = []
            self.gameplay_updates = []
            self.game_history_calls = []

        def reset(self):
            self.multi_calls.clear()
            self.single_calls.clear()
            self.gameplay_updates.clear()
            self.game_history_calls.clear()

        def update_user_history_multiplayer(self, uid, h):
            self.multi_calls.append((str(uid), dict(h)))

        def update_user_history(self, uid, h):
            self.single_calls.append((str(uid), dict(h)))

        def create_game_history(self, *args, **kwargs):
            self.game_history_calls.append((args, kwargs))

        def create_game_play_history(self, *args, **kwargs):
            pass

        def delete_game_play_history(self, *args, **kwargs):
            pass

        def update_game_play_history(self, *args, **kwargs):
            self.gameplay_updates.append((args, kwargs))

    class _MockClansManager:
        def record_member_match_contribution(self, **kwargs):
            pass

    class _MockGameDatabase:
        def __init__(self):
            self.users_manager = _MockUsersManager()
            self.user_history_manager = _MockHistoryManager()
            self.game_history_manager = self.user_history_manager
            self.game_play_history_manager = self.user_history_manager
            self.clans_manager = _MockClansManager()

    db_mod.game_database = _MockGameDatabase()
    sys.modules["Entities.Database"] = db_mod

    # Stub Spectator session manager
    if "Controllers.Spectator" not in sys.modules:
        spec_pkg = types.ModuleType("Controllers.Spectator")
        spec_pkg.__path__ = []
        sys.modules["Controllers.Spectator"] = spec_pkg

    spec_mod = types.ModuleType("Controllers.Spectator.spectator_session_manager")

    class _MockSpectatorMgr:
        def get_spectator_count(self, game_id):
            return 0

        def sync_live_match_metadata(self, *args, **kwargs):
            pass

        async def on_subgame_started(self, *args, **kwargs):
            pass

        async def on_game_ended(self, *args, **kwargs):
            pass

    spec_mod.spectator_session_manager = _MockSpectatorMgr()
    sys.modules["Controllers.Spectator.spectator_session_manager"] = spec_mod

    return {
        "emitted_public": emitted_public,
        "emitted_private": emitted_private,
        "finished_multiplayer_calls": finished_multiplayer_calls,
        "deleted_games": deleted_games,
        "game_database": db_mod.game_database,
        "game_ns_mod": game_ns_mod,
    }


STUBS = _install_stubs()

from Commons import commands
from Models.Gamer import GamerModel
from Entities.TimerClass import TimerClass
from Entities.TimerClass.UserDisconnectTimerClass import UserDisconnectTimerClass
from Entities.RewardManagerClass import RewardManagerClass, GameScoreTypesEnum
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass
from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession
from Controllers.GamePlay import BaseGamePlayClass
from Entities.Games.Ludo import LudoGameClass
from Controllers.GameSession.ludo_game_session import LudoGameSession
from Entities.Games.Uno import UnoGameClass
from Controllers.GameSession.uno_game_session import UnoGameSession
from Entities.Games.Coup import CoupGameClass
from Controllers.GameSession.coup_game_session import CoupGameSession
from Entities.Games.Monopoly import MonopolyGameClass
from Controllers.GameSession.monopoly_game_session import MonopolyGameSession
from Entities.Games.Risk import RiskGameClass
from Entities.Games.Risk.Models.models import RiskGameState, RiskContinentModel
from Controllers.GameSession.risk_game_session import RiskGameSession
from Entities.Games.Quiz import QuizGameClass
from Controllers.GameSession.quiz_game_session import QuizGameSession


def _make_gamers(user_ids):
    gamers = []
    for i, uid in enumerate(user_ids, start=1):
        g = GamerModel(
            user_id=uid,
            username=f"player_{uid}",
            user_image=1,
            user_coin=100,
            user_score=100,
            socket_id=f"sid_{uid}",
        )
        g.gamer_id = i
        g.is_joined_game = True
        gamers.append(g)
    return gamers


def _reset_stubs():
    STUBS["emitted_public"].clear()
    STUBS["emitted_private"].clear()
    STUBS["finished_multiplayer_calls"].clear()
    STUBS["deleted_games"].clear()
    STUBS["game_database"].users_manager.reset()
    STUBS["game_database"].user_history_manager.reset()
    STUBS["game_ns_mod"].games.clear()


class _DummyMultiGame(BaseMultiPlayerGameClass):
    def __init__(self, players_count=4):
        super().__init__(lambda *a, **kw: None, players_count=players_count)
        self.active_player_indexes = list(range(1, players_count + 1))
        self.current_turn = 1

    def get_game_winner(self):
        return self.rank1 if self.rank1 is not None else 0


class _DummyMultiSession(BaseMultiplayerGameSession):
    def __init__(self, game_id, user_ids, score_type=GameScoreTypesEnum.MultiRANK):
        super().__init__(game_id, GameTypesEnum.LUDO, score_type)
        self.gamers = _make_gamers(user_ids)
        for g in self.gamers:
            g.set_finish_reconnect_time_function(self.finish_reconnect_time)
        self.game_controller = _DummyMultiGame(players_count=len(user_ids))
        self.is_game_running = True
        self.sent_current_turn_count = 0

    def send_current_turn(self):
        self.sent_current_turn_count += 1
        self.game_controller.change_turn()

    def send_reconnect_data(self, socket_id):
        pass


class TestTimersAndBaseMultiplayer(unittest.TestCase):
    def setUp(self):
        _reset_stubs()

    def test_disconnect_timer_stop_prevents_callback(self):
        fired = []
        t = UserDisconnectTimerClass(user_id="u1")
        t.set_finish_timer_function(lambda uid: fired.append(uid))
        t.max_time = 2
        t.start()
        t.stop()
        # Even if start_timer is invoked again after stop, it must not fire
        t.start_timer()
        self.assertEqual(fired, [])

    def test_timer_pause_resume_threadsafe_state(self):
        t = TimerClass()
        t.start(30, lambda: None)
        t.pause()
        self.assertTrue(t.is_paused)
        t.resume()
        self.assertFalse(t.is_paused)
        t.stop(False)
        self.assertTrue(t.is_canceled)

    def test_base_multiplayer_surrender_when_rank1_already_won(self):
        """Regression: when rank1 already won and 2 players remain, surrendering must give rank2 to survivor, NOT surrenderer."""
        gc = _DummyMultiGame(players_count=4)
        # Player 1 already won legitimately (removed from active, rank1=1)
        gc.rank1 = 1
        gc.active_player_indexes = [2, 3]
        gc.current_turn = 2

        changed = gc._apply_surrender_sync(2)
        self.assertTrue(changed)
        self.assertTrue(gc.is_game_finished)
        self.assertEqual(gc.rank1, 1)
        self.assertEqual(gc.rank2, 3)  # Survivor P3 gets 2nd, NOT P2!
        self.assertEqual(gc.eliminated_order, [2])

    def test_base_multiplayer_sequential_surrenders_order(self):
        gc = _DummyMultiGame(players_count=4)
        self.assertFalse(gc._apply_surrender_sync(4))  # non-turn
        self.assertEqual(gc.eliminated_order, [4])
        self.assertFalse(gc.is_game_finished)

        self.assertTrue(gc._apply_surrender_sync(1))  # current turn
        self.assertEqual(gc.eliminated_order, [4, 1])
        self.assertFalse(gc.is_game_finished)

        self.assertTrue(gc._apply_surrender_sync(3))  # leaves only P2
        self.assertTrue(gc.is_game_finished)
        self.assertEqual(gc.rank1, 2)
        self.assertEqual(gc.rank2, 3)
        self.assertEqual(gc.eliminated_order, [4, 1, 3])


class TestMultiplayerSessionLifecycle(unittest.TestCase):
    def setUp(self):
        _reset_stubs()

    def test_multi_disconnect_pause_resume_requires_zero_active_disconnected(self):
        sess = _DummyMultiSession("g_dc", ["u1", "u2", "u3", "u4"])
        sess.timer.start(30, lambda: None)

        # P2 and P3 both disconnect
        sess.disconnect_user("sid_u2")
        sess.disconnect_user("sid_u3")
        self.assertTrue(sess.timer.is_paused)

        # P2 reconnects -> P3 is STILL disconnected -> timer MUST remain paused!
        sess.join_gamer("u2", "sid_u2_new")
        self.assertTrue(sess.timer.is_paused)

        # P3 reconnects -> ZERO active disconnected -> timer MUST resume!
        sess.join_gamer("u3", "sid_u3_new")
        self.assertFalse(sess.timer.is_paused)

        sess.timer.stop(False)
        for g in sess.gamers:
            g.timer.stop()

    def test_multi_disconnect_timeout_of_second_player_resumes_timer(self):
        sess = _DummyMultiSession("g_dc2", ["u1", "u2", "u3", "u4"])
        sess.timer.start(30, lambda: None)

        sess.disconnect_user("sid_u2")
        sess.disconnect_user("sid_u3")
        sess.join_gamer("u2", "sid_u2_new")
        self.assertTrue(sess.timer.is_paused)

        # P3 times out -> eliminated -> no remaining active disconnected -> timer resumes!
        sess.finish_reconnect_time("u3")
        self.assertFalse(sess.timer.is_paused)
        self.assertIn("u3", sess.dc_timeout_user_ids)

        sess.timer.stop(False)
        for g in sess.gamers:
            g.timer.stop()

    def test_dc_timeout_when_last_survivor_also_disconnected_ends_as_draw(self):
        sess = _DummyMultiSession("g_dc_draw", ["u1", "u2", "u3", "u4"])
        sess._eliminate_player_locked(sess.gamers[2], reason="surrender")
        sess._eliminate_player_locked(sess.gamers[3], reason="surrender")
        self.assertFalse(sess.is_game_finished)

        # Both remaining players P1 and P2 disconnect
        sess.disconnect_user("sid_u1")
        sess.disconnect_user("sid_u2")

        # P1 times out while P2 is ALSO disconnected -> Draw (0, 0) & BOTH penalized
        sess.finish_reconnect_time("u1")
        self.assertTrue(sess.is_game_finished)
        self.assertEqual(sess.game_controller.rank1, 0)
        self.assertEqual(sess.game_controller.rank2, 0)
        self.assertEqual(sess.dc_timeout_user_ids, {"u1", "u2"})
        self.assertEqual(STUBS["finished_multiplayer_calls"][-1], ("g_dc_draw", 0, 0))

    def test_dc_timeout_when_last_survivor_also_dc_preserves_existing_rank1(self):
        sess = _DummyMultiSession("g_dc_r1", ["u1", "u2", "u3", "u4"])
        # P1 already won legitimately; P2 and P3 fight for 2nd, P4 surrendered
        sess.game_controller.rank1 = 1
        sess.game_controller.active_player_indexes = [2, 3]
        sess.disconnect_user("sid_u2")
        sess.disconnect_user("sid_u3")

        sess.finish_reconnect_time("u2")
        self.assertTrue(sess.is_game_finished)
        self.assertEqual(sess.game_controller.rank1, 1)
        self.assertEqual(sess.game_controller.rank2, 0)
        self.assertEqual(sess.dc_timeout_user_ids, {"u2", "u3"})

    def test_only_bots_remaining_finishes_immediately(self):
        sess = _DummyMultiSession("g_bots", ["u1", "bot_1", "bot_2", "bot_3"])
        sess._eliminate_player_locked(sess.gamers[0], reason="surrender")
        self.assertTrue(sess.is_game_finished)
        self.assertIn(sess.game_controller.rank1, [2, 3, 4])
        self.assertEqual(len(STUBS["finished_multiplayer_calls"]), 1)

    def test_duplicate_surrender_and_post_elimination_commands_rejected(self):
        sess = _DummyMultiSession("g_dup", ["u1", "u2", "u3", "u4"])
        sess.disconnect_user("sid_u2")
        self.assertTrue(sess.gamers[1].is_disconnected)

        # Surrender stops disconnect timer and clears is_disconnected
        ok1 = sess._eliminate_player_locked(sess.gamers[1], reason="surrender")
        self.assertTrue(ok1)
        self.assertFalse(sess.gamers[1].is_disconnected)
        self.assertTrue(sess.gamers[1].timer.is_canceled)

        # Duplicate surrender is ignored
        ok2 = sess._eliminate_player_locked(sess.gamers[1], reason="surrender")
        self.assertFalse(ok2)

        # Gameplay command from eliminated player returns None
        res = asyncio.run(sess.command_received({"id": commands.Roll_Dice, "data": {}}, "sid_u2"))
        self.assertIsNone(res)

    def test_clear_open_game_id_never_clobbers_newer_match(self):
        users_mgr = STUBS["game_database"].users_manager
        users_mgr.users["u2"] = {"score": 100, "xp": 0, "coin": 0, "open_game_id": "g_new_match"}
        sess = _DummyMultiSession("g_old_match", ["u1", "u2", "u3", "u4"])
        sess._clear_user_open_game_id("u2")
        # Must NOT overwrite g_new_match!
        self.assertEqual(users_mgr.users["u2"]["open_game_id"], "g_new_match")

        users_mgr.users["u3"] = {"score": 100, "xp": 0, "coin": 0, "open_game_id": "g_old_match"}
        sess._clear_user_open_game_id("u3")
        self.assertEqual(users_mgr.users["u3"]["open_game_id"], "")


class TestGamePlayAndRewards(unittest.TestCase):
    def setUp(self):
        _reset_stubs()

    def test_finish_multiplayer_game_idempotent_and_sanitizes_rank2_eq_rank1(self):
        gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        for u in ["u1", "u2", "u3", "u4"]:
            STUBS["game_database"].users_manager.users[u] = {"score": 100, "xp": 50, "coin": 20, "open_game_id": "gp1"}

        gp = BaseGamePlayClass("gp1", gamers, ["Ludo"], GameScoreTypesEnum.MultiRANK)
        gp.score_manager.set_user_data(["u1", "u2", "u3", "u4"])
        gp.game_session = _DummyMultiSession("gp1", ["u1", "u2", "u3", "u4"])

        gp.finish_multiplayer_game("u1", "u1")  # accidental rank2 == rank1
        gp.finish_multiplayer_game("u1", "u2")  # second call must be no-op

        self.assertEqual(len(STUBS["game_database"].user_history_manager.gameplay_updates), 1)
        self.assertEqual(gp.game_winners, [1])  # rank2 was sanitized to None
        self.assertEqual(len(STUBS["deleted_games"]), 1)

    def test_is_user_active_in_game_unlocks_eliminated_player_for_queues(self):
        gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        gp = BaseGamePlayClass("gp_q", gamers, ["Ludo"], GameScoreTypesEnum.MultiRANK)
        gp.game_session = _DummyMultiSession("gp_q", ["u1", "u2", "u3", "u4"])

        self.assertTrue(gp.is_user_active_in_game("u2"))
        gp.game_session._eliminate_player_locked(gp.game_session.gamers[1], reason="surrender")
        self.assertFalse(gp.is_user_active_in_game("u2"))
        self.assertTrue(gp.is_user_active_in_game("u1"))

    def test_pre_start_multiplayer_surrender_terminates_cleanly(self):
        gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        gp = BaseGamePlayClass("gp_pre", gamers, ["Ludo"], GameScoreTypesEnum.MultiRANK)
        gp.register_user_connection("u1", "sid_u1")
        gp.register_user_connection("u2", "sid_u2")

        asyncio.run(gp.command_received({"id": commands.Surrender, "data": {}}, "sid_u1"))
        self.assertTrue(gp.is_game_terminated)
        self.assertTrue(gp.is_game_finished)
        self.assertIn("gp_pre", STUBS["deleted_games"])
        finish_cmds = [e for e in STUBS["emitted_private"] if e["command"].get("id") == commands.Game_Finished]
        self.assertEqual(len(finish_cmds), 2)

    def test_reward_manager_true_3rd_vs_4th_place_and_afk_penalty_and_id_collision(self):
        # Use small integer user IDs in reversed order to verify NO seat-index vs user-ID collision!
        players = [4, 3, 2, 1]
        for uid in players:
            STUBS["game_database"].users_manager.users[str(uid)] = {
                "score": 100,
                "xp": 0,
                "coin": 0,
                "open_game_id": "g_rew" if uid != 2 else "g_other_new_match",
            }

        rm = RewardManagerClass(GameScoreTypesEnum.MultiRANK)
        rm.set_user_data(players)
        # Elimination order: user 2 surrendered FIRST (4th place, seat idx=2),
        # user 1 surrendered SECOND (3rd place, seat idx=3), user 3 got 2nd, user 4 won 1st.
        # Also user 2 was AFK/DC penalized; user 1 surrendered normally (unpenalized).
        rm.finish_multiplayer_game(
            rank1_gamer_id=4,
            rank2_gamer_id=3,
            game_types=["Ludo"],
            afk_or_dc_user_ids={"2"},
            elimination_order_user_ids=["2", "1"],
            game_id="g_rew",
        )

        # User 4 (rank1): +12 score, User 3 (rank2): +4 score
        # User 1 (true 3rd place, even though seat idx=3!): -4 score, +8 XP
        # User 2 (4th place + AFK/DC penalty): -12 score, 0 XP, 0 Coin
        self.assertEqual(rm.last_awarded_score[4], 12)
        self.assertEqual(rm.last_awarded_score[3], 4)
        self.assertEqual(rm.last_awarded_score[1], -4)
        self.assertEqual(rm.last_awarded_xp[1], 8)
        self.assertEqual(rm.last_awarded_score[2], -12)
        self.assertEqual(rm.last_awarded_xp[2], 0)
        self.assertEqual(rm.last_awarded_coin[2], 0)

        # User 2's newer open_game_id must NOT be clobbered!
        self.assertEqual(STUBS["game_database"].users_manager.users["2"]["open_game_id"], "g_other_new_match")
        self.assertEqual(STUBS["game_database"].users_manager.users["4"]["open_game_id"], "")


class TestAllSixMultiplayerGames(unittest.TestCase):
    def setUp(self):
        _reset_stubs()

    def test_ludo_sync_reconnect_timeout_payload_and_3_turn_afk(self):
        sess = LudoGameSession("g_ludo", GameTypesEnum.LUDO, GameScoreTypesEnum.MultiRANK)
        sess.gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        for g in sess.gamers:
            g.set_finish_reconnect_time_function(sess.finish_reconnect_time)
        sess.game_controller = LudoGameClass(send_data_function=sess.send_command, players_count=4)
        sess.game_controller.current_turn = 1
        sess.is_game_running = True

        # Place a piece of P1 on the board to confirm surrender clears it synchronously
        sess.game_controller.board[0].count = 1
        sess.game_controller.board[0].equipped_user = 1

        # Disconnect timeout on active turn P1
        sess.disconnect_user("sid_u1")
        sess.finish_reconnect_time("u1")
        self.assertNotIn(1, sess.game_controller.active_player_indexes)
        self.assertEqual(sess.game_controller.board[0].count, 0)
        self.assertEqual(sess.game_controller.current_turn, 2)

        surr_cmds = [e["command"] for e in STUBS["emitted_public"] if e["command"].get("id") == commands.Surrender]
        self.assertTrue(len(surr_cmds) >= 1)
        self.assertIn("board", surr_cmds[-1]["data"])
        self.assertIn("active_player_indexes", surr_cmds[-1]["data"])

        # 3-turn AFK elimination for P2
        for _ in range(3):
            sess.game_controller.current_turn = 2
            sess.on_turn_timeout()
        self.assertNotIn(2, sess.game_controller.active_player_indexes)
        self.assertIn("u2", sess.afk_user_ids)

        sess.timer.stop(False)
        for g in sess.gamers:
            g.timer.stop()

    def test_uno_active_turn_surrender_and_dc_timeout_advance_turn(self):
        sess = UnoGameSession("g_uno", GameTypesEnum.UNO, GameScoreTypesEnum.MultiRANK)
        sess.gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        for g in sess.gamers:
            g.set_finish_reconnect_time_function(sess.finish_reconnect_time)
        sess.game_controller = UnoGameClass(send_data_function=sess.send_command, players_count=4)
        sess.game_controller.current_turn = 1
        sess.game_controller.last_drawn_card = {"color": "red", "value": "5"}
        sess.is_game_running = True

        # Active turn P1 surrenders -> must advance turn to P2 (previously stalled!)
        sess._eliminate_player_locked(sess.gamers[0], reason="surrender")
        self.assertNotIn(1, sess.game_controller.active_player_indexes)
        self.assertEqual(sess.game_controller.current_turn, 2)
        self.assertIsNone(sess.game_controller.last_drawn_card)
        turn_cmds = [e["command"] for e in STUBS["emitted_public"] if e["command"].get("id") == commands.Current_Turn]
        self.assertTrue(any(c["data"]["turn"] == 2 for c in turn_cmds))

        # Active turn P2 disconnects & times out -> must advance turn to P3!
        sess.disconnect_user("sid_u2")
        sess.finish_reconnect_time("u2")
        self.assertNotIn(2, sess.game_controller.active_player_indexes)
        self.assertEqual(sess.game_controller.current_turn, 3)

        sess.timer.stop(False)
        for g in sess.gamers:
            g.timer.stop()

    def test_coup_exchange_deck_return_blocker_surrender_and_responder_dc(self):
        # 1) Exchange deck leak fix
        gc = CoupGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gc.current_turn = 1
        gc.phase = "exchange"
        drawn = [gc.court_deck.pop(), gc.court_deck.pop()]
        gc.exchange_pool = list(gc.hands[1]) + list(drawn)
        deck_before = len(gc.court_deck)
        gc._apply_surrender_sync(1)
        self.assertEqual(len(gc.court_deck), deck_before + 2)
        self.assertEqual(gc.exchange_pool, [])

        # 2) Blocker surrender during challenge_block resolves unblocked action (does NOT give actor extra turn)
        gc2 = CoupGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gc2.current_turn = 1
        coins_before = gc2.coins[1]
        ev_act = gc2.submit_action(1, "foreign_aid")
        self.assertEqual(ev_act["action"], "foreign_aid")
        ev_blk = gc2.submit_block(2, "duke")
        self.assertEqual(ev_blk["blocker_id"], 2)
        self.assertEqual(gc2.phase, "challenge_block")

        gc2._apply_surrender_sync(2)  # blocker P2 surrenders
        self.assertEqual(gc2.coins[1], coins_before + 2)  # Foreign Aid resolved!
        self.assertEqual(gc2.current_turn, 3)  # Turn advanced to P3, NOT stuck on P1!
        self.assertEqual(gc2.phase, "action")

        # 3) submit_lose_influence preserves non-empty reason
        gc3 = CoupGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gc3.phase = "lose_influence"
        gc3.pending_loss_player = 2
        gc3.loss_reason = "coup"
        gc3.after_loss_step = "end_turn"
        evt = gc3.submit_lose_influence(2, 0)
        self.assertEqual(evt["reason"], "coup")

        # 4) 4P non-turn responder DC timeout triggers _on_all_passed and broadcasts Coup_State
        sess = CoupGameSession("g_coup", GameTypesEnum.COUP, GameScoreTypesEnum.MultiRANK)
        sess.gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        for g in sess.gamers:
            g.set_finish_reconnect_time_function(sess.finish_reconnect_time)
        sess.game_controller = CoupGameClass(send_data_function=sess.send_command, players_count=4)
        sess.game_controller.current_turn = 1
        sess.is_game_running = True
        sess.game_controller.submit_action(1, "foreign_aid")
        sess.game_controller.submit_pass(2)
        sess.game_controller.submit_pass(3)
        # Only P4 left in eligible_responders -> P4 disconnects and times out
        sess.disconnect_user("sid_u4")
        sess.finish_reconnect_time("u4")
        self.assertEqual(sess.game_controller.phase, "action")
        self.assertEqual(sess.game_controller.current_turn, 2)
        state_cmds = [e["command"] for e in STUBS["emitted_public"] if e["command"].get("id") == commands.Coup_State]
        self.assertTrue(len(state_cmds) >= 1)

        sess.timer.stop(False)
        for g in sess.gamers:
            g.timer.stop()

    def test_monopoly_debt_creditor_bystander_pending_tile_and_auction_surrender(self):
        # 1) Creditor surrender during debt forgives debt & restores return_phase
        gc = MonopolyGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gc.current_turn = 1
        gc.phase = "debt"
        gc.debt = {"player_id": 1, "creditor_id": 2, "amount": 500, "reason": "rent", "return_phase": "manage"}
        gc._apply_surrender_sync(2)  # creditor P2 surrenders
        self.assertIsNone(gc.debt)
        self.assertEqual(gc.phase, "manage")
        self.assertEqual(gc.current_turn, 1)

        # 2) Bystander surrender during debt preserves debt & phase
        gc2 = MonopolyGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gc2.current_turn = 1
        gc2.phase = "debt"
        gc2.debt = {"player_id": 1, "creditor_id": 2, "amount": 500, "reason": "rent", "return_phase": "manage"}
        gc2._apply_surrender_sync(4)  # bystander P4 surrenders
        self.assertIsNotNone(gc2.debt)
        self.assertEqual(gc2.phase, "debt")

        # 3) Non-turn surrender during buy_or_auction preserves pending_tile_id
        gc3 = MonopolyGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gc3.current_turn = 1
        gc3.phase = "buy_or_auction"
        gc3.pending_tile_id = 3
        gc3._apply_surrender_sync(4)
        self.assertEqual(gc3.pending_tile_id, 3)

        # 4) Highest-bidder surrender during auction clears dead highest_bidder & doesn't skip current bidder
        gc4 = MonopolyGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gc4.current_turn = 1
        gc4.phase = "auction"
        gc4.auction = {
            "tile_id": 3,
            "current_bid": 150,
            "highest_bidder": 2,
            "eligible": [1, 2, 3, 4],
            "passed": [],
            "current_bidder": 3,
        }
        gc4._apply_surrender_sync(2)  # highest bidder P2 surrenders while it's P3's turn to bid
        self.assertEqual(gc4.auction["highest_bidder"], 0)
        self.assertEqual(gc4.auction["current_bid"], 0)
        self.assertEqual(gc4.auction["current_bidder"], 3)  # P3 was NOT skipped!
        self.assertIn(2, gc4.auction["passed"])
        self.assertNotIn(2, gc4.active_player_indexes)

    def test_risk_defender_and_attacker_surrender_and_dc_timeout(self):
        sess = RiskGameSession("g_risk", GameTypesEnum.RISK, GameScoreTypesEnum.MultiRANK)
        sess.gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        for g in sess.gamers:
            g.set_finish_reconnect_time_function(sess.finish_reconnect_time)
        sess.game_controller = RiskGameClass(send_data_function=sess.send_command, players_count=4)
        sess.is_game_running = True

        # Set up an active attack: P1 attacking P2
        gc = sess.game_controller
        gc.current_turn = 1
        gc.game_state = RiskGameState.ATTACK
        gc.attack_handler.is_attack_active = True
        gc.attack_handler.source_id = 0  # P1
        gc.attack_handler.target_id = 2  # P2
        gc.attack_handler.source_continent = RiskContinentModel.EUROPE
        gc.attack_handler.target_continent = RiskContinentModel.ASIA
        token_before = sess._combat_token

        # Defender P2 disconnects & times out -> battle canceled, Roll_Result emitted, SelectAction restored
        sess.disconnect_user("sid_u2")
        sess.finish_reconnect_time("u2")
        self.assertEqual(gc.game_state, RiskGameState.SELECTACTION)
        self.assertFalse(gc.attack_handler.is_attack_active)
        self.assertEqual(gc.current_turn, 1)
        self.assertGreater(sess._combat_token, token_before)
        roll_cmds = [e["command"] for e in STUBS["emitted_public"] if e["command"].get("id") == commands.Roll_Result]
        self.assertTrue(any(c["data"].get("canceled") is True for c in roll_cmds))
        surr_cmds = [e["command"] for e in STUBS["emitted_public"] if e["command"].get("id") == commands.Surrender]
        self.assertIn("players_data", surr_cmds[-1]["data"])
        self.assertIn("tokens", surr_cmds[-1]["data"])

        # Now P1 attacks P3, then ATTACKER P1 surrenders -> NO fake canceled Roll_Result, turn advances to P3!
        STUBS["emitted_public"].clear()
        gc.game_state = RiskGameState.ATTACK
        gc.attack_handler.is_attack_active = True
        gc.attack_handler.source_id = 0  # P1
        gc.attack_handler.target_id = 3  # P3
        gc.attack_handler.source_continent = RiskContinentModel.EUROPE
        gc.attack_handler.target_continent = RiskContinentModel.ASIA

        sess._eliminate_player_locked(sess.gamers[0], reason="surrender")
        roll_cmds_after = [e["command"] for e in STUBS["emitted_public"] if e["command"].get("id") == commands.Roll_Result]
        self.assertEqual(len(roll_cmds_after), 0)
        self.assertEqual(gc.current_turn, 3)

        sess.timer.stop(False)
        for g in sess.gamers:
            g.timer.stop()

    def test_quiz_surrender_and_dc_trigger_immediate_reveal_and_preserve_early_surrender(self):
        # 1) Early surrender preserved across setup_players & rank2 != rank1
        gc = QuizGameClass(send_data_function=lambda *a, **kw: None, players_count=4)
        gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        gc.active_player_indexes = [1, 2, 3, 4]
        gc._apply_surrender_sync(4)
        gc.setup_players(gamers)
        self.assertNotIn(4, gc.active_player_indexes)
        self.assertIn(4, gc.surrendered_players)

        # Single active survivor ranking never sets rank2 == rank1
        gc2 = QuizGameClass(send_data_function=lambda *a, **kw: None, players_count=2)
        gc2.active_player_indexes = [1]
        gc2.surrendered_players = []
        gc2._compute_final_rankings()
        self.assertEqual(gc2.rank1, 1)
        self.assertNotEqual(gc2.rank2, gc2.rank1)

        # 2) 4P DC timeout triggers reveal_turn_results immediately when remaining active players already answered
        sess = QuizGameSession("g_quiz", GameTypesEnum.QUIZ, GameScoreTypesEnum.MultiRANK)
        sess.gamers = _make_gamers(["u1", "u2", "u3", "u4"])
        for g in sess.gamers:
            g.set_finish_reconnect_time_function(sess.finish_reconnect_time)
        sess.game_controller = QuizGameClass(send_data_function=sess.send_command, players_count=4)
        sess.game_controller.setup_players(sess.gamers)
        sess.is_game_running = True
        sess.game_controller.is_turn_round_finished = False
        sess.game_controller.turn_answers = {1: 1, 2: 2, 3: 3}  # P4 hasn't answered

        reveal_called = []
        sess.reveal_turn_results = lambda: reveal_called.append(True)

        sess.disconnect_user("sid_u4")
        sess.finish_reconnect_time("u4")
        self.assertEqual(len(reveal_called), 1)

        sess.timer.stop(False)
        for g in sess.gamers:
            g.timer.stop()

    def test_bot_controller_stays_active_on_other_surrender_in_4p_match(self):
        from Bots.bot_controller import ClassicRankBot

        bot = ClassicRankBot(
            game_id="g_bot4p",
            game_type="Ludo",
            bot_user_id="bot_1",
            bot_name="Bot1",
            bot_avatar=1,
            token="tok",
        )
        bot.is_active = True
        bot.my_role = 2
        bot.players_count = 4

        disconnected = []

        async def _mock_disconnect():
            disconnected.append(True)

        bot.disconnect = _mock_disconnect

        # Another player (P3) surrenders in a 4P match -> bot MUST stay active!
        asyncio.run(bot._handle_command({"id": "Surrender", "data": {"gamer_id": 3}}))
        self.assertTrue(bot.is_active)
        self.assertEqual(disconnected, [])

        # Bot itself (P2) surrenders -> bot stops & disconnects!
        asyncio.run(bot._handle_command({"id": "Surrender", "data": {"gamer_id": 2}}))
        self.assertFalse(bot.is_active)
        self.assertEqual(len(disconnected), 1)

        # In a 2P match, opponent surrender -> bot stops & disconnects!
        disconnected.clear()
        bot.is_active = True
        bot.players_count = 2
        asyncio.run(bot._handle_command({"id": "Surrender", "data": {"gamer_id": 1}}))
        self.assertFalse(bot.is_active)
        self.assertEqual(len(disconnected), 1)

    def test_bot_is_not_treated_as_banned(self):
        from Commons.static_functions import is_user_banned
        self.assertFalse(is_user_banned(None))
        self.assertFalse(is_user_banned({"_id": "bot_12345", "username": "Bot"}))
        self.assertFalse(is_user_banned({"is_bot": True, "username": "Bot"}))
        self.assertTrue(is_user_banned({"_id": "user1", "is_banned": True}))
        self.assertTrue(is_user_banned({"_id": "user1", "is_active": False}))
        self.assertFalse(is_user_banned({"_id": "user1", "is_active": True, "is_banned": False}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
