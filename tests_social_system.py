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


if __name__ == "__main__":
    unittest.main(verbosity=2)
