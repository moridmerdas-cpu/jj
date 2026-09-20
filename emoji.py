# emoji.py - پریمیوم ایموجی‌های تلگرام (با سوییچ زنده حالت پیام‌رسانی)
# ─────────────────────────────────────────
#  حالت‌ها:
#   - "premium" → همه‌جا از ایموجی انیمیشنی پریمیوم استفاده می‌شه
#   - "normal"  → همه‌جا از ایموجی معمولی (fallback) استفاده می‌شه
#  حالت فعلی توی amel_global_settings ذخیره می‌شه (کلید emoji_mode) و از
#  پنل مدیریت مالک با یه دکمه سوییچ می‌شه. تغییرش فوراً روی همه‌ی پیام‌ها
#  و دکمه‌ها اثر می‌ذاره، بدون نیاز به ری‌استارت ربات.
#
#  دو نوع استفاده:
#
#  ۱) در متن پیام‌ها (parse_mode="HTML"):
#       f"{EM.EMOJI_BALANCE} موجودی شما..."
#     → حالت premium: ایموجی انیمیشنی
#     → حالت normal:  ایموجی معمولی
#
#  ۲) در دکمه‌های InlineKeyboard/KeyboardButton:
#       types.InlineKeyboardButton(
#           "موجودی",
#           callback_data="menu_balance",
#           icon_custom_emoji_id=EM.icon(EM.ID_BALANCE)
#       )
#     → حالت premium: شناسه‌ی ایموجی پریمیوم
#     → حالت normal:  None (بدون آیکون سفارشی)
# ─────────────────────────────────────────

import database as db

SETTING_KEY = "emoji_mode"
MODE_PREMIUM = "premium"
MODE_NORMAL = "normal"

_cache = {"mode": None, "ts": 0}
_CACHE_TTL = 5  # ثانیه - جلوی کوئری زدن به ازای هر پیام رو می‌گیره


def is_premium_mode() -> bool:
    """وضعیت فعلی سوییچ ایموجی رو برمی‌گردونه (کش‌شده، حداکثر ۵ ثانیه قدیمی)."""
    import time
    now = time.time()
    if _cache["mode"] is None or (now - _cache["ts"]) > _CACHE_TTL:
        try:
            _cache["mode"] = db.get_global_setting(SETTING_KEY, MODE_NORMAL)
        except Exception:
            _cache["mode"] = MODE_NORMAL
        _cache["ts"] = now
    return _cache["mode"] == MODE_PREMIUM


def set_mode(mode: str):
    """سوییچ حالت ایموجی - از پنل مدیریت مالک صدا زده می‌شه."""
    mode = MODE_PREMIUM if mode == MODE_PREMIUM else MODE_NORMAL
    db.set_global_setting(SETTING_KEY, mode)
    _cache["mode"] = mode
    _cache["ts"] = 0
    return mode


def toggle_mode() -> str:
    """حالت رو برعکس می‌کنه و مقدار جدید رو برمی‌گردونه."""
    return set_mode(MODE_NORMAL if is_premium_mode() else MODE_PREMIUM)


def mode_label() -> str:
    return "پریمیوم" if is_premium_mode() else "معمولی"


# ─────────────────────────────────────────
#  شناسه‌های عددی ایموجی‌ها
# ─────────────────────────────────────────

ID_DAILY_GIFT   = 5834422787661369616   # 🎁 هدیه روزانه
ID_BALANCE      = 6001287064589439895   # 💎 موجودی
ID_CONFIRM      = 5830326445422940546   # ✅ تایید
ID_CANCEL       = 5832353674281620438   # ❌ لغو
ID_DIAMONDS     = 5814670671153730702   # 💎 الماس‌ها
ID_BUY_DIAMOND  = 4960766907113276588   # 🛒 خرید الماس
ID_REFERRAL     = 5260730055880876557   # 🔗 رفرال
ID_MISSION      = 5352629724516458059   # 🎯 ماموریت
ID_GUIDE        = 5814171260946485530   # 📖 راهنما
ID_SELF_MANAGE  = 6219810752887262728   # 🤖 مدیریت سلف
ID_ADMIN        = 6298670698948724690   # 👮 مدیریت
ID_SELF_ON      = 5260726538302660868   # 🟢 روشن کردن سلف
ID_SELF_OFF     = 5260342697075416641   # 🔴 خاموش کردن سلف
ID_SELF_DELETE  = 5258130763148172425   # 🗑 حذف سلف
ID_BET_JOIN     = 6001567998400273892   # ⚔️ ورود به شرط‌بندی
ID_FORCED_JOIN  = 6255593645848660539
ID_World_Cup    = 5292279335154136992
ID_USERS        = 5193150897256936958
ID_DAY_GAME     = 5854750459851445043
ID_Transition   = 5269491346783099131
ID_SET_CARD     = 6111771632240433101
ID_Pending      = 5262838597060422237
ID_MESSAGE_ALL  = 5938311423712039050
ID_MISSION      = 6298649503285118920
ID_GIFT_DIAMOND = 4965219701572503640
ID_UESRS_WC     = 5193150897256936958
ID_GIFT         = 5264710902153767489
ID_ADMINE       = 5949327894567195412
ID_HELP         = 5827738598778080268
ID_WELCOME      = 5436203513149404753
ID_BET          = 6105002016457625114
ID_CONNECT      = 6001099232784683975
ID_SELF_EDIT    = 6001136607590096242
ID_STAR_1       = 5951810621887484519   # ⭐ استارز تک‌ستاره‌ای (پلن هفتگی)
ID_STAR_2       = 5951940205345771959   # ⭐⭐ استارز دو‌ستاره‌ای (پلن ماهانه)
ID_STAR_3       = 5953931579817465240   # ⭐⭐⭐ استارز سه‌ستاره‌ای (پلن دو ماهه)
ID_BET_ROBOT    = 5467715628070608538   # 🎲 شرط‌بندی با ربات
ID_PREV_NUMBER  = 5920344347152224466   # 📞 همان شماره قبلی
ID_NEW_NUMBER   = 5985774024968379294   # 🆕 شماره جدید
ID_REACT_CANCEL = 5985346521103604145   # ❌ لغو (فعال‌سازی مجدد سلف)
ID_REACT_CONFIRM = 5985596818912712352  # ✅ تایید (فعال‌سازی مجدد سلف)

# پنل «مدیریت سلف» — متن پیام
ID_SELF_MGMT_TITLE = 5335021522539009147   # 🤖 عنوان «مدیریت سلف»
ID_STATUS_LABEL     = 5465124852258059291  # 📊 لیبل «وضعیت:» و «اشتراک:»
ID_SUB_ACTIVE       = 5334749663994074793  # ✅ اشتراک فعال
ID_SUB_EXPIRED      = 5332668120978967508  # ❌ اشتراک منقضی/ندارید

# پنل «موجودی الماس» — متن پیام
ID_BALANCE_TITLE   = 5807465992363710697   # 💎 عنوان «موجودی الماس»
ID_BALANCE_CURRENT = 6028530359975548369   # 💰 فعلی
ID_BALANCE_TOTAL   = 5931472654660800739   # 📊 کل
ID_BALANCE_REFERRAL = 5920052658743283381  # 👥 رفرال
ID_BALANCE_PRICE   = 5927169041595634481   # 💵 قیمت هر الماس

#پنل خرید
ID_SHOMARE_KART   = 5927169041595634481
ID_MENOY_KHARID   = 5816928449561892419
ID_MOJODI         = 5970026312629228447
ID_ESHTRACK        = 5962804544164338396
ID_ALMAS          = 5465498106390920109
ID_MAX_ALMAS      = 5956180995924300841
ID_PARDAKHT       = 5467679271172446725
ID_MABLAGH        = 5467897094733832077
ID_COD            = 5816537843761160266
ID_MANFI          = 5816590375506156707
ID_ENGHEZA        = 5271787358990125058



#پنل لینک رفرال
ID_LINK_REFRAL    = 5334618207930045692
ID_TEDAD          = 5920090136627908485
ID_PADASH         = 5985472565508838112

# ─────────────────────────────────────────
#  توابع کمکی
# ─────────────────────────────────────────

def pe(emoji_id: int, fallback: str = "⭐") -> str:
    """
    رشته ایموجی برای استفاده در متن پیام‌ها (parse_mode='HTML').
    حالت premium → تگ tg-emoji پریمیوم | حالت normal → همون ایموجی معمولی.
    """
    if is_premium_mode():
        return f"<tg-emoji emoji-id='{emoji_id}'>{fallback}</tg-emoji>"
    return fallback


def icon(emoji_id: int):
    """
    مقدار icon_custom_emoji_id برای دکمه‌ها.
    حالت premium → شناسه‌ی ایموجی | حالت normal → None (بدون آیکون سفارشی).
    """
    return str(emoji_id) if is_premium_mode() else None


# ─────────────────────────────────────────
#  نگاشت نام → (شناسه، فالبک) برای دسترسی پویا EM.EMOJI_X
#  این جدول جایگزین ثابت‌های استاتیک قبلی شده تا سوییچ حالت فوری اثر بذاره.
# ─────────────────────────────────────────

_EMOJI_MAP = {
    "DAILY_GIFT":   (ID_DAILY_GIFT,   "🎁"),
    "BALANCE":      (ID_BALANCE,      "💎"),
    "CONFIRM":      (ID_CONFIRM,      "✅"),
    "CANCEL":       (ID_CANCEL,       "❌"),
    "DIAMONDS":     (ID_DIAMONDS,     "💎"),
    "BUY_DIAMOND":  (ID_BUY_DIAMOND,  "🛒"),
    "REFERRAL":     (ID_REFERRAL,     "🔗"),
    "MISSION":      (ID_MISSION,      "🎯"),
    "GUIDE":        (ID_GUIDE,        "📖"),
    "SELF_MANAGE":  (ID_SELF_MANAGE,  "🤖"),
    "ADMIN":        (ID_ADMIN,        "👮"),
    "SELF_ON":      (ID_SELF_ON,      "🟢"),
    "SELF_OFF":     (ID_SELF_OFF,     "🔴"),
    "SELF_DELETE":  (ID_SELF_DELETE,  "🗑"),
    "BET_JOIN":     (ID_BET_JOIN,     "⚔️"),
    "FORCED_JOIN":  (ID_FORCED_JOIN,  "📢"),
    "CONNECT":      (ID_CONNECT,      "🤖"),
    "World_Cup":    (ID_World_Cup,    "🌍"),
    "USERS":        (ID_USERS,        "👥"),
    "DAY_GAME":     (ID_DAY_GAME,     "🎮"),
    "Transition":   (ID_Transition,   "🔁"),
    "SET_CARD":     (ID_SET_CARD,     "💳"),
    "Pending":      (ID_Pending,      "⏳"),
    "MESSAGE_ALL":  (ID_MESSAGE_ALL,  "📣"),
    "GIFT_DIAMOND": (ID_GIFT_DIAMOND, "🎁"),
    "UESRS_WC":     (ID_UESRS_WC,     "👥"),
    "GIFT":         (ID_GIFT,         "🎁"),
    "ADMINE":       (ID_ADMINE,       "👮"),
    "HELP":         (ID_HELP,         "🆘"),
    "WELCOME":      (ID_WELCOME,      "👋"),
    "BET":          (ID_BET,          "🎲"),
    "SELF_EDIT":    (ID_SELF_EDIT,    "✏️"),
    "STAR_1":       (ID_STAR_1,       "⭐"),
    "STAR_2":       (ID_STAR_2,       "⭐"),
    "STAR_3":       (ID_STAR_3,       "⭐"),
    "BET_ROBOT":    (ID_BET_ROBOT,    "🎲"),
    "PREV_NUMBER":  (ID_PREV_NUMBER,  "📞"),
    "NEW_NUMBER":   (ID_NEW_NUMBER,   "🆕"),
    "REACT_CANCEL": (ID_REACT_CANCEL, "❌"),
    "REACT_CONFIRM": (ID_REACT_CONFIRM, "✅"),
    "SELF_MGMT_TITLE": (ID_SELF_MGMT_TITLE, "🤖"),
    "STATUS_LABEL":    (ID_STATUS_LABEL,    "📊"),
    "SUB_ACTIVE":      (ID_SUB_ACTIVE,      "✅"),
    "SUB_EXPIRED":     (ID_SUB_EXPIRED,     "❌"),
    "BALANCE_TITLE":    (ID_BALANCE_TITLE,    "💎"),
    "BALANCE_CURRENT":  (ID_BALANCE_CURRENT,  "💰"),
    "BALANCE_TOTAL":    (ID_BALANCE_TOTAL,    "📊"),
    "BALANCE_REFERRAL": (ID_BALANCE_REFERRAL, "👥"),
    "BALANCE_PRICE":    (ID_BALANCE_PRICE,    "💵"),
    "SHOMARE_KART":     (ID_SHOMARE_KART,    "💵"),
    "LINK_REFRAL":      (ID_LINK_REFRAL,    "💵"),
    "TEDAD":          (ID_TEDAD,        "💵"),
    "PADASH":         (ID_PADASH,       "💵"),
    "MENOY_KHARID":    (ID_MENOY_KHARID,  "💵"),
    "MOJODI":          (ID_MOJODI,      "💵"),
    "ESHTRACK":         (ID_ESHTRACK,      "💵"),
    "ALMAS":          (ID_ALMAS,       "💵"),
    "MAX_ALMAS":    (ID_MAX_ALMAS,     "💵"),
    "PARDAKHT":     (ID_PARDAKHT,      "💵"),
    "MABLAGH":       (ID_MABLAGH,       "💵"),
    "COD":           (ID_COD,        "💵"),
    "MANFI":         (ID_MANFI,       "💵"),
    "ENGHEZA":       (ID_ENGHEZA,      "💵"),





}


def __getattr__(name: str):
    """
    دسترسی پویا: EM.EMOJI_BALANCE و مثل اون‌ها هر بار که خونده بشن،
    بر اساس حالت فعلی (premium/normal) دوباره محاسبه می‌شن.
    """
    if name.startswith("EMOJI_"):
        key = name[len("EMOJI_"):]
        if key in _EMOJI_MAP:
            emoji_id, fallback = _EMOJI_MAP[key]
            return pe(emoji_id, fallback)
    raise AttributeError(f"module 'emoji' has no attribute {name!r}")
