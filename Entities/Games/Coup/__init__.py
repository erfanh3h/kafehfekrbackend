import random
from typing import Any, Dict, List, Optional, Tuple

from Commons import commands
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass


COUP_ROLES = ("duke", "assassin", "captain", "ambassador", "contessa")
COUP_ACTIONS = ("income", "foreign_aid", "coup", "tax", "assassinate", "steal", "exchange")

ACTION_CLAIMED_ROLE = {
    "tax": "duke",
    "assassinate": "assassin",
    "steal": "captain",
    "exchange": "ambassador",
}

ACTION_ALLOWED_BLOCKS = {
    "foreign_aid": ("duke",),
    "assassinate": ("contessa",),
    "steal": ("captain", "ambassador"),
}


class CoupGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count: int = 2):
        super().__init__(send_data_function, players_count)
        self.players_count = max(2, min(4, int(players_count)))
        self.active_player_indexes: List[int] = [i for i in range(1, self.players_count + 1)]
        self.eliminated_order: List[int] = []
        self.court_deck: List[Dict[str, Any]] = []
        self.hands: Dict[int, List[Dict[str, Any]]] = {
            i: [] for i in range(1, self.players_count + 1)
        }
        self.coins: Dict[int, int] = {i: 2 for i in range(1, self.players_count + 1)}
        self._next_uid: int = 1

        # Authoritative Coup state machine
        self.phase: str = "action"  # action | challenge_action | block_action | challenge_block | lose_influence | exchange | finished
        self.state_seq: int = 1
        self.current_turn: int = 1

        self.pending_action: Optional[str] = None
        self.pending_actor: int = 0
        self.pending_target: int = 0
        self.pending_claimed_role: str = ""
        self.pending_blocker: int = 0
        self.pending_block_role: str = ""
        self.eligible_responders: List[int] = []
        self.passed_players: List[int] = []

        self.pending_loss_player: int = 0
        self.loss_reason: str = ""
        self.after_loss_step: str = "end_turn"

        self.exchange_pool: List[Dict[str, Any]] = []
        self.exchange_keep_count: int = 0

        self.last_event: Optional[Dict[str, Any]] = None
        self._build_and_deal()

    def _create_card(self, role: str) -> Dict[str, Any]:
        uid = self._next_uid
        self._next_uid += 1
        return {
            "uid": uid,
            "role": role,
            "revealed": False,
        }

    def _build_and_deal(self):
        self.court_deck = []
        for role in COUP_ROLES:
            for _ in range(3):
                self.court_deck.append(self._create_card(role))
        random.shuffle(self.court_deck)

        self.hands = {i: [] for i in range(1, self.players_count + 1)}
        self.coins = {i: 2 for i in range(1, self.players_count + 1)}
        for _ in range(2):
            for pid in range(1, self.players_count + 1):
                self.hands[pid].append(self._draw_deck_card())

        self.active_player_indexes = [i for i in range(1, self.players_count + 1)]
        self.eliminated_order = []
        self.current_turn = 1
        self.phase = "action"
        self.state_seq = 1
        self._reset_pending_fields()

    def _draw_deck_card(self) -> Dict[str, Any]:
        if not self.court_deck:
            # Safety fallback if ever exhausted (should never happen with 15 cards & <=8 dealt)
            self.court_deck.append(self._create_card(random.choice(COUP_ROLES)))
        card = self.court_deck.pop()
        card["revealed"] = False
        return card

    def _reset_pending_fields(self):
        self.pending_action = None
        self.pending_actor = 0
        self.pending_target = 0
        self.pending_claimed_role = ""
        self.pending_blocker = 0
        self.pending_block_role = ""
        self.eligible_responders = []
        self.passed_players = []
        self.pending_loss_player = 0
        self.loss_reason = ""
        self.after_loss_step = "end_turn"
        self.exchange_pool = []
        self.exchange_keep_count = 0

    def _bump_seq(self):
        self.state_seq += 1

    def get_alive_cards(self, gamer_id: int) -> List[Dict[str, Any]]:
        return [c for c in self.hands.get(gamer_id, []) if not c.get("revealed", False)]

    def get_alive_card_count(self, gamer_id: int) -> int:
        return len(self.get_alive_cards(gamer_id))

    def _has_hidden_role(self, gamer_id: int, role: str) -> bool:
        for c in self.hands.get(gamer_id, []):
            if not c.get("revealed", False) and c.get("role") == role:
                return True
        return False

    def _swap_proven_card(self, gamer_id: int, role: str) -> Optional[Dict[str, Any]]:
        hand = self.hands.get(gamer_id, [])
        for idx, c in enumerate(hand):
            if not c.get("revealed", False) and c.get("role") == role:
                proven = hand.pop(idx)
                proven["revealed"] = False
                self.court_deck.append(proven)
                random.shuffle(self.court_deck)
                replacement = self._draw_deck_card()
                hand.insert(idx, replacement)
                return replacement
        return None

    def _eliminate_player(self, gamer_id: int):
        if gamer_id in self.active_player_indexes:
            self.active_player_indexes.remove(gamer_id)
        if gamer_id not in self.eliminated_order:
            self.eliminated_order.append(gamer_id)
        for c in self.hands.get(gamer_id, []):
            c["revealed"] = True

        if len(self.active_player_indexes) == 1:
            survivor = self.active_player_indexes[0]
            self.rank1 = survivor
            if self.rank2 is None:
                self.rank2 = gamer_id
            self.is_game_finished = True
            self.phase = "finished"

    def _clear_pending_and_advance_turn(self):
        self._reset_pending_fields()
        if self.is_game_finished or len(self.active_player_indexes) <= 1:
            self.phase = "finished"
            if len(self.active_player_indexes) == 1 and self.rank1 is None:
                self.rank1 = self.active_player_indexes[0]
                self.is_game_finished = True
            return
        self.change_turn()
        self.phase = "action"

    def change_turn(self):
        self.is_current_turn_played = False
        super().change_turn()

    def get_game_winner(self):
        if self.rank1 is not None:
            return self.rank1
        return super().get_game_winner()

    def check_end_game(self) -> Tuple[bool, int]:
        if self.is_game_finished or (self.rank1 is not None and self.rank2 is not None):
            return True, (self.rank1 if self.rank1 is not None else 0)
        return False, 0

    def _apply_surrender_sync(self, gamer_id: int) -> bool:
        if gamer_id not in self.active_player_indexes:
            return self.is_game_finished

        was_turn = (self.current_turn == gamer_id)
        was_responder = (gamer_id in self.eligible_responders)
        was_loss_player = (self.phase == "lose_influence" and self.pending_loss_player == gamer_id)
        was_target = (self.pending_target == gamer_id)
        was_actor = (self.pending_actor == gamer_id)
        was_blocker = (self.pending_blocker == gamer_id)

        next_turn_candidate = self.current_turn
        if was_turn and len(self.active_player_indexes) > 1:
            for step in range(1, self.players_count + 1):
                cand = ((gamer_id - 1 + step) % self.players_count) + 1
                if cand != gamer_id and cand in self.active_player_indexes:
                    next_turn_candidate = cand
                    break

        self._eliminate_player(gamer_id)

        if self.is_game_finished:
            self._bump_seq()
            return True

        # Clean up any active phase referencing the surrendering player
        if was_actor or was_blocker:
            # Cancel current pending move and advance from next alive player
            self._reset_pending_fields()
            self.current_turn = next_turn_candidate if next_turn_candidate in self.active_player_indexes else self.active_player_indexes[0]
            self.phase = "action"
        elif was_loss_player:
            self._execute_after_loss(self.after_loss_step)
        elif was_target and self.phase in ("challenge_action", "block_action"):
            self._reset_pending_fields()
            self.change_turn()
            self.phase = "action"
        elif was_responder and self.phase in ("challenge_action", "block_action", "challenge_block"):
            self.eligible_responders = [p for p in self.eligible_responders if p != gamer_id]
            self.passed_players = [p for p in self.passed_players if p != gamer_id]
            if set(self.passed_players) >= set(self.eligible_responders):
                self._on_all_passed()
        elif was_turn and self.phase == "action":
            self.current_turn = next_turn_candidate if next_turn_candidate in self.active_player_indexes else self.active_player_indexes[0]

        self._bump_seq()
        return self.is_game_finished or was_turn or was_actor or was_blocker or was_loss_player or was_target or was_responder

    def check_authority(self, data: Dict[str, Any], gamer_id: int) -> bool:
        if self.is_game_finished or gamer_id not in self.active_player_indexes:
            return False

        cmd_id = data.get("id")
        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(payload, dict):
            payload = {}

        if cmd_id == commands.Coup_Action:
            if self.phase != "action" or gamer_id != self.current_turn:
                return False
            action = str(payload.get("action", "")).strip().lower()
            if action not in COUP_ACTIONS:
                return False
            my_coins = int(self.coins.get(gamer_id, 0))
            if my_coins >= 10 and action != "coup":
                return False
            if action == "coup" and my_coins < 7:
                return False
            if action == "assassinate" and my_coins < 3:
                return False
            if action in ("coup", "assassinate", "steal"):
                target_id = int(payload.get("target_id", payload.get("target", 0)) or 0)
                if target_id == gamer_id or target_id not in self.active_player_indexes:
                    return False
            return True

        if cmd_id == commands.Coup_Challenge:
            if self.phase not in ("challenge_action", "challenge_block"):
                return False
            return gamer_id in self.eligible_responders and gamer_id not in self.passed_players

        if cmd_id == commands.Coup_Block:
            if self.phase != "block_action":
                return False
            if gamer_id not in self.eligible_responders or gamer_id in self.passed_players:
                return False
            allowed = ACTION_ALLOWED_BLOCKS.get(self.pending_action or "", ())
            if not allowed:
                return False
            block_role = str(payload.get("block_role", payload.get("role", allowed[0]))).strip().lower()
            return block_role in allowed

        if cmd_id == commands.Coup_Pass:
            if self.phase not in ("challenge_action", "block_action", "challenge_block"):
                return False
            return gamer_id in self.eligible_responders and gamer_id not in self.passed_players

        if cmd_id == commands.Coup_Lose_Influence:
            if self.phase != "lose_influence" or gamer_id != self.pending_loss_player:
                return False
            card_idx = self._resolve_lose_card_index(gamer_id, payload)
            return card_idx is not None

        if cmd_id == commands.Coup_Exchange:
            if self.phase != "exchange" or gamer_id != self.current_turn:
                return False
            keep_indices = payload.get("keep_indices", payload.get("indices", []))
            return self._validate_exchange_indices(keep_indices)

        return False

    def _resolve_lose_card_index(self, gamer_id: int, payload: Dict[str, Any]) -> Optional[int]:
        hand = self.hands.get(gamer_id, [])
        if "card_uid" in payload and payload["card_uid"] is not None:
            try:
                uid = int(payload["card_uid"])
                for idx, c in enumerate(hand):
                    if int(c.get("uid", -1)) == uid and not c.get("revealed", False):
                        return idx
            except (TypeError, ValueError):
                return None
        if "card_index" in payload and payload["card_index"] is not None:
            try:
                idx = int(payload["card_index"])
                if 0 <= idx < len(hand) and not hand[idx].get("revealed", False):
                    return idx
            except (TypeError, ValueError):
                return None
        return None

    def _validate_exchange_indices(self, keep_indices: Any) -> bool:
        if not isinstance(keep_indices, list):
            return False
        if len(keep_indices) != self.exchange_keep_count:
            return False
        try:
            ints = [int(x) for x in keep_indices]
        except (TypeError, ValueError):
            return False
        if len(set(ints)) != len(ints):
            return False
        return all(0 <= i < len(self.exchange_pool) for i in ints)

    async def recieve_data(self, command_type: str, data: Dict[str, Any], gamer_id: int) -> Dict[str, Any]:
        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(payload, dict):
            payload = {}

        if command_type == commands.Coup_Action:
            action = str(payload.get("action", "")).strip().lower()
            target_id = int(payload.get("target_id", payload.get("target", 0)) or 0)
            return self.submit_action(gamer_id, action, target_id)

        if command_type == commands.Coup_Challenge:
            return self.submit_challenge(gamer_id)

        if command_type == commands.Coup_Block:
            allowed = ACTION_ALLOWED_BLOCKS.get(self.pending_action or "", ("duke",))
            block_role = str(payload.get("block_role", payload.get("role", allowed[0]))).strip().lower()
            return self.submit_block(gamer_id, block_role)

        if command_type == commands.Coup_Pass:
            return self.submit_pass(gamer_id)

        if command_type == commands.Coup_Lose_Influence:
            idx = self._resolve_lose_card_index(gamer_id, payload)
            if idx is None:
                return {}
            return self.submit_lose_influence(gamer_id, idx)

        if command_type == commands.Coup_Exchange:
            keep_indices = [int(x) for x in payload.get("keep_indices", payload.get("indices", []))]
            return self.submit_exchange(gamer_id, keep_indices)

        return {}

    def _trigger_influence_loss(self, target_id: int, reason: str, after_loss_step: str) -> Dict[str, Any]:
        alive_indices = [i for i, c in enumerate(self.hands.get(target_id, [])) if not c.get("revealed", False)]
        if not alive_indices:
            self._execute_after_loss(after_loss_step)
            return {"target_id": target_id, "auto_revealed": False, "lost_role": None, "eliminated": True}

        if len(alive_indices) == 1:
            last_idx = alive_indices[0]
            card = self.hands[target_id][last_idx]
            card["revealed"] = True
            lost_role = card["role"]
            self._eliminate_player(target_id)
            if not self.is_game_finished:
                self._execute_after_loss(after_loss_step)
            return {
                "target_id": target_id,
                "auto_revealed": True,
                "lost_role": lost_role,
                "card_index": last_idx,
                "eliminated": True,
            }

        # Player has 2 alive cards -> let them choose which influence to lose
        self.phase = "lose_influence"
        self.pending_loss_player = target_id
        self.loss_reason = reason
        self.after_loss_step = after_loss_step
        return {
            "target_id": target_id,
            "auto_revealed": False,
            "lost_role": None,
            "eliminated": False,
        }

    def _execute_after_loss(self, step: str):
        if self.is_game_finished:
            self.phase = "finished"
            return
        if step == "continue_to_block":
            if self.pending_action in ("assassinate", "steal") and self.pending_target in self.active_player_indexes:
                self.phase = "block_action"
                self.pending_loss_player = 0
                self.loss_reason = ""
                self.eligible_responders = [self.pending_target]
                self.passed_players = []
            else:
                self._clear_pending_and_advance_turn()
        elif step == "resolve_action":
            self.pending_loss_player = 0
            self.loss_reason = ""
            self._resolve_pending_action()
        else:
            self._clear_pending_and_advance_turn()

    def _resolve_pending_action(self) -> Dict[str, Any]:
        action = self.pending_action
        actor = self.pending_actor
        target = self.pending_target

        if action == "foreign_aid":
            self.coins[actor] = int(self.coins.get(actor, 0)) + 2
            ev = {"event": "action_resolved", "action": "foreign_aid", "actor_id": actor, "coins_delta": 2}
            self._clear_pending_and_advance_turn()
            return ev

        if action == "tax":
            self.coins[actor] = int(self.coins.get(actor, 0)) + 3
            ev = {"event": "action_resolved", "action": "tax", "actor_id": actor, "coins_delta": 3}
            self._clear_pending_and_advance_turn()
            return ev

        if action == "steal":
            stolen = 0
            if target in self.active_player_indexes:
                t_coins = int(self.coins.get(target, 0))
                stolen = min(2, t_coins)
                self.coins[target] = t_coins - stolen
                self.coins[actor] = int(self.coins.get(actor, 0)) + stolen
            ev = {
                "event": "action_resolved",
                "action": "steal",
                "actor_id": actor,
                "target_id": target,
                "stolen": stolen,
            }
            self._clear_pending_and_advance_turn()
            return ev

        if action == "assassinate":
            if target in self.active_player_indexes:
                loss_info = self._trigger_influence_loss(target, "assassinate", "end_turn")
                return {
                    "event": "assassinate_hit",
                    "action": "assassinate",
                    "actor_id": actor,
                    "target_id": target,
                    "loss": loss_info,
                }
            self._clear_pending_and_advance_turn()
            return {"event": "action_resolved", "action": "assassinate", "actor_id": actor, "target_id": target}

        if action == "exchange":
            alive = [dict(c) for c in self.hands.get(actor, []) if not c.get("revealed", False)]
            drawn = [self._draw_deck_card(), self._draw_deck_card()]
            self.exchange_pool = alive + drawn
            self.exchange_keep_count = len(alive)
            self.phase = "exchange"
            return {
                "event": "exchange_started",
                "action": "exchange",
                "actor_id": actor,
                "keep_count": self.exchange_keep_count,
            }

        self._clear_pending_and_advance_turn()
        return {"event": "action_resolved", "action": action, "actor_id": actor}

    def _on_all_passed(self) -> Dict[str, Any]:
        if self.phase == "challenge_action":
            if self.pending_action in ("assassinate", "steal"):
                if self.pending_target in self.active_player_indexes:
                    self.phase = "block_action"
                    self.eligible_responders = [self.pending_target]
                    self.passed_players = []
                    return {
                        "event": "awaiting_block",
                        "action": self.pending_action,
                        "actor_id": self.pending_actor,
                        "target_id": self.pending_target,
                    }
                self._clear_pending_and_advance_turn()
                return {"event": "action_resolved", "action": self.pending_action}
            return self._resolve_pending_action()

        if self.phase == "block_action":
            return self._resolve_pending_action()

        if self.phase == "challenge_block":
            ev = {
                "event": "block_succeeded",
                "action": self.pending_action,
                "actor_id": self.pending_actor,
                "blocker_id": self.pending_blocker,
                "block_role": self.pending_block_role,
            }
            self._clear_pending_and_advance_turn()
            return ev

        return {}

    def submit_action(self, gamer_id: int, action: str, target_id: int = 0) -> Dict[str, Any]:
        self._reset_pending_fields()
        self.pending_actor = gamer_id
        self.pending_action = action
        self.pending_target = target_id

        if action == "income":
            self.coins[gamer_id] = int(self.coins.get(gamer_id, 0)) + 1
            ev = {
                "event": "action_declared",
                "action": "income",
                "actor_id": gamer_id,
                "resolved": True,
            }
            self._clear_pending_and_advance_turn()
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "foreign_aid":
            self.phase = "block_action"
            self.eligible_responders = [p for p in self.active_player_indexes if p != gamer_id]
            self.passed_players = []
            ev = {
                "event": "action_declared",
                "action": "foreign_aid",
                "actor_id": gamer_id,
                "resolved": False,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "coup":
            self.coins[gamer_id] = max(0, int(self.coins.get(gamer_id, 0)) - 7)
            loss_info = self._trigger_influence_loss(target_id, "coup", "end_turn")
            ev = {
                "event": "coup_launched",
                "action": "coup",
                "actor_id": gamer_id,
                "target_id": target_id,
                "loss": loss_info,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        # Claimed role actions (tax, assassinate, steal, exchange)
        claimed_role = ACTION_CLAIMED_ROLE[action]
        self.pending_claimed_role = claimed_role
        if action == "assassinate":
            self.coins[gamer_id] = max(0, int(self.coins.get(gamer_id, 0)) - 3)

        self.phase = "challenge_action"
        self.eligible_responders = [p for p in self.active_player_indexes if p != gamer_id]
        self.passed_players = []
        ev = {
            "event": "action_declared",
            "action": action,
            "actor_id": gamer_id,
            "target_id": target_id,
            "claimed_role": claimed_role,
            "resolved": False,
        }
        self._bump_seq()
        self.last_event = ev
        return ev

    def submit_challenge(self, challenger_id: int) -> Dict[str, Any]:
        if self.phase == "challenge_action":
            actor = self.pending_actor
            role = self.pending_claimed_role
            has_role = self._has_hidden_role(actor, role)
            if has_role:
                self._swap_proven_card(actor, role)
                next_step = "continue_to_block" if self.pending_action in ("assassinate", "steal") else "resolve_action"
                loss_info = self._trigger_influence_loss(challenger_id, "failed_challenge", next_step)
                ev = {
                    "event": "challenge_result",
                    "target_phase": "challenge_action",
                    "challenger_id": challenger_id,
                    "claimed_by": actor,
                    "claimed_role": role,
                    "challenge_won": False,  # challenger lost!
                    "loss": loss_info,
                }
            else:
                if self.pending_action == "assassinate":
                    self.coins[actor] = int(self.coins.get(actor, 0)) + 3
                loss_info = self._trigger_influence_loss(actor, "bluff_caught", "end_turn")
                ev = {
                    "event": "challenge_result",
                    "target_phase": "challenge_action",
                    "challenger_id": challenger_id,
                    "claimed_by": actor,
                    "claimed_role": role,
                    "challenge_won": True,  # challenger caught bluff!
                    "loss": loss_info,
                }
            self._bump_seq()
            self.last_event = ev
            return ev

        if self.phase == "challenge_block":
            blocker = self.pending_blocker
            role = self.pending_block_role
            has_role = self._has_hidden_role(blocker, role)
            if has_role:
                self._swap_proven_card(blocker, role)
                loss_info = self._trigger_influence_loss(challenger_id, "failed_challenge", "end_turn")
                ev = {
                    "event": "challenge_result",
                    "target_phase": "challenge_block",
                    "challenger_id": challenger_id,
                    "claimed_by": blocker,
                    "claimed_role": role,
                    "challenge_won": False,  # block holds!
                    "loss": loss_info,
                }
            else:
                loss_info = self._trigger_influence_loss(blocker, "bluff_caught", "resolve_action")
                ev = {
                    "event": "challenge_result",
                    "target_phase": "challenge_block",
                    "challenger_id": challenger_id,
                    "claimed_by": blocker,
                    "claimed_role": role,
                    "challenge_won": True,  # blocker caught bluffing!
                    "loss": loss_info,
                }
            self._bump_seq()
            self.last_event = ev
            return ev

        return {}

    def submit_block(self, blocker_id: int, block_role: str) -> Dict[str, Any]:
        self.pending_blocker = blocker_id
        self.pending_block_role = block_role
        self.phase = "challenge_block"
        self.eligible_responders = [p for p in self.active_player_indexes if p != blocker_id]
        self.passed_players = []
        ev = {
            "event": "block_declared",
            "action": self.pending_action,
            "actor_id": self.pending_actor,
            "blocker_id": blocker_id,
            "block_role": block_role,
        }
        self._bump_seq()
        self.last_event = ev
        return ev

    def submit_pass(self, gamer_id: int) -> Dict[str, Any]:
        if gamer_id not in self.passed_players:
            self.passed_players.append(gamer_id)
        if set(self.passed_players) >= set(self.eligible_responders):
            ev = self._on_all_passed()
        else:
            ev = {
                "event": "player_passed",
                "gamer_id": gamer_id,
                "phase": self.phase,
                "remaining": [p for p in self.eligible_responders if p not in self.passed_players],
            }
        self._bump_seq()
        self.last_event = ev
        return ev

    def submit_lose_influence(self, gamer_id: int, card_index: int) -> Dict[str, Any]:
        hand = self.hands.get(gamer_id, [])
        if not (0 <= card_index < len(hand)) or hand[card_index].get("revealed", False):
            return {}
        hand[card_index]["revealed"] = True
        lost_role = hand[card_index]["role"]
        remaining_alive = self.get_alive_card_count(gamer_id)
        eliminated = (remaining_alive == 0)
        if eliminated:
            self._eliminate_player(gamer_id)

        step = self.after_loss_step
        if not self.is_game_finished:
            self._execute_after_loss(step)

        ev = {
            "event": "influence_lost",
            "gamer_id": gamer_id,
            "card_index": card_index,
            "lost_role": lost_role,
            "eliminated": eliminated,
            "reason": self.loss_reason,
        }
        self._bump_seq()
        self.last_event = ev
        return ev

    def submit_exchange(self, gamer_id: int, keep_indices: List[int]) -> Dict[str, Any]:
        if not self._validate_exchange_indices(keep_indices):
            return {}
        kept_set = set(keep_indices)
        kept_cards = []
        returned_cards = []
        for idx, card in enumerate(self.exchange_pool):
            c_copy = dict(card)
            c_copy["revealed"] = False
            if idx in kept_set:
                kept_cards.append(c_copy)
            else:
                returned_cards.append(c_copy)

        # Preserve already-revealed dead cards and replace unrevealed cards
        dead_cards = [c for c in self.hands.get(gamer_id, []) if c.get("revealed", False)]
        self.hands[gamer_id] = dead_cards + kept_cards
        self.court_deck.extend(returned_cards)
        random.shuffle(self.court_deck)

        ev = {
            "event": "exchange_completed",
            "actor_id": gamer_id,
            "kept_count": len(kept_cards),
        }
        self._clear_pending_and_advance_turn()
        self._bump_seq()
        self.last_event = ev
        return ev

    def auto_resolve_timeout(self) -> Dict[str, Any]:
        """Resolves current phase safely when timer expires."""
        if self.is_game_finished:
            return {}

        if self.phase == "action":
            cur = self.current_turn
            if int(self.coins.get(cur, 0)) >= 10:
                opponents = [p for p in self.active_player_indexes if p != cur]
                target = opponents[0] if opponents else 0
                if target > 0:
                    return self.submit_action(cur, "coup", target)
            return self.submit_action(cur, "income", 0)

        if self.phase in ("challenge_action", "block_action", "challenge_block"):
            ev = self._on_all_passed()
            self._bump_seq()
            self.last_event = ev
            return ev

        if self.phase == "lose_influence":
            target = self.pending_loss_player
            alive = [i for i, c in enumerate(self.hands.get(target, [])) if not c.get("revealed", False)]
            if alive:
                return self.submit_lose_influence(target, alive[0])
            self._execute_after_loss(self.after_loss_step)
            self._bump_seq()
            return {"event": "timeout_loss_skipped"}

        if self.phase == "exchange":
            actor = self.current_turn
            keep_indices = list(range(self.exchange_keep_count))
            return self.submit_exchange(actor, keep_indices)

        return {}

    def get_public_players(self) -> List[Dict[str, Any]]:
        players = []
        for pid in range(1, self.players_count + 1):
            hand = self.hands.get(pid, [])
            cards_pub = [
                {
                    "uid": int(c["uid"]),
                    "revealed": bool(c.get("revealed", False)),
                    "role": c["role"] if c.get("revealed", False) else None,
                }
                for c in hand
            ]
            players.append({
                "gamer_id": pid,
                "coins": int(self.coins.get(pid, 0)),
                "alive": pid in self.active_player_indexes,
                "alive_cards": sum(1 for c in hand if not c.get("revealed", False)),
                "cards": cards_pub,
            })
        return players

    def get_game_data(self) -> Dict[str, Any]:
        return {
            "game_type": "Coup",
            "players_count": self.players_count,
            "active_player_indexes": list(self.active_player_indexes),
            "eliminated_order": list(self.eliminated_order),
            "current_turn": self.current_turn,
            "turn": self.current_turn,
            "phase": self.phase,
            "state_seq": self.state_seq,
            "deck_remaining": len(self.court_deck),
            "players": self.get_public_players(),
            "pending_action": self.pending_action,
            "pending_actor": self.pending_actor,
            "pending_target": self.pending_target,
            "pending_claimed_role": self.pending_claimed_role,
            "pending_blocker": self.pending_blocker,
            "pending_block_role": self.pending_block_role,
            "eligible_responders": list(self.eligible_responders),
            "passed_players": list(self.passed_players),
            "pending_loss_player": self.pending_loss_player,
            "loss_reason": self.loss_reason,
            "exchange_keep_count": self.exchange_keep_count,
            "last_event": dict(self.last_event) if isinstance(self.last_event, dict) else None,
            "rank1": self.rank1,
            "rank2": self.rank2,
            "is_game_finished": self.is_game_finished,
        }

    def get_user_private_game_data(self, gamer_id: int) -> Dict[str, Any]:
        my_cards = [dict(c) for c in self.hands.get(gamer_id, [])]
        ex_cards = []
        if self.phase == "exchange" and self.current_turn == gamer_id:
            ex_cards = [dict(c) for c in self.exchange_pool]
        data = self.get_game_data()
        data.update({
            "user": gamer_id,
            "index": gamer_id,
            "gamer_id": gamer_id,
            "my_cards": my_cards,
            "exchange_cards": ex_cards,
        })
        return data
