"""
resolve_premium_clock_emojis.py
────────────────────────────────────────────────────────────────────────────
این اسکریپت کمک می‌کنه تا لیستِ نامرتبِ ۱۴۴۰ تا آیدیِ ایموجیِ پرمیوم رو
خودکار «بخونه» و بفهمه هر کدوم دقیقاً مالِ چه ساعت:دقیقه‌ای هست، و در نهایت
فایلِ نهاییِ premium_clock_emojis.py (به‌ترتیبِ ۰۰:۰۰ تا ۲۳:۵۹) رو خودش
بسازه — دقیقاً همون کاری که گفتی «سلف سرچ کنه ببینه کدوم ایموجیه».

روشِ کار:
  ۱. تمامِ آیدی‌ها رو (هر تعداد، به هر ترتیبی) توی فایلِ
     tools/premium_clock_emoji_ids.txt می‌ریزی — هر خط یک آیدی.
  ۲. این اسکریپت با همون سشنِ سلفِ خودت (که قبلاً لاگین کرده) به تلگرام
     وصل می‌شه و مستنداتِ واقعیِ هر ایموجی رو می‌گیره
     (GetCustomEmojiDocumentsRequest) — چون این‌ها ایموجیِ سفارشی/پرمیوم
     هستن، برای گرفتنشون فقط آیدی کافیه (access_hash لازم نیست).
  ۳. برای هر ایموجی، یک فریم ازش (اگه انیمیشنه) یا خودِ تصویر (اگه استاتیکه)
     رو می‌گیره و با OCR سعی می‌کنه متنِ «HH:MM» روش رو بخونه.
  ۴. در پایان، اگه همه‌چی خوب پیش بره، فایلِ premium_clock_emojis.py رو
     خودش با ترتیبِ درست بازنویسی می‌کنه؛ و یک گزارش (CSV) هم از هر آیدی +
     ساعتِ تشخیص‌داده‌شده می‌سازه تا بتونی دستی چک/تصحیح کنی.

⚠️ نیازمندی‌ها (روی سرورِ خودت نصب کن، این‌ها از قبل توی پروژه نیستن):
    pip install telethon pillow pytesseract --break-system-packages
    apt install tesseract-ocr ffmpeg          # (دیبیان/اوبونتو)

  - اگه ایموجی‌ها انیمیشنِ ویدیویی (webm) باشن → از ffmpeg برای گرفتنِ یک
    فریم استفاده می‌شه (باید ffmpeg نصب باشه).
  - اگه انیمیشنِ لاتی (tgs) باشن، این اسکریپت خودش نمی‌تونه رندرش کنه
    (رندرِ tgs به PNG کتابخونه‌ی سنگین‌تری می‌خواد: pip install "lottie[all]")
    — در اون حالت فایلِ خام .tgs رو ذخیره می‌کنه و توی گزارش «نیاز به رندرِ
    دستی» می‌نویسه؛ به من بگو تا اون بخش رو هم اضافه کنم.

  ⚠️ این اسکریپت باید روی همون سروری اجرا بشه که به اینترنت/تلگرام دسترسیِ
  واقعی داره (نه توی این محیطِ چت) — چون این‌جا نه اینترنت داریم نه سشنِ
  واقعیِ سلف.

اجرا:
    python3 tools/resolve_premium_clock_emojis.py
"""

import asyncio
import csv
import os
import re
import subprocess
import sys

# ─── تنظیمات ────────────────────────────────────────────────────────────────
IDS_FILE = os.path.join(os.path.dirname(__file__), "premium_clock_emoji_ids.txt")
FRAMES_DIR = os.path.join(os.path.dirname(__file__), "_clock_emoji_frames")
REPORT_CSV = os.path.join(os.path.dirname(__file__), "premium_clock_emoji_report.csv")
OUTPUT_PY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "premium_clock_emojis.py")

# سشن سلف برای گرفتنِ مستنداتِ ایموجی. یکی از سشن‌های فعالِ پروژه رو این‌جا
# بذار (مسیرِ فایلِ .session یا رشته‌ی StringSession) — همون چیزی که
# bot_manager برای این owner استفاده می‌کنه.
SESSION = os.environ.get("CLOCK_RESOLVER_SESSION", "clock_resolver_session")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config  # noqa: E402  — برای API_ID / API_HASH پروژه


TIME_RE = re.compile(r"([01]?\d|2[0-3])[:.\s]?([0-5]\d)")


def _ocr_image_to_time(image_path: str):
    """یک عکس رو با OCR می‌خونه و اگه الگوی HH:MM توش پیدا شد برمی‌گردونه."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print("❌ pytesseract/Pillow نصب نیست. اجرا کن:\n"
              "   pip install pillow pytesseract --break-system-packages\n"
              "   apt install tesseract-ocr")
        return None

    try:
        img = Image.open(image_path).convert("L")
        # بزرگ‌نمایی برای دقتِ بهترِ OCR روی متنِ کوچیک
        img = img.resize((img.width * 4, img.height * 4))
        text = pytesseract.image_to_string(
            img, config="--psm 7 -c tessedit_char_whitelist=0123456789:."
        )
        m = TIME_RE.search(text)
        if m:
            h, mnt = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mnt <= 59:
                return h, mnt
    except Exception as e:
        print(f"⚠️ خطای OCR روی {image_path}: {e}")
    return None


def _extract_frame_from_webm(webm_path: str, out_png: str) -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path, "-frames:v", "1", out_png],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        return os.path.exists(out_png)
    except Exception as e:
        print(f"⚠️ ffmpeg نتونست فریم بگیره از {webm_path}: {e}")
        return False


async def main():
    from telethon import TelegramClient
    from telethon.tl.functions.messages import GetCustomEmojiDocumentsRequest

    if not os.path.exists(IDS_FILE):
        print(f"❌ فایلِ {IDS_FILE} پیدا نشد.\n"
              f"همه‌ی آیدی‌های ایموجی رو (هر ترتیبی، هر تعداد) توش بریز، هر خط یک آیدی.")
        return

    with open(IDS_FILE, "r", encoding="utf-8") as f:
        raw_ids = [line.strip() for line in f if line.strip()]
    # حذف تکراری‌ها ولی حفظِ ترتیبِ اول
    seen = set()
    ids = []
    for x in raw_ids:
        if x not in seen:
            seen.add(x)
            ids.append(int(x))

    print(f"📋 {len(ids)} آیدیِ یکتا خونده شد (از {len(raw_ids)} خط).")

    os.makedirs(FRAMES_DIR, exist_ok=True)

    client = TelegramClient(SESSION, config.API_ID, config.API_HASH)
    await client.start()

    resolved = {}   # {(hour, minute): document_id}
    unresolved = []  # [(document_id, reason)]

    # تلگرام معمولاً محدودیتِ تعداد در هر درخواست داره؛ ۱۰۰ تایی می‌فرستیم
    CHUNK = 100
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i:i + CHUNK]
        try:
            docs = await client(GetCustomEmojiDocumentsRequest(document_id=chunk))
        except Exception as e:
            print(f"❌ خطا در گرفتنِ چانکِ {i}-{i+len(chunk)}: {e}")
            unresolved.extend((d, f"fetch_error: {e}") for d in chunk)
            continue

        for doc in docs:
            doc_id = doc.id
            mime = getattr(doc, "mime_type", "")
            try:
                if mime == "video/webm":
                    webm_path = os.path.join(FRAMES_DIR, f"{doc_id}.webm")
                    await client.download_media(doc, file=webm_path)
                    png_path = os.path.join(FRAMES_DIR, f"{doc_id}.png")
                    if _extract_frame_from_webm(webm_path, png_path):
                        t = _ocr_image_to_time(png_path)
                    else:
                        t = None
                elif mime in ("image/webp", "image/png", "image/jpeg"):
                    img_path = os.path.join(FRAMES_DIR, f"{doc_id}.png")
                    await client.download_media(doc, file=img_path)
                    t = _ocr_image_to_time(img_path)
                elif "tgsticker" in mime or "lottie" in mime:
                    # لاتی (وکتور) — این اسکریپت فعلاً رندرش نمی‌کنه
                    raw_path = os.path.join(FRAMES_DIR, f"{doc_id}.tgs")
                    await client.download_media(doc, file=raw_path)
                    t = None
                    unresolved.append((doc_id, f"lottie_needs_render:{raw_path}"))
                    continue
                else:
                    t = None
                    unresolved.append((doc_id, f"unknown_mime:{mime}"))
                    continue
            except Exception as e:
                unresolved.append((doc_id, f"download_error:{e}"))
                continue

            if t is None:
                unresolved.append((doc_id, "ocr_failed"))
            else:
                h, m = t
                if (h, m) in resolved:
                    unresolved.append((doc_id, f"duplicate_time_{h:02d}:{m:02d} (قبلاً {resolved[(h, m)]})"))
                else:
                    resolved[(h, m)] = doc_id

        print(f"⏳ پردازش شد: {min(i + CHUNK, len(ids))}/{len(ids)} "
              f"(حل‌شده تا الان: {len(resolved)})")

    await client.disconnect()

    # ─── گزارش ──────────────────────────────────────────────────────────────
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hour", "minute", "document_id"])
        for (h, m), doc_id in sorted(resolved.items()):
            w.writerow([h, m, doc_id])
        w.writerow([])
        w.writerow(["--- حل‌نشده‌ها ---"])
        w.writerow(["document_id", "دلیل"])
        for doc_id, reason in unresolved:
            w.writerow([doc_id, reason])

    print(f"\n✅ {len(resolved)}/1440 دقیقه حل شد.")
    print(f"❌ {len(unresolved)} تا حل نشد (جزئیات توی {REPORT_CSV}).")

    missing = [(h, m) for h in range(24) for m in range(60) if (h, m) not in resolved]
    if missing:
        print(f"⚠️ {len(missing)} دقیقه هنوز آیدی نداره. چندتاش: "
              + ", ".join(f"{h:02d}:{m:02d}" for h, m in missing[:10]))

    # ─── ساختِ فایلِ نهایی (فقط اگه همه‌چی کامل بود) ───────────────────────────
    if not missing:
        lines = [
            "# premium_clock_emojis.py",
            "# این فایل به‌صورتِ خودکار توسطِ tools/resolve_premium_clock_emojis.py ساخته شده.",
            "",
            "PREMIUM_CLOCK_EMOJIS = [",
        ]
        for h in range(24):
            for m in range(60):
                lines.append(f"    {resolved[(h, m)]},  # {h:02d}:{m:02d}")
        lines.append("]")
        with open(OUTPUT_PY, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"🎉 فایلِ {OUTPUT_PY} کامل ساخته شد!")
    else:
        print("ℹ️ چون هنوز کامل نیست، premium_clock_emojis.py بازنویسی نشد "
              "(بعد از تکمیلِ کمبودها دوباره اجرا کن).")


if __name__ == "__main__":
    asyncio.run(main())
