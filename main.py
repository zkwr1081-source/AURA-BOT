import logging
import os
import sqlite3
from datetime import datetime, timezone

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

LEAD_DETAILS = 1


def save_lead(user, message: str) -> int:
    """Persist a consented sales inquiry without collecting payment credentials."""
    db_path = os.getenv("LEADS_DB_PATH", "aura_leads.sqlite3")
    with sqlite3.connect(db_path) as connection:
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
        cursor = connection.execute(
            """
            INSERT INTO leads
                (telegram_user_id, username, display_name, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.username,
                user.full_name,
                message,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return int(cursor.lastrowid)


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
    await update.effective_message.reply_text(
        "قبل إرسال طلبك: سنحفظ اسم حساب Telegram ومعرّفك ورسالتك للرد على استفسارك. "
        "لا ترسل كلمات مرور أو رموز تحقق أو بيانات بطاقات أو أسرار دفع. "
        "يمكنك الإلغاء الآن.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return LEAD_DETAILS


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

    admin_chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
    if admin_chat_id:
        try:
            await context.bot.send_message(
                chat_id=int(admin_chat_id),
                text=(
                    f"طلب جديد #{lead_id}\n"
                    f"الاسم: {update.effective_user.full_name}\n"
                    f"المستخدم: @{update.effective_user.username or 'غير محدد'}\n"
                    f"Telegram ID: {update.effective_user.id}\n"
                    f"التفاصيل:\n{message}"
                ),
            )
        except (ValueError, Exception):
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


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing. Set it as an environment variable; "
            "never put bot tokens in source code."
        )

    application = ApplicationBuilder().token(token).build()
    lead_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("request", request_start),
            CallbackQueryHandler(request_start, pattern="^lead_start$"),
        ],
        states={
            LEAD_DETAILS: [
                CallbackQueryHandler(lead_consent, pattern="^lead_consent$"),
                CallbackQueryHandler(lead_cancel, pattern="^lead_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lead_details),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(lead_conversation)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    logger.info("AURA bot is starting")
    application.run_polling()


if __name__ == "__main__":
    main()
