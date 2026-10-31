"""
Persian names, avatars, and reaction/chat data for Cafe Fekr Classic Rank bots.
"""

import random
from typing import Optional

PERSIAN_BOT_NAMES = [
    "آرش", "سهراب", "رها", "آناهیتا", "سامان", "بیتا", "پارسا", "ترانه",
    "امید", "نیما", "مریم", "بهزاد", "سارا", "کیان", "نگین", "علی",
    "مهسا", "دانیال", "فرناز", "سینا", "یاسمن", "امیررضا", "پریا", "نوید",
    "شیما", "آرمین", "هلیا", "بردیا", "رویا", "شاهین", "سپیده", "کاوه",
    "مونا", "ارشیا", "الناز", "پوریا", "مهرداد", "غزل", "فرزاد", "نیلوفر",
]

# Reaction stickers (IDs 1..44)
STICKER_HELLO = [1, 2, 18, 20]
STICKER_THINKING = [6, 14, 27]
STICKER_SURPRISED = [7, 10, 15]
STICKER_CONFIDENT = [3, 8]
STICKER_PRAISE = [11, 18]
STICKER_GG = [1, 11, 20, 22]

# Persian Kori reactions (IDs 101..178 matching Godot & Flutter app_consts)
# 101: شکست دیگه عادتت شده!
# 102: عجب حرکت هوشمندانه‌ای بود!
# 105: خیلی خوب بازی کردی!
# 108: اون استراتژی عالی بود!
# 111: خوشم اومد از سبک بازیت!
# 114: آفرین!
# 117: حرکتت واقعاً تحسین‌برانگیز بود!
# 120: ممنونم!
# 122: این فقط شروعشه!
# 123: اون تاکتیک خیلی جالب بود!
# 126: این یکی رو عالی مدیریت کردی!
# 129: ایده خوبی داشتی، بهش ادامه بده!
# 132: این حرکت غیرمنتظره بود

KORI_GREETING = [1, 2, 18, 20]
KORI_COMPLIMENT = [102, 105, 108, 111, 114, 117, 120, 126]
KORI_SURPRISED = [123, 132, 7, 14]
KORI_WITTY = [122, 3, 8]
KORI_FINISH = [105, 114, 11, 22, 1]


def get_random_bot_profile(exclude_avatar: Optional[int] = None):
    name = random.choice(PERSIAN_BOT_NAMES)
    available_avatars = [a for a in range(27) if a != exclude_avatar]
    avatar = random.choice(available_avatars) if available_avatars else random.randint(0, 26)
    score = random.randint(350, 1450)
    return {
        "name": name,
        "avatar": avatar,
        "score": score
    }
