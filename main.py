import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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
        [InlineKeyboardButton("💳 دفع اشتراك", callback_data="pay_sub")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "serv_enterprise":
        await query.message.reply_text("🏢 **قسم Enterprise**\n\nنقدم حلولاً متكاملة للشركات وإدارة المشاريع الكبرى بكفاءة واحترافية عالية.", parse_mode='Markdown')
    elif data == "serv_multi":
        await query.message.reply_text("🤖 **قسم Multi-Agent System**\n\nنظام وكلاء متعددين يعملون معاً لتوزيع المهام وتنفيذها بشكل آلي وسريع.", parse_mode='Markdown')
    elif data == "serv_chat":
        await query.message.reply_text("💬 **قسم Telegram/WhatsApp**\n\nربط وتطوير بوتات محادثة متقدمة للرد على العملاء على مدار الساعة.", parse_mode='Markdown')
    elif data == "serv_code":
        await query.message.reply_text("🎨 **قسم Code & Design**\n\nتصميم الواجهات البرمجية وتطوير السكربتات المخصصة بدقة عالية.", parse_mode='Markdown')
    elif data == "serv_analytics":
        await query.message.reply_text("📊 **قسم Analytics & Data**\n\nتحليل البيانات واستخراج التقارير والإحصائيات لاتخاذ القرارات السليمة.", parse_mode='Markdown')
    elif data == "serv_automation":
        await query.message.reply_text("⚡ **قسم Automation & Speed**\n\nأتمتة العمليات المتكررة وتوفير الوقت والجهد بأعلى سرعة ممكنة.", parse_mode='Markdown')
    elif data == "pay_sub":
        keyboard = [
            [InlineKeyboardButton("💳 دفع عبر البطاقة الائتمانية", callback_data="pay_card")],
            [InlineKeyboardButton("🅿️ دفع عبر PayPal", callback_data="pay_paypal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("💳 **اختر وسيلة الدفع المناسبة:**", reply_markup=reply_markup, parse_mode='Markdown')
    elif data == "pay_card":
        await query.message.reply_text("🔗 **رابط الدفع بالبطاقة:**\nhttps://t.me/our/secure_payment_card", parse_mode='Markdown')
    elif data == "pay_paypal":
        await query.message.reply_text("🔗 **رابط الدفع عبر PayPal:**\nhttps://t.me/our/secure_payment_paypal", parse_mode='Markdown')

def main():
    TOKEN = "856410689:AAGXHGmifmzUnp6T6EZfhOGPr1OD5AZaF94"
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
