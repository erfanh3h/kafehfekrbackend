import random
from typing import Any, Dict, List, Optional, Tuple
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass

STARTING_CASH = 1500
GO_SALARY = 200
JAIL_BAIL = 50
JAIL_TILE_ID = 8
GO_TO_JAIL_TILE_ID = 24
BOARD_SIZE = 32
MAX_ROUNDS = 100

BOARD_TILES: List[Dict[str, Any]] = [
    {"id": 0, "name": "شروع", "type": "corner", "subtype": "go", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 1, "name": "مولوی", "type": "street", "subtype": "street", "group": "brown", "price": 60, "house_cost": 50, "rents": [4, 20, 60, 180, 320, 450], "tax_amount": 0},
    {"id": 2, "name": "صندوق شانس", "type": "chest", "subtype": "chest", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 3, "name": "بازار بزرگ", "type": "street", "subtype": "street", "group": "brown", "price": 60, "house_cost": 50, "rents": [6, 30, 90, 270, 400, 550], "tax_amount": 0},
    {"id": 4, "name": "مالیات درآمد", "type": "tax", "subtype": "tax", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 150},
    {"id": 5, "name": "راه‌آهن جنوب", "type": "railroad", "subtype": "railroad", "group": "railroad", "price": 200, "house_cost": 0, "rents": [25, 50, 100, 200], "tax_amount": 0},
    {"id": 6, "name": "لاله‌زار", "type": "street", "subtype": "street", "group": "light_blue", "price": 100, "house_cost": 50, "rents": [8, 40, 100, 300, 450, 600], "tax_amount": 0},
    {"id": 7, "name": "بهارستان", "type": "street", "subtype": "street", "group": "light_blue", "price": 120, "house_cost": 50, "rents": [10, 50, 150, 450, 625, 750], "tax_amount": 0},
    {"id": 8, "name": "زندان", "type": "corner", "subtype": "jail", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 9, "name": "ولیعصر", "type": "street", "subtype": "street", "group": "pink", "price": 140, "house_cost": 100, "rents": [12, 60, 180, 500, 700, 900], "tax_amount": 0},
    {"id": 10, "name": "نیروگاه برق", "type": "utility", "subtype": "utility", "group": "utility", "price": 150, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 11, "name": "بلوار کشاورز", "type": "street", "subtype": "street", "group": "pink", "price": 160, "house_cost": 100, "rents": [14, 70, 200, 550, 750, 950], "tax_amount": 0},
    {"id": 12, "name": "کارت شانس", "type": "chance", "subtype": "chance", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 13, "name": "راه‌آهن غرب", "type": "railroad", "subtype": "railroad", "group": "railroad", "price": 200, "house_cost": 0, "rents": [25, 50, 100, 200], "tax_amount": 0},
    {"id": 14, "name": "جردن", "type": "street", "subtype": "street", "group": "orange", "price": 180, "house_cost": 100, "rents": [16, 80, 220, 600, 800, 1000], "tax_amount": 0},
    {"id": 15, "name": "میدان ونک", "type": "street", "subtype": "street", "group": "orange", "price": 200, "house_cost": 100, "rents": [18, 90, 250, 700, 875, 1050], "tax_amount": 0},
    {"id": 16, "name": "پارکینگ آزاد", "type": "corner", "subtype": "free_parking", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 17, "name": "سعادت‌آباد", "type": "street", "subtype": "street", "group": "red", "price": 220, "house_cost": 150, "rents": [20, 100, 300, 750, 925, 1100], "tax_amount": 0},
    {"id": 18, "name": "کارت شانس", "type": "chance", "subtype": "chance", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 19, "name": "شهرک غرب", "type": "street", "subtype": "street", "group": "red", "price": 240, "house_cost": 150, "rents": [22, 110, 330, 800, 975, 1150], "tax_amount": 0},
    {"id": 20, "name": "راه‌آهن شمال", "type": "railroad", "subtype": "railroad", "group": "railroad", "price": 200, "house_cost": 0, "rents": [25, 50, 100, 200], "tax_amount": 0},
    {"id": 21, "name": "اندرزگو", "type": "street", "subtype": "street", "group": "yellow", "price": 260, "house_cost": 150, "rents": [24, 120, 360, 850, 1025, 1200], "tax_amount": 0},
    {"id": 22, "name": "شرکت آب", "type": "utility", "subtype": "utility", "group": "utility", "price": 150, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 23, "name": "نیاوران", "type": "street", "subtype": "street", "group": "yellow", "price": 280, "house_cost": 150, "rents": [26, 130, 390, 900, 1100, 1275], "tax_amount": 0},
    {"id": 24, "name": "برو به زندان", "type": "corner", "subtype": "go_to_jail", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 25, "name": "الهیه", "type": "street", "subtype": "street", "group": "green", "price": 300, "house_cost": 200, "rents": [28, 150, 450, 1000, 1200, 1400], "tax_amount": 0},
    {"id": 26, "name": "صندوق شانس", "type": "chest", "subtype": "chest", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 0},
    {"id": 27, "name": "زعفرانیه", "type": "street", "subtype": "street", "group": "green", "price": 320, "house_cost": 200, "rents": [30, 160, 480, 1050, 1275, 1450], "tax_amount": 0},
    {"id": 28, "name": "راه‌آهن شرق", "type": "railroad", "subtype": "railroad", "group": "railroad", "price": 200, "house_cost": 0, "rents": [25, 50, 100, 200], "tax_amount": 0},
    {"id": 29, "name": "فرشته", "type": "street", "subtype": "street", "group": "dark_blue", "price": 350, "house_cost": 200, "rents": [35, 175, 500, 1100, 1300, 1500], "tax_amount": 0},
    {"id": 30, "name": "مالیات لوکس", "type": "tax", "subtype": "tax", "group": "", "price": 0, "house_cost": 0, "rents": [], "tax_amount": 100},
    {"id": 31, "name": "تجریش", "type": "street", "subtype": "street", "group": "dark_blue", "price": 400, "house_cost": 200, "rents": [50, 200, 600, 1400, 1700, 2000], "tax_amount": 0},
]

STREET_GROUPS: Dict[str, List[int]] = {
    "brown": [1, 3],
    "light_blue": [6, 7],
    "pink": [9, 11],
    "orange": [14, 15],
    "red": [17, 19],
    "yellow": [21, 23],
    "green": [25, 27],
    "dark_blue": [29, 31],
}

RAILROAD_IDS: Tuple[int, ...] = (5, 13, 20, 28)
UTILITY_IDS: Tuple[int, ...] = (10, 22)
PURCHASABLE_TYPES: Tuple[str, ...] = ("street", "railroad", "utility")

CHANCE_CARDS: List[Dict[str, Any]] = [
    {"id": "ch_go", "title": "پرواز به خط شروع!", "desc": "مستقیم به خانه شروع بروید و ۲۰۰$ جایزه بگیرید.", "effect": "move_to", "target": 0, "collect_go": True},
    {"id": "ch_tajrish", "title": "دعوت ویژه در تجریش", "desc": "به خیابان تجریش بروید. اگر از شروع عبور کردید ۲۰۰$ بگیرید.", "effect": "move_to", "target": 31, "collect_go": True},
    {"id": "ch_jordan", "title": "دیدار تجاری در جردن", "desc": "به خیابان جردن بروید. اگر از شروع عبور کردید ۲۰۰$ بگیرید.", "effect": "move_to", "target": 14, "collect_go": True},
    {"id": "ch_rail", "title": "سفر با قطار سریع‌السیر", "desc": "به نزدیک‌ترین ایستگاه راه‌آهن بروید.", "effect": "nearest_railroad"},
    {"id": "ch_back3", "title": "ترافیک ناگهانی!", "desc": "۳ خانه به عقب برگردید.", "effect": "move_rel", "delta": -3},
    {"id": "ch_jail", "title": "حکم بازداشت!", "desc": "مستقیم به زندان بروید و از پاداش شروع خبری نیست.", "effect": "go_to_jail"},
    {"id": "ch_jail_free", "title": "کارت عفو ویژه", "desc": "این کارت را نگه دارید تا هر زمان خواستید رایگان از زندان آزاد شوید.", "effect": "jail_card"},
    {"id": "ch_dividend", "title": "سود سهام بانک", "desc": "بانک ۱۵۰$ سود سهام به شما پرداخت می‌کند.", "effect": "cash", "amount": 150},
    {"id": "ch_speeding", "title": "جریمه سرعت غیرمجاز", "desc": "۵۰$ جریمه به بانک بپردازید.", "effect": "pay", "amount": 50},
    {"id": "ch_repairs", "title": "نوسازی املاک", "desc": "به ازای هر خانه ۲۵$ و هر هتل ۱۰۰$ هزینه تعمیر بپردازید.", "effect": "repairs", "house": 25, "hotel": 100},
    {"id": "ch_gift_all", "title": "سرمایه‌گذاری موفق", "desc": "از هر بازیکن فعال ۲۵$ دریافت کنید.", "effect": "collect_each", "amount": 25},
    {"id": "ch_bonus_100", "title": "برنده قرعه‌کشی بازار", "desc": "۱۰۰$ جایزه نقدی دریافت کنید.", "effect": "cash", "amount": 100},
]

CHEST_CARDS: List[Dict[str, Any]] = [
    {"id": "cc_go", "title": "بازگشت به خانه شروع", "desc": "به خانه شروع بروید و ۲۰۰$ دریافت کنید.", "effect": "move_to", "target": 0, "collect_go": True},
    {"id": "cc_bank_err", "title": "اشتباه بانکی به نفع شما!", "desc": "۲۰۰$ به حساب شما واریز شد.", "effect": "cash", "amount": 200},
    {"id": "cc_tax_refund", "title": "بازگشت مالیات", "desc": "۷۵$ بازپرداخت مالیات دریافت کنید.", "effect": "cash", "amount": 75},
    {"id": "cc_doctor", "title": "هزینه بیمه و درمان", "desc": "۵۰$ به بانک پرداخت کنید.", "effect": "pay", "amount": 50},
    {"id": "cc_school", "title": "هزینه ثبت‌نام", "desc": "۱۰۰$ هزینه اداری بپردازید.", "effect": "pay", "amount": 100},
    {"id": "cc_inherit", "title": "ارثیه خانوادگی", "desc": "۱۰۰$ جایزه دریافت کنید.", "effect": "cash", "amount": 100},
    {"id": "cc_birthday", "title": "جشن تولد شماست!", "desc": "هر بازیکن فعال ۲۵$ هدیه به شما می‌دهد.", "effect": "collect_each", "amount": 25},
    {"id": "cc_jail_free", "title": "کارت آزادی از زندان", "desc": "این کارت شما را از زندان نجات می‌دهد.", "effect": "jail_card"},
    {"id": "cc_jail", "title": "بازرسی ناگهانی!", "desc": "مستقیم به زندان بروید.", "effect": "go_to_jail"},
    {"id": "cc_beauty", "title": "جایزه طراحی معماری", "desc": "۵۰$ جایزه دریافت کنید.", "effect": "cash", "amount": 50},
    {"id": "cc_street_repairs", "title": "عوارض نوسازی شهری", "desc": "به ازای هر خانه ۲۰$ و هر هتل ۸۰$ پرداخت کنید.", "effect": "repairs", "house": 20, "hotel": 80},
    {"id": "cc_sale", "title": "فروش موفق سهام", "desc": "۱۲۵$ سود خالص دریافت کنید.", "effect": "cash", "amount": 125},
]


class MonopolyGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count: int = 2):
        super().__init__(send_data_function, players_count)
        self.players_count = max(2, min(4, int(players_count)))
        self.active_player_indexes: List[int] = [i for i in range(1, self.players_count + 1)]
        self.eliminated_order: List[int] = []

        self.cash: Dict[int, int] = {i: STARTING_CASH for i in range(1, self.players_count + 1)}
        self.positions: Dict[int, int] = {i: 0 for i in range(1, self.players_count + 1)}
        self.in_jail: Dict[int, bool] = {i: False for i in range(1, self.players_count + 1)}
        self.jail_turns: Dict[int, int] = {i: 0 for i in range(1, self.players_count + 1)}
        self.jail_cards: Dict[int, int] = {i: 0 for i in range(1, self.players_count + 1)}
        self.doubles_streak: Dict[int, int] = {i: 0 for i in range(1, self.players_count + 1)}
        self.bankrupt: Dict[int, bool] = {i: False for i in range(1, self.players_count + 1)}

        self.tile_owners: Dict[int, int] = {i: 0 for i in range(BOARD_SIZE)}
        self.tile_houses: Dict[int, int] = {i: 0 for i in range(BOARD_SIZE)}
        self.tile_mortgaged: Dict[int, bool] = {i: False for i in range(BOARD_SIZE)}

        self.chance_deck: List[Dict[str, Any]] = []
        self.chest_deck: List[Dict[str, Any]] = []
        self._refill_decks()

        self.current_turn: int = 1
        self.round_number: int = 1
        self.phase: str = "roll"  # roll | buy_or_auction | auction | debt | manage | trade | finished
        self.state_seq: int = 1
        self.last_dice: List[int] = [0, 0]
        self.last_event: Optional[Dict[str, Any]] = None
        self.last_card: Optional[Dict[str, Any]] = None

        self.pending_tile_id: int = -1
        self.auction: Optional[Dict[str, Any]] = None
        self.debt: Optional[Dict[str, Any]] = None
        self.pending_trade: Optional[Dict[str, Any]] = None
        self.trades_this_turn: int = 0
        self._pending_bonus_doubles: bool = False

    def _refill_decks(self):
        if not self.chance_deck:
            self.chance_deck = [dict(c) for c in CHANCE_CARDS]
            random.shuffle(self.chance_deck)
        if not self.chest_deck:
            self.chest_deck = [dict(c) for c in CHEST_CARDS]
            random.shuffle(self.chest_deck)

    def _draw_card(self, deck_type: str) -> Dict[str, Any]:
        self._refill_decks()
        if deck_type == "chance":
            if not self.chance_deck:
                self.chance_deck = [dict(c) for c in CHANCE_CARDS]
                random.shuffle(self.chance_deck)
            return self.chance_deck.pop(0)
        if not self.chest_deck:
            self.chest_deck = [dict(c) for c in CHEST_CARDS]
            random.shuffle(self.chest_deck)
        return self.chest_deck.pop(0)

    def _bump_seq(self):
        self.state_seq += 1

    # ------------------------------------------------------------------
    # Property & Economics Helpers
    # ------------------------------------------------------------------
    def owns_full_group(self, player_id: int, group: str) -> bool:
        tids = STREET_GROUPS.get(group)
        if not tids or player_id <= 0:
            return False
        return all(self.tile_owners.get(tid, 0) == player_id for tid in tids)

    def group_has_any_mortgaged(self, group: str) -> bool:
        for tid in STREET_GROUPS.get(group, []):
            if self.tile_mortgaged.get(tid, False):
                return True
        return False

    def group_has_any_houses(self, group: str) -> bool:
        for tid in STREET_GROUPS.get(group, []):
            if self.tile_houses.get(tid, 0) > 0:
                return True
        return False

    def get_buildable_tiles(self, player_id: int) -> List[int]:
        if player_id not in self.active_player_indexes:
            return []
        res: List[int] = []
        player_cash = int(self.cash.get(player_id, 0))
        for group, tids in STREET_GROUPS.items():
            if not self.owns_full_group(player_id, group):
                continue
            if self.group_has_any_mortgaged(group):
                continue
            min_h = min(self.tile_houses.get(tid, 0) for tid in tids)
            for tid in tids:
                h = self.tile_houses.get(tid, 0)
                cost = int(BOARD_TILES[tid]["house_cost"])
                if h < 5 and h <= min_h and player_cash >= cost:
                    res.append(tid)
        return res

    def get_sellable_house_tiles(self, player_id: int) -> List[int]:
        if player_id not in self.active_player_indexes:
            return []
        res: List[int] = []
        for group, tids in STREET_GROUPS.items():
            if not self.owns_full_group(player_id, group):
                continue
            max_h = max(self.tile_houses.get(tid, 0) for tid in tids)
            if max_h <= 0:
                continue
            for tid in tids:
                h = self.tile_houses.get(tid, 0)
                if h > 0 and h >= max_h:
                    res.append(tid)
        return res

    def get_mortgageable_tiles(self, player_id: int) -> List[int]:
        if player_id not in self.active_player_indexes:
            return []
        res: List[int] = []
        for tid in range(BOARD_SIZE):
            if self.tile_owners.get(tid, 0) != player_id or self.tile_mortgaged.get(tid, False):
                continue
            tile = BOARD_TILES[tid]
            if tile["type"] == "street" and self.group_has_any_houses(tile["group"]):
                continue
            res.append(tid)
        return res

    def get_unmortgageable_tiles(self, player_id: int) -> List[int]:
        if player_id not in self.active_player_indexes:
            return []
        res: List[int] = []
        player_cash = int(self.cash.get(player_id, 0))
        for tid in range(BOARD_SIZE):
            if self.tile_owners.get(tid, 0) == player_id and self.tile_mortgaged.get(tid, False):
                cost = self.get_unmortgage_cost(tid)
                if player_cash >= cost:
                    res.append(tid)
        return res

    def get_mortgage_value(self, tile_id: int) -> int:
        return int(BOARD_TILES[tile_id]["price"]) // 2

    def get_unmortgage_cost(self, tile_id: int) -> int:
        m_val = self.get_mortgage_value(tile_id)
        return int(round(m_val * 1.1))

    def calculate_rent(self, tile_id: int, dice_sum: int) -> int:
        owner = self.tile_owners.get(tile_id, 0)
        if owner <= 0 or self.tile_mortgaged.get(tile_id, False):
            return 0
        tile = BOARD_TILES[tile_id]
        t_type = tile["type"]
        if t_type == "street":
            houses = self.tile_houses.get(tile_id, 0)
            rents = tile["rents"]
            if houses == 0:
                base = int(rents[0])
                if self.owns_full_group(owner, tile["group"]) and not self.group_has_any_mortgaged(tile["group"]):
                    return base * 2
                return base
            return int(rents[min(houses, len(rents) - 1)])
        if t_type == "railroad":
            cnt = sum(
                1 for rid in RAILROAD_IDS
                if self.tile_owners.get(rid, 0) == owner and not self.tile_mortgaged.get(rid, False)
            )
            if cnt <= 0:
                return 0
            return 25 * (2 ** (cnt - 1))
        if t_type == "utility":
            cnt = sum(
                1 for uid in UTILITY_IDS
                if self.tile_owners.get(uid, 0) == owner and not self.tile_mortgaged.get(uid, False)
            )
            if cnt <= 0:
                return 0
            mult = 10 if cnt >= 2 else 4
            return mult * max(2, int(dice_sum))
        return 0

    def get_player_liquidation_value(self, player_id: int) -> int:
        total = max(0, int(self.cash.get(player_id, 0)))
        for tid in range(BOARD_SIZE):
            if self.tile_owners.get(tid, 0) == player_id:
                h = self.tile_houses.get(tid, 0)
                if h > 0:
                    total += h * (int(BOARD_TILES[tid]["house_cost"]) // 2)
                if not self.tile_mortgaged.get(tid, False):
                    total += self.get_mortgage_value(tid)
        return total

    def get_player_net_worth(self, player_id: int) -> int:
        if self.bankrupt.get(player_id, False):
            return -1
        total = int(self.cash.get(player_id, 0))
        for tid in range(BOARD_SIZE):
            if self.tile_owners.get(tid, 0) == player_id:
                tile = BOARD_TILES[tid]
                if self.tile_mortgaged.get(tid, False):
                    total += self.get_mortgage_value(tid)
                else:
                    total += int(tile["price"])
                total += self.tile_houses.get(tid, 0) * int(tile["house_cost"])
        return total

    def get_tradeable_tiles(self, player_id: int) -> List[int]:
        if player_id not in self.active_player_indexes:
            return []
        res: List[int] = []
        for tid in range(BOARD_SIZE):
            if self.tile_owners.get(tid, 0) != player_id:
                continue
            tile = BOARD_TILES[tid]
            if tile["type"] == "street" and self.group_has_any_houses(tile["group"]):
                continue
            res.append(tid)
        return res

    # ------------------------------------------------------------------
    # Authority & Legal Turn Checks
    # ------------------------------------------------------------------
    def check_authority(self, data: dict, gamer_id: int) -> bool:
        if self.is_game_finished or self.phase == "finished":
            return False
        if gamer_id not in self.active_player_indexes:
            return False
        cmd_id = data.get("id")
        if self.phase == "auction":
            if cmd_id != "MonopolyAuction":
                return False
            return bool(self.auction and self.auction.get("current_bidder") == gamer_id)
        if self.phase == "trade":
            if cmd_id != "MonopolyTrade":
                return False
            if not self.pending_trade:
                return False
            act = str((data.get("data") or {}).get("action", ""))
            return act in ("accept", "reject") and self.pending_trade.get("to_player") == gamer_id
        if self.phase == "debt":
            if not self.debt or self.debt.get("player_id") != gamer_id:
                return False
            return cmd_id == "MonopolyAction"
        if gamer_id != self.current_turn:
            return False
        if self.phase == "buy_or_auction":
            return cmd_id == "MonopolyAction"
        if self.phase in ("roll", "manage"):
            return cmd_id in ("MonopolyRoll", "MonopolyAction", "MonopolyTrade")
        return False

    # ------------------------------------------------------------------
    # Debt & Bankruptcy Resolution
    # ------------------------------------------------------------------
    def _charge_player(
        self,
        player_id: int,
        amount: int,
        creditor_id: int,
        reason: str,
        next_phase_on_paid: str,
        after_jail_move_sum: int = 0,
    ) -> Dict[str, Any]:
        amount = max(0, int(amount))
        if amount == 0:
            self.phase = next_phase_on_paid
            return {"paid": True, "bankrupt": False}

        if int(self.cash.get(player_id, 0)) >= amount:
            self.cash[player_id] -= amount
            if creditor_id > 0 and creditor_id in self.active_player_indexes:
                self.cash[creditor_id] = int(self.cash.get(creditor_id, 0)) + amount
            self.phase = next_phase_on_paid
            return {"paid": True, "bankrupt": False}

        max_liq = self.get_player_liquidation_value(player_id)
        if max_liq < amount:
            self._apply_bankruptcy(player_id, creditor_id)
            return {"paid": False, "bankrupt": True}

        # Player can pay by selling houses or mortgaging properties!
        self.phase = "debt"
        self.debt = {
            "player_id": player_id,
            "amount": amount,
            "creditor_id": creditor_id,
            "reason": reason,
            "return_phase": next_phase_on_paid,
            "after_jail_move_sum": after_jail_move_sum,
        }
        return {"paid": False, "bankrupt": False, "entered_debt": True}

    def _apply_bankruptcy(self, loser_id: int, creditor_id: int = 0):
        if loser_id not in self.active_player_indexes:
            return
        # Liquidate all houses to cash first so creditor receives fair remaining estate
        for tid in range(BOARD_SIZE):
            if self.tile_owners.get(tid, 0) == loser_id:
                h = self.tile_houses.get(tid, 0)
                if h > 0:
                    self.cash[loser_id] = int(self.cash.get(loser_id, 0)) + h * (int(BOARD_TILES[tid]["house_cost"]) // 2)
                    self.tile_houses[tid] = 0

        rem_cash = max(0, int(self.cash.get(loser_id, 0)))
        if creditor_id > 0 and creditor_id != loser_id and creditor_id in self.active_player_indexes:
            self.cash[creditor_id] = int(self.cash.get(creditor_id, 0)) + rem_cash
            self.jail_cards[creditor_id] = int(self.jail_cards.get(creditor_id, 0)) + int(self.jail_cards.get(loser_id, 0))
            for tid in range(BOARD_SIZE):
                if self.tile_owners.get(tid, 0) == loser_id:
                    self.tile_owners[tid] = creditor_id
        else:
            for tid in range(BOARD_SIZE):
                if self.tile_owners.get(tid, 0) == loser_id:
                    self.tile_owners[tid] = 0
                    self.tile_houses[tid] = 0
                    self.tile_mortgaged[tid] = False

        self.cash[loser_id] = 0
        self.jail_cards[loser_id] = 0
        self.bankrupt[loser_id] = True
        self.in_jail[loser_id] = False
        self.debt = None
        self.pending_tile_id = -1

        if loser_id not in self.eliminated_order:
            self.eliminated_order.append(loser_id)

        if len(self.active_player_indexes) == 2:
            if self.rank2 is None:
                self.rank2 = loser_id
        self.active_player_indexes.remove(loser_id)

        if len(self.active_player_indexes) == 1:
            survivor = self.active_player_indexes[0]
            if self.rank1 is None:
                self.rank1 = survivor
            if self.rank2 is None:
                self.rank2 = loser_id
            self.is_game_finished = True
            self.phase = "finished"
            return

        if self.current_turn == loser_id:
            self._advance_to_next_player()

    def _finish_game_by_net_worth(self):
        ranked = sorted(
            list(self.active_player_indexes),
            key=lambda pid: (self.get_player_net_worth(pid), int(self.cash.get(pid, 0))),
            reverse=True,
        )
        if ranked:
            self.rank1 = ranked[0]
        if len(ranked) >= 2:
            self.rank2 = ranked[1]
        elif self.eliminated_order:
            self.rank2 = self.eliminated_order[-1]
        self.is_game_finished = True
        self.phase = "finished"

    def _advance_to_next_player(self):
        if self.is_game_finished or len(self.active_player_indexes) <= 1:
            return
        prev_turn = self.current_turn
        self.doubles_streak[prev_turn] = 0
        self._pending_bonus_doubles = False
        self.pending_tile_id = -1
        self.auction = None
        self.pending_trade = None
        self.trades_this_turn = 0

        self.change_turn()
        if self.current_turn <= prev_turn:
            self.round_number += 1
            if self.round_number > MAX_ROUNDS:
                self._finish_game_by_net_worth()
                return
        self.phase = "roll"

    # ------------------------------------------------------------------
    # Movement, Cards & Landing Resolution
    # ------------------------------------------------------------------
    def _send_to_jail(self, player_id: int):
        self.positions[player_id] = JAIL_TILE_ID
        self.in_jail[player_id] = True
        self.jail_turns[player_id] = 0
        self.doubles_streak[player_id] = 0
        self._pending_bonus_doubles = False

    def _move_player_and_resolve(
        self,
        player_id: int,
        target_tile: int,
        collect_go: bool,
        dice_sum: int,
        allow_doubles_bonus: bool,
    ) -> Dict[str, Any]:
        old_pos = int(self.positions.get(player_id, 0))
        target_tile = target_tile % BOARD_SIZE
        passed_go = False
        if collect_go and target_tile <= old_pos and target_tile != old_pos:
            passed_go = True
        elif collect_go and target_tile == 0 and old_pos != 0:
            passed_go = True

        # Wait: moving forward by delta >= 0 checks wrap-around cleanly:
        path: List[int] = []
        steps = (target_tile - old_pos) % BOARD_SIZE
        if steps == 0 and dice_sum > 0:
            steps = BOARD_SIZE
        for s in range(1, steps + 1):
            t = (old_pos + s) % BOARD_SIZE
            path.append(t)
            if t == 0 and collect_go:
                passed_go = True

        if passed_go:
            self.cash[player_id] = int(self.cash.get(player_id, 0)) + GO_SALARY

        self.positions[player_id] = target_tile
        return self._resolve_tile_landing(
            player_id=player_id,
            tile_id=target_tile,
            dice_sum=dice_sum,
            allow_doubles_bonus=allow_doubles_bonus,
            passed_go=passed_go,
            path=path,
        )

    def _resolve_tile_landing(
        self,
        player_id: int,
        tile_id: int,
        dice_sum: int,
        allow_doubles_bonus: bool,
        passed_go: bool,
        path: List[int],
    ) -> Dict[str, Any]:
        tile = BOARD_TILES[tile_id]
        t_type = tile["type"]
        next_phase = "roll" if allow_doubles_bonus else "manage"
        self._pending_bonus_doubles = allow_doubles_bonus

        ev: Dict[str, Any] = {
            "event": "landed",
            "player_id": player_id,
            "tile_id": tile_id,
            "tile_name": tile["name"],
            "tile_type": t_type,
            "passed_go": passed_go,
            "path": path,
            "dice": list(self.last_dice),
        }

        if t_type == "corner":
            sub = tile["subtype"]
            if sub == "go_to_jail":
                self._send_to_jail(player_id)
                ev["event"] = "go_to_jail"
                ev["jailed"] = True
                self._advance_to_next_player()
                return ev
            self.phase = next_phase
            return ev

        if t_type == "tax":
            tax_amt = int(tile["tax_amount"])
            ev["event"] = "tax_paid"
            ev["amount"] = tax_amt
            res = self._charge_player(player_id, tax_amt, 0, f"مالیات {tile['name']}", next_phase)
            ev.update(res)
            return ev

        if t_type in ("chance", "chest"):
            card = self._draw_card(t_type)
            self.last_card = dict(card)
            ev["event"] = "card_drawn"
            ev["deck"] = t_type
            ev["card"] = dict(card)
            eff = card["effect"]

            if eff == "cash":
                amt = int(card["amount"])
                self.cash[player_id] += amt
                ev["amount"] = amt
                self.phase = next_phase
                return ev

            if eff == "pay":
                amt = int(card["amount"])
                ev["amount"] = amt
                res = self._charge_player(player_id, amt, 0, card["title"], next_phase)
                ev.update(res)
                return ev

            if eff == "jail_card":
                self.jail_cards[player_id] = int(self.jail_cards.get(player_id, 0)) + 1
                self.phase = next_phase
                return ev

            if eff == "go_to_jail":
                self._send_to_jail(player_id)
                ev["jailed"] = True
                self._advance_to_next_player()
                return ev

            if eff == "repairs":
                total_cost = 0
                for tid in range(BOARD_SIZE):
                    if self.tile_owners.get(tid, 0) == player_id:
                        h = self.tile_houses.get(tid, 0)
                        if h == 5:
                            total_cost += int(card["hotel"])
                        elif h > 0:
                            total_cost += h * int(card["house"])
                ev["amount"] = total_cost
                res = self._charge_player(player_id, total_cost, 0, card["title"], next_phase)
                ev.update(res)
                return ev

            if eff == "collect_each":
                per_p = int(card["amount"])
                collected = 0
                for op in list(self.active_player_indexes):
                    if op != player_id:
                        paid = min(per_p, max(0, int(self.cash.get(op, 0))))
                        self.cash[op] -= paid
                        collected += paid
                self.cash[player_id] += collected
                ev["amount"] = collected
                self.phase = next_phase
                return ev

            if eff == "move_to":
                dest = int(card["target"])
                sub_ev = self._move_player_and_resolve(
                    player_id=player_id,
                    target_tile=dest,
                    collect_go=bool(card.get("collect_go", True)),
                    dice_sum=dice_sum,
                    allow_doubles_bonus=allow_doubles_bonus,
                )
                ev["followup"] = sub_ev
                ev["path"] = path + sub_ev.get("path", [])
                ev["tile_id"] = sub_ev.get("tile_id", dest)
                if sub_ev.get("passed_go"):
                    ev["passed_go"] = True
                return ev

            if eff == "nearest_railroad":
                dest = next((rid for rid in RAILROAD_IDS if rid > tile_id), RAILROAD_IDS[0])
                sub_ev = self._move_player_and_resolve(
                    player_id=player_id,
                    target_tile=dest,
                    collect_go=True,
                    dice_sum=dice_sum,
                    allow_doubles_bonus=allow_doubles_bonus,
                )
                ev["followup"] = sub_ev
                ev["path"] = path + sub_ev.get("path", [])
                ev["tile_id"] = sub_ev.get("tile_id", dest)
                if sub_ev.get("passed_go"):
                    ev["passed_go"] = True
                return ev

            if eff == "move_rel":
                dest = (tile_id + int(card["delta"])) % BOARD_SIZE
                self.positions[player_id] = dest
                sub_ev = self._resolve_tile_landing(
                    player_id=player_id,
                    tile_id=dest,
                    dice_sum=dice_sum,
                    allow_doubles_bonus=allow_doubles_bonus,
                    passed_go=False,
                    path=[dest],
                )
                ev["followup"] = sub_ev
                ev["path"] = path + [dest]
                ev["tile_id"] = dest
                return ev

            self.phase = next_phase
            return ev

        if t_type in PURCHASABLE_TYPES:
            owner = self.tile_owners.get(tile_id, 0)
            if owner == 0:
                self.pending_tile_id = tile_id
                self.phase = "buy_or_auction"
                ev["event"] = "offer_purchase"
                ev["price"] = int(tile["price"])
                return ev
            if owner == player_id:
                ev["event"] = "own_property"
                self.phase = next_phase
                return ev
            # Opponent owns it!
            if self.tile_mortgaged.get(tile_id, False):
                ev["event"] = "mortgaged_no_rent"
                self.phase = next_phase
                return ev
            rent = self.calculate_rent(tile_id, dice_sum)
            ev["event"] = "rent_paid"
            ev["owner_id"] = owner
            ev["amount"] = rent
            res = self._charge_player(player_id, rent, owner, f"اجاره {tile['name']}", next_phase)
            ev.update(res)
            return ev

        self.phase = next_phase
        return ev

    # ------------------------------------------------------------------
    # Auction Starter & Helpers
    # ------------------------------------------------------------------
    def _start_auction(self, tile_id: int) -> Dict[str, Any]:
        order: List[int] = []
        for step in range(1, self.players_count + 1):
            cand = ((self.current_turn - 1 + step) % self.players_count) + 1
            if cand in self.active_player_indexes and int(self.cash.get(cand, 0)) >= 10:
                order.append(cand)
        if not order:
            self.pending_tile_id = -1
            self.auction = None
            self.phase = "roll" if self._pending_bonus_doubles else "manage"
            return {"event": "auction_skipped_no_funds", "tile_id": tile_id}

        self.phase = "auction"
        self.auction = {
            "tile_id": tile_id,
            "tile_name": BOARD_TILES[tile_id]["name"],
            "tile_price": int(BOARD_TILES[tile_id]["price"]),
            "current_bid": 0,
            "highest_bidder": 0,
            "eligible": order,
            "passed": [],
            "current_bidder": order[0],
        }
        return {"event": "auction_started", "tile_id": tile_id, "current_bidder": order[0]}

    def _advance_auction_bidder(self):
        if not self.auction:
            return
        elig = self.auction["eligible"]
        passed = set(self.auction["passed"])
        remaining = [pid for pid in elig if pid not in passed and pid in self.active_player_indexes]
        highest_bidder = int(self.auction.get("highest_bidder", 0))

        # Winner found: only 1 remaining bidder and they hold the highest bid
        if len(remaining) == 1 and highest_bidder == remaining[0]:
            winner = remaining[0]
            bid = int(self.auction["current_bid"])
            tid = int(self.auction["tile_id"])
            self.cash[winner] -= bid
            self.tile_owners[tid] = winner
            self.pending_tile_id = -1
            self.auction = None
            self.phase = "roll" if self._pending_bonus_doubles else "manage"
            self.last_event = {
                "event": "auction_won",
                "winner_id": winner,
                "tile_id": tid,
                "tile_name": BOARD_TILES[tid]["name"],
                "amount": bid,
            }
            return

        if not remaining:
            tid = int(self.auction["tile_id"])
            self.pending_tile_id = -1
            self.auction = None
            self.phase = "roll" if self._pending_bonus_doubles else "manage"
            self.last_event = {
                "event": "auction_unsold",
                "tile_id": tid,
                "tile_name": BOARD_TILES[tid]["name"],
            }
            return

        # Find next non-passed bidder after current_bidder
        cur = int(self.auction.get("current_bidder", elig[0]))
        idx = elig.index(cur) if cur in elig else 0
        for step in range(1, len(elig) + 1):
            nxt = elig[(idx + step) % len(elig)]
            if nxt in remaining:
                self.auction["current_bidder"] = nxt
                return
        self.auction["current_bidder"] = remaining[0]

    # ------------------------------------------------------------------
    # Command Handlers
    # ------------------------------------------------------------------
    def roll_dice_action(self, player_id: int) -> Dict[str, Any]:
        if self.phase != "roll" or player_id != self.current_turn:
            return {}
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.last_dice = [d1, d2]
        dice_sum = d1 + d2
        is_doubles = (d1 == d2)

        if self.in_jail.get(player_id, False):
            if is_doubles:
                self.in_jail[player_id] = False
                self.jail_turns[player_id] = 0
                self.doubles_streak[player_id] = 0
                ev = self._move_player_and_resolve(
                    player_id=player_id,
                    target_tile=(self.positions[player_id] + dice_sum) % BOARD_SIZE,
                    collect_go=True,
                    dice_sum=dice_sum,
                    allow_doubles_bonus=False,
                )
                ev["jail_freed_doubles"] = True
                ev["dice"] = [d1, d2]
                self._bump_seq()
                self.last_event = ev
                return ev

            self.jail_turns[player_id] = int(self.jail_turns.get(player_id, 0)) + 1
            if self.jail_turns[player_id] >= 3:
                # Mandatory 3rd-turn bail payment of $50, then move dice_sum
                if int(self.cash.get(player_id, 0)) >= JAIL_BAIL:
                    self.cash[player_id] -= JAIL_BAIL
                    self.in_jail[player_id] = False
                    self.jail_turns[player_id] = 0
                    ev = self._move_player_and_resolve(
                        player_id=player_id,
                        target_tile=(self.positions[player_id] + dice_sum) % BOARD_SIZE,
                        collect_go=True,
                        dice_sum=dice_sum,
                        allow_doubles_bonus=False,
                    )
                    ev["jail_forced_bail"] = True
                    ev["dice"] = [d1, d2]
                    self._bump_seq()
                    self.last_event = ev
                    return ev
                # Try liquidation or bankrupt
                res = self._charge_player(player_id, JAIL_BAIL, 0, "وثیقه اجباری زندان", "manage", after_jail_move_sum=dice_sum)
                if res.get("bankrupt"):
                    ev = {"event": "bankrupt", "player_id": player_id, "dice": [d1, d2], "reason": "عدم توانایی پرداخت وثیقه زندان"}
                    self._bump_seq()
                    self.last_event = ev
                    return ev
                self.in_jail[player_id] = False
                self.jail_turns[player_id] = 0
                ev = {"event": "jail_debt", "player_id": player_id, "dice": [d1, d2], "amount": JAIL_BAIL}
                self._bump_seq()
                self.last_event = ev
                return ev

            # Stay in jail -> end turn
            ev = {
                "event": "jail_stay",
                "player_id": player_id,
                "dice": [d1, d2],
                "jail_turns": self.jail_turns[player_id],
            }
            self._advance_to_next_player()
            self._bump_seq()
            self.last_event = ev
            return ev

        # Normal roll outside jail
        if is_doubles:
            self.doubles_streak[player_id] = int(self.doubles_streak.get(player_id, 0)) + 1
            if self.doubles_streak[player_id] >= 3:
                self._send_to_jail(player_id)
                ev = {
                    "event": "three_doubles_jail",
                    "player_id": player_id,
                    "dice": [d1, d2],
                    "jailed": True,
                }
                self._advance_to_next_player()
                self._bump_seq()
                self.last_event = ev
                return ev
        else:
            self.doubles_streak[player_id] = 0

        old_pos = int(self.positions.get(player_id, 0))
        dest = (old_pos + dice_sum) % BOARD_SIZE
        ev = self._move_player_and_resolve(
            player_id=player_id,
            target_tile=dest,
            collect_go=True,
            dice_sum=dice_sum,
            allow_doubles_bonus=is_doubles,
        )
        ev["dice"] = [d1, d2]
        ev["is_doubles"] = is_doubles
        self._bump_seq()
        self.last_event = ev
        return ev

    def submit_action(self, player_id: int, action: str, payload: dict) -> Dict[str, Any]:
        if action == "roll_jail":
            return self.roll_dice_action(player_id)

        if action == "pay_bail":
            if self.phase != "roll" or not self.in_jail.get(player_id, False):
                return {}
            if int(self.cash.get(player_id, 0)) < JAIL_BAIL:
                return {}
            self.cash[player_id] -= JAIL_BAIL
            self.in_jail[player_id] = False
            self.jail_turns[player_id] = 0
            ev = {"event": "bail_paid", "player_id": player_id, "amount": JAIL_BAIL}
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "use_jail_card":
            if self.phase != "roll" or not self.in_jail.get(player_id, False):
                return {}
            if int(self.jail_cards.get(player_id, 0)) <= 0:
                return {}
            self.jail_cards[player_id] -= 1
            self.in_jail[player_id] = False
            self.jail_turns[player_id] = 0
            ev = {"event": "jail_card_used", "player_id": player_id}
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "buy_property":
            if self.phase != "buy_or_auction" or self.pending_tile_id < 0:
                return {}
            tid = self.pending_tile_id
            price = int(BOARD_TILES[tid]["price"])
            if int(self.cash.get(player_id, 0)) < price or self.tile_owners.get(tid, 0) != 0:
                return {}
            self.cash[player_id] -= price
            self.tile_owners[tid] = player_id
            self.pending_tile_id = -1
            self.phase = "roll" if self._pending_bonus_doubles else "manage"
            ev = {
                "event": "property_bought",
                "player_id": player_id,
                "tile_id": tid,
                "tile_name": BOARD_TILES[tid]["name"],
                "amount": price,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "decline_buy":
            if self.phase != "buy_or_auction" or self.pending_tile_id < 0:
                return {}
            tid = self.pending_tile_id
            ev = self._start_auction(tid)
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "build_house":
            if self.phase not in ("roll", "manage"):
                return {}
            tid = int(payload.get("tile_id", -1))
            if tid not in self.get_buildable_tiles(player_id):
                return {}
            cost = int(BOARD_TILES[tid]["house_cost"])
            self.cash[player_id] -= cost
            self.tile_houses[tid] = self.tile_houses.get(tid, 0) + 1
            ev = {
                "event": "house_built",
                "player_id": player_id,
                "tile_id": tid,
                "tile_name": BOARD_TILES[tid]["name"],
                "houses": self.tile_houses[tid],
                "amount": cost,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "sell_house":
            if self.phase not in ("roll", "manage", "debt"):
                return {}
            tid = int(payload.get("tile_id", -1))
            if tid not in self.get_sellable_house_tiles(player_id):
                return {}
            refund = int(BOARD_TILES[tid]["house_cost"]) // 2
            self.tile_houses[tid] -= 1
            self.cash[player_id] += refund
            ev = {
                "event": "house_sold",
                "player_id": player_id,
                "tile_id": tid,
                "tile_name": BOARD_TILES[tid]["name"],
                "houses": self.tile_houses[tid],
                "amount": refund,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "mortgage":
            if self.phase not in ("roll", "manage", "debt"):
                return {}
            tid = int(payload.get("tile_id", -1))
            if tid not in self.get_mortgageable_tiles(player_id):
                return {}
            val = self.get_mortgage_value(tid)
            self.tile_mortgaged[tid] = True
            self.cash[player_id] += val
            ev = {
                "event": "property_mortgaged",
                "player_id": player_id,
                "tile_id": tid,
                "tile_name": BOARD_TILES[tid]["name"],
                "amount": val,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "unmortgage":
            if self.phase not in ("roll", "manage"):
                return {}
            tid = int(payload.get("tile_id", -1))
            if tid not in self.get_unmortgageable_tiles(player_id):
                return {}
            cost = self.get_unmortgage_cost(tid)
            self.cash[player_id] -= cost
            self.tile_mortgaged[tid] = False
            ev = {
                "event": "property_unmortgaged",
                "player_id": player_id,
                "tile_id": tid,
                "tile_name": BOARD_TILES[tid]["name"],
                "amount": cost,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "pay_debt":
            if self.phase != "debt" or not self.debt or self.debt.get("player_id") != player_id:
                return {}
            amt = int(self.debt["amount"])
            if int(self.cash.get(player_id, 0)) < amt:
                return {}
            creditor = int(self.debt["creditor_id"])
            ret_phase = str(self.debt["return_phase"])
            jail_move_sum = int(self.debt.get("after_jail_move_sum", 0))
            self.cash[player_id] -= amt
            if creditor > 0 and creditor in self.active_player_indexes:
                self.cash[creditor] += amt
            self.debt = None
            if jail_move_sum > 0:
                self.in_jail[player_id] = False
                self.jail_turns[player_id] = 0
                ev = self._move_player_and_resolve(
                    player_id=player_id,
                    target_tile=(self.positions[player_id] + jail_move_sum) % BOARD_SIZE,
                    collect_go=True,
                    dice_sum=jail_move_sum,
                    allow_doubles_bonus=False,
                )
                ev["debt_paid"] = True
                self._bump_seq()
                self.last_event = ev
                return ev
            self.phase = ret_phase
            ev = {"event": "debt_paid", "player_id": player_id, "amount": amt, "creditor_id": creditor}
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "declare_bankruptcy":
            if self.phase != "debt" or not self.debt or self.debt.get("player_id") != player_id:
                return {}
            creditor = int(self.debt.get("creditor_id", 0))
            self._apply_bankruptcy(player_id, creditor)
            ev = {"event": "bankrupt", "player_id": player_id, "creditor_id": creditor}
            self._bump_seq()
            self.last_event = ev
            return ev

        if action == "end_turn":
            if self.phase != "manage" or player_id != self.current_turn:
                return {}
            prev = player_id
            self._advance_to_next_player()
            ev = {"event": "turn_ended", "player_id": prev, "next_turn": self.current_turn}
            self._bump_seq()
            self.last_event = ev
            return ev

        return {}

    def submit_auction(self, player_id: int, decision: str, amount: int = 0) -> Dict[str, Any]:
        if self.phase != "auction" or not self.auction:
            return {}
        if self.auction.get("current_bidder") != player_id:
            return {}

        if decision == "pass":
            if player_id not in self.auction["passed"]:
                self.auction["passed"].append(player_id)
            self.last_event = {"event": "auction_pass", "player_id": player_id}
            self._advance_auction_bidder()
            self._bump_seq()
            return dict(self.last_event)

        if decision == "bid":
            cur_bid = int(self.auction.get("current_bid", 0))
            min_next = 10 if cur_bid == 0 else (cur_bid + 10)
            target_bid = int(amount) if int(amount) >= min_next else min_next
            if target_bid > int(self.cash.get(player_id, 0)):
                return {}
            self.auction["current_bid"] = target_bid
            self.auction["highest_bidder"] = player_id
            ev = {
                "event": "auction_bid",
                "player_id": player_id,
                "amount": target_bid,
                "tile_id": int(self.auction["tile_id"]),
            }
            self._advance_auction_bidder()
            if self.auction is None and isinstance(self.last_event, dict) and self.last_event.get("event") == "auction_won":
                ev = dict(self.last_event)
            else:
                self.last_event = ev
            self._bump_seq()
            return ev

        return {}

    def submit_trade(self, player_id: int, payload: dict) -> Dict[str, Any]:
        act = str(payload.get("action", ""))
        if act == "propose":
            if self.phase not in ("roll", "manage") or player_id != self.current_turn:
                return {}
            if self.trades_this_turn >= 2:
                return {}
            target_id = int(payload.get("target_id", 0))
            if target_id == player_id or target_id not in self.active_player_indexes:
                return {}
            offer_cash = max(0, int(payload.get("offer_cash", 0)))
            request_cash = max(0, int(payload.get("request_cash", 0)))
            offer_tiles = [int(t) for t in (payload.get("offer_tiles") or [])]
            request_tiles = [int(t) for t in (payload.get("request_tiles") or [])]

            if offer_cash > int(self.cash.get(player_id, 0)):
                return {}
            if request_cash > int(self.cash.get(target_id, 0)):
                return {}
            my_tradeable = set(self.get_tradeable_tiles(player_id))
            their_tradeable = set(self.get_tradeable_tiles(target_id))
            if not set(offer_tiles).issubset(my_tradeable):
                return {}
            if not set(request_tiles).issubset(their_tradeable):
                return {}
            if offer_cash == 0 and request_cash == 0 and not offer_tiles and not request_tiles:
                return {}
            if (offer_cash == 0 and not offer_tiles) or (request_cash == 0 and not request_tiles):
                return {}

            self.trades_this_turn += 1
            return_phase = self.phase
            self.phase = "trade"
            self.pending_trade = {
                "from_player": player_id,
                "to_player": target_id,
                "offer_cash": offer_cash,
                "offer_tiles": offer_tiles,
                "request_cash": request_cash,
                "request_tiles": request_tiles,
                "return_phase": return_phase,
            }
            ev = {
                "event": "trade_proposed",
                "from_player": player_id,
                "to_player": target_id,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if act == "accept":
            if self.phase != "trade" or not self.pending_trade or self.pending_trade.get("to_player") != player_id:
                return {}
            tr = self.pending_trade
            p_from = int(tr["from_player"])
            p_to = int(tr["to_player"])
            o_cash = int(tr["offer_cash"])
            r_cash = int(tr["request_cash"])
            o_tiles = [int(t) for t in tr["offer_tiles"]]
            r_tiles = [int(t) for t in tr["request_tiles"]]
            ret_phase = str(tr.get("return_phase", "manage"))

            if (
                int(self.cash.get(p_from, 0)) < o_cash
                or int(self.cash.get(p_to, 0)) < r_cash
                or not set(o_tiles).issubset(set(self.get_tradeable_tiles(p_from)))
                or not set(r_tiles).issubset(set(self.get_tradeable_tiles(p_to)))
            ):
                self.pending_trade = None
                self.phase = ret_phase
                ev = {"event": "trade_rejected", "from_player": p_from, "to_player": p_to}
                self._bump_seq()
                self.last_event = ev
                return ev

            self.cash[p_from] = self.cash[p_from] - o_cash + r_cash
            self.cash[p_to] = self.cash[p_to] - r_cash + o_cash
            for tid in o_tiles:
                self.tile_owners[tid] = p_to
            for tid in r_tiles:
                self.tile_owners[tid] = p_from

            self.pending_trade = None
            self.phase = ret_phase
            ev = {
                "event": "trade_accepted",
                "from_player": p_from,
                "to_player": p_to,
                "offer_cash": o_cash,
                "request_cash": r_cash,
                "offer_tiles": o_tiles,
                "request_tiles": r_tiles,
            }
            self._bump_seq()
            self.last_event = ev
            return ev

        if act == "reject":
            if self.phase != "trade" or not self.pending_trade or self.pending_trade.get("to_player") != player_id:
                return {}
            tr = self.pending_trade
            p_from = int(tr["from_player"])
            p_to = int(tr["to_player"])
            ret_phase = str(tr.get("return_phase", "manage"))
            self.pending_trade = None
            self.phase = ret_phase
            ev = {"event": "trade_rejected", "from_player": p_from, "to_player": p_to}
            self._bump_seq()
            self.last_event = ev
            return ev

        return {}

    async def recieve_data(self, command_id: str, data: dict, gamer_id: int) -> Dict[str, Any]:
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        if not isinstance(payload, dict):
            payload = {}

        if command_id == "MonopolyRoll":
            return self.roll_dice_action(gamer_id)
        if command_id == "MonopolyAction":
            act = str(payload.get("action", ""))
            return self.submit_action(gamer_id, act, payload)
        if command_id == "MonopolyAuction":
            dec = str(payload.get("decision", "pass"))
            amt = int(payload.get("amount", 0))
            return self.submit_auction(gamer_id, dec, amt)
        if command_id == "MonopolyTrade":
            return self.submit_trade(gamer_id, payload)
        return {}

    # ------------------------------------------------------------------
    # Timeout & Surrender
    # ------------------------------------------------------------------
    def auto_resolve_timeout(self) -> Dict[str, Any]:
        if self.is_game_finished:
            return {}
        if self.phase == "roll":
            return self.roll_dice_action(self.current_turn)
        if self.phase == "buy_or_auction":
            return self.submit_action(self.current_turn, "decline_buy", {})
        if self.phase == "auction" and self.auction:
            bidder = int(self.auction.get("current_bidder", 0))
            return self.submit_auction(bidder, "pass", 0)
        if self.phase == "trade" and self.pending_trade:
            target = int(self.pending_trade.get("to_player", 0))
            return self.submit_trade(target, {"action": "reject"})
        if self.phase == "debt" and self.debt:
            pid = int(self.debt["player_id"])
            amt = int(self.debt["amount"])
            # Deterministically mortgage then sell houses until enough or bankrupt
            for tid in list(self.get_mortgageable_tiles(pid)):
                if int(self.cash.get(pid, 0)) >= amt:
                    break
                self.submit_action(pid, "mortgage", {"tile_id": tid})
            while int(self.cash.get(pid, 0)) < amt:
                sellable = self.get_sellable_house_tiles(pid)
                if not sellable:
                    break
                self.submit_action(pid, "sell_house", {"tile_id": sellable[0]})
            for tid in list(self.get_mortgageable_tiles(pid)):
                if int(self.cash.get(pid, 0)) >= amt:
                    break
                self.submit_action(pid, "mortgage", {"tile_id": tid})
            if int(self.cash.get(pid, 0)) >= amt:
                return self.submit_action(pid, "pay_debt", {})
            return self.submit_action(pid, "declare_bankruptcy", {})
        if self.phase == "manage":
            return self.submit_action(self.current_turn, "end_turn", {})
        return {}

    def _apply_surrender_sync(self, gamer_id):
        if gamer_id not in self.active_player_indexes:
            return False
        was_turn = (self.current_turn == gamer_id)
        was_auction_bidder = (self.phase == "auction" and self.auction and self.auction.get("current_bidder") == gamer_id)
        was_trade_party = (self.phase == "trade" and self.pending_trade and gamer_id in (self.pending_trade.get("from_player"), self.pending_trade.get("to_player")))

        self._apply_bankruptcy(gamer_id, 0)
        if not self.is_game_finished:
            if was_auction_bidder and self.auction:
                if gamer_id not in self.auction["passed"]:
                    self.auction["passed"].append(gamer_id)
                self._advance_auction_bidder()
            elif was_trade_party and self.pending_trade:
                ret_p = str(self.pending_trade.get("return_phase", "manage"))
                self.pending_trade = None
                self.phase = ret_p
            if was_turn and self.current_turn not in self.active_player_indexes:
                self._advance_to_next_player()
        self._bump_seq()
        return True

    def get_game_winner(self):
        if self.rank1 is not None:
            return self.rank1
        if len(self.active_player_indexes) == 1:
            return self.active_player_indexes[0]
        return 0

    # ------------------------------------------------------------------
    # State Serialization
    # ------------------------------------------------------------------
    def get_game_data(self) -> Dict[str, Any]:
        players = []
        for pid in range(1, self.players_count + 1):
            owned = [tid for tid in range(BOARD_SIZE) if self.tile_owners.get(tid, 0) == pid]
            players.append({
                "gamer_id": pid,
                "cash": int(self.cash.get(pid, 0)),
                "position": int(self.positions.get(pid, 0)),
                "in_jail": bool(self.in_jail.get(pid, False)),
                "jail_turns": int(self.jail_turns.get(pid, 0)),
                "jail_cards": int(self.jail_cards.get(pid, 0)),
                "bankrupt": bool(self.bankrupt.get(pid, False)),
                "alive": pid in self.active_player_indexes,
                "owned_count": len(owned),
                "net_worth": self.get_player_net_worth(pid),
            })

        tiles_state = []
        for tid in range(BOARD_SIZE):
            tiles_state.append({
                "id": tid,
                "owner": int(self.tile_owners.get(tid, 0)),
                "houses": int(self.tile_houses.get(tid, 0)),
                "mortgaged": bool(self.tile_mortgaged.get(tid, False)),
            })

        acting_pid = self.current_turn
        if self.phase == "debt" and self.debt:
            acting_pid = int(self.debt.get("player_id", self.current_turn))

        return {
            "game_type": "Monopoly",
            "players_count": self.players_count,
            "active_player_indexes": list(self.active_player_indexes),
            "eliminated_order": list(self.eliminated_order),
            "current_turn": self.current_turn,
            "turn": self.current_turn,
            "round_number": self.round_number,
            "phase": self.phase,
            "state_seq": self.state_seq,
            "last_dice": list(self.last_dice),
            "players": players,
            "tiles": tiles_state,
            "pending_tile_id": self.pending_tile_id,
            "auction": dict(self.auction) if isinstance(self.auction, dict) else None,
            "debt": dict(self.debt) if isinstance(self.debt, dict) else None,
            "pending_trade": dict(self.pending_trade) if isinstance(self.pending_trade, dict) else None,
            "trades_this_turn": self.trades_this_turn,
            "bonus_doubles": self._pending_bonus_doubles,
            "buildable_tiles": self.get_buildable_tiles(acting_pid),
            "sellable_tiles": self.get_sellable_house_tiles(acting_pid),
            "mortgageable_tiles": self.get_mortgageable_tiles(acting_pid),
            "unmortgageable_tiles": self.get_unmortgageable_tiles(acting_pid),
            "last_card": dict(self.last_card) if isinstance(self.last_card, dict) else None,
            "last_event": dict(self.last_event) if isinstance(self.last_event, dict) else None,
            "rank1": self.rank1,
            "rank2": self.rank2,
            "is_game_finished": self.is_game_finished,
        }

    def get_user_private_game_data(self, gamer_id: int) -> Dict[str, Any]:
        data = self.get_game_data()
        data.update({
            "user": gamer_id,
            "index": gamer_id,
            "gamer_id": gamer_id,
        })
        return data
