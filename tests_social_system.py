import copy
import sys
import types
import unittest
from datetime import datetime, timedelta


def _match_condition(val, cond, doc=None, key=None):
    if isinstance(cond, dict):
        for op, op_val in cond.items():
            if op == "$in":
                if isinstance(val, list):
                    if not any(v in op_val for v in val):
                        return False
                elif val not in op_val:
                    return False
            elif op == "$nin":
                if isinstance(val, list):
                    if any(v in op_val for v in val):
                        return False
                elif val in op_val:
                    return False
            elif op == "$ne":
                if val == op_val:
                    return False
            elif op == "$gt":
                if val is None or not (val > op_val):
                    return False
            elif op == "$gte":
                if val is None or not (val >= op_val):
                    return False
            elif op == "$lt":
                if val is None or not (val < op_val):
                    return False
            elif op == "$lte":
                if val is None or not (val <= op_val):
                    return False
            elif op == "$regex":
                import re
                flags = re.IGNORECASE if cond.get("$options") == "i" else 0
                if not re.search(op_val, str(val or ""), flags):
                    return False
            elif op == "$options":
                continue
        return True
    if isinstance(val, list) and not isinstance(cond, list):
        return cond in val
    return val == cond


def _match_query(doc, query):
    if not query:
        return True
    for k, v in query.items():
        if k == "$or":
            if not any(_match_query(doc, sub) for sub in v):
                return False
        elif k == "$and":
            if not all(_match_query(doc, sub) for sub in v):
                return False
        else:
            if not _match_condition(doc.get(k), v, doc, k):
                return False
    return True


class InMemoryCursor:
    def __init__(self, docs):
        self._docs = [copy.deepcopy(d) for d in docs]

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                self._docs.sort(key=lambda x: (x.get(k) is None, x.get(k)), reverse=(d == -1))
        else:
            self._docs.sort(
                key=lambda x: (x.get(key_or_list) is None, x.get(key_or_list)),
                reverse=(direction == -1),
            )
        return self

    def skip(self, n):
        self._docs = self._docs[int(n):]
        return self

    def limit(self, n):
        self._docs = self._docs[:int(n)]
        return self

    def __iter__(self):
        return iter(self._docs)


class InMemoryCollection:
    def __init__(self, name):
        self.name = name
        self.docs = []
        self.unique_indexes = []

    def create_index(self, keys, unique=False, **kwargs):
        if unique:
            if isinstance(keys, str):
                self.unique_indexes.append([keys])
            else:
                self.unique_indexes.append([k for k, _ in keys])

    def _check_unique(self, candidate, exclude_idx=None):
        from pymongo.errors import DuplicateKeyError
        for fields in self.unique_indexes:
            for i, existing in enumerate(self.docs):
                if exclude_idx is not None and i == exclude_idx:
                    continue
                if all(existing.get(f) == candidate.get(f) and candidate.get(f) is not None for f in fields):
                    raise DuplicateKeyError(f"Duplicate key on {fields}")

    def insert_one(self, doc):
        d = copy.deepcopy(doc)
        if "_id" not in d:
            d["_id"] = f"id_{len(self.docs) + 1}"
        self._check_unique(d)
        self.docs.append(d)
        return types.SimpleNamespace(inserted_id=d["_id"])

    def find_one(self, query=None, projection=None, sort=None):
        matches = [d for d in self.docs if _match_query(d, query or {})]
        if sort:
            c = InMemoryCursor(matches).sort(sort)
            matches = list(c)
        if not matches:
            return None
        res = copy.deepcopy(matches[0])
        if projection and projection.get("_id") == 0:
            res.pop("_id", None)
        return res

    def find(self, query=None, projection=None):
        matches = []
        for d in self.docs:
            if _match_query(d, query or {}):
                item = copy.deepcopy(d)
                if projection and projection.get("_id") == 0:
                    item.pop("_id", None)
                matches.append(item)
        return InMemoryCursor(matches)

    def count_documents(self, query=None):
        return sum(1 for d in self.docs if _match_query(d, query or {}))

    def _apply_update(self, doc, update):
        for op, payload in update.items():
            if op == "$set":
                for k, v in payload.items():
                    if "." in k:
                        parts = k.split(".", 1)
                        doc.setdefault(parts[0], {})[parts[1]] = copy.deepcopy(v)
                    else:
                        doc[k] = copy.deepcopy(v)
            elif op == "$inc":
                for k, v in payload.items():
                    if "." in k:
                        parts = k.split(".", 1)
                        sub = doc.setdefault(parts[0], {})
                        sub[parts[1]] = sub.get(parts[1], 0) + v
                    else:
                        doc[k] = doc.get(k, 0) + v
            elif op == "$addToSet":
                for k, v in payload.items():
                    arr = doc.setdefault(k, [])
                    if v not in arr:
                        arr.append(copy.deepcopy(v))
            elif op == "$pull":
                for k, v in payload.items():
                    arr = doc.setdefault(k, [])
                    if v in arr:
                        arr.remove(v)
            elif op == "$setOnInsert":
                pass

    def update_one(self, query, update, upsert=False):
        for idx, d in enumerate(self.docs):
            if _match_query(d, query):
                self._apply_update(d, update)
                return types.SimpleNamespace(modified_count=1, matched_count=1)
        if upsert:
            new_doc = {}
            for k, v in query.items():
                if not k.startswith("$") and not isinstance(v, dict):
                    new_doc[k] = copy.deepcopy(v)
            if "$setOnInsert" in update:
                for k, v in update["$setOnInsert"].items():
                    new_doc[k] = copy.deepcopy(v)
            self._apply_update(new_doc, update)
            self.insert_one(new_doc)
            return types.SimpleNamespace(modified_count=1, matched_count=1)
        return types.SimpleNamespace(modified_count=0, matched_count=0)

    def update_many(self, query, update):
        mod = 0
        for d in self.docs:
            if _match_query(d, query):
                self._apply_update(d, update)
                mod += 1
        return types.SimpleNamespace(modified_count=mod)

    def find_one_and_update(self, query, update, upsert=False, return_document=True, projection=None):
        for d in self.docs:
            if _match_query(d, query):
                self._apply_update(d, update)
                res = copy.deepcopy(d)
                if projection and projection.get("_id") == 0:
                    res.pop("_id", None)
                return res
        if upsert:
            self.update_one(query, update, upsert=True)
            return self.find_one(query, projection=projection)
        return None

    def delete_one(self, query):
        for idx, d in enumerate(self.docs):
            if _match_query(d, query):
                self.docs.pop(idx)
                return types.SimpleNamespace(deleted_count=1)
        return types.SimpleNamespace(deleted_count=0)

    def delete_many(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _match_query(d, query)]
        return types.SimpleNamespace(deleted_count=before - len(self.docs))


class InMemoryDB:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = InMemoryCollection(name)
        return self.collections[name]


class InMemoryMongoClient:
    def __init__(self, *args, **kwargs):
        self._dbs = {}

    def __getitem__(self, db_name):
        if db_name not in self._dbs:
            self._dbs[db_name] = InMemoryDB()
        return self._dbs[db_name]


def _install_backend_stubs():
    if "pymongo" not in sys.modules:
        pymongo_mod = types.ModuleType("pymongo")
        pymongo_mod.ASCENDING = 1
        pymongo_mod.DESCENDING = -1
        pymongo_mod.ReturnDocument = types.SimpleNamespace(AFTER=True, BEFORE=False)
        pymongo_mod.MongoClient = InMemoryMongoClient
        errors_mod = types.ModuleType("pymongo.errors")

        class DuplicateKeyError(Exception):
            pass

        errors_mod.DuplicateKeyError = DuplicateKeyError
        pymongo_mod.errors = errors_mod
        sys.modules["pymongo"] = pymongo_mod
        sys.modules["pymongo.errors"] = errors_mod

    if "dotenv" not in sys.modules:
        dotenv_mod = types.ModuleType("dotenv")
        dotenv_mod.load_dotenv = lambda *a, **kw: None
        sys.modules["dotenv"] = dotenv_mod

    if "socketio" not in sys.modules:
        sio_mod = types.ModuleType("socketio")

        class AsyncNamespace:
            def __init__(self, namespace=None):
                self.namespace = namespace

        class AsyncServer:
            def __init__(self, *a, **kw):
                self.emitted = []

            def register_namespace(self, ns):
                pass

            async def emit(self, event, data, **kw):
                self.emitted.append((event, data, kw))

            async def enter_room(self, sid, room, namespace=None):
                pass

            async def leave_room(self, sid, room, namespace=None):
                pass

        sio_mod.AsyncNamespace = AsyncNamespace
        sio_mod.AsyncServer = AsyncServer
        sys.modules["socketio"] = sio_mod

    if "jwt" not in sys.modules:
        jwt_mod = types.ModuleType("jwt")
        jwt_mod.encode = lambda payload, key, algorithm="HS256": "stub_jwt_token"
        jwt_mod.decode = lambda token, key, algorithms=None: {"id": "stub_user", "device_id": "dev1"}
        sys.modules["jwt"] = jwt_mod

    if "jose" not in sys.modules:
        jose_mod = types.ModuleType("jose")
        jose_mod.jwt = sys.modules["jwt"]
        jose_mod.JWTError = Exception
        sys.modules["jose"] = jose_mod

    if "fastapi" not in sys.modules:
        fa_mod = types.ModuleType("fastapi")
        fa_mod.Depends = lambda x=None: x
        fa_mod.HTTPException = Exception
        fa_mod.status = types.SimpleNamespace(HTTP_401_UNAUTHORIZED=401, HTTP_404_NOT_FOUND=404)
        sec_mod = types.ModuleType("fastapi.security")
        sec_mod.OAuth2PasswordBearer = lambda **kw: None
        fa_mod.security = sec_mod
        sys.modules["fastapi"] = fa_mod
        sys.modules["fastapi.security"] = sec_mod

    if "passlib" not in sys.modules:
        pl_mod = types.ModuleType("passlib")
        ctx_mod = types.ModuleType("passlib.context")
        ctx_mod.CryptContext = lambda **kw: types.SimpleNamespace(verify=lambda a, b: True, hash=lambda a: a)
        pl_mod.context = ctx_mod
        sys.modules["passlib"] = pl_mod
        sys.modules["passlib.context"] = ctx_mod

    if "pydantic" not in sys.modules:
        pyd_mod = types.ModuleType("pydantic")

        class BaseModel:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        pyd_mod.BaseModel = BaseModel
        sys.modules["pydantic"] = pyd_mod


_install_backend_stubs()

from Commons import commands
from Entities.Database import game_database
from Entities.RewardManagerClass import RewardManagerClass, GameScoreTypesEnum
from Controllers.SocialSession import SAFE_SPECTATOR_GAMES, PRIVATE_STATE_GAMES, social_session


class CafeFekrBackendSocialTests(unittest.TestCase):
    def setUp(self):
        for col in game_database.base_db.collections.values():
            col.docs.clear()
        self.u1 = {"_id": "u1", "username": "Erfan", "coin": 500, "score": 1200, "xp": 800, "image": 1}
        self.u2 = {"_id": "u2", "username": "Niloofar", "coin": 400, "score": 1100, "xp": 600, "image": 2}
        for u in (self.u1, self.u2):
            game_database.base_db["users"].insert_one(u)

    def test_01_commands_and_spectator_safety_lists(self):
        self.assertTrue(hasattr(commands, "Social_Init"))
        self.assertTrue(hasattr(commands, "Social_Spectate_Data"))
        self.assertIn("ludo", SAFE_SPECTATOR_GAMES)
        self.assertIn("monopoly", SAFE_SPECTATOR_GAMES)
        self.assertIn("chess", SAFE_SPECTATOR_GAMES)
        # Private/hidden-state games must be strictly in PRIVATE_STATE_GAMES and NOT in SAFE_SPECTATOR_GAMES
        for hidden_game in ("battleship", "uno", "coup", "sudoku", "msweeper", "quiz"):
            self.assertIn(hidden_game, PRIVATE_STATE_GAMES)
            self.assertNotIn(hidden_game, SAFE_SPECTATOR_GAMES)

    def test_02_reward_manager_awards_clan_contribution_on_ranked_match(self):
        clan = game_database.clans_manager.create_clan(
            leader_id="u1", name="BackendHeroes", tag="#BKND"
        )
        rm = RewardManagerClass(GameScoreTypesEnum.RANK)
        rm.set_user_data(["u1", "u2"])
        rm.finish_game(1, ["Monopoly"], [1], gamer_scores=[1, 0])

        updated_clan = game_database.clans_manager.read_clan(clan["_id"])
        self.assertGreater(updated_clan["clan_score"], 0)
        self.assertGreater(updated_clan["clan_xp"], 0)
        self.assertEqual(updated_clan["total_wins"], 1)

    def test_03_spectator_serializer_sanitizes_and_protects_hidden_state(self):
        from Controllers.Spectator.spectator_state_serializer import SpectatorStateSerializer

        # Safe games allowed, hidden-info games blocked
        for safe_game in ("Ludo", "Chess", "Monopoly", "Backgammon", "Risk", "Checkers", "FourInRow", "Othello", "XOGame", "DotsAndBoxes"):
            ok, _ = SpectatorStateSerializer.is_game_spectatable(safe_game)
            self.assertTrue(ok, f"Expected {safe_game} to be spectatable")

        for hidden_game in ("BattleShip", "Uno", "Coup", "FekrBekr", "Sudoku", "MSweeper", "MNumbers", "Quiz", "RPC"):
            ok, _ = SpectatorStateSerializer.is_game_spectatable(hidden_game)
            self.assertFalse(ok, f"Expected {hidden_game} to be blocked from spectating")

        # Deep recursive sanitization strips forbidden keys without mutating source
        raw_state = {
            "turn": 1,
            "board": [0, 1, 2],
            "secret": "hidden_code",
            "ships": [[1, 2], [3, 4]],
            "players": [
                {"id": "u1", "score": 10, "hand": ["cardA", "cardB"], "token": "jwt_xyz"},
                {"id": "u2", "score": 20, "private_cards": ["ace"], "device_id": "dev_999"},
            ],
        }
        original_copy = copy.deepcopy(raw_state)
        sanitized = SpectatorStateSerializer.sanitize_dict(raw_state)

        self.assertEqual(raw_state, original_copy)
        self.assertNotIn("secret", sanitized)
        self.assertNotIn("ships", sanitized)
        self.assertNotIn("hand", sanitized["players"][0])
        self.assertNotIn("token", sanitized["players"][0])
        self.assertNotIn("private_cards", sanitized["players"][1])
        self.assertNotIn("device_id", sanitized["players"][1])
        self.assertEqual(sanitized["turn"], 1)
        self.assertEqual(sanitized["players"][0]["score"], 10)

        # Public command envelope sanitization
        pub_cmd = {"id": commands.Current_Turn, "data": {"turn_id": 2, "secret_answer": "42"}}
        clean_cmd = SpectatorStateSerializer.sanitize_live_command("Chess", pub_cmd)
        self.assertIsNotNone(clean_cmd)
        self.assertEqual(clean_cmd["id"], commands.Current_Turn)
        self.assertEqual(clean_cmd["data"]["turn_id"], 2)
        self.assertNotIn("secret_answer", clean_cmd["data"])

        # Private/disallowed commands are never forwarded to spectators
        priv_cmd = {"id": 999999, "data": {"hand": [1, 2, 3]}}
        self.assertIsNone(SpectatorStateSerializer.sanitize_live_command("Chess", priv_cmd))
        self.assertIsNone(SpectatorStateSerializer.sanitize_live_command("Uno", pub_cmd))

    def test_04_spectator_access_and_lifecycle_flow(self):
        import asyncio
        from Entities.SocketIOClass import Socket_Server
        from Entities.SocketIOClass.game import games
        from Controllers.Spectator import spectator_controller, spectator_session_manager, SpectatorAccessManager

        MAX_SPECTATORS_PER_GAME = SpectatorAccessManager.MAX_SPECTATORS_PER_GAME

        u3 = {"_id": "u3", "username": "WatcherOne", "coin": 200, "score": 900, "xp": 300, "image": 3}
        u4 = {"_id": "u4", "username": "BlockedWatcher", "coin": 200, "score": 900, "xp": 300, "image": 4}
        game_database.base_db["users"].insert_one(u3)
        game_database.base_db["users"].insert_one(u4)

        # Build a mock active Chess game between u1 and u2
        g_1 = types.SimpleNamespace(
            user_id="u1", gamer_id=1, username="Erfan", score=1200, xp=800, image=1, is_ai=False
        )
        g_2 = types.SimpleNamespace(
            user_id="u2", gamer_id=2, username="Niloofar", score=1100, xp=600, image=2, is_ai=False
        )
        fake_controller = types.SimpleNamespace(
            get_game_data=lambda: {"turn": 1, "pieces": ["K", "Q"], "secret_seed": "do_not_leak"},
            turn_id=1,
            round_number=1,
        )
        fake_session = types.SimpleNamespace(
            game_type=types.SimpleNamespace(value="Chess"),
            game_controller=fake_controller,
            turn_id=1,
        )
        fake_gameplay = types.SimpleNamespace(
            id="game_live_1",
            game_play_id="game_live_1",
            gamers=[g_1, g_2],
            game_session=fake_session,
            game_types=[types.SimpleNamespace(value="Chess")],
            current_game_index=0,
        )
        games.clear()
        games["game_live_1"] = fake_gameplay
        spectator_session_manager.game_spectators.clear()
        spectator_session_manager.sid_registry.clear()
        spectator_session_manager.user_spectating_game.clear()
        Socket_Server.emitted.clear()

        async def run_flow():
            # 1. Active participant u1 cannot spectate while playing in an active match
            res1 = await spectator_controller.handle_request_spectate("u1", "sid_u1", {"game_id": "game_live_1"})
            self.assertEqual(res1["id"], commands.SpectateRejected)
            self.assertEqual(res1["data"]["reason"], "is_participant")

            # 2. Blocked user u4 cannot spectate u1's game
            game_database.friends_manager.block_user("u1", "u4", "test block")
            res2 = await spectator_controller.handle_request_spectate("u4", "sid_u4", {"game_id": "game_live_1"})
            self.assertEqual(res2["id"], commands.SpectateRejected)
            self.assertEqual(res2["data"]["reason"], "blocked")

            # 3. Privacy check: if u1 sets allow_spectators='friends', non-friend u3 is rejected
            game_database.base_db["users"].update_one(
                {"_id": "u1"}, {"$set": {"privacy.allow_spectators": "friends"}}
            )
            res3 = await spectator_controller.handle_request_spectate("u3", "sid_u3", {"game_id": "game_live_1"})
            self.assertEqual(res3["id"], commands.SpectateRejected)
            self.assertEqual(res3["data"]["reason"], "friends_only")

            # 4. Make u1 allow everyone -> u3 joins as spectator and receives sanitized snapshot
            game_database.base_db["users"].update_one(
                {"_id": "u1"}, {"$set": {"privacy.allow_spectators": "everyone"}}
            )
            res4 = await spectator_controller.handle_request_spectate("u3", "sid_u3", {"game_id": "game_live_1"})
            self.assertEqual(res4["id"], commands.SpectateAccepted)
            self.assertEqual(spectator_session_manager.get_spectator_count("game_live_1"), 1)
            snap = res4["data"]
            self.assertEqual(snap["game_id"], "game_live_1")
            self.assertEqual(snap["game_type"], "Chess")
            self.assertNotIn("secret_seed", snap["board_state"])

            # 5. Live public command broadcast reaches spectators in spectate_game_live_1 room
            Socket_Server.emitted.clear()
            await spectator_session_manager.on_game_command(
                "game_live_1", {"id": commands.Current_Turn, "data": {"turn_id": 2, "secret": "hidden"}}, fake_gameplay
            )
            self.assertEqual(len(Socket_Server.emitted), 1)
            _, fwd_payload, fwd_kw = Socket_Server.emitted[0]
            self.assertEqual(fwd_payload["id"], commands.SpectatorGameState)
            self.assertEqual(fwd_kw.get("room"), "spectate_game_live_1")
            self.assertNotIn("secret", fwd_payload["data"]["command"]["data"])

            # 6. Spectator capacity limit enforcement
            users_map = spectator_session_manager.game_spectators["game_live_1"]
            for idx in range(MAX_SPECTATORS_PER_GAME):
                users_map[f"du_{idx}"] = {f"dummy_sid_{idx}"}
            u5 = {"_id": "u5", "username": "LateWatcher", "coin": 100, "score": 500, "xp": 100, "image": 1}
            game_database.base_db["users"].insert_one(u5)
            res6 = await spectator_controller.handle_request_spectate("u5", "sid_u5", {"game_id": "game_live_1"})
            self.assertEqual(res6["id"], commands.SpectateRejected)
            self.assertEqual(res6["data"]["reason"], "spectator_limit_reached")

            # Clean up dummy spectators
            for idx in range(MAX_SPECTATORS_PER_GAME):
                users_map.pop(f"du_{idx}", None)

            # 7. Ending the game notifies spectators and cleans up session
            Socket_Server.emitted.clear()
            await spectator_session_manager.on_game_ended(
                "game_live_1", game_play=fake_gameplay, final_payload={"winner": "u1"}, reason="finished"
            )
            end_events = [p for _, p, _ in Socket_Server.emitted if p.get("id") == commands.SpectatorGameEnded]
            self.assertEqual(len(end_events), 1)
            self.assertEqual(spectator_session_manager.get_spectator_count("game_live_1"), 0)

        asyncio.run(run_flow())
        games.clear()


if __name__ == "__main__":
    unittest.main(verbosity=2)

