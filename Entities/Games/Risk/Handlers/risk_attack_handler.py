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
        self.source_army: int = 0     # active ARMY tactic cards committed before battle starts
        self.target_army: int = 0     # active ARMY tactic cards committed before battle starts
        self.attacker_canon_bonus: int = 0
        self.defender_canon_bonus: int = 0
        self.is_attack_active: bool = False
        self.attacker_committed: bool = False
        self.defender_committed: bool = False
        self.battle_started: bool = False
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
        self.battle_started = False

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
        # In Risk Strike, once an attack is declared/started on a turn, a second separate attack declaration cannot be made
        if self.is_attack_active or self.game.attacked_this_turn:
            return False
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
        self.battle_started = False
        self.game.attacked_this_turn = True
        self.game.attacks_this_turn = getattr(self.game, "attacks_this_turn", 0) + 1
        return True

    def add_attacker_army(self, count: int, gamer_id: int = None) -> int:
        # Rule: After attack starts (or once attacker has committed), players can NO LONGER add new army cards to battle!
        if not self.is_attack_active or self.battle_started or self.attacker_committed:
            return 0
        p_idx = (gamer_id - 1) if gamer_id is not None else self.source_id
        if p_idx != self.source_id or not (0 <= p_idx < len(self.game.players_data)):
            return 0
        player = self.game.players_data[p_idx]
        req = max(0, int(count or 0))
        avail = player.count_strategy(RiskStrategyModel.ARMY)
        actual = min(req, avail)
        for _ in range(actual):
            player.remove_strategy(RiskStrategyModel.ARMY)
            self.game.discarded_strategies.append(RiskStrategyModel.ARMY)
        self.source_army += actual
        self.attacker_committed = True
        return actual

    def add_defender_army(self, count: int, gamer_id: int = None) -> int:
        # Rule: After attack starts (or once defender has committed), players can NO LONGER add new army cards to battle!
        if not self.is_attack_active or self.battle_started or self.defender_committed:
            return 0
        p_idx = (gamer_id - 1) if gamer_id is not None else (self.target_id - 1)
        if p_idx != (self.target_id - 1) or not (0 <= p_idx < len(self.game.players_data)):
            return 0
        player = self.game.players_data[p_idx]
        req = max(0, int(count or 0))
        avail = player.count_strategy(RiskStrategyModel.ARMY)
        actual = min(req, avail)
        for _ in range(actual):
            player.remove_strategy(RiskStrategyModel.ARMY)
            self.game.discarded_strategies.append(RiskStrategyModel.ARMY)
        self.target_army += actual
        self.defender_committed = True
        return actual

    def stop_attack(self) -> dict:
        if not self.is_attack_active:
            return self.last_battle_result or {}
        stopped_summary = {
            "canceled": False,
            "stopped": True,
            "attacker_id": self.source_id + 1,
            "defender_id": self.target_id,
            "source_continent": self.source_continent.value,
            "target_continent": self.target_continent.value,
            "attacker_dice": [],
            "defender_dice": [],
            "attacker_army": 0,
            "defender_army": 0,
            "attacker_losses": 0,
            "defender_losses": 0,
            "returned_continents_count": 0,
            "conquered": False,
            "battle_continues": False,
            "token_events": [],
            "is_game_finished": False,
            "winner": 0,
        }
        self.last_battle_result = stopped_summary
        self.reset()
        self.game.game_state = RiskGameState.SELECTACTION
        return stopped_summary

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
            "attacker_army": 0,
            "defender_army": 0,
            "attacker_losses": 0,
            "defender_losses": 0,
            "returned_continents_count": 0,
            "conquered": False,
            "battle_continues": False,
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

        # Once dice rolling starts, the battle has officially started and no new Army cards can be added
        self.attacker_committed = True
        self.defender_committed = True
        self.battle_started = True

        attacker = self.game.players_data[self.source_id]
        defender = self.game.players_data[self.target_id - 1]
        src_c = self.source_continent.value
        tgt_c = self.target_continent.value

        atk_cards = attacker.continents.get(src_c, 0)
        def_cards = defender.continents.get(tgt_c, 0)

        # Official Risk Strike Dice Limits:
        # Total combat dice = participating continent cards + active troop (Army) cards
        # Maximum 3 dice for Attacker, Maximum 2 dice for Defender
        atk_dice_count = min(3, max(1, atk_cards + self.source_army))
        def_dice_count = min(2, max(1, def_cards + self.target_army))

        attacker_dice = _roll_sorted_dice(atk_dice_count, bonus=self.attacker_canon_bonus)
        defender_dice = _roll_sorted_dice(def_dice_count, bonus=self.defender_canon_bonus)
        self.attacker_canon_bonus = 0
        self.defender_canon_bonus = 0
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

        # 1. Attacker casualties: first discard active Army cards; remaining losses surrender Continent cards to center of table
        atk_army_lost = min(self.source_army, atk_casualties)
        self.source_army -= atk_army_lost
        rem_atk_casualties = atk_casualties - atk_army_lost
        actual_atk_c_loss = attacker.remove_continent(self.source_continent, rem_atk_casualties)
        if actual_atk_c_loss > 0:
            self.game.return_continent_cards_to_table(self.source_continent, actual_atk_c_loss)

        # 2. Defender casualties: first discard active Army cards; remaining losses surrender Continent cards to center of table
        def_army_lost = min(self.target_army, def_casualties)
        self.target_army -= def_army_lost
        rem_def_casualties = def_casualties - def_army_lost
        actual_def_c_loss = defender.remove_continent(self.target_continent, rem_def_casualties)
        if actual_def_c_loss > 0:
            self.game.return_continent_cards_to_table(self.target_continent, actual_def_c_loss)

        total_atk_loss = atk_army_lost + actual_atk_c_loss
        total_def_loss = def_army_lost + actual_def_c_loss
        returned_to_table = actual_atk_c_loss + actual_def_c_loss

        rem_atk_c = attacker.continents.get(src_c, 0)
        rem_def_c = defender.continents.get(tgt_c, 0)
        conquered = (rem_def_c == 0 and actual_def_c_loss > 0)

        token_events = self.game.update_domination_tokens()

        self.game.check_player_eliminations()
        is_ended = self.game.check_game_ended()

        # If both sides still have continent cards in the battle and the match isn't over,
        # the battle can continue (Attack state) using remaining committed forces (no new Army cards allowed!)
        battle_continues = (not is_ended and not conquered and rem_atk_c > 0 and rem_def_c > 0)

        result = {
            "canceled": False,
            "stopped": False,
            "attacker_id": self.source_id + 1,
            "defender_id": self.target_id,
            "source_continent": src_c,
            "target_continent": tgt_c,
            "attacker_dice": attacker_dice,
            "defender_dice": defender_dice,
            "attacker_army": self.source_army,
            "defender_army": self.target_army,
            "attacker_losses": total_atk_loss,
            "defender_losses": total_def_loss,
            "attacker_continent_losses": actual_atk_c_loss,
            "defender_continent_losses": actual_def_c_loss,
            "returned_continents_count": returned_to_table,
            "captured_cards": 0,
            "conquered": conquered,
            "battle_continues": battle_continues,
            "token_events": token_events,
            "is_game_finished": is_ended,
            "winner": self.game.get_game_winner() if is_ended else 0,
        }
        self.last_battle_result = result
        if battle_continues:
            self.game.game_state = RiskGameState.ATTACK
        else:
            self.reset()
            if not is_ended:
                self.game.game_state = RiskGameState.SELECTACTION
        return result

