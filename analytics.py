# analytics.py
"""
ماژول سبکِ آنالیتیکسِ کسب‌وکار (نه لاگِ فنی).

قبل از این فایل، هیچ‌جای پروژه داده‌ای برای سوالاتی مثل «کدوم پلن بیشتر
فروش می‌ره؟»، «چند درصد کاربرها بعد از انقضای اشتراک تمدید نمی‌کنن
(churn)؟» یا «کدوم قابلیت بیشتر روشن می‌شه؟» جمع نمی‌شد. این ماژول با
یک جدول ساده (`amel_events`) همین‌ها رو اضافه می‌کنه، بدون تغییر در
معماری فعلی (execute_query روی Supabase).

نحوه‌ی استفاده:
    import analytics
    analytics.track_event(owner_id, "subscription_activated", {"plan": "monthly", "days": 30})

    # برای دیدنِ خلاصه (مثلاً از پنل ادمین یا یک اسکریپت جدا):
    analytics.get_summary(days=30)

نکته: track_event هرگز نباید کاری که صداش می‌زنه رو fail کنه — برای
همین هرجا صدا زده می‌شه، توی try/except پیچیده شده و خطاش فقط لاگ می‌شه.
"""
import json
import database_supabase as db


# ─── ثبت رویداد ────────────────────────────────────────────────────────────
def track_event(owner_id, event_type: str, metadata: dict = None) -> None:
    """یک رویدادِ کسب‌وکار رو توی amel_events ثبت می‌کنه.

    ✅ همیشه در پس‌زمینه (بدون بلاک کردن صدازننده) — آنالیتیکس هیچ‌وقت
    نباید سرعتِ پاسخ‌دهی به کاربر رو کند کنه.
    """
    db._bg_executor.submit(_write_event, owner_id, event_type, metadata)


def _write_event(owner_id, event_type: str, metadata: dict = None) -> None:
    try:
        db.execute_query(
            "INSERT INTO amel_events (owner_id, event_type, metadata) VALUES (%s, %s, %s)",
            (owner_id, event_type, json.dumps(metadata or {}, ensure_ascii=False)),
        )
    except Exception as e:
        print(f"⚠️ analytics: خطا در ثبت رویداد {event_type}: {e}")


# ─── خواندن/تحلیل ──────────────────────────────────────────────────────────
def get_event_counts(days: int = 30) -> dict:
    """تعداد هر نوع رویداد در N روز اخیر — برای دیدنِ کدوم قابلیت پراستفاده‌تره."""
    try:
        rows = db.execute_query(
            """SELECT event_type, COUNT(*) AS cnt
               FROM amel_events
               WHERE created_at >= NOW() - (%s || ' days')::interval
               GROUP BY event_type
               ORDER BY cnt DESC""",
            (days,),
            fetch_all=True,
        )
        return {r["event_type"]: r["cnt"] for r in (rows or [])}
    except Exception as e:
        print(f"⚠️ analytics: خطا در get_event_counts: {e}")
        return {}


def get_plan_breakdown(days: int = 30) -> dict:
    """تعداد خرید/تمدید هر پلن در N روز اخیر."""
    try:
        rows = db.execute_query(
            """SELECT metadata FROM amel_events
               WHERE event_type = 'subscription_activated'
                 AND created_at >= NOW() - (%s || ' days')::interval""",
            (days,),
            fetch_all=True,
        )
        breakdown = {}
        for r in (rows or []):
            try:
                meta = json.loads(r["metadata"] or "{}")
                plan = meta.get("plan", "unknown")
                breakdown[plan] = breakdown.get(plan, 0) + 1
            except Exception:
                continue
        return breakdown
    except Exception as e:
        print(f"⚠️ analytics: خطا در get_plan_breakdown: {e}")
        return {}


def get_churn_estimate(days: int = 30) -> dict:
    """
    تخمینِ ریزش (churn): از بینِ اشتراک‌هایی که توی N روز اخیر منقضی شدن،
    چند درصدشون بعد از تاریخ انقضا یک رویدادِ subscription_activated جدید
    (یعنی تمدید) نداشتن.

    این یک تخمینه، نه عددِ دقیقِ حسابداری‌شده — اگه کاربر با owner_id
    دیگه‌ای دوباره اشتراک بخره (مثلاً اکانتِ جدید)، به‌عنوانِ ریزش حساب
    می‌شه.
    """
    try:
        expired = db.execute_query(
            """SELECT owner_id, expires_at FROM amel_subscriptions
               WHERE expires_at < NOW()
                 AND expires_at >= NOW() - (%s || ' days')::interval""",
            (days,),
            fetch_all=True,
        )
        if not expired:
            return {"expired_count": 0, "renewed_count": 0, "churn_rate": 0.0}

        expired_count = len(expired)
        renewed_count = 0
        for row in expired:
            renewed = db.execute_query(
                """SELECT 1 FROM amel_events
                   WHERE owner_id = %s AND event_type = 'subscription_activated'
                     AND created_at > %s LIMIT 1""",
                (row["owner_id"], row["expires_at"]),
                fetch_one=True,
            )
            if renewed:
                renewed_count += 1

        churn_rate = round((expired_count - renewed_count) / expired_count * 100, 1)
        return {
            "expired_count": expired_count,
            "renewed_count": renewed_count,
            "churn_rate": churn_rate,
        }
    except Exception as e:
        print(f"⚠️ analytics: خطا در get_churn_estimate: {e}")
        return {"expired_count": 0, "renewed_count": 0, "churn_rate": 0.0}


def get_summary(days: int = 30) -> dict:
    """خلاصه‌ی یک‌جا — برای پنل ادمین یا چاپ توی لاگ."""
    return {
        "period_days": days,
        "event_counts": get_event_counts(days),
        "plan_breakdown": get_plan_breakdown(days),
        "churn": get_churn_estimate(days),
    }
