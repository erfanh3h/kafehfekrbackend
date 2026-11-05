"""
Persian names, avatars, and reaction/chat data for Cafe Fekr Classic Rank bots.
Provides intelligent sentiment-aware responses to user Koris (101..178) and Stickers (1..44).
"""

import random
from typing import Optional

# ---------------------------------------------------------------------------
# Bot Profiles (Names & Avatars separated by gender)
# ---------------------------------------------------------------------------

MALE_BOT_NAMES = [
    "آرش", "سهراب", "سامان", "پارسا", "امید", "نیما", "بهزاد", "کیان",
    "علی", "دانیال", "سینا", "امیررضا", "نوید", "آرمین", "بردیا", "شاهین",
    "کاوه", "ارشیا", "پوریا", "مهرداد", "فرزاد",
]

FEMALE_BOT_NAMES = [
    "رها", "آناهیتا", "بیتا", "ترانه", "مریم", "سارا", "نگین", "مهسا",
    "فرناز", "یاسمن", "پریا", "شیما", "هلیا", "رویا", "سپیده", "مونا",
    "الناز", "غزل", "نیلوفر",
]

PERSIAN_BOT_NAMES = MALE_BOT_NAMES + FEMALE_BOT_NAMES

# Avatar ID categorization (total 27 avatars: 0..26)
MALE_BOT_AVATARS = [0, 1, 3, 4, 6, 8, 9, 12, 14, 16, 18, 20, 22, 24, 25, 26]
FEMALE_BOT_AVATARS = [2, 5, 7, 10, 11, 13, 15, 17, 19, 21, 23]


def get_random_bot_profile(exclude_avatar: Optional[int] = None):
    # 50% chance male or female
    is_male = random.random() < 0.5

    if is_male:
        name = random.choice(MALE_BOT_NAMES)
        candidates = [a for a in MALE_BOT_AVATARS if a != exclude_avatar] or MALE_BOT_AVATARS
    else:
        name = random.choice(FEMALE_BOT_NAMES)
        candidates = [a for a in FEMALE_BOT_AVATARS if a != exclude_avatar] or FEMALE_BOT_AVATARS

    avatar = random.choice(candidates)
    score = random.randint(350, 1450)
    return {
        "name": name,
        "avatar": avatar,
        "score": score
    }


# ---------------------------------------------------------------------------
# Reaction Stickers (IDs 1..44)
# ---------------------------------------------------------------------------
STICKER_HELLO = [1, 2, 18, 20]
STICKER_THINKING = [6, 14, 27]
STICKER_SURPRISED = [7, 10, 15]
STICKER_CONFIDENT = [3, 4, 8]
STICKER_PRAISE = [11, 18, 20]
STICKER_GG = [1, 11, 20, 22]


# ---------------------------------------------------------------------------
# Persian Kori Definitions (IDs 101..178) Categorized by Semantic Intent
# ---------------------------------------------------------------------------

# 1. TAUNT / ARROGANT / PROVOCATIVE KORIS (حریف کُری سنگین یا تحقیرآمیز خوانده)
# 101: شکست دیگه عادتت شده!
# 103: برنده فقط منم!
# 104: بازی شروع نشده، تمومه!
# 106: حریف من نیستی!
# 107: بازم بردم!
# 109: قهرمان برگشته!
# 110: این فقط تمرین بود!
# 112: یه باخت دیگه تو کارنامت!
# 113: بهتره تسلیم شی!
# 115: سریع‌تر از اینم می‌بازی؟
# 116: حیف وقتی که گذاشتی!
# 118: بهتره تمرین کنی!
# 119: حالا یاد گرفتی؟
# 121: راحت‌تر از این نبود!
# 124: تو حتی نزدیک هم نشدی!
# 125: پایانش همین بود؟
# 127: بازم دیر کردی!
# 128: این برد مال منه!
# 130: مثل همیشه برنده!
# 131: یک حرکت و تموم!
# 133: بازی رو یاد بگیر!
# 134: بهترین بودن سخته!
# 136: حریف من نیستی!
# 137: دوباره باختی!
# 139: تو از اول هم شانسی نداشتی!
# 140: بردم، طبق معمول!
# 142: تسلیم شو، هنوز وقت داری!
# 143: بازم ساده بردم!
# 145: این فقط یه گرم کردن بود!
# 146: قهرمان برگشت!
# 148: دیر رسیدی به بازی!
# 149: بازی کردن با تو وقت تلف کردنه!
# 151: با همین سرعت می‌بازی!
# 152: یه کلاس درس دیگه برات بود!
# 154: هنوز مونده تا به من برسی!
# 155: فقط نگاه کن چطور برنده می‌شم!
# 157: شروع نکرده باختی!
# 158: پایان داستان تو همین‌جاست!
# 160: به همین سادگی!
# 161: این فقط یک نمایش بود!
# 163: پایان رو از الان می‌دونم!
# 164: خسته نشدی از باختن؟
# 167: فکر کنم هنوز نوبتت نشده!
# 169: بازی براتو تفریحه، برا من زندگیه!
# 170: توی لیگ خودت بازی کن!
# 172: این بود تمام توانت؟
# 173: امروز روز تو نبود!
# 175: شاید دفعه بعد!
# 176: باید تلاش بیشتری کنی!
KORIS_TAUNT = {
    101, 103, 104, 106, 107, 109, 110, 112, 113, 115, 116, 118, 119, 121,
    124, 125, 127, 128, 130, 131, 133, 134, 136, 137, 139, 140, 142, 143,
    145, 146, 148, 149, 151, 152, 154, 155, 157, 158, 160, 161, 163, 164,
    167, 169, 170, 172, 173, 175, 176
}

# 2. PRAISE / COMPLIMENT KORIS (حریف از حرکت ربات تعریف کرده)
# 102: عجب حرکت هوشمندانه‌ای بود!
# 105: خیلی خوب بازی کردی!
# 108: اون استراتژی عالی بود!
# 111: خوشم اومد از سبک بازیت!
# 114: آفرین!
# 117: حرکتت واقعاً تحسین‌برانگیز بود!
# 123: اون تاکتیک خیلی جالب بود!
# 126: این یکی رو عالی مدیریت کردی!
# 129: ایده خوبی داشتی، بهش ادامه بده!
# 135: خیلی خوب مسیر بازی رو تغییر دادی!
# 138: این تاکتیکت واقعاً کارساز بود!
# 141: پیشرفتت تو این بازی محسوسه!
# 144: خیلی خوب کنترل کردی اوضاع رو!
# 147: اون تصمیم واقعاً درست بود!
# 150: حرکت نهایی‌ات خیلی قوی بود!
# 153: این راندو خیلی حرفه‌ای زدی!
# 156: خیلی خوب بود!
# 159: عجب حرکت هوشمندانه‌ای!
# 162: عالی بازی کردی!
# 165: به به!
# 168: اون تاکتیک معرکه بود!
# 171: چقد خوب دفاع کردی!
# 174: بازی خفنی کردی!
# 177: ایده فوق‌العاده‌ای بود!
KORIS_PRAISE = {
    102, 105, 108, 111, 114, 117, 123, 126, 129, 135, 138, 141, 144, 147,
    150, 153, 156, 159, 162, 165, 168, 171, 174, 177
}

# 3. THANKS KORIS (تشکر)
# 120: ممنونم!
KORIS_THANKS = {120}

# 4. SURPRISE KORIS (تعجب از حرکت غیرمنتظره)
# 132: این حرکت غیرمنتظره بود
KORIS_SURPRISE = {132}

# 5. COMEBACK / EARLY GAME KORIS (شروع بازی و روحیه کامبک)
# 122: این فقط شروعشه!
# 166: دوباره شانس داری، امتحان کن!
# 178: هنوز اول راحته!
KORIS_COMEBACK = {122, 166, 178}


# ---------------------------------------------------------------------------
# Intelligent Response Candidate Pools
# ---------------------------------------------------------------------------

# Response when opponent TAUNTS the bot:
# Instead of thanking or praising them (which looked naive), the bot replies with sharp counter-taunt or cool smirk!
BOT_COUNTER_TAUNT_KORIS = [122, 178, 155, 128, 103, 166, 160, 131, 154]
# 122: این فقط شروعشه!
# 178: هنوز اول راحته!
# 155: فقط نگاه کن چطور برنده می‌شم!
# 128: این برد مال منه!
# 103: برنده فقط منم!
# 166: دوباره شانس داری، امتحان کن!
# 160: به همین سادگی!
# 131: یک حرکت و تموم!
# 154: هنوز مونده تا به من برسی!
BOT_COUNTER_TAUNT_STICKERS = [3, 4, 8]

# Response when opponent PRAISES the bot:
# Bot responds with gratitude, return compliment, or witty pride:
BOT_PRAISE_REPLY_KORIS = [120, 165, 111, 156, 134, 160]
# 120: ممنونم!
# 165: به به!
# 111: خوشم اومد از سبک بازیت!
# 156: خیلی خوب بود!
# 134: بهترین بودن سخته!
# 160: به همین سادگی!
BOT_PRAISE_REPLY_STICKERS = [18, 20, 11, 1]

# Response when opponent says THANKS (120):
BOT_THANKS_REPLY_KORIS = [114, 165, 111]
# 114: آفرین!
# 165: به به!
# 111: خوشم اومد از سبک بازیت!
BOT_THANKS_REPLY_STICKERS = [18, 20, 1]

# Response when opponent is SURPRISED (132 or surprise stickers 7, 10, 15):
BOT_SURPRISE_REPLY_KORIS = [123, 160, 108, 122, 168]
# 123: اون تاکتیک خیلی جالب بود!
# 160: به همین سادگی!
# 108: اون استراتژی عالی بود!
# 122: این فقط شروعشه!
# 168: اون تاکتیک معرکه بود!
BOT_SURPRISE_REPLY_STICKERS = [3, 8, 14]

# Response when opponent says COMEBACK / EARLY GAME (122, 178):
BOT_COMEBACK_REPLY_KORIS = [128, 104, 155, 131, 160]
# 128: این برد مال منه!
# 104: بازی شروع نشده، تمومه!
# 155: فقط نگاه کن چطور برنده می‌شم!
# 131: یک حرکت و تموم!
# 160: به همین سادگی!
BOT_COMEBACK_REPLY_STICKERS = [3, 8]

# Match Finish - Victory for Bot:
BOT_FINISH_WIN_KORIS = [107, 128, 140, 160, 130, 103, 105, 174]
# 107: بازم بردم!
# 128: این برد مال منه!
# 140: بردم، طبق معمول!
# 160: به همین سادگی!
# 130: مثل همیشه برنده!
# 103: برنده فقط منم!
# 105: خیلی خوب بازی کردی!
# 174: بازی خفنی کردی!
BOT_FINISH_WIN_STICKERS = [22, 11, 3, 8]

# Match Finish - Bot Defeat (Congratulate user with good sportsmanship):
BOT_FINISH_LOSE_KORIS = [105, 114, 174, 162, 150, 147, 120, 175, 166]
# 105: خیلی خوب بازی کردی!
# 114: آفرین!
# 174: بازی خفنی کردی!
# 162: عالی بازی کردی!
# 150: حرکت نهایی‌ات خیلی قوی بود!
# 147: اون تصمیم واقعاً درست بود!
# 120: ممنونم!
# 175: شاید دفعه بعد!
# 166: دوباره شانس داری، امتحان کن!
BOT_FINISH_LOSE_STICKERS = [11, 18, 20, 1]

# Match Finish - Draw:
BOT_FINISH_DRAW_KORIS = [105, 156, 174, 120]
BOT_FINISH_DRAW_STICKERS = [1, 11, 20]

# Legacy constants for backwards compatibility
KORI_GREETING = [1, 2, 18, 20, 178, 122]
KORI_COMPLIMENT = list(KORIS_PRAISE)
KORI_SURPRISED = [123, 132, 7, 10, 14, 15]
KORI_WITTY = [122, 160, 3, 8]
KORI_FINISH = [105, 114, 11, 20, 22, 1]


def get_intelligent_bot_reaction(incoming_reaction_id: int) -> int:
    """
    Analyzes user reaction / kori and returns the most contextually intelligent response.
    Balances between text koris (~65%) and expressive stickers (~35%).
    """
    prefer_kori = random.random() < 0.65

    # 1. Opponent sent TAUNT / ARROGANT Kori
    if incoming_reaction_id in KORIS_TAUNT or incoming_reaction_id in (4, 9, 12):
        if prefer_kori:
            return random.choice(BOT_COUNTER_TAUNT_KORIS)
        return random.choice(BOT_COUNTER_TAUNT_STICKERS)

    # 2. Opponent sent PRAISE / COMPLIMENT Kori or praise sticker
    elif incoming_reaction_id in KORIS_PRAISE or incoming_reaction_id in (11, 16):
        if prefer_kori:
            return random.choice(BOT_PRAISE_REPLY_KORIS)
        return random.choice(BOT_PRAISE_REPLY_STICKERS)

    # 3. Opponent sent THANKS ("ممنونم!")
    elif incoming_reaction_id in KORIS_THANKS:
        if prefer_kori:
            return random.choice(BOT_THANKS_REPLY_KORIS)
        return random.choice(BOT_THANKS_REPLY_STICKERS)

    # 4. Opponent expressed SURPRISE ("این حرکت غیرمنتظره بود" or surprise stickers)
    elif incoming_reaction_id in KORIS_SURPRISE or incoming_reaction_id in (7, 10, 15):
        if prefer_kori:
            return random.choice(BOT_SURPRISE_REPLY_KORIS)
        return random.choice(BOT_SURPRISE_REPLY_STICKERS)

    # 5. Opponent sent COMEBACK / EARLY GAME ("این فقط شروعشه!", "هنوز اول راحته!")
    elif incoming_reaction_id in KORIS_COMEBACK:
        if prefer_kori:
            return random.choice(BOT_COMEBACK_REPLY_KORIS)
        return random.choice(BOT_COMEBACK_REPLY_STICKERS)

    # 6. Opponent sent GREETING / HELLO sticker (1, 2, 18, 20)
    elif incoming_reaction_id in (1, 2, 18, 20):
        if prefer_kori and random.random() < 0.5:
            return random.choice([178, 122, 165])
        return random.choice([1, 2, 18, 20])

    # 7. Fallback: intelligent balanced pool
    else:
        if prefer_kori:
            return random.choice(BOT_COUNTER_TAUNT_KORIS + BOT_PRAISE_REPLY_KORIS)
        return random.choice([1, 3, 8, 11, 18, 20])


def get_opening_reaction() -> int:
    """Returns a natural greeting or competitive opening reaction at match start."""
    if random.random() < 0.55:
        # Friendly sticker
        return random.choice([1, 2, 18, 20])
    # Opening kori: "هنوز اول راحته!", "این فقط شروعشه!", "به به!"
    return random.choice([178, 122, 165])


def get_critical_move_reaction() -> int:
    """Returns a reaction when a critical, high-stakes move occurs."""
    if random.random() < 0.60:
        # Tactical kori
        return random.choice([132, 123, 160, 168])
    # Thinking or confident sticker
    return random.choice([6, 14, 27, 3, 8])


def get_game_finish_reaction(bot_won: bool, is_draw: bool = False) -> int:
    """Returns an intelligent end-of-game reaction based on actual match outcome."""
    prefer_kori = random.random() < 0.70

    if is_draw:
        if prefer_kori:
            return random.choice(BOT_FINISH_DRAW_KORIS)
        return random.choice(BOT_FINISH_DRAW_STICKERS)

    if bot_won:
        if prefer_kori:
            return random.choice(BOT_FINISH_WIN_KORIS)
        return random.choice(BOT_FINISH_WIN_STICKERS)
    else:
        # Bot lost -> gracious sportsmanship complimenting the human player
        if prefer_kori:
            return random.choice(BOT_FINISH_LOSE_KORIS)
        return random.choice(BOT_FINISH_LOSE_STICKERS)
