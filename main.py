import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("aura-bot")


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
    ]
    await update.effective_message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


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
            "💳 الدفع غير مفعّل بعد. لن نعرض روابط دفع تجريبية أو غير موثوقة. "
            "يرجى التواصل مع إدارة البوت لتفعيل وسيلة دفع رسمية."
        )
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
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    logger.info("AURA bot is starting")
    application.run_polling()


if __name__ == "__main__":
    main()
