import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ContextTypes,
    CommandHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🌟 **مرحباً بك في AURA** 🌟\n\n"
        "✨ **أنت الآن في قلب الناصع** ✨\n\n"
        "🤖 **بوت ذكي ومتقدم لمساعدتك في كل ما تحتاجه** 🤖\n\n"
        "📌 **الخدمات المتاحة حالياً:**\n\n"
        "🏢 **[Enterprise]** إدارة أعمالك وخدمات الشركات الكبرى\n"
        "🤖 **[Multi-Agent System]** نظام الوكلاء المتعددين لتوزيع المهام بكفاءة عالية\n"
        "💬 **[Telegram/WhatsApp]** ربط وإدارة بوتات المحادثات الذكية\n"
        "🎨 **[Code & Design]** تصميم وتطوير الأكواد والواجهات البرمجية\n"
        "📊 **[Analytics & Data]** تحليل البيانات وعرض التقارير بدقة متناهية\n"
        "⚡ **[Automation & Speed]** أتمتة العمليات والمهام الروتينية بسرعة فائقة\n\n"
        "👇 **اختر إحدى الخدمات التالية للبدء:**"
    )
    keyboard = [
        [InlineKeyboardButton("🏢 Enterprise", callback_data="serv_enterprise"), InlineKeyboardButton("🤖 Multi-Agent", callback_data="serv_multi")],
        [InlineKeyboardButton("💬 Telegram/WhatsApp", callback_data="serv_chat"), InlineKeyboardButton("🎨 Code & Design", callback_data="serv_code")],
        [InlineKeyboardButton("📊 Analytics & Data", callback_data="serv_analytics"), InlineKeyboardButton("⚡ Automation", callback_data="serv_automation")],
        [InlineKeyboardButton("💳 دفع اشتراك", callback_data="pay_sub")],
    ]
    await update.effective_message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    data = query.data

    sections = {
        "serv_enterprise": ("🏢 **قسم Enterprise**\n\nنقدم حلولاً متكاملة للشركات وإدارة المشاريع الكبرى بكفاءة واحترافية عالية."),
        "serv_multi": ("🤖 **قسم Multi-Agent System**\n\nنظام وكلاء متعددين يعملون معاً لتوزيع المهام وتنفيذها بشكل آلي وسريع."),
        "serv_chat": ("💬 **قسم Telegram/WhatsApp**\n\nربط وتطوير بوتات محادثة متقدمة للرد على العملاء على مدار الساعة."),
        "serv_code": ("🎨 **قسم Code & Design**\n\nتصميم الواجهات البرمجية وتطوير السكربتات المخصصة بدقة عالية."),
        "serv_analytics": ("📊 **قسم Analytics & Data**\n\nتحليل البيانات واستخراج التقارير والإحصائيات لاتخاذ القرارات السليمة."),
        "serv_automation": ("⚡ **قسم Automation & Speed**\n\nأتمتة العمليات المتكررة وتوفير الوقت والجهد بأعلى سرعة ممكنة."),
    }
    if data in sections:
        await query.message.reply_text(sections[data], parse_mode="Markdown")
    elif data == "pay_sub":
        keyboard = [
            [InlineKeyboardButton("💳 دفع عبر البطاقة الائتمانية", callback_data="pay_card")],
            [InlineKeyboardButton("🅿️ دفع عبر PayPal", callback_data="pay_paypal")],
        ]
        await query.message.reply_text(
            "💳 **اختر وسيلة الدفع المناسبة:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    elif data in {"pay_card", "pay_paypal"}:
        env_name = "PAYMENT_CARD_URL" if data == "pay_card" else "PAYMENT_PAYPAL_URL"
        payment_url = os.getenv(env_name, "").strip()
        if payment_url.startswith(("https://", "http://")):
            await query.message.reply_text(f"رابط الدفع: {payment_url}")
        else:
            await query.message.reply_text(
                "خدمة الدفع غير مهيأة بعد. يرجى التواصل مع إدارة AURA لإتمام الاشتراك."
            )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is required. Set it in the deployment environment."
        )

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()


if __name__ == "__main__":
    main()
