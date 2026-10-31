import logging
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from aura_store import Store

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("aura-bot")

STATUSES = {"new", "contacted", "confirmed", "completed", "cancelled"}


def get_store(context):
    return context.application.bot_data["store"]


def is_admin(update, context):
    return update.effective_user and update.effective_user.id in context.application.bot_data["admin_ids"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🛍️ *AURA Commerce*\n\n"
        "متجر Telegram يساعد نشاطك التجاري على عرض المنتجات واستقبال الطلبات ومتابعتها.\n\n"
        "استخدم /shop لتصفح المنتجات.\n"
        "استخدم /help لمعرفة الأوامر."
    )
    await update.effective_message.reply_text(welcome, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "أوامر العملاء:\n"
        "/shop — تصفح المنتجات\n"
        "/cancel — إلغاء إدخال بيانات الطلب"
    )
    if is_admin(update, context):
        message += (
            "\n\nأوامر الإدارة (للمصرّح لهم فقط):\n"
            "/add_product الاسم | السعر | الوصف\n"
            "/products — قائمة المنتجات\n"
            "/orders — آخر الطلبات\n"
            "/set_status رقم_الطلب الحالة"
        )
    await update.effective_message.reply_text(message)


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = get_store(context).list_products()
    if not products:
        await update.effective_message.reply_text(
            "لا توجد منتجات معروضة حالياً. سيضيف المتجر المنتجات قريباً."
        )
        return
    keyboard = [
        [InlineKeyboardButton(
            f"{item['name']} — {item['price']} {context.application.bot_data['currency']}",
            callback_data=f"product:{item['id']}",
        )]
        for item in products[:50]
    ]
    await update.effective_message.reply_text(
        "اختر منتجاً لعرض التفاصيل:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "pay_sub":
        await query.message.reply_text(
            "الدفع الإلكتروني غير مفعّل. لن نرسل روابط دفع غير موثقة. "
            "يمكن للإدارة تأكيد الطلب والتواصل معك."
        )
        return

    if data.startswith("product:"):
        try:
            product_id = int(data.split(":", 1)[1])
        except ValueError:
            await query.message.reply_text("المنتج غير صالح.")
            return
        product = get_store(context).get_product(product_id)
        if not product:
            await query.message.reply_text("هذا المنتج لم يعد متاحاً.")
            return
        currency = context.application.bot_data["currency"]
        text = f"*{product['name']}*\n{product['description']}\nالسعر: {product['price']} {currency}"
        keyboard = [[InlineKeyboardButton("🛒 اطلب الآن", callback_data=f"order:{product_id}")]]
        await query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("order:"):
        try:
            product_id = int(data.split(":", 1)[1])
            user = query.from_user
            order_id = get_store(context).create_order(
                product_id=product_id,
                telegram_user_id=user.id,
                customer_name=user.full_name,
                username=user.username or "",
                currency=context.application.bot_data["currency"],
            )
        except (ValueError, TypeError) as exc:
            await query.message.reply_text(str(exc) or "تعذر إنشاء الطلب.")
            return
        context.user_data["pending_order_id"] = order_id
        keyboard = [[KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True)]]
        await query.message.reply_text(
            f"تم تسجيل طلبك رقم #{order_id}.\n"
            "أرسل رقم هاتفك عبر الزر أدناه أو اكتب وسيلة التواصل المناسبة. "
            "لن يتم تحصيل أي مبلغ من خلال هذا البوت حالياً.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        )
        return

    await query.message.reply_text("الخيار غير معروف.")


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("pending_order_id")
    if not order_id:
        return
    contact = update.effective_message.contact
    if contact.user_id and contact.user_id != update.effective_user.id:
        await update.effective_message.reply_text("يرجى مشاركة رقم هاتفك أنت.")
        return
    saved = get_store(context).attach_contact(order_id, update.effective_user.id, contact.phone_number)
    context.user_data.pop("pending_order_id", None)
    await update.effective_message.reply_text(
        f"وصلت بيانات التواصل للطلب #{order_id}. ستتواصل معك الإدارة لتأكيد التفاصيل.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("pending_order_id")
    if not order_id:
        return
    contact = (update.effective_message.text or "").strip()
    if len(contact) < 3:
        await update.effective_message.reply_text("أرسل رقم هاتف أو وسيلة تواصل واضحة.")
        return
    get_store(context).attach_contact(order_id, update.effective_user.id, contact)
    context.user_data.pop("pending_order_id", None)
    await update.effective_message.reply_text(
        f"تم حفظ وسيلة التواصل للطلب #{order_id}. ستتواصل معك الإدارة للتأكيد.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_order_id", None)
    await update.effective_message.reply_text(
        "تم إلغاء إدخال بيانات الطلب.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        await update.effective_message.reply_text("هذا الأمر مخصص للإدارة.")
        return
    raw = " ".join(context.args)
    parts = [part.strip() for part in raw.split("|", 2)]
    if len(parts) != 3:
        await update.effective_message.reply_text(
            "الصيغة: /add_product الاسم | السعر | الوصف"
        )
        return
    try:
        product_id = get_store(context).add_product(*parts)
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await update.effective_message.reply_text(f"تمت إضافة المنتج بنجاح. رقمه: #{product_id}")


async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        await update.effective_message.reply_text("هذا الأمر مخصص للإدارة.")
        return
    products = get_store(context).list_products(active_only=False)
    if not products:
        await update.effective_message.reply_text("لا توجد منتجات.")
        return
    lines = [
        f"#{p['id']} — {p['name']} — {p['price']} {context.application.bot_data['currency']} "
        f"({'نشط' if p['active'] else 'متوقف'})"
        for p in products
    ]
    await update.effective_message.reply_text("\n".join(lines))


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        await update.effective_message.reply_text("هذا الأمر مخصص للإدارة.")
        return
    orders = get_store(context).list_orders()
    if not orders:
        await update.effective_message.reply_text("لا توجد طلبات حتى الآن.")
        return
    lines = [
        f"#{o['id']} | {o['product_name']} | {o['unit_price']} {o['currency']} "
        f"| {o['status']} | {o['customer_name']} | {o['contact'] or 'بانتظار التواصل'}"
        for o in orders
    ]
    await update.effective_message.reply_text("\n".join(lines))


async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        await update.effective_message.reply_text("هذا الأمر مخصص للإدارة.")
        return
    if len(context.args) != 2:
        await update.effective_message.reply_text(
            "الصيغة: /set_status رقم_الطلب new|contacted|confirmed|completed|cancelled"
        )
        return
    try:
        order_id = int(context.args[0])
        status = context.args[1].lower()
        if status not in STATUSES:
            raise ValueError("حالة الطلب غير صالحة.")
        changed = get_store(context).update_order_status(order_id, status)
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await update.effective_message.reply_text(
        "تم تحديث حالة الطلب." if changed else "لم يتم العثور على الطلب."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled bot error", exc_info=context.error)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing. Set it as an environment variable; "
            "never put bot tokens in source code."
        )

    admin_ids = {
        int(value.strip())
        for value in os.getenv("ADMIN_IDS", "").split(",")
        if value.strip().isdigit()
    }
    database_path = os.getenv("AURA_DATABASE_PATH", "aura_store.db")
    currency = os.getenv("AURA_CURRENCY", "USD").strip().upper()[:8] or "USD"

    application = ApplicationBuilder().token(token).build()
    application.bot_data["store"] = Store(database_path)
    application.bot_data["admin_ids"] = admin_ids
    application.bot_data["currency"] = currency

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("shop", shop))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("add_product", add_product))
    application.add_handler(CommandHandler("products", admin_products))
    application.add_handler(CommandHandler("orders", admin_orders))
    application.add_handler(CommandHandler("set_status", set_status))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.CONTACT, receive_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    application.add_error_handler(error_handler)

    logger.info("AURA Commerce is starting")
    application.run_polling()


if __name__ == "__main__":
    main()
