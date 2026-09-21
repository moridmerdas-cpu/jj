# crystal_game.py
# ─────────────────────────────────────────────────────────────────────────────
# ارسال خودکار «کریستال» برای رباتِ بازی‌ای که هر ۵ دقیقه یک‌بار به‌ازای این
# کلمه امتیاز می‌ده. قلاب‌شدنش به bot.py به این شکله:
#
#   1) SETTING_DEFAULTS_EXTRA  → با SETTING_DEFAULTS توی database_supabase.py مرج بشه.
#   2) register_handlers(cl, owner_id, db)  → توی _register_handlers() در bot.py.
#   3) crystal_loop(cl, owner_id, db)       → کنار بقیه‌ی لوپ‌ها با ensure_future.
#   4) handle_panel_command(text, owner_id, ss, gs, edit) → توی _handle_command.
#   5) PANEL_CATEGORY → با کلید "crystal_game" توی PANEL_CATEGORIES.
#
# روش کار: قابلیت رو روشن می‌کنی، بعد داخل هر چتی که خواستی یک‌بار دستی
# «کریستال» می‌نویسی. همون چت ثبت می‌شه و از اون لحظه هر ۵ دقیقه (به‌علاوه‌ی
# چند ثانیه حاشیه‌ی امن) خودکار «کریستال» فرستاده می‌شه. فقط توی همون یک چت،
# فقط با همون فاصله‌ی کول‌داونِ خودِ ربات؛ نه سریع‌تر، نه توی چت دیگه.
# ─────────────────────────────────────────────────────────────────────────────

import time
import asyncio

from telethon import events, errors

CRYSTAL_WORD = "کریستال"

# کول‌داونِ ربات بازی
CRYSTAL_INTERVAL_SECONDS = 300

# چند ثانیه اضافه روی کول‌داون تا اگه ساعتِ ربات/تأخیر شبکه کمی جلو یا عقب
# بود، پیام زودتر از موعد نرسه و «هنوز زوده» نخوره.
_SAFETY_MARGIN_SECONDS = 5

# اگه ارسال شکست خورد (مثلاً چت در دسترس نبود) چقدر بعد دوباره امتحان کنه
_RETRY_AFTER_FAILURE_SECONDS = 60

# فاصله‌ی چک‌کردنِ حلقه
_LOOP_TICK_SECONDS = 5

SETTING_DEFAULTS_EXTRA = {
    "crystal_game_active": "0",      # روشن/خاموش کلی
    "crystal_game_chat_id": "",      # آیدی عددیِ چتِ ثبت‌شده (اولین چتی که دستی «کریستال» گفتی)
    "crystal_next_ts": "0",          # یونیکس‌تایمِ ارسال بعدی
    "crystal_last_msg_id": "",       # آیدیِ آخرین پیام «کریستال»
}


def _next_send_ts(now: float) -> float:
    return now + CRYSTAL_INTERVAL_SECONDS + _SAFETY_MARGIN_SECONDS


# ─── پنل دکمه‌ای ─────────────────────────────────────────────────────────────
PANEL_CATEGORY = {
    "title": "کریستال خودکار",
    "menu_style": "primary",
    "toggles": [
        ("crystal_game_active", "کریستال خودکار", "کریستال خودکار روشن", "کریستال خودکار خاموش"),
    ],
    "actions": [
        (
            "📖 راهنما",
            "INFO::💎 دکمه‌ی بالا رو روشن کن. بعد داخل چتی که ربات بازی توشه یک‌بار "
            "دستی بنویس «کریستال» تا همون چت ذخیره بشه. از اون به بعد هر ۵ دقیقه "
            "خودش «کریستال» می‌فرسته. برای عوض کردن چت، «ریست چت کریستال» رو بفرست "
            "و بعد توی چت جدید دستی «کریستال» بنویس.",
        ),
        ("🗑 حذف چت کریستال", "ریست چت کریستال"),
    ],
}


# ─── دیسپچر دستورهای متنی ───────────────────────────────────────────────────
def handle_panel_command(text: str, owner_id: int, ss, gs, edit_coro_factory):
    """
    (handled, coroutine) برمی‌گردونه؛ کالر اگه handled بود coroutine رو await می‌کنه.
    """
    if text == "کریستال خودکار روشن":
        ss("crystal_game_active", "1")
        if not gs("crystal_game_chat_id", ""):
            msg = (
                "💎 کریستال خودکار روشن شد.\n"
                "📍 حالا داخل چتی که ربات بازی توشه یک‌بار دستی بنویس «کریستال» "
                "تا همون چت ثبت بشه."
            )
        else:
            msg = "💎 کریستال خودکار روشن شد و روی چتِ قبلاً ثبت‌شده ادامه پیدا می‌کنه."
        return True, edit_coro_factory(msg)

    if text == "کریستال خودکار خاموش":
        ss("crystal_game_active", "0")
        return True, edit_coro_factory("💎 کریستال خودکار خاموش شد.")

    if text in ("ریست چت کریستال", "حذف چت کریستال"):
        ss("crystal_game_chat_id", "")
        ss("crystal_next_ts", "0")
        return True, edit_coro_factory(
            "🗑 چتِ کریستال حذف شد. دفعه‌ی بعد که «کریستال» رو دستی داخل هر چتی "
            "بنویسی، همون چت به‌عنوان چت جدید ثبت می‌شه."
        )

    return False, None


# ─── هندلر Telethon ─────────────────────────────────────────────────────────
def register_handlers(cl, owner_id: int, db):
    def gs(key, default=None):
        return db.get_setting(owner_id, key, default)

    def ss(key, value):
        db.set_setting(owner_id, key, value)

    # هر پیام خروجیِ دقیقاً «کریستال» (چه دستیِ خودِ کاربر، چه ارسالِ خودکارِ
    # حلقه). دو کار می‌کنه:
    #   - اگه هنوز چتی ثبت نشده، همین چت رو ثبت می‌کنه (بایند).
    #   - اگه توی همون چتِ ثبت‌شده‌ست، تایمرِ بعدی رو از همین لحظه ریست می‌کنه؛
    #     چون این پیام کول‌داون رو مصرف کرده. برای «کریستال»ِ دستی هم درسته:
    #     اگه کاربر خودش وسط راه دستی بفرسته، حلقه بعدش ۵ دقیقه صبر می‌کنه.
    @cl.on(events.NewMessage(outgoing=True, pattern=r"^\s*کریستال\s*$"))
    async def _crystal_track(event):
        try:
            if gs("crystal_game_active", "0") != "1":
                return

            bound = gs("crystal_game_chat_id", "")
            chat_id_str = str(event.chat_id)

            if not bound:
                ss("crystal_game_chat_id", chat_id_str)
                ss("crystal_last_msg_id", str(event.message.id))
                ss("crystal_next_ts", str(_next_send_ts(time.time())))
                try:
                    await event.reply(
                        "💎 این چت به‌عنوان چت کریستال ثبت شد. از این به بعد هر ۵ "
                        "دقیقه خودکار «کریستال» فرستاده می‌شه."
                    )
                except Exception:
                    pass
                return

            if bound == chat_id_str:
                ss("crystal_last_msg_id", str(event.message.id))
                ss("crystal_next_ts", str(_next_send_ts(time.time())))
        except Exception as e:
            print(f"❌ [{owner_id}] خطا در هندلر کریستال: {e}")


# ─── حلقه‌ی پس‌زمینه ─────────────────────────────────────────────────────────
async def crystal_loop(cl, owner_id: int, db):
    """
    هر چند ثانیه چک می‌کنه؛ اگه وقتِ «کریستال» رسیده باشه توی چتِ ثبت‌شده
    می‌فرسته و تایمر رو ۵ دقیقه (+ حاشیه‌ی امن) جلو می‌بره.
    """
    while True:
        try:
            if db.get_setting(owner_id, "crystal_game_active", "0") != "1":
                await asyncio.sleep(_LOOP_TICK_SECONDS)
                continue

            chat_id_raw = db.get_setting(owner_id, "crystal_game_chat_id", "")
            if not chat_id_raw:
                await asyncio.sleep(_LOOP_TICK_SECONDS)
                continue

            try:
                chat_id = int(chat_id_raw)
            except ValueError:
                await asyncio.sleep(_LOOP_TICK_SECONDS)
                continue

            now = time.time()
            next_ts = float(db.get_setting(owner_id, "crystal_next_ts", "0") or "0")

            if next_ts > 0 and now >= next_ts:
                # تایمر رو قبل از ارسال جلو می‌بریم تا اگه هندلرِ بالا و لوپ
                # هم‌زمان اجرا شدن، دوباره‌کاری نشه.
                db.set_setting(owner_id, "crystal_next_ts", str(_next_send_ts(now)))
                try:
                    sent = await cl.send_message(chat_id, CRYSTAL_WORD)
                    db.set_setting(owner_id, "crystal_last_msg_id", str(sent.id))
                    print(f"💎 [{owner_id}] «کریستال» ارسال شد.")
                except errors.FloodWaitError as e:
                    wait = int(getattr(e, "seconds", 60)) + 5
                    print(f"⏳ [{owner_id}] FloodWait در کریستال: {wait} ثانیه صبر.")
                    db.set_setting(owner_id, "crystal_next_ts", str(time.time() + wait))
                except Exception as e:
                    print(f"❌ [{owner_id}] خطا در ارسال کریستال: {e}")
                    db.set_setting(
                        owner_id, "crystal_next_ts",
                        str(time.time() + _RETRY_AFTER_FAILURE_SECONDS),
                    )

            await asyncio.sleep(_LOOP_TICK_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"خطا در crystal_loop ({owner_id}): {e}")
            await asyncio.sleep(15)
