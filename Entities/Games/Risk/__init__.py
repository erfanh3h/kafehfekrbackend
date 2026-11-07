import random
from typing import Optional

from Commons import commands
from Entities.Games.Risk.Models.models import RiskContinentModel, RiskStrategyModel, RiskGameState
from Entities.Games.Risk.Models.user_spot import UserSpotClass
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass


DOMINATION_THRESHOLDS: dict[str, int] = {
    "Asia": 8,
    "NorthAmerica": 6,
    "Europe": 5,
    "Africa": 4,
    "Australia": 3,
    "SouthAmerica": 3,
}


def roll_dice(dice_count: int) -> list[int]:
    return [random.randint(1, 6) for _ in range(max(0, int(dice_count)))]


class RiskGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count: int = 2):
        super().__init__(send_data_function, players_count)
        self.strategies: list[RiskStrategyModel] = []
        self.continents: list[RiskContinentModel] = []
        self.discarded_strategies: list[RiskStrategyModel] = []
        self.discarded_continents: list[RiskContinentModel] = []
        self.tokens: list[str] = []
        self.last_token_events: list[dict] = []
        self.current_dice: dict = {"attacker": [], "defender": []}
        self.attacked_this_turn: bool = False
        self.attacks_this_turn: int = 0
        self.ignore_adjacency: bool = False
        self.pending_attacker_canon_bonus: int = 0
        self.winner_id: int = 0

        self.init_cards()
        self.players_data: list[UserSpotClass] = []
        self.init_game()
        self.current_turn = 1
        self.game_state = RiskGameState.STARTGAME

        from Entities.Games.Risk.Handlers.risk_draw_handler import RiskDrawHandler
        self.draw_handler = RiskDrawHandler(self)
        from Entities.Games.Risk.Handlers.risk_attack_handler import RiskAttackHandler
        self.attack_handler = RiskAttackHandler(self)

    def init_cards(self):
        self.strategies.clear()
        self.continents.clear()
        self.discarded_strategies.clear()
        self.discarded_continents.clear()
        self.tokens.clear()

        # Official 38 Strategy / Tactic Cards
        for _ in range(18):
            self.strategies.append(RiskStrategyModel.ARMY)
        for _ in range(4):
            self.strategies.append(RiskStrategyModel.BACKUP)
            self.strategies.append(RiskStrategyModel.BOMB)
            self.strategies.append(RiskStrategyModel.DESTROY)
        for _ in range(3):
            self.strategies.append(RiskStrategyModel.CANCEL)
            self.strategies.append(RiskStrategyModel.CANON)
        for _ in range(2):
            self.strategies.append(RiskStrategyModel.EXPAND)
            self.strategies.append(RiskStrategyModel.SPY)

        # Official 42 Continent Cards (12 Asia, 9 NorthAmerica, 7 Europe, 6 Africa, 4 Australia, 4 SouthAmerica)
        for _ in range(12):
            self.continents.append(RiskContinentModel.ASIA)
        for _ in range(9):
            self.continents.append(RiskContinentModel.NORTHAMERICA)
        for _ in range(7):
            self.continents.append(RiskContinentModel.EUROPE)
        for _ in range(6):
            self.continents.append(RiskContinentModel.AFRICA)
        for _ in range(4):
            self.continents.append(RiskContinentModel.AUSTRALIA)
            self.continents.append(RiskContinentModel.SOUTHAMERICA)

        # 6 Continent Domination Tokens start unclaimed on the board
        for continent in RiskContinentModel.all():
            self.tokens.append(continent.value)

        for _ in range(5):
            random.shuffle(self.strategies)
            random.shuffle(self.continents)

    def return_continent_cards_to_table(self, continent_model: Optional[RiskContinentModel], count: int = 1):
        """
        Official Risk Strike rule: When a player loses Continent (قاره) cards in battle,
        Destroy/Sabotage, Bomb, or surrender, those Continent cards are returned to the
        center of the table (bottom of the Continent deck), immediately updating the table count.
        """
        if continent_model is None or count <= 0:
            return
        for _ in range(int(count)):
            self.continents.insert(0, continent_model)

    def draw_continent_card(self) -> Optional[RiskContinentModel]:
        if not self.continents and self.discarded_continents:
            self.continents.extend(self.discarded_continents)
            self.discarded_continents.clear()
            random.shuffle(self.continents)
        if self.continents:
            return self.continents.pop()
        return None

    def draw_strategy_card(self) -> Optional[RiskStrategyModel]:
        if not self.strategies and self.discarded_strategies:
            self.strategies.extend(self.discarded_strategies)
            self.discarded_strategies.clear()
            random.shuffle(self.strategies)
        if self.strategies:
            return self.strategies.pop()
        return None

    def init_game(self):
        self.players_data.clear()
        self.active_player_indexes.clear()
        for index in range(self.players_count):
            self.players_data.append(UserSpotClass(index + 1))
            self.active_player_indexes.append(index + 1)

        # Official Risk Strike Setup:
        # Each player starts with 3 Continent cards and 3 Strategy cards;
        # Non-starting players (index != 0) receive 1 extra Strategy card (4 Strategy cards total).
        for index, player_data in enumerate(self.players_data):
            for _ in range(3):
                c_card = self.draw_continent_card()
                s_card = self.draw_strategy_card()
                if c_card is not None:
                    player_data.add_continent(c_card)
                if s_card is not None:
                    player_data.add_strategy(s_card)
            if index != 0:
                extra_s = self.draw_strategy_card()
                if extra_s is not None:
                    player_data.add_strategy(extra_s)

        # Ensure no player starts Turn 0 with 3 identical continent cards (so no continent starts pre-dominated)
        for p in self.players_data:
            for c_name, cnt in list(p.continents.items()):
                if cnt >= 3 and self.continents:
                    replacement_idx = next(
                        (i for i, c in enumerate(self.continents) if c.value != c_name),
                        None,
                    )
                    if replacement_idx is not None:
                        rep_card = self.continents.pop(replacement_idx)
                        p.remove_continent(c_name, 1)
                        p.add_continent(rep_card, 1)
                        self.continents.insert(0, RiskContinentModel.data_to_model(c_name))

    def update_domination_tokens(
        self,
        conquered_continent: Optional[str] = None,
        conqueror_idx: Optional[int] = None,
    ) -> list[dict]:
        """
        Official Risk Strike Rulebook — Domination Coins (نشان سلطه):
        1. Each continent card has a Domination Number (Asia: 8, NorthAmerica: 6, Europe: 5,
           Africa: 4, SouthAmerica: 3, Australia: 3).
        2. As soon as an active player holds a number of continent cards for continent C
           equal to or greater than DOMINATION_THRESHOLDS[C], they immediately claim C's
           Domination Coin (either from the center table or from another player who held it).
        3. Once a player holds the Domination Coin for continent C, they KEEP it even if
           they later lose continent cards and drop below DOMINATION_THRESHOLDS[C]—as long
           as another active player does not collect DOMINATION_THRESHOLDS[C] cards of C
           (or the holder leaves/surrenders the match).
        """
        events = []
        for c_model in RiskContinentModel.all():
            c_name = c_model.value
            threshold = DOMINATION_THRESHOLDS.get(c_name, 3)

            # Step 1: If the current holder surrendered / left the match, return the coin to the table
            current_owner = None
            for p in self.players_data:
                if c_name in p.tokens:
                    if p.index not in self.active_player_indexes:
                        p.remove_token(c_name)
                        if c_name not in self.tokens:
                            self.tokens.append(c_name)
                        events.append({"event": "token_lost", "continent": c_name, "gamer_id": p.index})
                    else:
                        current_owner = p

            # Step 2: Check if any active player has reached or exceeded the continent's Domination Number
            qualifying_players = [
                p for p in self.players_data
                if p.index in self.active_player_indexes and p.continents.get(c_name, 0) >= threshold
            ]
            if qualifying_players:
                qualifying_players.sort(
                    key=lambda p: (
                        p.continents.get(c_name, 0),
                        1 if p == current_owner else 0,
                    ),
                    reverse=True,
                )
                dominator = qualifying_players[0]
                if current_owner != dominator:
                    prev_owner_id = current_owner.index if current_owner is not None else 0
                    if current_owner is not None:
                        current_owner.remove_token(c_name)
                    if c_name in self.tokens:
                        self.tokens.remove(c_name)
                    dominator.add_token(c_name)
                    current_owner = dominator
                    events.append({
                        "event": "token_claimed",
                        "continent": c_name,
                        "gamer_id": dominator.index,
                        "previous_owner": prev_owner_id,
                        "count": dominator.continents.get(c_name, 0),
                        "threshold": threshold,
                    })

        self.last_token_events = list(events)
        return events

    def check_player_eliminations(self):
        # Official Risk Strike rule:
        # Players draw 2 cards at the start of every turn and keep earned Domination Coins
        # even if they lose continent cards, unless they surrender/leave the match.
        for p in self.players_data:
            if p.index not in self.active_player_indexes and p.tokens:
                for t in list(p.tokens):
                    p.remove_token(t)
                    if t not in self.tokens:
                        self.tokens.append(t)

    def _compute_runner_up(self, winner_id: int) -> int:
        candidates = [p for p in self.players_data if p.index != winner_id]
        if not candidates:
            return 0
        candidates.sort(
            key=lambda p: (
                1 if p.index in self.active_player_indexes else 0,
                len(p.tokens),
                p.total_continents(),
                len(p.strategies),
            ),
            reverse=True,
        )
        return candidates[0].index

    def check_game_ended(self) -> bool:
        if self.is_game_finished:
            return True

        # 1. Official Risk Strike Victory Condition: First player to hold 2 Domination Tokens wins immediately!
        for p in self.players_data:
            if p.index in self.active_player_indexes and len(p.tokens) >= 2:
                self.winner_id = p.index
                self.rank1 = p.index
                self.rank2 = self._compute_runner_up(p.index)
                self.is_game_finished = True
                return True

        # 2. Last surviving active player wins
        if len(self.active_player_indexes) == 1:
            last_id = self.active_player_indexes[0]
            self.winner_id = last_id
            self.rank1 = last_id
            if self.rank2 is None:
                self.rank2 = self._compute_runner_up(last_id)
            self.is_game_finished = True
            return True

        return False

    def get_game_winner(self) -> int:
        if self.rank1 is not None:
            return self.rank1
        return self.winner_id

    def check_end_game(self) -> tuple[bool, int]:
        is_ended = bool(self.is_game_finished or self.check_game_ended())
        winner_id = int(self.get_game_winner() or 0) if is_ended else 0
        return is_ended, winner_id

    def get_game_data(self):
        players_data = [player_data.to_global_json() for player_data in self.players_data]
        atk_info = None
        if hasattr(self, "attack_handler") and self.attack_handler.is_attack_active:
            atk_info = {
                "attacker_id": self.attack_handler.source_id + 1,
                "defender_id": self.attack_handler.target_id,
                "source_continent": self.attack_handler.source_continent.value,
                "target_continent": self.attack_handler.target_continent.value,
                "attacker_army": self.attack_handler.source_army,
                "defender_army": self.attack_handler.target_army,
                "battle_started": self.attack_handler.battle_started,
            }
        return {
            "current_turn": self.current_turn,
            "active_player_indexes": list(self.active_player_indexes),
            "rank1": self.rank1,
            "rank2": self.rank2,
            "strategies": len(self.strategies),
            "continents": len(self.continents),
            "players_data": players_data,
            "tokens": list(self.tokens),
            "tokens_count": len(self.tokens),
            "game_state": self.game_state.value,
            "active_attack": atk_info,
        }

    def get_user_private_game_data(self, gamer_index: int):
        if 0 <= gamer_index < len(self.players_data):
            return self.players_data[gamer_index].to_private_json()
        return {"index": gamer_index + 1, "continents": {}, "strategies": [], "tokens": []}

    def _pick_valid_opponent(self, gamer_id: int, requested_target_id: Optional[int], require_continents: bool = False, preferred_continent: Optional[str] = None) -> Optional[int]:
        opponents = [
            p for p in self.players_data
            if p.index != gamer_id and p.index in self.active_player_indexes
        ]
        if not opponents:
            return None

        if require_continents:
            eligible = [p for p in opponents if p.total_continents() > 0]
            if preferred_continent:
                with_pref = [p for p in eligible if p.continents.get(preferred_continent, 0) > 0]
                if requested_target_id is not None and any(p.index == requested_target_id for p in with_pref):
                    return requested_target_id
                if with_pref:
                    with_pref.sort(key=lambda p: (len(p.tokens), p.total_continents(), len(p.strategies)), reverse=True)
                    return with_pref[0].index
            if requested_target_id is not None and any(p.index == requested_target_id for p in eligible):
                return requested_target_id
            if not eligible:
                return None
            eligible.sort(key=lambda p: (len(p.tokens), p.total_continents(), len(p.strategies)), reverse=True)
            return eligible[0].index
        else:
            eligible = [p for p in opponents if len(p.strategies) > 0 or p.total_continents() > 0]
            if requested_target_id is not None and any(p.index == requested_target_id for p in eligible):
                return requested_target_id
            if not eligible:
                return None
            eligible.sort(key=lambda p: (len(p.tokens), len(p.strategies), p.total_continents()), reverse=True)
            return eligible[0].index

    def use_strategy_card(self, gamer_id: int, data: dict) -> Optional[dict]:
        if not (1 <= gamer_id <= len(self.players_data)):
            return None
        player = self.players_data[gamer_id - 1]
        raw_strategy = data.get("strategy", data.get("card", data.get("type"))) if isinstance(data, dict) else data
        strat = RiskStrategyModel.data_to_model(raw_strategy)
        if strat is None or not player.has_strategy(strat):
            return None

        raw_target_id = data.get("target_index", data.get("target_id")) if isinstance(data, dict) else None
        if raw_target_id is not None:
            try:
                raw_target_id = int(raw_target_id)
            except (TypeError, ValueError):
                raw_target_id = None
        if raw_target_id == gamer_id or (raw_target_id is not None and raw_target_id not in self.active_player_indexes):
            raw_target_id = None

        raw_c = data.get("target_continent", data.get("continent")) if isinstance(data, dict) else None
        req_c_model = RiskContinentModel.data_to_model(raw_c) if raw_c else None

        if strat == RiskStrategyModel.DESTROY:
            target_id = self._pick_valid_opponent(
                gamer_id,
                raw_target_id,
                require_continents=True,
                preferred_continent=req_c_model.value if req_c_model else None,
            )
        elif strat in (RiskStrategyModel.BOMB, RiskStrategyModel.SPY):
            target_id = self._pick_valid_opponent(gamer_id, raw_target_id, require_continents=False)
        else:
            target_id = raw_target_id

        effect_summary = {"gamer_id": gamer_id, "strategy": strat.value, "target_index": target_id}

        if strat == RiskStrategyModel.BACKUP:
            player.remove_strategy(strat)
            self.discarded_strategies.append(strat)
            c1 = self.draw_continent_card()
            c2 = self.draw_continent_card()
            drawn = []
            if c1 is not None:
                player.add_continent(c1)
                drawn.append(c1.value)
            if c2 is not None:
                player.add_continent(c2)
                drawn.append(c2.value)
            effect_summary["drawn_continents"] = drawn
            effect_summary["token_events"] = self.update_domination_tokens()

        elif strat == RiskStrategyModel.EXPAND:
            player.remove_strategy(strat)
            self.discarded_strategies.append(strat)
            self.ignore_adjacency = True
            c1 = self.draw_continent_card()
            drawn = []
            if c1 is not None:
                player.add_continent(c1)
                drawn.append(c1.value)
            effect_summary["ignore_adjacency"] = True
            effect_summary["drawn_continents"] = drawn
            effect_summary["token_events"] = self.update_domination_tokens()

        elif strat == RiskStrategyModel.BOMB:
            if target_id is None:
                return None
            target_p = self.players_data[target_id - 1]
            if len(target_p.strategies) == 0 and target_p.total_continents() == 0:
                return None
            player.remove_strategy(strat)
            self.discarded_strategies.append(strat)
            discarded = []
            returned_continents = []
            for _ in range(min(2, len(target_p.strategies))):
                victim_card = random.choice(target_p.strategies)
                target_p.remove_strategy(victim_card)
                self.discarded_strategies.append(victim_card)
                discarded.append(victim_card.value)
            if not discarded and target_p.total_continents() > 0:
                avail_c = [k for k, v in target_p.continents.items() if v > 0]
                if avail_c:
                    c_hit = random.choice(avail_c)
                    c_hit_model = RiskContinentModel.data_to_model(c_hit)
                    target_p.remove_continent(c_hit, 1)
                    self.return_continent_cards_to_table(c_hit_model, 1)
                    discarded.append(c_hit)
                    returned_continents.append(c_hit)
            effect_summary["discarded"] = discarded
            if returned_continents:
                effect_summary["returned_continents"] = returned_continents
            effect_summary["token_events"] = self.update_domination_tokens()

        elif strat == RiskStrategyModel.DESTROY:
            if target_id is None:
                return None
            target_p = self.players_data[target_id - 1]
            c_model = req_c_model
            if c_model is None or target_p.continents.get(c_model.value, 0) <= 0:
                avail_c = [k for k, v in target_p.continents.items() if v > 0]
                if not avail_c:
                    return None
                avail_c.sort(key=lambda c: (1 if c in target_p.tokens else 0, -target_p.continents[c]), reverse=True)
                c_model = RiskContinentModel.data_to_model(avail_c[0])

            player.remove_strategy(strat)
            self.discarded_strategies.append(strat)
            target_p.remove_continent(c_model, 1)
            # Return lost continent card to the center of the table
            self.return_continent_cards_to_table(c_model, 1)
            effect_summary["target_continent"] = c_model.value
            effect_summary["returned_continents"] = [c_model.value]
            effect_summary["token_events"] = self.update_domination_tokens()

        elif strat == RiskStrategyModel.SPY:
            if target_id is None:
                return None
            target_p = self.players_data[target_id - 1]
            if len(target_p.strategies) == 0 and target_p.total_continents() == 0:
                return None
            player.remove_strategy(strat)
            self.discarded_strategies.append(strat)
            if len(target_p.strategies) > 0:
                stolen = random.choice(target_p.strategies)
                target_p.remove_strategy(stolen)
                player.add_strategy(stolen)
                effect_summary["stolen_strategy"] = stolen.value
            else:
                avail_c = [k for k, v in target_p.continents.items() if v > 0]
                stolen_c = random.choice(avail_c)
                target_p.remove_continent(stolen_c, 1)
                player.add_continent(stolen_c, 1)
                effect_summary["stolen_continent"] = stolen_c
                effect_summary["token_events"] = self.update_domination_tokens()

        elif strat == RiskStrategyModel.CANON:
            player.remove_strategy(strat)
            self.discarded_strategies.append(strat)
            if self.attack_handler.is_attack_active:
                if gamer_id == (self.attack_handler.source_id + 1):
                    self.attack_handler.attacker_canon_bonus += 1
                elif gamer_id == self.attack_handler.target_id:
                    self.attack_handler.defender_canon_bonus += 1
            else:
                self.pending_attacker_canon_bonus += 1
            effect_summary["canon_bonus"] = 1

        elif strat == RiskStrategyModel.CANCEL:
            if self.attack_handler.is_attack_active:
                ok = self.attack_handler.cancel_attack_by_card(gamer_id)
                if not ok:
                    return None
                effect_summary["attack_canceled"] = True
            else:
                return None

        elif strat == RiskStrategyModel.ARMY:
            if self.attack_handler.is_attack_active:
                # Once dice rolling has started, players can no longer add new Army cards to the battle!
                if self.attack_handler.battle_started:
                    return None
                if gamer_id == (self.attack_handler.source_id + 1):
                    added = self.attack_handler.add_attacker_army(1, gamer_id)
                    if added <= 0:
                        return None
                    effect_summary["army_added"] = "Attacker"
                elif gamer_id == self.attack_handler.target_id:
                    added = self.attack_handler.add_defender_army(1, gamer_id)
                    if added <= 0:
                        return None
                    effect_summary["army_added"] = "Defender"
                else:
                    return None
            else:
                c1 = self.draw_continent_card()
                if c1 is None:
                    return None
                player.remove_strategy(strat)
                self.discarded_strategies.append(strat)
                player.add_continent(c1)
                effect_summary["drawn_continents"] = [c1.value]
                effect_summary["token_events"] = self.update_domination_tokens()

        self.check_player_eliminations()
        self.check_game_ended()
        return effect_summary

    async def recieve_data(self, command_id, data, gamer_id):
        payload = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else (data if isinstance(data, dict) else {})

        if command_id == commands.Draw_Card:
            draw_type = payload.get("draw_type", data.get("draw_type", 3) if isinstance(data, dict) else 3)
            res = self.draw_handler.draw_card(draw_type, gamer_id - 1)
            if not self.is_game_finished:
                self.game_state = RiskGameState.SELECTACTION
            return res

        elif command_id == commands.Pass_Turn:
            if self.attack_handler.is_attack_active and self.attack_handler.battle_started:
                self.attack_handler.stop_attack()
            # In official Risk Strike, a player draws 1 Tactic/Strategy card at end of turn if they did not attack
            res = self.draw_handler.draw_card(4, gamer_id - 1) if not self.attacked_this_turn else []
            return res

        elif command_id == commands.Declare_Attack:
            src_c = payload.get("source_continent", data.get("source_continent") if isinstance(data, dict) else None)
            tgt_c = payload.get("target_continent", data.get("target_continent") if isinstance(data, dict) else None)
            tgt_idx = payload.get("target_index", data.get("target_index") if isinstance(data, dict) else None)
            is_attack_valid = self.attack_handler.declare_war(src_c, tgt_c, tgt_idx)
            if is_attack_valid:
                self.game_state = RiskGameState.ATTACKERARMY
            return is_attack_valid

        elif command_id == commands.AttackerArmy:
            if self.attack_handler.battle_started:
                return 0
            cnt = payload.get("count", data.get("count", 0) if isinstance(data, dict) else 0)
            added = self.attack_handler.add_attacker_army(cnt, gamer_id)
            self.game_state = RiskGameState.DEFENDERARMY
            return added

        elif command_id == commands.DefenderArmy:
            if payload.get("cancel") or (isinstance(data, dict) and data.get("cancel")):
                if self.attack_handler.cancel_attack_by_card(gamer_id):
                    return self.attack_handler.last_battle_result
            if self.attack_handler.battle_started:
                return None
            cnt = payload.get("count", data.get("count", 0) if isinstance(data, dict) else 0)
            self.attack_handler.add_defender_army(cnt, gamer_id)
            return self.attack_handler.resolve_attack()

        elif command_id == commands.QuestArmy:
            if self.attack_handler.battle_started:
                return 0
            q_type = payload.get("type", data.get("type", "Attacker") if isinstance(data, dict) else "Attacker")
            cnt = payload.get("count", data.get("count", 0) if isinstance(data, dict) else 0)
            if str(q_type).lower() == "defender":
                return self.attack_handler.add_defender_army(cnt, gamer_id)
            else:
                return self.attack_handler.add_attacker_army(cnt, gamer_id)

        elif command_id in (commands.Attack, commands.Roll_Dice):
            if self.attack_handler.is_attack_active:
                if payload.get("stop") or (isinstance(data, dict) and data.get("stop")):
                    return self.attack_handler.stop_attack()
                return self.attack_handler.resolve_attack()
            return None

        elif command_id == getattr(commands, "Cancel_Attack", "CancelAttack"):
            if (
                self.attack_handler.is_attack_active
                and self.attack_handler.battle_started
                and gamer_id == (self.attack_handler.source_id + 1)
                and (
                    payload.get("stop")
                    or (isinstance(data, dict) and data.get("stop"))
                    or not self.players_data[gamer_id - 1].has_strategy(RiskStrategyModel.CANCEL)
                )
            ):
                return self.attack_handler.stop_attack()
            if self.attack_handler.cancel_attack_by_card(gamer_id):
                return self.attack_handler.last_battle_result
            return None

        elif command_id in (getattr(commands, "Use_Strategy", "UseStrategy"), commands.Select_Peace):
            return self.use_strategy_card(gamer_id, payload)

        return True

    def change_turn(self):
        self.attacked_this_turn = False
        self.attacks_this_turn = 0
        self.ignore_adjacency = False
        self.pending_attacker_canon_bonus = 0
        self.attack_handler.reset()
        self.game_state = RiskGameState.DRAW
        super().change_turn()

    def _apply_risk_surrender_sync(self, gamer_id: int) -> bool:
        if gamer_id not in self.active_player_indexes:
            return False
        if 1 <= gamer_id <= len(self.players_data):
            p = self.players_data[gamer_id - 1]
            for t in list(p.tokens):
                p.remove_token(t)
                if t not in self.tokens:
                    self.tokens.append(t)
            for c_name, cnt in list(p.continents.items()):
                c_mod = RiskContinentModel.data_to_model(c_name)
                if c_mod is not None and cnt > 0:
                    self.return_continent_cards_to_table(c_mod, cnt)
            for s_mod in list(p.strategies):
                self.discarded_strategies.append(s_mod)
            p.clear()

        if self.attack_handler.is_attack_active:
            if gamer_id in (self.attack_handler.source_id + 1, self.attack_handler.target_id):
                self.attack_handler.reset()
                if not self.is_game_finished:
                    self.game_state = RiskGameState.SELECTACTION

        res = self._apply_surrender_sync(gamer_id)
        self.update_domination_tokens()
        self.check_game_ended()
        return res

    async def surrender(self, gamer_id):
        return self._apply_risk_surrender_sync(gamer_id)

    def finish_reconnect_time(self, gamer_id):
        self._apply_risk_surrender_sync(gamer_id)

    def check_authority(self, data, gamer_id: int) -> bool:
        if self.is_game_finished:
            return False
        if not isinstance(data, dict) or "id" not in data:
            return False
        if gamer_id not in self.active_player_indexes:
            return False

        cmd_id = data["id"]
        payload = data.get("data") if isinstance(data.get("data"), dict) else data

        if cmd_id == commands.DefenderArmy:
            if (
                self.attack_handler.is_attack_active
                and gamer_id == self.attack_handler.target_id
                and (payload.get("cancel") or (isinstance(data, dict) and data.get("cancel")))
                and self.players_data[gamer_id - 1].has_strategy(RiskStrategyModel.CANCEL)
            ):
                return True
            return (
                self.attack_handler.is_attack_active
                and not self.attack_handler.battle_started
                and self.game_state in (RiskGameState.DECLAREATTACK, RiskGameState.ATTACKERARMY, RiskGameState.DEFENDERARMY)
                and gamer_id == self.attack_handler.target_id
            )

        if cmd_id == getattr(commands, "Cancel_Attack", "CancelAttack"):
            if (
                self.attack_handler.is_attack_active
                and self.attack_handler.battle_started
                and gamer_id == (self.attack_handler.source_id + 1)
            ):
                return True
            return (
                self.attack_handler.is_attack_active
                and gamer_id in (self.attack_handler.target_id, self.attack_handler.source_id + 1)
                and self.players_data[gamer_id - 1].has_strategy(RiskStrategyModel.CANCEL)
            )

        if cmd_id == commands.QuestArmy:
            return (
                self.attack_handler.is_attack_active
                and not self.attack_handler.battle_started
                and gamer_id in (self.attack_handler.source_id + 1, self.attack_handler.target_id)
                and self.players_data[gamer_id - 1].has_strategy(RiskStrategyModel.ARMY)
            )

        if cmd_id in (getattr(commands, "Use_Strategy", "UseStrategy"), commands.Select_Peace):
            raw_strat = payload.get("strategy", payload.get("card", payload.get("type"))) if isinstance(payload, dict) else None
            strat = RiskStrategyModel.data_to_model(raw_strat)
            if strat is None or not self.players_data[gamer_id - 1].has_strategy(strat):
                return False
            if self.attack_handler.is_attack_active:
                if gamer_id in (self.attack_handler.source_id + 1, self.attack_handler.target_id):
                    if strat == RiskStrategyModel.ARMY and self.attack_handler.battle_started:
                        return False
                    return strat in (RiskStrategyModel.CANCEL, RiskStrategyModel.CANON, RiskStrategyModel.ARMY)
                return False
            if self.current_turn != gamer_id:
                return False
            if strat == RiskStrategyModel.CANCEL:
                return False
            return self.game_state in (RiskGameState.DRAWRESULT, RiskGameState.SELECTACTION, RiskGameState.ACTIONRESULT)

        # All other commands require it to be `gamer_id`'s turn
        if self.current_turn != gamer_id:
            return False

        if cmd_id == commands.Draw_Card:
            if self.attack_handler.is_attack_active:
                return False
            raw_dt = payload.get("draw_type", data.get("draw_type", 3)) if isinstance(payload, dict) else 3
            try:
                dt = int(raw_dt)
            except (TypeError, ValueError):
                return False
            return dt in (1, 2, 3) and self.game_state in (RiskGameState.STARTGAME, RiskGameState.DRAW)

        if cmd_id == commands.Declare_Attack:
            if self.attack_handler.is_attack_active or self.attacked_this_turn:
                return False
            if self.game_state not in (RiskGameState.DRAWRESULT, RiskGameState.SELECTACTION, RiskGameState.ACTIONRESULT):
                return False
            src_c = payload.get("source_continent", data.get("source_continent")) if isinstance(payload, dict) else None
            tgt_c = payload.get("target_continent", data.get("target_continent")) if isinstance(payload, dict) else None
            tgt_idx = payload.get("target_index", data.get("target_index")) if isinstance(payload, dict) else None
            src_m = RiskContinentModel.data_to_model(src_c)
            tgt_m = RiskContinentModel.data_to_model(tgt_c)
            return self.attack_handler.check_declare_is_valid(src_m, tgt_m, tgt_idx, attacker_idx=gamer_id - 1)

        if cmd_id == commands.AttackerArmy:
            return (
                self.attack_handler.is_attack_active
                and not self.attack_handler.battle_started
                and gamer_id == (self.attack_handler.source_id + 1)
                and self.game_state in (RiskGameState.DECLAREATTACK, RiskGameState.ATTACKERARMY)
            )

        if cmd_id in (commands.Attack, commands.Roll_Dice):
            return self.attack_handler.is_attack_active

        if cmd_id == commands.Pass_Turn:
            if self.attack_handler.is_attack_active and not self.attack_handler.battle_started:
                return False
            return self.game_state in (
                RiskGameState.DRAWRESULT,
                RiskGameState.SELECTACTION,
                RiskGameState.ACTIONRESULT,
                RiskGameState.ATTACK,
            )

        return False
