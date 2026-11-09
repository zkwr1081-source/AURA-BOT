import logging
import os
import sqlite3
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logger = logging.getLogger("aura-bot.leads")

ASK_NAME, ASK_CONTACT, ASK_DETAILS = range(3)

SERVICES = {
    "automation": "أتمتة المهام",
    "telegram": "بوت Telegram للأعمال",
    "data": "تنظيف وتحويل ملفات Excel/CSV/PDF",
    "transcription": "تفريغ الصوت العربي إلى Word",
    "dashboard": "لوحات تقارير ومبيعات",
    "integration": "ربط الأنظمة وتكامل API",
}


def _database_path() -> Path:
    return Path(os.getenv("AURA_LEADS_DB", "aura_leads.sqlite3")).expanduser()


def _initialize_database() -> None:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS service_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                telegram_username TEXT,
                service_key TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_service_leads_created_at "
            "ON service_leads(created_at)"
        )


def _save_lead(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if user is None:
        raise ValueError("Telegram user context is missing")

    service_key = str(context.user_data.get("lead_service", ""))
    if service_key not in SERVICES:
        raise ValueError("Invalid service selection")

    values = (
        user.id,
        user.username,
        service_key,
        str(context.user_data["lead_name"]).strip(),
        str(context.user_data["lead_contact"]).strip(),
        str(context.user_data["lead_details"]).strip(),
    )
    with sqlite3.connect(_database_path(), timeout=10) as connection:
        cursor = connection.execute(
            """
            INSERT INTO service_leads
                (telegram_user_id, telegram_username, service_key,
                 customer_name, contact, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return int(cursor.lastrowid)


async def request_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    service_key = query.data.removeprefix("inquiry:")
    if service_key not in SERVICES:
        await query.message.reply_text("الخدمة المختارة غير صالحة.")
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["lead_service"] = service_key
    await query.message.reply_text(
        f"طلب خدمة: {SERVICES[service_key]}\n\n"
        "أرسل اسمك أو اسم شركتك:"
    )
    return ASK_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.effective_message.text or "").strip()
    if not 2 <= len(value) <= 120:
        await update.effective_message.reply_text("الاسم يجب أن يكون بين 2 و120 حرفاً. أعد الإرسال:")
        return ASK_NAME
    context.user_data["lead_name"] = value
    await update.effective_message.reply_text(
        "أرسل وسيلة التواصل المناسبة (Telegram أو بريد أو رقم هاتف):"
    )
    return ASK_CONTACT


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.effective_message.text or "").strip()
    if not 3 <= len(value) <= 200:
        await update.effective_message.reply_text("وسيلة التواصل يجب أن تكون بين 3 و200 حرف. أعد الإرسال:")
        return ASK_CONTACT
    context.user_data["lead_contact"] = value
    await update.effective_message.reply_text(
        "اشرح المطلوب باختصار (من 10 إلى 2000 حرف):"
    )
    return ASK_DETAILS


async def receive_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.effective_message.text or "").strip()
    if not 10 <= len(value) <= 2000:
        await update.effective_message.reply_text("التفاصيل يجب أن تكون بين 10 و2000 حرف. أعد الإرسال:")
        return ASK_DETAILS

    context.user_data["lead_details"] = value
    try:
        lead_id = _save_lead(update, context)
    except (sqlite3.Error, ValueError, KeyError):
        logger.exception("Unable to persist service lead")
        await update.effective_message.reply_text(
            "تعذر حفظ الطلب حالياً. حاول لاحقاً أو تواصل مع الإدارة."
        )
        return ConversationHandler.END

    service_name = SERVICES[context.user_data["lead_service"]]
    await update.effective_message.reply_text(
        f"✅ تم تسجيل طلبك رقم #{lead_id}.\n"
        f"الخدمة: {service_name}\n"
        "الطلب محفوظ محلياً، وسيتم التواصل معك عند توفر فريق الإدارة."
    )

    admin_chat_id = os.getenv("AURA_ADMIN_CHAT_ID", "").strip()
    if admin_chat_id:
        admin_message = (
            f"طلب خدمة جديد #{lead_id}\n"
            f"الخدمة: {service_name}\n"
            f"الاسم: {context.user_data['lead_name']}\n"
            f"التواصل: {context.user_data['lead_contact']}\n"
            f"Telegram user ID: {update.effective_user.id}\n"
            f"التفاصيل: {value}"
        )
        try:
            await context.bot.send_message(chat_id=int(admin_chat_id), text=admin_message)
        except (ValueError, Exception):
            logger.exception("Lead saved but admin notification failed")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("تم إلغاء الطلب.")
    return ConversationHandler.END


def build_service_inquiry_handler() -> ConversationHandler:
    _initialize_database()
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(request_service, pattern=r"^inquiry:")],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_contact)],
            ASK_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel_request)],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
    )


def service_inquiry_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"inquiry:{key}")]
        for key, label in SERVICES.items()
    ]
    return InlineKeyboardMarkup(rows)
