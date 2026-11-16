import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from aura_core import (
    MENU_ROWS,
    PAYMENT_DISABLED_MESSAGE,
    UNKNOWN_CALLBACK_MESSAGE,
    get_section_text,
    is_supported_callback,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("aura-bot")

WELCOME_TEXT = (
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


def build_main_keyboard() -> InlineKeyboardMarkup:
    """Build the user-facing menu from the validated callback registry."""
    rows = [
        [InlineKeyboardButton(label, callback_data=callback) for label, callback in row]
        for row in MENU_ROWS
    ]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        WELCOME_TEXT,
        reply_markup=build_main_keyboard(),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "حالة AURA: البوت متصل بمعالج Telegram عند تنفيذ هذا الأمر.\n"
        "الأقسام: 6 | الدفع: غير مفعّل | لا توجد معاملات مالية مفعّلة."
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    if query.message is None:
        logger.warning("Callback received without an accessible message")
        return

    callback_data = query.data or ""
    if not is_supported_callback(callback_data):
        await query.message.reply_text(UNKNOWN_CALLBACK_MESSAGE)
        return
    if callback_data == "pay_sub":
        await query.message.reply_text(PAYMENT_DISABLED_MESSAGE)
        return

    section_text = get_section_text(callback_data)
    if section_text is None:
        await query.message.reply_text(UNKNOWN_CALLBACK_MESSAGE)
        return
    await query.message.reply_text(section_text)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled bot error", exc_info=context.error)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing. Set it as an environment variable; "
            "never put bot tokens in source code."
        )

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    logger.info("AURA bot is starting")
    application.run_polling()


if __name__ == "__main__":
    main()

[executed on device: localhost (cbcd1892-30b4-4d96-8398-6c3486f41f3e)]