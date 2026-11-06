import random
from typing import TYPE_CHECKING, Optional

from Entities.Games.Risk.Models.models import RiskContinentModel, RiskStrategyModel, RiskGameState
from Entities.Games.Risk.Utils.continent_connections import is_two_continent_connected

if TYPE_CHECKING:
    from Entities.Games.Risk import RiskGameClass


def _roll_sorted_dice(count: int, bonus: int = 0) -> list[int]:
    if count <= 0:
        return []
    rolls = [random.randint(1, 6) for _ in range(count)]
    rolls.sort(reverse=True)
    rem_bonus = max(0, int(bonus))
    while rem_bonus > 0:
        boosted = False
        for i in range(len(rolls)):
            if rolls[i] < 6:
                rolls[i] += 1
                boosted = True
                break
        if not boosted:
            break
        rem_bonus -= 1
    rolls.sort(reverse=True)
    return rolls


class RiskAttackHandler:
    def __init__(self, game: "RiskGameClass"):
        self.game = game
        self.source_continent: RiskContinentModel = RiskContinentModel.ASIA
        self.target_continent: RiskContinentModel = RiskContinentModel.ASIA
        self.source_id: int = 0       # 0-based attacker index (gamer_id - 1)
        self.target_id: int = 0       # 1-based defender gamer_id
        self.source_army: int = 0     # extra ARMY tactic cards committed to attack
        self.target_army: int = 0     # extra ARMY tactic cards committed to defense
        self.attacker_canon_bonus: int = 0
        self.defender_canon_bonus: int = 0
        self.is_attack_active: bool = False
        self.attacker_committed: bool = False
        self.defender_committed: bool = False
        self.last_battle_result: Optional[dict] = None

    def reset(self):
        self.source_id = 0
        self.target_id = 0
        self.source_continent = RiskContinentModel.ASIA
        self.target_continent = RiskContinentModel.ASIA
        self.source_army = 0
        self.target_army = 0
        self.attacker_canon_bonus = 0
        self.defender_canon_bonus = 0
        self.is_attack_active = False
        self.attacker_committed = False
        self.defender_committed = False

    def check_declare_is_valid(
        self,
        source_continent: RiskContinentModel,
        target_continent: RiskContinentModel,
        target_id: int,
        attacker_idx: Optional[int] = None,
    ) -> bool:
        if source_continent is None or target_continent is None:
            return False
        src_idx = self.source_id if attacker_idx is None else int(attacker_idx)
        if not (0 <= src_idx < len(self.game.players_data)):
            return False
        try:
            tgt_id = int(target_id)
        except (TypeError, ValueError):
            return False
        if not (1 <= tgt_id <= len(self.game.players_data)):
            return False
        if tgt_id == (src_idx + 1):
            return False
        if tgt_id not in self.game.active_player_indexes:
            return False
        if self.game.players_data[src_idx].continents.get(source_continent.value, 0) <= 0:
            return False
        if self.game.players_data[tgt_id - 1].continents.get(target_continent.value, 0) <= 0:
            return False
        if not self.game.ignore_adjacency and not is_two_continent_connected(source_continent, target_continent):
            return False
        return True

    def declare_war(self, source_continent, target_continent, target_id) -> bool:
        src_model = RiskContinentModel.data_to_model(source_continent)
        tgt_model = RiskContinentModel.data_to_model(target_continent)
        self.source_id = self.game.current_turn - 1
        try:
            tgt_id_int = int(target_id)
        except (TypeError, ValueError):
            return False
        if not self.check_declare_is_valid(src_model, tgt_model, tgt_id_int, attacker_idx=self.source_id):
            return False

        self.source_continent = src_model
        self.target_continent = tgt_model
        self.target_id = tgt_id_int
        self.source_army = 0
        self.target_army = 0
        self.attacker_canon_bonus = self.game.pending_attacker_canon_bonus
        self.game.pending_attacker_canon_bonus = 0
        self.defender_canon_bonus = 0
        self.is_attack_active = True
        self.attacker_committed = False
        self.defender_committed = False
        self.game.attacked_this_turn = True
        self.game.attacks_this_turn = getattr(self.game, "attacks_this_turn", 0) + 1
        return True

    def add_attacker_army(self, count: int, gamer_id: int = None) -> int:
        if not self.is_attack_active:
            return 0
        p_idx = (gamer_id - 1) if gamer_id is not None else self.source_id
        if not (0 <= p_idx < len(self.game.players_data)):
            return 0
        player = self.game.players_data[p_idx]
        attacker = self.game.players_data[self.source_id]
        atk_cards = attacker.continents.get(self.source_continent.value, 1)
        base_atk_dice = min(3, max(1, atk_cards))
        max_extra = max(0, 5 - base_atk_dice - self.source_army)
        req = max(0, int(count or 0))
        avail = player.count_strategy(RiskStrategyModel.ARMY)
        actual = min(req, avail, max_extra)
        for _ in range(actual):
            player.remove_strategy(RiskStrategyModel.ARMY)
            self.game.discarded_strategies.append(RiskStrategyModel.ARMY)
        self.source_army += actual
        if p_idx == self.source_id:
            self.attacker_committed = True
        return actual

    def add_defender_army(self, count: int, gamer_id: int = None) -> int:
        if not self.is_attack_active:
            return 0
        p_idx = (gamer_id - 1) if gamer_id is not None else (self.target_id - 1)
        if not (0 <= p_idx < len(self.game.players_data)):
            return 0
        player = self.game.players_data[p_idx]
        defender = self.game.players_data[self.target_id - 1]
        def_cards = defender.continents.get(self.target_continent.value, 1)
        base_def_dice = min(2, max(1, def_cards))
        max_extra = max(0, 4 - base_def_dice - self.target_army)
        req = max(0, int(count or 0))
        avail = player.count_strategy(RiskStrategyModel.ARMY)
        actual = min(req, avail, max_extra)
        for _ in range(actual):
            player.remove_strategy(RiskStrategyModel.ARMY)
            self.game.discarded_strategies.append(RiskStrategyModel.ARMY)
        self.target_army += actual
        if p_idx == (self.target_id - 1):
            self.defender_committed = True
        return actual

    def cancel_attack_by_card(self, gamer_id: int) -> bool:
        if not self.is_attack_active:
            return False
        if not (1 <= gamer_id <= len(self.game.players_data)):
            return False
        player = self.game.players_data[gamer_id - 1]
        if not player.has_strategy(RiskStrategyModel.CANCEL):
            return False

        player.remove_strategy(RiskStrategyModel.CANCEL)
        self.game.discarded_strategies.append(RiskStrategyModel.CANCEL)

        canceled_summary = {
            "canceled": True,
            "canceled_by": gamer_id,
            "attacker_id": self.source_id + 1,
            "defender_id": self.target_id,
            "source_continent": self.source_continent.value,
            "target_continent": self.target_continent.value,
            "attacker_dice": [],
            "defender_dice": [],
            "attacker_losses": 0,
            "defender_losses": 0,
            "conquered": False,
            "token_events": [],
            "is_game_finished": False,
            "winner": 0,
        }
        self.last_battle_result = canceled_summary
        self.reset()
        self.game.game_state = RiskGameState.SELECTACTION
        return True

    def resolve_attack(self) -> dict:
        if not self.is_attack_active:
            return self.last_battle_result or {}

        attacker = self.game.players_data[self.source_id]
        defender = self.game.players_data[self.target_id - 1]
        src_c = self.source_continent.value
        tgt_c = self.target_continent.value

        atk_cards = attacker.continents.get(src_c, 0)
        def_cards = defender.continents.get(tgt_c, 0)

        # Official Risk Strike Dice Limits:
        # Base attack dice: 1 to 3 based on continent cards in attacking continent + committed ARMY cards (max 5 dice)
        # Base defense dice: 1 to 2 based on continent cards in defending continent + committed ARMY cards (max 4 dice)
        atk_dice_count = min(5, min(3, max(1, atk_cards)) + self.source_army)
        def_dice_count = min(4, min(2, max(1, def_cards)) + self.target_army)

        attacker_dice = _roll_sorted_dice(atk_dice_count, bonus=self.attacker_canon_bonus)
        defender_dice = _roll_sorted_dice(def_dice_count, bonus=self.defender_canon_bonus)
        self.game.current_dice = {"attacker": attacker_dice, "defender": defender_dice}

        # Pairwise comparison of highest dice (ties go to Defender per official Risk Strike rules)
        pairs = min(len(attacker_dice), len(defender_dice))
        atk_casualties = 0
        def_casualties = 0
        for i in range(pairs):
            if attacker_dice[i] > defender_dice[i]:
                def_casualties += 1
            else:
                atk_casualties += 1

        # Apply attacker casualties to attacking Continent cards (discarded to continent discard pile)
        actual_atk_loss = attacker.remove_continent(self.source_continent, atk_casualties)
        for _ in range(actual_atk_loss):
            self.game.discarded_continents.append(self.source_continent)

        # Apply defender casualties to defending Continent cards:
        # Per Risk Strike rules, if the defender suffers losses in the attacked continent,
        # the attacker captures 1 card of target_continent, and any additional losses go to discard.
        actual_def_loss = defender.remove_continent(self.target_continent, def_casualties)
        captured_cards = 0
        if actual_def_loss > 0:
            attacker.add_continent(self.target_continent, 1)
            captured_cards = 1
            for _ in range(actual_def_loss - 1):
                self.game.discarded_continents.append(self.target_continent)

        conquered = (defender.continents.get(tgt_c, 0) == 0 and actual_def_loss > 0)
        if conquered:
            token_events = self.game.update_domination_tokens(
                conquered_continent=tgt_c,
                conqueror_idx=self.source_id
            )
        else:
            token_events = self.game.update_domination_tokens()

        self.game.check_player_eliminations()
        is_ended = self.game.check_game_ended()

        result = {
            "canceled": False,
            "attacker_id": self.source_id + 1,
            "defender_id": self.target_id,
            "source_continent": src_c,
            "target_continent": tgt_c,
            "attacker_dice": attacker_dice,
            "defender_dice": defender_dice,
            "attacker_army": self.source_army,
            "defender_army": self.target_army,
            "attacker_losses": actual_atk_loss,
            "defender_losses": actual_def_loss,
            "captured_cards": captured_cards,
            "conquered": conquered,
            "token_events": token_events,
            "is_game_finished": is_ended,
            "winner": self.game.get_game_winner() if is_ended else 0,
        }
        self.last_battle_result = result
        self.reset()
        if not is_ended:
            self.game.game_state = RiskGameState.SELECTACTION
        return result
