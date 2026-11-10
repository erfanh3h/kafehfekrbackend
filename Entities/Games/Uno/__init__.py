import random
from typing import Any, Dict, List, Optional

from Commons import commands
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass


UNO_COLORS = ("red", "blue", "green", "yellow")
UNO_NUMBER_VALUES = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
UNO_ACTION_VALUES = ("skip", "reverse", "draw2")
UNO_WILD_VALUES = ("wild", "wild_draw4")


def get_card_points(card: Dict[str, Any]) -> int:
    val = str(card.get("value", "0"))
    if val.isdigit():
        return int(val)
    if val in UNO_ACTION_VALUES:
        return 20
    if val in UNO_WILD_VALUES:
        return 50
    return 10


class UnoGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count: int = 2):
        super().__init__(send_data_function, players_count)
        self.active_player_indexes = [i for i in range(1, self.players_count + 1)]
        self.direction: int = 1  # 1 = clockwise (1->2->3->4), -1 = counter-clockwise
        self.draw_pile: List[Dict[str, Any]] = []
        self.discard_pile: List[Dict[str, Any]] = []
        self.hands: Dict[int, List[Dict[str, Any]]] = {
            i: [] for i in range(1, self.players_count + 1)
        }
        self.current_color: str = "red"
        self.current_value: str = "0"
        self.has_drawn_this_turn: bool = False
        self.last_drawn_card: Optional[Dict[str, Any]] = None
        self.uno_called: Dict[int, bool] = {
            i: False for i in range(1, self.players_count + 1)
        }
        self._next_uid: int = 1
        self.last_action: Optional[Dict[str, Any]] = None
        self._build_and_deal()

    def _create_card(self, color: str, value: str) -> Dict[str, Any]:
        uid = self._next_uid
        self._next_uid += 1
        return {
            "uid": uid,
            "color": color,
            "value": value,
        }

    def _build_deck(self) -> List[Dict[str, Any]]:
        deck: List[Dict[str, Any]] = []
        for color in UNO_COLORS:
            deck.append(self._create_card(color, "0"))
            for val in UNO_NUMBER_VALUES[1:] + UNO_ACTION_VALUES:
                deck.append(self._create_card(color, val))
                deck.append(self._create_card(color, val))
        for _ in range(4):
            deck.append(self._create_card("wild", "wild"))
            deck.append(self._create_card("wild", "wild_draw4"))
        random.shuffle(deck)
        return deck

    def _build_and_deal(self):
        self.draw_pile = self._build_deck()
        self.discard_pile = []
        self.hands = {i: [] for i in range(1, self.players_count + 1)}

        for _ in range(7):
            for pid in range(1, self.players_count + 1):
                self.hands[pid].append(self._draw_one_card())

        # Ensure initial top discard card is a colored number card (0..9)
        top_card = None
        for idx, card in enumerate(self.draw_pile):
            if card["color"] in UNO_COLORS and card["value"] in UNO_NUMBER_VALUES:
                top_card = self.draw_pile.pop(idx)
                break
        if top_card is None:
            top_card = self._create_card("red", "5")

        self.discard_pile.append(top_card)
        self.current_color = top_card["color"]
        self.current_value = top_card["value"]
        self.direction = 1
        self.current_turn = 1
        self.has_drawn_this_turn = False
        self.last_drawn_card = None

    def _draw_one_card(self) -> Dict[str, Any]:
        if not self.draw_pile:
            if len(self.discard_pile) > 1:
                recycle = self.discard_pile[:-1]
                self.discard_pile = [self.discard_pile[-1]]
                for c in recycle:
                    if c["value"] in UNO_WILD_VALUES:
                        c["color"] = "wild"
                random.shuffle(recycle)
                self.draw_pile.extend(recycle)
            else:
                self.draw_pile = self._build_deck()
        return self.draw_pile.pop()

    def is_card_playable(self, card: Dict[str, Any]) -> bool:
        if not isinstance(card, dict):
            return False
        c_color = str(card.get("color", ""))
        c_value = str(card.get("value", ""))
        if c_color == "wild" or c_value in UNO_WILD_VALUES:
            return True
        if c_color == self.current_color:
            return True
        if c_value == self.current_value:
            return True
        return False

    def get_playable_card_uids(self, gamer_id: int) -> List[int]:
        hand = self.hands.get(gamer_id, [])
        return [int(c["uid"]) for c in hand if self.is_card_playable(c)]

    def _find_card_in_hand(self, gamer_id: int, card_uid: int) -> Optional[Dict[str, Any]]:
        for c in self.hands.get(gamer_id, []):
            if int(c.get("uid", -1)) == int(card_uid):
                return c
        return None

    def _best_color_for_player(self, gamer_id: int) -> str:
        counts = {c: 0 for c in UNO_COLORS}
        for card in self.hands.get(gamer_id, []):
            col = card.get("color")
            if col in counts:
                counts[col] += 1
        best = max(UNO_COLORS, key=lambda c: counts[c])
        return best if counts[best] > 0 else random.choice(UNO_COLORS)

    def _next_active_player(self, from_player: int, steps: int = 1) -> int:
        if not self.active_player_indexes:
            return from_player
        active = list(self.active_player_indexes)
        n = len(active)
        if n == 1:
            return active[0]
        if from_player in active:
            idx = active.index(from_player)
        else:
            idx = 0
        target_idx = (idx + steps * self.direction) % n
        return active[target_idx]

    def change_turn(self, steps: int = 1):
        self.is_current_turn_played = False
        self.has_drawn_this_turn = False
        self.last_drawn_card = None
        if not self.active_player_indexes:
            return
        self.current_turn = self._next_active_player(self.current_turn, steps=steps)

    def _hand_points(self, gamer_id: int) -> int:
        return sum(get_card_points(c) for c in self.hands.get(gamer_id, []))

    def _assign_winner_and_runner_up(self, winner_id: int):
        if self.rank1 is None:
            self.rank1 = winner_id
        if self.rank2 is None:
            candidates = [
                pid for pid in self.active_player_indexes if pid != self.rank1
            ]
            if not candidates:
                candidates = [
                    pid for pid in range(1, self.players_count + 1) if pid != self.rank1
                ]
            if candidates:
                candidates.sort(
                    key=lambda pid: (len(self.hands.get(pid, [])), self._hand_points(pid), pid)
                )
                self.rank2 = candidates[0]
        if self.rank2 is None:
            self.rank2 = 2 if self.rank1 == 1 else 1
        self.is_game_finished = True

    def _apply_surrender_sync(self, gamer_id: int) -> bool:
        was_turn = (self.current_turn == gamer_id)
        next_turn_candidate = self._next_active_player(gamer_id, steps=1) if was_turn else self.current_turn
        was_finished = super()._apply_surrender_sync(gamer_id)
        if was_finished and self.rank1 is not None and self.rank2 is None:
            self._assign_winner_and_runner_up(self.rank1)
        elif not self.is_game_finished and was_turn and self.active_player_indexes:
            self.current_turn = (
                next_turn_candidate
                if next_turn_candidate in self.active_player_indexes
                else self.active_player_indexes[0]
            )
            self.has_drawn_this_turn = False
        return self.is_game_finished

    def check_authority(self, data: Dict[str, Any], gamer_id: int) -> bool:
        if self.is_game_finished or gamer_id not in self.active_player_indexes:
            return False
        cmd_id = data.get("id")
        payload = data.get("data") if isinstance(data.get("data"), dict) else data

        if cmd_id == commands.Call_Uno:
            return len(self.hands.get(gamer_id, [])) <= 2

        if gamer_id != self.current_turn:
            return False

        if cmd_id in (commands.Play_Card, commands.Select_Peace):
            card_uid = payload.get("card_uid", payload.get("uid", payload.get("index")))
            if card_uid is None:
                return False
            card = self._find_card_in_hand(gamer_id, int(card_uid))
            if card is None:
                return False
            return self.is_card_playable(card)

        if cmd_id == commands.Draw_Card:
            return not self.has_drawn_this_turn

        if cmd_id == commands.Pass_Turn:
            if self.has_drawn_this_turn:
                return True
            return len(self.get_playable_card_uids(gamer_id)) == 0

        return False

    async def recieve_data(self, command_type: str, data: Dict[str, Any], gamer_id: int) -> Dict[str, Any]:
        payload = data.get("data") if isinstance(data.get("data"), dict) else data

        if command_type == commands.Call_Uno:
            self.uno_called[gamer_id] = True
            return {
                "action": "call_uno",
                "gamer_id": gamer_id,
            }

        if command_type in (commands.Play_Card, commands.Select_Peace):
            card_uid = int(payload.get("card_uid", payload.get("uid", payload.get("index"))))
            chosen_color = str(payload.get("chosen_color", payload.get("color", ""))).strip().lower()
            return self.play_card(gamer_id, card_uid, chosen_color)

        if command_type == commands.Draw_Card:
            return self.draw_card_for_turn(gamer_id)

        if command_type == commands.Pass_Turn:
            return self.pass_turn(gamer_id)

        return {}

    def play_card(self, gamer_id: int, card_uid: int, chosen_color: str = "") -> Dict[str, Any]:
        card = self._find_card_in_hand(gamer_id, card_uid)
        if card is None or not self.is_card_playable(card):
            return {}

        self.hands[gamer_id] = [c for c in self.hands[gamer_id] if int(c["uid"]) != int(card_uid)]
        played_card = dict(card)
        c_val = str(played_card["value"])
        c_col = str(played_card["color"])

        if c_col == "wild" or c_val in UNO_WILD_VALUES:
            if chosen_color not in UNO_COLORS:
                chosen_color = self._best_color_for_player(gamer_id)
            self.current_color = chosen_color
        else:
            self.current_color = c_col
            chosen_color = c_col

        self.current_value = c_val
        self.discard_pile.append(played_card)
        self.has_drawn_this_turn = False
        self.last_drawn_card = None

        if len(self.hands[gamer_id]) == 1:
            self.uno_called[gamer_id] = True
        elif len(self.hands[gamer_id]) > 1:
            self.uno_called[gamer_id] = False

        penalty_target: int = 0
        penalty_cards: List[Dict[str, Any]] = []
        skipped_player: int = 0

        # Check win condition immediately
        if len(self.hands[gamer_id]) == 0:
            self._assign_winner_and_runner_up(gamer_id)
            result = {
                "action": "play_card",
                "gamer_id": gamer_id,
                "card": played_card,
                "current_color": self.current_color,
                "current_value": self.current_value,
                "chosen_color": chosen_color,
                "direction": self.direction,
                "skipped_player": 0,
                "penalty_target": 0,
                "penalty_count": 0,
                "penalty_cards": [],
                "uno_shout": False,
                "next_turn": self.current_turn,
                "is_game_finished": True,
                "rank1": self.rank1,
                "rank2": self.rank2,
            }
            self.last_action = result
            return result

        # Apply action card effects
        active_cnt = len(self.active_player_indexes)
        if c_val == "reverse":
            if active_cnt == 2:
                # In 2-player UNO, Reverse acts like Skip!
                skipped_player = self._next_active_player(gamer_id, steps=1)
                self.change_turn(steps=2)
            else:
                self.direction *= -1
                self.change_turn(steps=1)
        elif c_val == "skip":
            skipped_player = self._next_active_player(gamer_id, steps=1)
            self.change_turn(steps=2)
        elif c_val == "draw2":
            penalty_target = self._next_active_player(gamer_id, steps=1)
            skipped_player = penalty_target
            for _ in range(2):
                dc = self._draw_one_card()
                self.hands[penalty_target].append(dc)
                penalty_cards.append(dc)
            self.uno_called[penalty_target] = False
            self.change_turn(steps=2)
        elif c_val == "wild_draw4":
            penalty_target = self._next_active_player(gamer_id, steps=1)
            skipped_player = penalty_target
            for _ in range(4):
                dc = self._draw_one_card()
                self.hands[penalty_target].append(dc)
                penalty_cards.append(dc)
            self.uno_called[penalty_target] = False
            self.change_turn(steps=2)
        else:
            self.change_turn(steps=1)

        result = {
            "action": "play_card",
            "gamer_id": gamer_id,
            "card": played_card,
            "current_color": self.current_color,
            "current_value": self.current_value,
            "chosen_color": chosen_color,
            "direction": self.direction,
            "skipped_player": skipped_player,
            "penalty_target": penalty_target,
            "penalty_count": len(penalty_cards),
            "penalty_cards": penalty_cards,
            "uno_shout": len(self.hands[gamer_id]) == 1,
            "next_turn": self.current_turn,
            "is_game_finished": self.is_game_finished,
            "rank1": self.rank1,
            "rank2": self.rank2,
        }
        self.last_action = result
        return result

    def draw_card_for_turn(self, gamer_id: int, force_pass: bool = False) -> Dict[str, Any]:
        drawn = self._draw_one_card()
        self.hands[gamer_id].append(drawn)
        self.uno_called[gamer_id] = False
        self.last_drawn_card = drawn

        playable_uids = self.get_playable_card_uids(gamer_id)
        drawn_is_playable = self.is_card_playable(drawn)

        if force_pass or not playable_uids:
            self.change_turn(steps=1)
            turn_passed = True
        else:
            self.has_drawn_this_turn = True
            turn_passed = False

        result = {
            "action": "draw_card",
            "gamer_id": gamer_id,
            "drawn_card": drawn,
            "drawn_is_playable": drawn_is_playable,
            "playable_uids": playable_uids if not turn_passed else [],
            "has_drawn_this_turn": self.has_drawn_this_turn,
            "turn_passed": turn_passed,
            "next_turn": self.current_turn,
            "direction": self.direction,
        }
        self.last_action = result
        return result

    def pass_turn(self, gamer_id: int) -> Dict[str, Any]:
        self.change_turn(steps=1)
        result = {
            "action": "pass_turn",
            "gamer_id": gamer_id,
            "next_turn": self.current_turn,
            "direction": self.direction,
        }
        self.last_action = result
        return result

    def get_top_card(self) -> Dict[str, Any]:
        if self.discard_pile:
            return dict(self.discard_pile[-1])
        return {"uid": 0, "color": self.current_color, "value": self.current_value}

    def get_hands_count(self) -> List[int]:
        return [len(self.hands.get(i, [])) for i in range(1, self.players_count + 1)]

    def get_user_private_game_data(self, gamer_id: int) -> Dict[str, Any]:
        hand = [dict(c) for c in self.hands.get(gamer_id, [])]
        playable_uids = self.get_playable_card_uids(gamer_id) if gamer_id == self.current_turn else []
        return {
            "user": gamer_id,
            "index": gamer_id,
            "gamer_id": gamer_id,
            "hand": hand,
            "playable_uids": playable_uids,
            "has_drawn_this_turn": self.has_drawn_this_turn if gamer_id == self.current_turn else False,
            "current_color": self.current_color,
            "current_value": self.current_value,
            "top_card": self.get_top_card(),
            "direction": self.direction,
            "current_turn": self.current_turn,
            "hands_count": self.get_hands_count(),
            "draw_pile_count": len(self.draw_pile),
        }

    def get_game_data(self) -> Dict[str, Any]:
        return {
            "players_count": self.players_count,
            "active_player_indexes": list(self.active_player_indexes),
            "current_turn": self.current_turn,
            "direction": self.direction,
            "current_color": self.current_color,
            "current_value": self.current_value,
            "top_card": self.get_top_card(),
            "hands_count": self.get_hands_count(),
            "draw_pile_count": len(self.draw_pile),
            "has_drawn_this_turn": self.has_drawn_this_turn,
            "rank1": self.rank1,
            "rank2": self.rank2,
            "is_game_finished": self.is_game_finished,
        }
