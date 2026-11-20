"""
Risk Strike AI Bot Game Logic for Cafe Fekr.
Implements accurate, rulebook-faithful tactical AI for Classic Rank & Lobby matches:
- Exact analytical Risk Strike dice combat expectation (max 3 attack dice, max 2 defense dice, Canon +1, ties to defender)
- Win-condition & threat driven Domination Coin race awareness (first to 2 Domination Coins wins)
- Full offensive AND defensive strategy card play (Backup, Expand, Destroy, Bomb, Spy, Canon, Cancel, Army)
- Optimal Army commitment (reaching max dice + casualty shield protection) and smart multi-round continuation/stop
- Readable, natural human-like pacing between sequential actions
"""

import itertools
import random
from typing import Any, Dict, List, Optional, Tuple

try:
    from Bots.games.base_game import BaseGameLogic
except ImportError:
    from games.base_game import BaseGameLogic


CONTINENT_ADJACENCY: Dict[str, List[str]] = {
    "Asia": ["Asia", "Australia", "Europe", "Africa", "NorthAmerica"],
    "Australia": ["Australia", "Asia"],
    "Europe": ["Europe", "Asia", "NorthAmerica", "Africa"],
    "Africa": ["Africa", "Europe", "Asia", "SouthAmerica"],
    "SouthAmerica": ["SouthAmerica", "NorthAmerica", "Africa"],
    "NorthAmerica": ["NorthAmerica", "Europe", "Asia", "SouthAmerica"],
}

ALL_CONTINENTS = ["Asia", "NorthAmerica", "Europe", "Africa", "Australia", "SouthAmerica"]

DOMINATION_THRESHOLDS: Dict[str, int] = {
    "Asia": 8,
    "NorthAmerica": 6,
    "Europe": 5,
    "Africa": 4,
    "Australia": 3,
    "SouthAmerica": 3,
}

# Cache for exact analytical combat expectations:
# (atk_dice, def_dice, atk_canon, def_canon) -> (exp_atk_loss, exp_def_loss)
_COMBAT_EV_CACHE: Dict[Tuple[int, int, int, int], Tuple[float, float]] = {}


def _apply_canon_bonus_tuple(rolls_desc: Tuple[int, ...], bonus: int) -> Tuple[int, ...]:
    if bonus <= 0:
        return rolls_desc
    arr = list(rolls_desc)
    rem = int(bonus)
    while rem > 0:
        boosted = False
        for i in range(len(arr)):
            if arr[i] < 6:
                arr[i] += 1
                boosted = True
                break
        if not boosted:
            break
        rem -= 1
    arr.sort(reverse=True)
    return tuple(arr)


def expected_round_losses(
    atk_dice: int,
    def_dice: int,
    atk_canon: int = 0,
    def_canon: int = 0,
) -> Tuple[float, float]:
    """
    Exact expected (attacker_losses, defender_losses) for a single Risk Strike dice round.
    Matches Entities/Games/Risk/Handlers/risk_attack_handler.py identically.
    """
    a_n = max(1, min(3, int(atk_dice)))
    d_n = max(1, min(2, int(def_dice)))
    a_c = max(0, min(2, int(atk_canon)))
    d_c = max(0, min(2, int(def_canon)))
    key = (a_n, d_n, a_c, d_c)
    cached = _COMBAT_EV_CACHE.get(key)
    if cached is not None:
        return cached

    # Distribution over sorted descending tuples for attacker & defender
    atk_dist: Dict[Tuple[int, ...], int] = {}
    for roll in itertools.product(range(1, 7), repeat=a_n):
        s = _apply_canon_bonus_tuple(tuple(sorted(roll, reverse=True)), a_c)
        atk_dist[s] = atk_dist.get(s, 0) + 1

    def_dist: Dict[Tuple[int, ...], int] = {}
    for roll in itertools.product(range(1, 7), repeat=d_n):
        s = _apply_canon_bonus_tuple(tuple(sorted(roll, reverse=True)), d_c)
        def_dist[s] = def_dist.get(s, 0) + 1

    total_weight = (6 ** a_n) * (6 ** d_n)
    pairs = min(a_n, d_n)
    atk_loss_sum = 0
    def_loss_sum = 0

    for a_roll, a_w in atk_dist.items():
        for d_roll, d_w in def_dist.items():
            w = a_w * d_w
            a_l = 0
            d_l = 0
            for i in range(pairs):
                if a_roll[i] > d_roll[i]:
                    d_l += 1
                else:
                    a_l += 1
            atk_loss_sum += a_l * w
            def_loss_sum += d_l * w

    res = (atk_loss_sum / total_weight, def_loss_sum / total_weight)
    _COMBAT_EV_CACHE[key] = res
    return res


class RiskGameLogic(BaseGameLogic):
    def __init__(self, level: int = 2):
        super().__init__(
            game_type="Risk",
            game_type_aliases=["risk", "risk_strike", "riskstrike", "ریسک", "ریسک استرایک"],
            level=level,
        )
        self.reset()

    def reset(self):
        self.current_turn: int = 1
        self.game_state: str = "StartGame"
        self.is_game_finished: bool = False
        self.players_data: List[Dict[str, Any]] = []
        self.active_player_indexes: List[int] = [1, 2]
        self.my_continents: Dict[str, int] = {c: 0 for c in ALL_CONTINENTS}
        self.my_strategies: List[str] = []
        self.my_tokens: List[str] = []
        self.free_tokens: List[str] = list(ALL_CONTINENTS)
        self.active_attack: Optional[Dict[str, Any]] = None
        self.ignore_adjacency: bool = False
        self.attacked_this_turn: bool = False
        self.attacks_this_turn: int = 0
        self.pending_attacker_canon_bonus: int = 0
        self.canon_played_this_battle: bool = False
        self.continent_deck_count: int = 42
        self.strategy_deck_count: int = 38
        self._pending_action: bool = False
        self._last_event_cmd: str = ""

    def get_continuation_delay(self, cmd_id: str = "") -> float:
        """
        Provide readable, natural human-like pauses between Risk Strike actions so
        players clearly watch draws, tactic cards, attacks, and 3D dice rolls unfold.
        """
        c = cmd_id or self._last_event_cmd
        if c == "RollResult":
            return round(random.uniform(2.1, 2.6), 2)
        if c in ("DeclareAttack", "AttackArmy"):
            return round(random.uniform(1.35, 1.85), 2)
        if c == "StrategyResult":
            return round(random.uniform(1.30, 1.75), 2)
        if c in ("DrawResultPrivate", "DrawResult"):
            return round(random.uniform(1.15, 1.65), 2)
        return round(random.uniform(1.1, 1.55), 2)

    def _sync_my_private(self, priv: Dict[str, Any]):
        if not isinstance(priv, dict):
            return
        if "index" in priv and self.my_player_num is None:
            self.my_player_num = int(priv["index"])
        if isinstance(priv.get("continents"), dict):
            for c in ALL_CONTINENTS:
                self.my_continents[c] = int(priv["continents"].get(c, 0))
        if isinstance(priv.get("strategies"), list):
            self.my_strategies = [str(s) for s in priv["strategies"]]
        if isinstance(priv.get("tokens"), list):
            self.my_tokens = [str(t) for t in priv["tokens"]]

    def _sync_game_data(self, gd: Dict[str, Any]):
        if not isinstance(gd, dict):
            return
        if "current_turn" in gd:
            self.current_turn = int(gd["current_turn"])
        if "game_state" in gd:
            self.game_state = str(gd["game_state"])
        if "attacked_this_turn" in gd:
            self.attacked_this_turn = bool(gd["attacked_this_turn"])
            self.attacks_this_turn = 1 if self.attacked_this_turn else 0
        if "ignore_adjacency" in gd:
            self.ignore_adjacency = bool(gd["ignore_adjacency"])
        if "pending_attacker_canon_bonus" in gd:
            self.pending_attacker_canon_bonus = int(gd["pending_attacker_canon_bonus"] or 0)
        if isinstance(gd.get("active_player_indexes"), list):
            self.active_player_indexes = [int(x) for x in gd["active_player_indexes"]]
        if isinstance(gd.get("players_data"), list):
            self.players_data = gd["players_data"]
            my_role = self.my_player_num or 2
            for p in self.players_data:
                if isinstance(p, dict) and int(p.get("index", 0)) == my_role:
                    if isinstance(p.get("continents"), dict):
                        for c in ALL_CONTINENTS:
                            self.my_continents[c] = int(p["continents"].get(c, 0))
                    if isinstance(p.get("tokens"), list):
                        self.my_tokens = [str(t) for t in p["tokens"]]
        if "continents" in gd and isinstance(gd.get("continents"), (int, float)):
            self.continent_deck_count = int(gd["continents"])
        if "strategies" in gd and isinstance(gd.get("strategies"), (int, float)):
            self.strategy_deck_count = int(gd["strategies"])
        if isinstance(gd.get("tokens"), list):
            self.free_tokens = [str(t) for t in gd["tokens"]]
        if "active_attack" in gd:
            self.active_attack = gd["active_attack"]

    def handle_server_command(self, cmd_id: str, payload: Any) -> bool:
        my_role = self.my_player_num or 2
        self._pending_action = False
        self._last_event_cmd = cmd_id

        if isinstance(payload, dict):
            if isinstance(payload.get("continents"), (int, float)):
                self.continent_deck_count = int(payload["continents"])
            if isinstance(payload.get("strategies"), (int, float)):
                self.strategy_deck_count = int(payload["strategies"])

        if cmd_id == "GameData" and isinstance(payload, dict):
            gd = payload.get("game_data", payload)
            self._sync_game_data(gd)
            return True

        if cmd_id == "ReconnectData" and isinstance(payload, dict):
            gd = payload.get("game_data", payload)
            self._sync_game_data(gd)
            if isinstance(payload.get("user_data"), dict):
                self._sync_my_private(payload["user_data"])
            if not self.is_game_finished:
                if (
                    self.game_state == "DefenderArmy"
                    and self.active_attack
                    and int(self.active_attack.get("defender_id", 0)) == my_role
                ):
                    self._pending_action = True
                elif self.current_turn == my_role and self.game_state in ("Draw", "SelectAction", "AttackerArmy", "Attack"):
                    self._pending_action = True
            return True

        if cmd_id == "UserData" and isinstance(payload, dict):
            self._sync_my_private(payload)
            return True

        if cmd_id == "StartGame":
            if isinstance(payload, dict):
                if "turn" in payload:
                    self.current_turn = int(payload["turn"])
                if "game_state" in payload:
                    self.game_state = str(payload["game_state"])
            return True

        if cmd_id in ("DrawCard", "CurrentTurn"):
            if isinstance(payload, dict):
                self.current_turn = int(payload.get("turn", self.current_turn))
                self.game_state = str(payload.get("game_state", "Draw"))
            elif isinstance(payload, int):
                self.current_turn = int(payload)
                self.game_state = "Draw"
            self.ignore_adjacency = False
            self.attacked_this_turn = False
            self.attacks_this_turn = 0
            self.pending_attacker_canon_bonus = 0
            self.canon_played_this_battle = False
            self.active_attack = None
            if not self.is_game_finished and self.current_turn == my_role:
                self._pending_action = True
            return True

        if cmd_id == "DrawResult" and isinstance(payload, dict):
            new_data = payload.get("new_data")
            if isinstance(new_data, dict):
                self._update_player_global(new_data)
            if isinstance(payload.get("players_data"), list):
                self.players_data = payload["players_data"]
            if isinstance(payload.get("tokens"), list):
                self.free_tokens = [str(t) for t in payload["tokens"]]
            if payload.get("is_game_finished", False):
                self.is_game_finished = True
                self.game_state = "GameFinished"
                self._pending_action = False
                return True
            self.game_state = str(payload.get("game_state", "SelectAction"))
            return True

        if cmd_id == "DrawResultPrivate" and isinstance(payload, dict):
            if isinstance(payload.get("new_user_data"), dict):
                self._sync_my_private(payload["new_user_data"])
            if len(self.my_tokens) >= 2:
                self.is_game_finished = True
                self.game_state = "GameFinished"
                self._pending_action = False
                return True
            draw_type = int(payload.get("draw_type", 3))
            if draw_type in (1, 2, 3) and not self.is_game_finished and self.current_turn == my_role:
                self.game_state = "SelectAction"
                self._pending_action = True
            return True

        if cmd_id == "DeclareAttack" and isinstance(payload, dict):
            atk_id = int(payload.get("gamer_id", self.current_turn))
            tgt_id = int(payload.get("target_index", 0))
            src_c = str(payload.get("source_continent", "Asia"))
            tgt_c = str(payload.get("target_continent", "Asia"))
            self.game_state = str(payload.get("game_state", "AttackerArmy"))
            self.attacked_this_turn = True
            self.canon_played_this_battle = False
            if isinstance(payload.get("active_attack"), dict):
                self.active_attack = dict(payload["active_attack"])
            else:
                self.active_attack = {
                    "attacker_id": atk_id,
                    "defender_id": tgt_id,
                    "source_continent": src_c,
                    "target_continent": tgt_c,
                    "attacker_army": 0,
                    "defender_army": 0,
                    "attacker_canon_bonus": int(payload.get("attacker_canon_bonus", 0)),
                    "defender_canon_bonus": 0,
                    "battle_started": False,
                }
            if atk_id == my_role:
                self.attacks_this_turn += 1
                if self.game_state in ("DeclareAttack", "AttackerArmy"):
                    self._pending_action = True
            elif tgt_id == my_role and self.game_state == "DefenderArmy":
                self._pending_action = True
            return True

        if cmd_id == "AttackArmy" and isinstance(payload, dict):
            tgt_id = int(payload.get("target_index", (self.active_attack or {}).get("defender_id", 0)))
            self.game_state = str(payload.get("game_state", "DefenderArmy"))
            if isinstance(payload.get("players_data"), list):
                self.players_data = payload["players_data"]
            if isinstance(payload.get("active_attack"), dict):
                self.active_attack = dict(payload["active_attack"])
            elif self.active_attack is not None:
                self.active_attack["attacker_army"] = int(payload.get("count", 0))
            if not self.is_game_finished and tgt_id == my_role:
                self.canon_played_this_battle = False
                self._pending_action = True
            return True

        if cmd_id in ("RollResult", "Attack") and isinstance(payload, dict):
            if isinstance(payload.get("players_data"), list):
                self.players_data = payload["players_data"]
                for p in self.players_data:
                    if isinstance(p, dict) and int(p.get("index", 0)) == my_role:
                        if isinstance(p.get("continents"), dict):
                            for c in ALL_CONTINENTS:
                                self.my_continents[c] = int(p["continents"].get(c, 0))
                        if isinstance(p.get("tokens"), list):
                            self.my_tokens = [str(t) for t in p["tokens"]]
            if isinstance(payload.get("tokens"), list):
                self.free_tokens = [str(t) for t in payload["tokens"]]
            if payload.get("is_game_finished", False):
                self.active_attack = None
                self.is_game_finished = True
                self.game_state = "GameFinished"
                self._pending_action = False
                return True
            self.game_state = str(payload.get("game_state", "SelectAction"))
            self.canon_played_this_battle = False
            if payload.get("battle_continues", False) and self.game_state == "Attack":
                self.active_attack = {
                    "attacker_id": int(payload.get("attacker_id", self.current_turn)),
                    "defender_id": int(payload.get("defender_id", 0)),
                    "source_continent": str(payload.get("source_continent", "Asia")),
                    "target_continent": str(payload.get("target_continent", "Asia")),
                    "attacker_army": int(payload.get("attacker_army", 0)),
                    "defender_army": int(payload.get("defender_army", 0)),
                    "attacker_canon_bonus": 0,
                    "defender_canon_bonus": 0,
                    "battle_started": True,
                }
            else:
                self.active_attack = None
            if cmd_id == "Attack" and self.current_turn == my_role:
                self._pending_action = True
            return True

        if cmd_id == "StrategyResult" and isinstance(payload, dict):
            if isinstance(payload.get("players_data"), list):
                self.players_data = payload["players_data"]
                for p in self.players_data:
                    if isinstance(p, dict) and int(p.get("index", 0)) == my_role:
                        if isinstance(p.get("continents"), dict):
                            for c in ALL_CONTINENTS:
                                self.my_continents[c] = int(p["continents"].get(c, 0))
                        if isinstance(p.get("tokens"), list):
                            self.my_tokens = [str(t) for t in p["tokens"]]
            if isinstance(payload.get("tokens"), list):
                self.free_tokens = [str(t) for t in payload["tokens"]]
            if "active_attack" in payload:
                self.active_attack = dict(payload["active_attack"]) if isinstance(payload["active_attack"], dict) else None
            if "attacked_this_turn" in payload:
                self.attacked_this_turn = bool(payload["attacked_this_turn"])
            if "pending_attacker_canon_bonus" in payload:
                self.pending_attacker_canon_bonus = int(payload["pending_attacker_canon_bonus"] or 0)
            if payload.get("is_game_finished", False):
                self.active_attack = None
                self.is_game_finished = True
                self.game_state = "GameFinished"
                self._pending_action = False
                return True
            actor_id = int(payload.get("gamer_id", 0))
            if payload.get("ignore_adjacency") and actor_id == my_role:
                self.ignore_adjacency = True
            if payload.get("strategy") == "Canon" and actor_id == my_role:
                self.canon_played_this_battle = True
            self.game_state = str(payload.get("game_state", self.game_state))
            if payload.get("attack_canceled"):
                self.active_attack = None
                return True
            if not self.is_game_finished:
                # Continue acting if it's our SelectAction, AttackerArmy, Attack, OR DefenderArmy step!
                if self.game_state == "DefenderArmy" and self.active_attack and int(self.active_attack.get("defender_id", 0)) == my_role:
                    self._pending_action = True
                elif self.current_turn == my_role and self.game_state in ("SelectAction", "AttackerArmy", "Attack"):
                    self._pending_action = True
            return True

        if cmd_id == "PassTurn" and isinstance(payload, dict):
            if isinstance(payload.get("new_data"), dict):
                self._update_player_global(payload["new_data"])
            self._pending_action = False
            return True

        if cmd_id in ("FinishGame", "GameFinished"):
            self.is_game_finished = True
            self.game_state = "GameFinished"
            self._pending_action = False
            return True

        return False

    def _update_player_global(self, p_dict: Dict[str, Any]):
        idx = int(p_dict.get("index", 0))
        replaced = False
        for i, existing in enumerate(self.players_data):
            if isinstance(existing, dict) and int(existing.get("index", 0)) == idx:
                self.players_data[i] = p_dict
                replaced = True
                break
        if not replaced and idx > 0:
            self.players_data.append(p_dict)

    def should_continue_turn(self) -> bool:
        return bool(self._pending_action) and not self.is_game_finished

    def should_act_on_reconnect(self) -> bool:
        return bool(self._pending_action) and not self.is_game_finished

    def _count_my_strategy(self, name: str) -> int:
        return sum(1 for s in self.my_strategies if s.lower() == name.lower())

    def _get_player_dict(self, p_idx: int) -> Dict[str, Any]:
        for p in self.players_data:
            if isinstance(p, dict) and int(p.get("index", 0)) == p_idx:
                return p
        return {}

    def _get_active_opponents(self) -> List[Dict[str, Any]]:
        my_role = self.my_player_num or 2
        opps = []
        for p in self.players_data:
            if not isinstance(p, dict):
                continue
            opp_id = int(p.get("index", 0))
            if opp_id != my_role and opp_id in self.active_player_indexes:
                opps.append(p)
        opps.sort(
            key=lambda p: (
                len(p.get("tokens", [])) if isinstance(p.get("tokens"), list) else 0,
                sum(int(v) for v in (p.get("continents") or {}).values()) if isinstance(p.get("continents"), dict) else 0,
                int(p.get("strategies_count", 0)),
            ),
            reverse=True,
        )
        return opps

    def _continent_domination_gap(self, conts: Dict[str, Any], tokens: List[str], continent: str) -> int:
        if continent in tokens:
            return 99  # already dominated by this player
        thresh = DOMINATION_THRESHOLDS.get(continent, 4)
        return max(0, thresh - int(conts.get(continent, 0)))

    def _opp_threat_score(self, opp: Dict[str, Any], continent: str) -> float:
        """How dangerous is `opp` holding `continent` right now? Higher = more urgent to disrupt."""
        opp_conts = opp.get("continents", {}) if isinstance(opp.get("continents"), dict) else {}
        opp_tokens = opp.get("tokens", []) if isinstance(opp.get("tokens"), list) else []
        cnt = int(opp_conts.get(continent, 0))
        if cnt <= 0:
            return 0.0
        thresh = DOMINATION_THRESHOLDS.get(continent, 4)
        gap = self._continent_domination_gap(opp_conts, opp_tokens, continent)
        has_token_already = len(opp_tokens) >= 1
        # Match point: opponent has 1 domination coin and is 1 card away from winning!
        if has_token_already and gap == 1:
            return 220.0
        if gap == 1:
            return 135.0
        if has_token_already and gap == 2:
            return 95.0
        if gap == 2:
            return 60.0
        # Progress ratio (prefer low-threshold continents like Australia/SA where each card is 33% of a coin)
        progress = cnt / float(max(1, thresh))
        val = progress * 55.0 + (20.0 if has_token_already else 0.0)
        if continent in opp_tokens:
            # Already owns token; taking cards does not remove token unless someone else reaches threshold
            val *= 0.35
        return val

    def _my_continent_protection_value(self, continent: str) -> float:
        """How valuable is it for the bot to protect `continent` from losing cards?"""
        cnt = self.my_continents.get(continent, 0)
        if cnt <= 0:
            return 0.0
        thresh = DOMINATION_THRESHOLDS.get(continent, 4)
        gap = self._continent_domination_gap(self.my_continents, self.my_tokens, continent)
        am_at_match_point = len(self.my_tokens) >= 1
        if gap == 1:
            return 175.0 if am_at_match_point else 130.0
        if gap == 2:
            return 95.0 if am_at_match_point else 70.0
        if continent in self.my_tokens:
            # We already hold the coin — cards are mostly combat strength, not coin-risk
            return 22.0 + cnt * 8.0
        return (cnt / float(max(1, thresh))) * 55.0 + cnt * 6.0

    def _has_good_adjacent_attack(self) -> bool:
        opponents = self._get_active_opponents()
        my_army = self._count_my_strategy("Army")
        for src_c, my_cnt in self.my_continents.items():
            if my_cnt <= 0:
                continue
            connected = ALL_CONTINENTS if self.ignore_adjacency else CONTINENT_ADJACENCY.get(src_c, [src_c])
            atk_d = min(3, my_cnt + min(2, my_army))
            for opp in opponents:
                opp_conts = opp.get("continents", {}) if isinstance(opp.get("continents"), dict) else {}
                for tgt_c in connected:
                    opp_c = int(opp_conts.get(tgt_c, 0))
                    if opp_c <= 0:
                        continue
                    def_d = min(2, opp_c)
                    exp_a, exp_d = expected_round_losses(atk_d, def_d, self.pending_attacker_canon_bonus, 0)
                    if exp_d > exp_a + 0.12 or self._opp_threat_score(opp, tgt_c) >= 120.0:
                        return True
        return False

    def get_legal_moves(self) -> List[Any]:
        if self.is_game_finished:
            return []
        my_role = self.my_player_num or 2

        # 1. Defender Response Phase (before battle_started): DefenderArmy, Cancel, or Canon!
        if self.game_state == "DefenderArmy" and self.active_attack and not self.active_attack.get("battle_started", False):
            def_id = int(self.active_attack.get("defender_id", 0))
            if def_id == my_role:
                army_cnt = self._count_my_strategy("Army")
                max_commit = min(army_cnt, 3)
                moves = [{"action": "defender_army", "count": c} for c in range(0, max_commit + 1)]
                if self._count_my_strategy("Cancel") > 0:
                    moves.append({"action": "defender_cancel"})
                if self._count_my_strategy("Canon") > 0 and not self.canon_played_this_battle:
                    moves.append({"action": "defender_canon"})
                return moves
            return []

        if self.current_turn != my_role:
            return []

        # 2. Start-of-Turn Draw Phase
        if self.game_state in ("StartGame", "Draw"):
            return [
                {"action": "draw", "draw_type": 1},
                {"action": "draw", "draw_type": 2},
                {"action": "draw", "draw_type": 3},
            ]

        # 3. Attacker Army Commitment Phase (before battle_started)
        if self.game_state in ("DeclareAttack", "AttackerArmy") and self.active_attack and not self.active_attack.get("battle_started", False):
            army_cnt = self._count_my_strategy("Army")
            max_commit = min(army_cnt, 3)
            moves = [{"action": "attacker_army", "count": c} for c in range(0, max_commit + 1)]
            if self._count_my_strategy("Canon") > 0 and not self.canon_played_this_battle and int(self.active_attack.get("attacker_canon_bonus", 0)) == 0:
                moves.append({"action": "attacker_canon"})
            return moves

        # 3b. Ongoing Multi-Round Attack Phase (no new Army cards allowed once battle_started)
        if self.game_state == "Attack" and self.active_attack:
            moves = [
                {"action": "continue_attack"},
                {"action": "stop_attack"},
            ]
            if self._count_my_strategy("Canon") > 0 and not self.canon_played_this_battle and int(self.active_attack.get("attacker_canon_bonus", 0)) == 0:
                moves.append({"action": "attacker_canon"})
            return moves

        # 4. SelectAction Phase: Strategy cards, Declare Attack (max 1 per turn), or Pass Turn
        if self.game_state in ("DrawResult", "SelectAction", "ActionResult"):
            moves = [{"action": "pass"}]
            opponents = self._get_active_opponents()

            attack_moves = []
            if not self.attacked_this_turn and self.attacks_this_turn < 1:
                for src_c, my_cnt in self.my_continents.items():
                    if my_cnt <= 0:
                        continue
                    connected = ALL_CONTINENTS if self.ignore_adjacency else CONTINENT_ADJACENCY.get(src_c, [src_c])
                    for p in opponents:
                        opp_id = int(p.get("index", 0))
                        opp_conts = p.get("continents", {})
                        if not isinstance(opp_conts, dict):
                            continue
                        for tgt_c in connected:
                            if int(opp_conts.get(tgt_c, 0)) > 0:
                                attack_moves.append({
                                    "action": "declare_attack",
                                    "source_continent": src_c,
                                    "target_continent": tgt_c,
                                    "target_index": opp_id,
                                })

            # Non-reactive Strategy cards (respect continent deck availability!)
            if self._count_my_strategy("Backup") > 0 and self.continent_deck_count > 0:
                moves.append({"action": "strategy", "strategy": "Backup"})
            if self._count_my_strategy("Expand") > 0 and not self.ignore_adjacency and not self.attacked_this_turn:
                moves.append({"action": "strategy", "strategy": "Expand"})
            min_my_gap = min(
                (self._continent_domination_gap(self.my_continents, self.my_tokens, c) for c in ALL_CONTINENTS),
                default=5,
            )
            if (
                self._count_my_strategy("Army") > 0
                and self.continent_deck_count > 0
                and (
                    sum(self.my_continents.values()) == 0
                    or self._count_my_strategy("Army") >= 4
                    or (self._count_my_strategy("Army") >= 3 and min_my_gap <= 1)
                )
            ):
                moves.append({"action": "strategy", "strategy": "Army"})

            if self._count_my_strategy("Destroy") > 0:
                best_destroy = None
                best_destroy_score = -1.0
                for p in opponents:
                    opp_id = int(p.get("index", 0))
                    opp_conts = p.get("continents", {}) if isinstance(p.get("continents"), dict) else {}
                    for c, cnt in opp_conts.items():
                        if int(cnt) > 0:
                            sc = self._opp_threat_score(p, c)
                            if sc > best_destroy_score:
                                best_destroy_score = sc
                                best_destroy = {
                                    "action": "strategy",
                                    "strategy": "Destroy",
                                    "target_index": opp_id,
                                    "target_continent": c,
                                }
                if best_destroy is not None:
                    moves.append(best_destroy)

            for strat in ("Spy", "Bomb"):
                if self._count_my_strategy(strat) > 0:
                    best_opp = None
                    best_opp_score = -1.0
                    for p in opponents:
                        opp_id = int(p.get("index", 0))
                        opp_conts = p.get("continents", {}) if isinstance(p.get("continents"), dict) else {}
                        has_c = sum(int(v) for v in opp_conts.values()) > 0
                        s_cnt = int(p.get("strategies_count", 0))
                        if has_c or s_cnt > 0:
                            t_sc = len(p.get("tokens", [])) * 40.0 + s_cnt * 18.0 + sum(int(v) for v in opp_conts.values()) * 4.0
                            if t_sc > best_opp_score:
                                best_opp_score = t_sc
                                best_opp = opp_id
                    if best_opp is not None:
                        moves.append({
                            "action": "strategy",
                            "strategy": strat,
                            "target_index": best_opp,
                        })

            moves.extend(attack_moves)
            return moves

        return []

    def is_critical_turn(self) -> bool:
        if len(self.my_tokens) >= 1:
            return True
        if self.active_attack is not None:
            return True
        for opp in self._get_active_opponents():
            if len(opp.get("tokens", [])) >= 1:
                return True
        return False

    def _score_move(self, move: Dict[str, Any]) -> float:
        act = move.get("action")
        my_total_c = sum(self.my_continents.values())
        my_army_cnt = self._count_my_strategy("Army")
        my_strat_cnt = len(self.my_strategies)

        # ---- 1. DRAW PHASE ----
        if act == "draw":
            dt = int(move.get("draw_type", 3))
            min_my_gap = min(
                (self._continent_domination_gap(self.my_continents, self.my_tokens, c) for c in ALL_CONTINENTS),
                default=5,
            )
            has_defense_card = (self._count_my_strategy("Cancel") > 0 or my_army_cnt >= 1)
            likely_to_attack = self._has_good_adjacent_attack()

            if dt == 1:  # 2 Continents
                if self.continent_deck_count <= 0:
                    return 30.0
                score = 86.0
                if min_my_gap <= 1:
                    score += 58.0  # One card from a Domination Coin!
                elif min_my_gap <= 2:
                    score += 42.0  # Push for domination coin!
                if my_total_c <= 4:
                    score += 28.0
                if not likely_to_attack:
                    # Pro economy: draw 2 continents + pass for 1 free strategy = 3 cards!
                    score += 18.0
                if not has_defense_card and my_total_c >= 5 and min_my_gap >= 2:
                    score -= 22.0
                return score
            elif dt == 3:  # 1 Continent + 1 Strategy
                score = 84.0
                if my_strat_cnt <= 2:
                    score += 18.0
                if not has_defense_card and my_total_c >= 4:
                    score += 16.0
                if min_my_gap <= 1:
                    score -= 10.0
                return score
            else:  # 2 Strategies
                score = 52.0
                if my_strat_cnt <= 1 and my_total_c >= 6 and min_my_gap >= 3:
                    score += 42.0
                if not has_defense_card and my_total_c >= 7:
                    score += 20.0
                return score

        # ---- 2. DEFENDER PHASE ----
        if act in ("defender_cancel", "defender_canon", "defender_army"):
            atk = self.active_attack or {}
            src_c = str(atk.get("source_continent", "Asia"))
            tgt_c = str(atk.get("target_continent", "Asia"))
            atk_id = int(atk.get("attacker_id", self.current_turn))
            atk_army = int(atk.get("attacker_army", 0))
            atk_canon = int(atk.get("attacker_canon_bonus", 0))
            def_canon = int(atk.get("defender_canon_bonus", 0))
            atk_p = self._get_player_dict(atk_id)
            atk_cards = int((atk_p.get("continents") or {}).get(src_c, 1))
            atk_dice = min(3, max(1, atk_cards + atk_army))
            def_cards = max(1, self.my_continents.get(tgt_c, 1))
            prot_val = self._my_continent_protection_value(tgt_c)
            is_last_continent = (my_total_c <= def_cards and def_cards <= 2)

            if act == "defender_cancel":
                # Cancel is precious! Save it for high-value defenses or overwhelming assaults
                if prot_val >= 115.0 and (atk_dice >= 2 or atk_canon > 0):
                    return 190.0
                if is_last_continent and atk_dice >= 2:
                    return 165.0
                if prot_val >= 70.0 and (atk_dice >= 3 or atk_army >= 1 or atk_canon > 0):
                    return 155.0
                if atk_army >= 2 or atk_canon >= 1:
                    return 135.0
                # Don't waste Cancel on low-value 1-card Asia stack vs weak attack
                return 35.0

            if act == "defender_canon":
                # Playing Canon gives +1 to highest defense die (huge edge since defender wins ties!)
                if def_canon > 0:
                    return -10.0
                if prot_val >= 65.0 and atk_dice >= 2:
                    return 145.0
                if def_cards >= 2 and atk_dice >= 3:
                    return 130.0
                return 42.0

            if act == "defender_army":
                cnt = int(move.get("count", 0))
                def_dice = min(2, def_cards + cnt)
                exp_a, exp_d = expected_round_losses(atk_dice, def_dice, atk_canon, def_canon)
                # Value of preventing continent losses (extra Army cards beyond 2 dice still absorb casualties as shields!)
                shield_benefit = min(cnt, exp_d) * (prot_val * 0.45)
                # Base combat swing value
                combat_val = (exp_a - exp_d) * 55.0
                # Cost of spending each Army card
                card_cost = cnt * (24.0 if my_army_cnt <= 2 else 15.0)
                # Bonus for reaching 2 defense dice against 2+ attack dice
                reach_2d_bonus = 34.0 if (def_cards == 1 and cnt == 1 and atk_dice >= 2) else 0.0
                # Penalize over-committing more than 2 armies unless defending a critical stack
                over_pen = max(0, cnt - 1) * (22.0 if prot_val < 90.0 else 6.0)
                return 75.0 + combat_val + shield_benefit + reach_2d_bonus - card_cost - over_pen

        # ---- 3. ATTACKER ARMY COMMITMENT & COMBAT CANON ----
        if act in ("attacker_army", "attacker_canon"):
            atk = self.active_attack or {}
            src_c = str(atk.get("source_continent", "Asia"))
            tgt_c = str(atk.get("target_continent", "Asia"))
            def_id = int(atk.get("defender_id", 0))
            atk_p_cards = max(1, self.my_continents.get(src_c, 1))
            def_p = self._get_player_dict(def_id)
            def_cards = max(1, int((def_p.get("continents") or {}).get(tgt_c, 1)))
            def_strat_cnt = int(def_p.get("strategies_count", 0))
            est_def_dice = min(2, def_cards + (1 if (def_cards == 1 and def_strat_cnt >= 2) else 0))
            threat = self._opp_threat_score(def_p, tgt_c)
            atk_canon = int(atk.get("attacker_canon_bonus", 0))

            if act == "attacker_canon":
                if atk_canon > 0:
                    return -10.0
                # High value when rolling against 2 defense dice or disrupting a threatened opponent
                if threat >= 95.0 or (est_def_dice >= 2 and atk_p_cards + my_army_cnt >= 2):
                    return 155.0
                return 48.0

            if act == "attacker_army":
                cnt = int(move.get("count", 0))
                atk_dice = min(3, atk_p_cards + cnt)
                exp_a, exp_d = expected_round_losses(atk_dice, est_def_dice, atk_canon, 0)
                # Shield value of committed armies protecting our source continent
                src_prot = self._my_continent_protection_value(src_c)
                shield_val = min(cnt, exp_a) * (src_prot * 0.35)
                combat_val = (exp_d * (58.0 + threat * 0.25)) - (exp_a * (46.0 + src_prot * 0.2))
                card_cost = cnt * (22.0 if my_army_cnt <= 2 else 14.0)
                # Extra penalty for wasting armies beyond 3 dice when facing a weak 1-card defender
                wasted = max(0, (atk_p_cards + cnt) - 3)
                waste_pen = wasted * (28.0 if def_cards <= 1 and src_prot < 90.0 else 10.0)
                return 70.0 + combat_val + shield_val - card_cost - waste_pen

        # ---- 4. MULTI-ROUND CONTINUATION (`Attack`) ----
        if act in ("continue_attack", "stop_attack"):
            atk = self.active_attack or {}
            src_c = str(atk.get("source_continent", "Asia"))
            tgt_c = str(atk.get("target_continent", "Asia"))
            def_id = int(atk.get("defender_id", 0))
            atk_army = int(atk.get("attacker_army", 0))
            def_army = int(atk.get("defender_army", 0))
            atk_canon = int(atk.get("attacker_canon_bonus", 0))
            def_canon = int(atk.get("defender_canon_bonus", 0))
            my_c = self.my_continents.get(src_c, 0)
            def_p = self._get_player_dict(def_id)
            opp_c = int((def_p.get("continents") or {}).get(tgt_c, 1))
            atk_dice = min(3, max(1, my_c + atk_army))
            def_dice = min(2, max(1, opp_c + def_army))
            exp_a, exp_d = expected_round_losses(atk_dice, def_dice, atk_canon, def_canon)
            threat = self._opp_threat_score(def_p, tgt_c)
            src_prot = self._my_continent_protection_value(src_c)

            if act == "continue_attack":
                # Never keep rolling 1 die vs 2 dice unless opponent is at Match Point!
                if atk_dice == 1 and def_dice >= 2 and threat < 180.0:
                    return 20.0
                # Protect a near-domination source stack if we have no army shield left and odds aren't dominant
                if atk_army == 0 and src_prot >= 120.0 and exp_a > 0.65 and threat < 180.0:
                    return 35.0
                score = 72.0 + (exp_d - exp_a) * 85.0
                if opp_c == 1 and def_army == 0 and atk_dice >= 2:
                    score += 36.0  # Finish them!
                if threat >= 120.0:
                    score += 45.0
                return score
            else:
                return 68.0

        # ---- 5. SELECT ACTION: STRATEGY CARDS ----
        if act == "strategy":
            strat = move.get("strategy")
            if strat == "Backup":
                # Almost always play immediately before attacking so we can get domination coin or 3rd attack die!
                return 175.0
            if strat == "Destroy":
                tgt_id = int(move.get("target_index", 0))
                tgt_c = str(move.get("target_continent", ""))
                opp = self._get_player_dict(tgt_id)
                threat = self._opp_threat_score(opp, tgt_c)
                return 115.0 + threat * 0.55
            if strat == "Spy":
                tgt_id = int(move.get("target_index", 0))
                opp = self._get_player_dict(tgt_id)
                s_cnt = int(opp.get("strategies_count", 0))
                # Play Spy BEFORE attacking to steal opponent's Cancel/Army/Canon!
                return 142.0 if s_cnt >= 1 else 108.0
            if strat == "Bomb":
                tgt_id = int(move.get("target_index", 0))
                opp = self._get_player_dict(tgt_id)
                s_cnt = int(opp.get("strategies_count", 0))
                if s_cnt >= 2:
                    return 152.0  # Full 2-card strip!
                if s_cnt == 1:
                    return 102.0
                return 122.0  # Destroys 1 continent card when opponent has 0 strategies!
            if strat == "Expand":
                # Check if ignoring adjacency unlocks a high-value non-adjacent target (or we have no good adjacent attacks)
                best_non_adj = 0.0
                for opp in self._get_active_opponents():
                    opp_conts = opp.get("continents", {}) if isinstance(opp.get("continents"), dict) else {}
                    for c, cnt in opp_conts.items():
                        if int(cnt) > 0:
                            best_non_adj = max(best_non_adj, self._opp_threat_score(opp, c))
                if not self._has_good_adjacent_attack() and best_non_adj >= 60.0:
                    return 148.0
                if my_total_c <= 4 or best_non_adj >= 120.0:
                    return 134.0
                return 88.0
            if strat == "Army":
                if my_total_c == 0:
                    return 165.0
                min_gap_now = min(
                    (self._continent_domination_gap(self.my_continents, self.my_tokens, c) for c in ALL_CONTINENTS),
                    default=5,
                )
                if min_gap_now <= 1 and my_army_cnt >= 3:
                    return 126.0  # Push for immediate Domination Coin!
                return 96.0 if my_army_cnt >= 4 else 15.0

        # ---- 6. SELECT ACTION: DECLARE ATTACK ----
        if act == "declare_attack":
            src_c = str(move.get("source_continent"))
            tgt_c = str(move.get("target_continent"))
            tgt_idx = int(move.get("target_index", 0))
            my_c = self.my_continents.get(src_c, 0)
            opp = self._get_player_dict(tgt_idx)
            opp_c = int((opp.get("continents") or {}).get(tgt_c, 1))
            opp_s_cnt = int(opp.get("strategies_count", 0))

            # Estimate realistic dice if we commit up to 2 Army cards
            planned_army = min(my_army_cnt, max(0, 3 - my_c))
            atk_dice = min(3, my_c + planned_army)
            est_def_dice = min(2, opp_c + (1 if (opp_c == 1 and opp_s_cnt >= 2) else 0))
            has_canon = 1 if (self.pending_attacker_canon_bonus > 0 or self._count_my_strategy("Canon") > 0) else 0
            exp_a, exp_d = expected_round_losses(atk_dice, est_def_dice, has_canon, 0)

            threat = self._opp_threat_score(opp, tgt_c)
            src_prot = self._my_continent_protection_value(src_c)

            # Base EV score (Pass Turn is ~68.0 because passing gives 1 free Strategy card!)
            score = 68.0 + (exp_d - exp_a) * 84.0 + threat * 0.45

            # Finishing off a lone 1-card enemy continent is very clean
            if opp_c == 1 and atk_dice >= 2:
                score += 26.0

            # When the central Continent deck is running low/empty, combat returns cards to the deck and breaks stalemates!
            if self.continent_deck_count == 0:
                score += 36.0
            elif self.continent_deck_count <= 8:
                score += 16.0

            # Avoid risking our own near-domination continent unless we have army shields or opponent is at Match Point
            if src_prot >= 115.0 and planned_army == 0 and threat < 180.0 and self.continent_deck_count > 0:
                score -= 52.0
            elif atk_dice == 1 and has_canon == 0 and threat < 165.0 and self.continent_deck_count > 0:
                # Never take a losing 1-die coinflip (41.7% vs 1d, 25.5% vs 2d) instead of passing for a free Strategy card
                score -= 42.0 if opp_c == 1 else 68.0

            # Slight caution if defender has many hidden strategy cards (could hold Cancel/Army)
            if opp_s_cnt >= 3 and threat < 120.0:
                score -= 8.0

            return score

        # ---- 7. PASS TURN (Grants +1 Free Strategy Card if we didn't attack!) ----
        if act == "pass":
            # Passing without attacking gives a free Strategy card — strong play when no favorable attack exists!
            if not self.attacked_this_turn:
                return 72.0 if my_strat_cnt <= 2 else 64.0
            return 50.0

        return 0.0

    def compute_next_move(self) -> Any:
        legal_moves = self.get_legal_moves()
        if not legal_moves:
            return None
        if len(legal_moves) == 1:
            return legal_moves[0]

        # Level 1: casual (noise 22), Level 2 (Classic Rank): sharp & accurate (noise 3.5), Level 3: optimal (0)
        noise = 22.0 if self.level == 1 else (3.5 if self.level == 2 else 0.0)
        scored = [
            (self._score_move(m) + (random.uniform(-noise, noise) if noise > 0 else 0.0), m)
            for m in legal_moves
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def build_move_command(self, move: Any) -> dict:
        if not isinstance(move, dict):
            return {"id": "PassTurn", "data": {}}
        act = move.get("action")
        if act == "draw":
            return {"id": "DrawCard", "data": {"draw_type": int(move.get("draw_type", 3))}}
        if act == "declare_attack":
            return {
                "id": "DeclareAttack",
                "data": {
                    "source_continent": move["source_continent"],
                    "target_continent": move["target_continent"],
                    "target_index": int(move["target_index"]),
                },
            }
        if act == "attacker_army":
            return {"id": "AttackArmy", "data": {"count": int(move.get("count", 0))}}
        if act == "attacker_canon":
            return {"id": "UseStrategy", "data": {"strategy": "Canon"}}
        if act == "defender_army":
            return {"id": "DefenderArmy", "data": {"count": int(move.get("count", 0))}}
        if act == "defender_cancel":
            return {"id": "DefenderArmy", "data": {"count": 0, "cancel": True}}
        if act == "defender_canon":
            return {"id": "UseStrategy", "data": {"strategy": "Canon"}}
        if act == "continue_attack":
            return {"id": "Attack", "data": {}}
        if act == "stop_attack":
            return {"id": "CancelAttack", "data": {"stop": True}}
        if act == "strategy":
            payload: Dict[str, Any] = {"strategy": move.get("strategy")}
            if "target_index" in move and move["target_index"] is not None:
                payload["target_index"] = int(move["target_index"])
            if "target_continent" in move and move["target_continent"]:
                payload["target_continent"] = str(move["target_continent"])
            return {"id": "UseStrategy", "data": payload}
        return {"id": "PassTurn", "data": {}}

    def format_state(self) -> str:
        return (
            f"[Risk] Turn: P{self.current_turn} | State: {self.game_state} | "
            f"Tokens: {self.my_tokens} | Continents: {sum(self.my_continents.values())} | "
            f"Strategies: {len(self.my_strategies)}"
        )
