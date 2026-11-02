import asyncio
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("aura-bot")

LEAD_CONSENT = 0
LEAD_DETAILS = 1


DEFAULT_LEADS_RETENTION_DAYS = 90
MAX_LEADS_RETENTION_DAYS = 3650


def leads_retention_days() -> int:
    """Return a validated lead-retention period in days."""
    raw = os.getenv("LEADS_RETENTION_DAYS", "").strip()
    if not raw:
        raw = str(DEFAULT_LEADS_RETENTION_DAYS)
    try:
        days = int(raw)
    except ValueError as exc:
        raise ValueError("LEADS_RETENTION_DAYS must be an integer") from exc
    if not 1 <= days <= MAX_LEADS_RETENTION_DAYS:
        raise ValueError(
            f"LEADS_RETENTION_DAYS must be between 1 and {MAX_LEADS_RETENTION_DAYS}"
        )
    return days


def configured_admin_chat_id() -> int | None:
    """Return a validated optional Telegram admin chat ID."""
    raw = os.getenv("ADMIN_CHAT_ID", "").strip()
    if not raw:
        return None
    try:
        chat_id = int(raw)
    except ValueError as exc:
        raise ValueError("ADMIN_CHAT_ID must be a numeric Telegram chat ID") from exc
    if chat_id == 0:
        raise ValueError("ADMIN_CHAT_ID must not be zero")
    return chat_id


def _restrict_database_permissions(db_path: str) -> None:
    """Restrict the local lead database to its owner on POSIX systems."""
    if os.name != "posix":
        return
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        logger.warning("Unable to restrict permissions on the lead database file")


def purge_expired_leads() -> int:
    """Delete expired lead records without creating a database when none exists."""
    db_path = os.getenv("LEADS_DB_PATH", "aura_leads.sqlite3")
    if not os.path.isfile(db_path):
        return 0

    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=leads_retention_days())
    ).isoformat()
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='leads'"
            ).fetchone()
            if not table_exists:
                return 0
            cursor = connection.execute(
                "DELETE FROM leads WHERE created_at < ?",
                (cutoff,),
            )
            deleted = max(cursor.rowcount, 0)

    if deleted:
        _restrict_database_permissions(db_path)
    return deleted


def delete_leads_for_user(telegram_user_id: int) -> int:
    """Delete the current user's inquiry records from the local SQLite database."""
    if (
        not isinstance(telegram_user_id, int)
        or isinstance(telegram_user_id, bool)
        or telegram_user_id <= 0
    ):
        raise ValueError("telegram_user_id must be a positive integer")

    db_path = os.getenv("LEADS_DB_PATH", "aura_leads.sqlite3")
    if not os.path.isfile(db_path):
        return 0

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='leads'"
            ).fetchone()
            if not table_exists:
                return 0
            cursor = connection.execute(
                "DELETE FROM leads WHERE telegram_user_id = ?",
                (telegram_user_id,),
            )
            deleted = max(cursor.rowcount, 0)

    if deleted:
        _restrict_database_permissions(db_path)
    return deleted


def save_lead(user, message: str) -> int:
    """Persist a consented inquiry and prune expired records in the same transaction."""
    user_id = getattr(user, "id", None)
    if (
        not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id <= 0
    ):
        raise ValueError("A valid Telegram user is required")

    if not isinstance(message, str):
        raise ValueError("Lead message must be text")
    message = message.strip()
    if not 10 <= len(message) <= 2000:
        raise ValueError("Lead message must contain 10–2000 characters")

    retention_days = leads_retention_days()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=retention_days)).isoformat()
    db_path = os.getenv("LEADS_DB_PATH", "aura_leads.sqlite3")

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    username TEXT,
                    display_name TEXT,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new'
                )
                """
            )
            connection.execute(
                "DELETE FROM leads WHERE created_at < ?",
                (cutoff,),
            )
            cursor = connection.execute(
                """
                INSERT INTO leads
                    (telegram_user_id, username, display_name, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    getattr(user, "username", None),
                    getattr(user, "full_name", None),
                    message,
                    now.isoformat(),
                ),
            )
            lead_id = int(cursor.lastrowid)

    _restrict_database_permissions(db_path)
    return lead_id


async def retention_cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback for daily privacy-retention cleanup."""
    try:
        deleted = await asyncio.to_thread(purge_expired_leads)
        if deleted:
            logger.info("Purged %s expired lead records", deleted)
    except Exception:
        logger.exception("Lead retention cleanup failed")

async def forget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Let a Telegram user remove their inquiry records from the local database."""
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return ConversationHandler.END

    deleted = delete_leads_for_user(user.id)
    if deleted:
        response = f"تم حذف {deleted} سجل طلب من قاعدة AURA المحلية."
    else:
        response = "لم نعثر على طلبات محفوظة لك في قاعدة AURA المحلية."

    if os.getenv("ADMIN_CHAT_ID", "").strip():
        response += (
            "\nملاحظة: قد تبقى نسخة إشعار أُرسلت إلى محادثة الإدارة؛ "
            "حذفها من سجل Telegram يتم داخل تلك المحادثة. "
            "الأمر /forget يحذف سجلات قاعدة AURA فقط."
        )
    await message.reply_text(response)
    return ConversationHandler.END




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🌟 *مرحباً بك في AURA* 🌟\n\n"
        "🤖 مساعدك لإدارة الخدمات والمهام.\n\n"
        "📌 *الأقسام المتاحة:*\n"
        "🏢 Enterprise — حلول الأعمال\n"
        "🤖 Multi-Agent — تنسيق الوكلاء\n"
        "💬 Chat — خدمات المحادثة\n"
        "🎨 Code & Design — البرمجة والتصميم\n"
        "📊 Analytics — تحليل البيانات\n"
        "⚡ Automation — أتمتة المهام\n\n"
        "لطلب عرض سعر أو إعداد بوت لمتجرك استخدم /request.\n"
        "اختر قسماً للمتابعة:"
    )
    keyboard = [
        [InlineKeyboardButton("🏢 Enterprise", callback_data="serv_enterprise"),
         InlineKeyboardButton("🤖 Multi-Agent", callback_data="serv_multi")],
        [InlineKeyboardButton("💬 Chat", callback_data="serv_chat"),
         InlineKeyboardButton("🎨 Code & Design", callback_data="serv_code")],
        [InlineKeyboardButton("📊 Analytics", callback_data="serv_analytics"),
         InlineKeyboardButton("⚡ Automation", callback_data="serv_automation")],
        [InlineKeyboardButton("💳 الاشتراكات", callback_data="pay_sub")],
        [InlineKeyboardButton("🧾 اطلب عرض سعر", callback_data="lead_start")],
    ]
    await update.effective_message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def request_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("أوافق وأتابع", callback_data="lead_consent"),
        InlineKeyboardButton("إلغاء", callback_data="lead_cancel"),
    ]]
    retention_days = leads_retention_days()
    consent_text = (
        "قبل إرسال طلبك: سنحفظ اسم حساب Telegram ومعرّفك واسم العرض ورسالتك "
        f"للرد على استفسارك لمدة احتفاظ قدرها {retention_days} يوماً؛ "
        "تُحذف السجلات المنتهية ضمن التنظيف الدوري كل 24 ساعة أو عند بدء البوت أو حفظ طلب جديد. "
        "يمكنك حذف سجلات طلباتك من قاعدة AURA باستخدام /forget. "
        "لا ترسل كلمات مرور أو رموز تحقق أو بيانات بطاقات أو أسرار دفع."
    )
    admin_chat_id = configured_admin_chat_id()
    if admin_chat_id is not None:
        consent_text += (
            "\nإشعار الإدارة مفعّل: ستُرسل نسخة من تفاصيل الطلب إلى محادثة الإدارة. "
            "الأمر /forget لا يحذف نسخة الرسالة من سجل Telegram لدى الإدارة."
        )
    consent_text += "\nيمكنك الإلغاء الآن."
    await update.effective_message.reply_text(
        consent_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return LEAD_CONSENT


async def lead_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "اكتب طلبك في رسالة واحدة: نوع نشاطك، وما الذي تريد أن يفعله البوت. "
        "لا تضع أي كلمات مرور أو رموز تحقق أو بيانات دفع."
    )
    return LEAD_DETAILS


async def lead_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("تم إلغاء الطلب، ولم نحفظ أي بيانات.")
    return ConversationHandler.END


async def lead_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (update.effective_message.text or "").strip()
    if len(message) < 10:
        await update.effective_message.reply_text(
            "اكتب تفاصيل أكثر قليلاً (10 أحرف على الأقل)، أو استخدم /cancel للإلغاء."
        )
        return LEAD_DETAILS
    if len(message) > 2000:
        await update.effective_message.reply_text(
            "الرسالة طويلة جداً. اختصرها إلى 2000 حرف كحد أقصى."
        )
        return LEAD_DETAILS

    lead_id = save_lead(update.effective_user, message)
    await update.effective_message.reply_text(
        f"وصل طلبك بنجاح. رقم الطلب: #{lead_id}. سنتواصل معك عبر Telegram إذا كانت بيانات التواصل متاحة."
    )

    try:
        admin_chat_id = configured_admin_chat_id()
        if admin_chat_id is not None:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=(
                    f"طلب جديد #{lead_id}\n"
                    f"الاسم: {update.effective_user.full_name}\n"
                    f"المستخدم: @{update.effective_user.username or 'غير محدد'}\n"
                    f"Telegram ID: {update.effective_user.id}\n"
                    f"التفاصيل:\n{message}"
                ),
            )
    except Exception:
        logger.exception("Could not notify admin about lead #%s", lead_id)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("تم إلغاء الطلب.")
    return ConversationHandler.END


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sections = {
        "serv_enterprise": "🏢 قسم Enterprise\nحلول إدارة الأعمال والمشاريع.",
        "serv_multi": "🤖 قسم Multi-Agent\nتنسيق الوكلاء وتوزيع المهام.",
        "serv_chat": "💬 قسم Chat\nتكاملات المحادثة وخدمة العملاء.",
        "serv_code": "🎨 قسم Code & Design\nأدوات البرمجة والتصميم.",
        "serv_analytics": "📊 قسم Analytics\nتحليل البيانات والتقارير.",
        "serv_automation": "⚡ قسم Automation\nأتمتة المهام المتكررة.",
    }
    if query.data == "pay_sub":
        await query.message.reply_text(
            "💳 الدفع الآلي غير مفعّل حالياً. لطلب عرض سعر استخدم /request. "
            "لن نرسل روابط دفع غير موثوقة."
        )
    elif query.data == "lead_start":
        await request_start(update, context)
    else:
        await query.message.reply_text(sections.get(query.data, "الخيار غير معروف."))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled bot error", exc_info=context.error)


def build_lead_conversation() -> ConversationHandler:
    """Build the lead state machine; text collection is reachable only after consent."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("request", request_start),
            CallbackQueryHandler(request_start, pattern="^lead_start$"),
        ],
        states={
            LEAD_CONSENT: [
                CallbackQueryHandler(lead_consent, pattern="^lead_consent$"),
                CallbackQueryHandler(lead_cancel, pattern="^lead_cancel$"),
            ],
            LEAD_DETAILS: [
                CallbackQueryHandler(lead_cancel, pattern="^lead_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lead_details),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("forget", forget),
        ],
        per_user=True,
        per_chat=True,
    )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing. Set it as an environment variable; "
            "never put bot tokens in source code."
        )

    leads_retention_days()
    configured_admin_chat_id()
    purged = purge_expired_leads()
    if purged:
        logger.info("Purged %s expired lead records at startup", purged)

    application = ApplicationBuilder().token(token).build()
    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError(
            "Lead retention requires python-telegram-bot[job-queue] to be installed."
        )
    job_queue.run_repeating(
        retention_cleanup_job,
        interval=24 * 60 * 60,
        first=60,
        name="aura-lead-retention",
    )
    lead_conversation = build_lead_conversation()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(lead_conversation)
    application.add_handler(CommandHandler("forget", forget))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    logger.info("AURA bot is starting")
    application.run_polling()


if __name__ == "__main__":
    main()
