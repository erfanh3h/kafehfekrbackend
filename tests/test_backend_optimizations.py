import asyncio
import importlib.util
import os
import re
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


class TestBackendOptimizations(unittest.TestCase):
    def test_static_functions_difficulty_and_random_ids(self):
        from Commons.static_functions import (
            create_random_game_id,
            create_random_name,
            create_random_user_id,
            gametype_to_difficulty,
            safe_run_async,
        )
        from Entities.Games.game_difficulty import GameDifficultyEnum
        from Entities.Games.game_types import GameTypesEnum

        self.assertEqual(gametype_to_difficulty(GameTypesEnum.TIC_TAC_TOE), GameDifficultyEnum.Easy)
        self.assertEqual(gametype_to_difficulty("Uno"), GameDifficultyEnum.Easy)
        self.assertEqual(gametype_to_difficulty(GameTypesEnum.RISK), GameDifficultyEnum.Hard)
        self.assertEqual(gametype_to_difficulty("Quoridor"), GameDifficultyEnum.Hard)
        self.assertEqual(gametype_to_difficulty("Monopoly"), GameDifficultyEnum.Normal)

        self.assertEqual(len(create_random_name()), 6)
        self.assertEqual(len(create_random_game_id(9)), 9)
        self.assertEqual(len(create_random_user_id()), 6)

        async def _sample():
            return 42

        self.assertEqual(safe_run_async(_sample()), 42)

    def test_users_collection_empty_update_and_regex_escape(self):
        from Entities.Database.users_collection import UsersCollectionManager

        col = MagicMock()
        col.find.return_value.sort.return_value.limit.return_value = []
        mgr = UsersCollectionManager(col)

        # Empty update_user must not call find_one_and_update with empty $set
        self.assertIsNone(mgr.update_user("u1"))
        col.find_one_and_update.assert_not_called()

        # Malformed regex characters must be escaped
        mgr.search_users("a[b(c.*")
        query_arg = col.find.call_args[0][0]
        regex_pattern = query_arg["$or"][0]["_id"]["$regex"]
        self.assertEqual(regex_pattern, re.escape("a[b(c.*"))

    def test_risk_roll_dice_authority_and_malformed_army_count(self):
        from Commons import commands
        from Entities.Games.Risk import RiskGameClass
        from Entities.Games.Risk.Models.models import RiskGameState

        game = RiskGameClass(send_data_function=AsyncMock(), players_count=3)
        game.current_turn = 1
        game.attack_handler.is_attack_active = True
        game.attack_handler.battle_started = True
        game.attack_handler.source_id = 0  # gamer 1
        game.attack_handler.target_id = 2  # gamer 2
        game.game_state = RiskGameState.ATTACK

        self.assertTrue(game.check_authority({"id": commands.Roll_Dice}, 1))
        self.assertFalse(game.check_authority({"id": commands.Roll_Dice}, 2))
        self.assertFalse(game.check_authority({"id": commands.Roll_Dice}, 3))

        # Even if current_turn somehow desynced, non-attacker cannot roll
        game.current_turn = 3
        self.assertFalse(game.check_authority({"id": commands.Attack}, 3))

        # Malformed army counts must not raise ValueError/TypeError
        game.attack_handler.battle_started = False
        self.assertEqual(game.attack_handler.add_attacker_army("invalid_int", 1, commit=False), 0)
        self.assertEqual(game.attack_handler.add_defender_army(True, 2, commit=False), 0)

    def test_multi_rank_queue_preserves_list_aliases(self):
        from Controllers.QueueSession.multi_rank import MultiRankQueueSession
        from Models.Queuer import QueuerModel

        sess = MultiRankQueueSession()
        with patch.object(sess, "can_user_join_queue", return_value=True), \
             patch.object(sess, "broadcast_queue_status"), \
             patch.object(sess, "start_new_game"):
            for i in range(4):
                q = QueuerModel(f"u{i}", f"User{i}", user_image=1, user_coin=100, user_score=100, socket_id=f"sid{i}")
                self.assertTrue(sess.join_user(q, "Ludo"))

            # After 4 players matched, ludo_queuers alias itself is drained in-place
            self.assertEqual(len(sess.ludo_queuers), 0)
            self.assertIs(sess.ludo_queuers, sess._queues_by_type["Ludo"])

            q_extra = QueuerModel("u9", "User9", user_image=1, user_coin=100, user_score=100, socket_id="sid9")
            self.assertTrue(sess.join_user(q_extra, "Risk"))
            self.assertEqual(len(sess.risk_queuers), 1)
            asyncio.run(sess.disconnect_user("sid9"))
            self.assertEqual(len(sess.risk_queuers), 0)

    def test_lobby_malformed_payload_and_lookup(self):
        from Commons import commands
        from Controllers.QueueSession.lobby import LobbySession
        from Models.Queuer import QueuerModel

        sess = LobbySession()
        q = QueuerModel("u1", "Ali", user_image=1, user_coin=100, user_score=100, socket_id="sid1")
        sess.free_queuers.append(q)

        # Invalid game_type should not create a lobby
        asyncio.run(sess.command_received({"id": commands.Lobby_Create, "data": {"game_type": "InvalidGame"}}, "sid1"))
        self.assertEqual(len(sess.lobbies), 0)

        # Missing/non-dict data must not raise KeyError
        asyncio.run(sess.command_received({"id": commands.Lobby_Join, "data": None}, "sid1"))
        asyncio.run(sess.command_received({"id": commands.Lobby_Kick, "data": {}}, "sid1"))
        self.assertIsNone(sess.find_lobbyid_from_socketid("sid1"))

    def test_namespace_auth_guard(self):
        from Commons import commands

        guard_path = os.path.join(BACKEND_ROOT, "Entities", "SocketIOClass", "_auth_guard.py")
        spec = importlib.util.spec_from_file_location("test_auth_guard_mod", guard_path)
        auth_guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_guard)

        ns = MagicMock()
        ns.emit = AsyncMock()
        ns.disconnect = AsyncMock()

        async def _run():
            with patch.object(auth_guard, "check_is_token_valid", new=AsyncMock(return_value={"id": "u1"})), \
                 patch.object(auth_guard, "game_database") as mock_db:
                mock_db.users_manager.read_user.return_value = {"_id": "u1", "is_banned": False, "is_active": True}
                mock_db.config_manager.read_config.return_value = {
                    "maintenance_mode": False,
                    "allowed_version": "2.0.0",
                    "is_queue_open": False,
                }
                # Queue closed blocks non-reconnect join
                res = await auth_guard.authenticate_namespace_user(
                    ns, "sid1", {"token": "t", "version": "2.1.2"}, "/queue",
                    check_maintenance=True, check_version=True, check_queue=True,
                )
                self.assertIsNone(res)
                emitted_cmd = ns.emit.call_args[0][1]
                self.assertEqual(emitted_cmd["id"], getattr(commands, "Queue_Closed", "QueueClosed"))

                # Valid when queue is open
                ns.emit.reset_mock()
                mock_db.config_manager.read_config.return_value = {
                    "maintenance_mode": False,
                    "allowed_version": "2.0.0",
                    "is_queue_open": True,
                }
                res_ok = await auth_guard.authenticate_namespace_user(
                    ns, "sid1", {"token": "t", "version": "2.1.2"}, "/queue",
                    check_maintenance=True, check_version=True, check_queue=True,
                )
                self.assertIsNotNone(res_ok)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
