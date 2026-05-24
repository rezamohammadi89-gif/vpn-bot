import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── تنظیمات ───────────────────────────────────────────────
BOT_TOKEN = "8627485120:AAH9cntRWuOPeFyaCKIjP69_ZC_YCvrHJGY"
ADMIN_ID = 84749442
CARD_NUMBER = "6104-3387-7954-8946"
CARD_OWNER = "رضا م"

PLANS = {
    "plan_3": {"name": "۳ گیگ", "price": "۱,۰۰۰,۰۰۰ تومان", "duration": "۱ ماهه"},
    "plan_6": {"name": "۶ گیگ", "price": "۱,۵۰۰,۰۰۰ تومان", "duration": "۱ ماهه"},
    "plan_9": {"name": "۹ گیگ", "price": "۲,۰۰۰,۰۰۰ تومان", "duration": "۱ ماهه"},
}

WAITING_RECEIPT = 1
pending_orders = {}  # order_id -> {user_id, plan, username}

logging.basicConfig(level=logging.INFO)

# ─── /start ────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 خرید VPN", callback_data="buy")],
        [InlineKeyboardButton("📦 پلن‌های من", callback_data="my_plans")],
        [InlineKeyboardButton("🆘 پشتیبانی", callback_data="support")],
    ]
    await update.message.reply_text(
        "👋 به ربات فروش VPN خوش اومدی!\n\n"
        "سرویس پرسرعت و پایدار با پشتیبانی ۲۴/۷\n\n"
        "یه گزینه انتخاب کن 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── نمایش پلن‌ها ──────────────────────────────────────────
async def show_plans(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for plan_id, plan in PLANS.items():
        label = f"{'📦' if '۳' in plan['name'] else '🚀' if '۶' in plan['name'] else '💎'} {plan['name']} — {plan['price']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"select_{plan_id}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="back_home")])

    await query.edit_message_text(
        "📋 پلن‌های موجود:\n\n"
        "📦 ۳ گیگ — ۱,۰۰۰,۰۰۰ تومان\n"
        "🚀 ۶ گیگ — ۱,۵۰۰,۰۰۰ تومان\n"
        "💎 ۹ گیگ — ۲,۰۰۰,۰۰۰ تومان\n\n"
        "یه پلن انتخاب کن 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── انتخاب پلن → نمایش شماره کارت ───────────────────────
async def select_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.replace("select_", "")
    plan = PLANS[plan_id]
    user = query.from_user

    # ذخیره سفارش موقت
    order_id = f"{user.id}_{plan_id}"
    pending_orders[order_id] = {
        "user_id": user.id,
        "username": user.username or user.first_name,
        "plan": plan,
        "plan_id": plan_id,
    }
    ctx.user_data["current_order"] = order_id

    keyboard = [
        [InlineKeyboardButton("✅ رسید پرداخت رو فرستادم", callback_data=f"sent_receipt_{order_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data="buy")],
    ]

    await query.edit_message_text(
        f"✅ پلن انتخابی: {plan['name']} — {plan['price']}\n\n"
        f"💳 شماره کارت برای واریز:\n"
        f"`{CARD_NUMBER}`\n"
        f"👤 به نام: {CARD_OWNER}\n\n"
        f"📌 مبلغ: {plan['price']}\n\n"
        f"بعد از واریز، روی دکمه زیر کلیک کن و اسکرین‌شات رسید رو بفرست 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ─── دریافت رسید ──────────────────────────────────────────
async def receipt_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = query.data.replace("sent_receipt_", "")
    ctx.user_data["current_order"] = order_id

    await query.edit_message_text(
        "📸 عکس رسید پرداخت رو همین الان بفرست:"
    )
    return WAITING_RECEIPT

async def receive_receipt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    order_id = ctx.user_data.get("current_order")
    if not order_id or order_id not in pending_orders:
        await update.message.reply_text("⚠️ سفارشی پیدا نشد. دوباره از /start شروع کن.")
        return ConversationHandler.END

    order = pending_orders[order_id]
    plan = order["plan"]
    user = update.effective_user

    # ارسال به ادمین
    keyboard = [
        [
            InlineKeyboardButton("✅ تأیید و ارسال اکانت", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ رد کردن", callback_data=f"reject_{order_id}"),
        ]
    ]

    caption = (
        f"🔔 سفارش جدید!\n\n"
        f"👤 کاربر: {order['username']} (ID: {user.id})\n"
        f"📦 پلن: {plan['name']}\n"
        f"💰 مبلغ: {plan['price']}\n"
        f"🔑 Order ID: `{order_id}`"
    )

    if update.message.photo:
        await ctx.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif update.message.document:
        await ctx.bot.send_document(
            chat_id=ADMIN_ID,
            document=update.message.document.file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ لطفاً عکس رسید رو بفرست.")
        return WAITING_RECEIPT

    await update.message.reply_text(
        "✅ رسیدت دریافت شد!\n\n"
        "⏳ ادمین بررسی می‌کنه و معمولاً تا ۳۰ دقیقه اکانتت فعال می‌شه.\n\n"
        "🆘 اگه مشکلی بود: @RezaMhm"
    )
    return ConversationHandler.END

# ─── تأیید توسط ادمین ─────────────────────────────────────
async def approve_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ فقط ادمین می‌تونه تأیید کنه!", show_alert=True)
        return

    order_id = query.data.replace("approve_", "")
    order = pending_orders.get(order_id)
    if not order:
        await query.edit_message_caption("⚠️ این سفارش قبلاً پردازش شده.")
        return

    ctx.user_data[f"approve_{order_id}"] = True

    await query.edit_message_caption(
        query.message.caption + "\n\n✅ تأیید شد — در حال ارسال اکانت..."
    )

    await ctx.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"📤 اکانت رو برای کاربر {order['username']} (ID: `{order['user_id']}`) بفرست.\n\n"
            f"کانفیگ رو ریپلای کن یا مستقیم به کاربر پیام بده."
        ),
        parse_mode="Markdown"
    )

    await ctx.bot.send_message(
        chat_id=order["user_id"],
        text=(
            f"🎉 پرداختت تأیید شد!\n\n"
            f"✅ پلن: {order['plan']['name']}\n\n"
            f"⏳ اکانت VPN تو چند دقیقه دیگه برات ارسال می‌شه.\n\n"
            f"🆘 پشتیبانی: @RezaMhm"
        )
    )

    del pending_orders[order_id]

# ─── رد توسط ادمین ────────────────────────────────────────
async def reject_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ فقط ادمین!", show_alert=True)
        return

    order_id = query.data.replace("reject_", "")
    order = pending_orders.get(order_id)
    if not order:
        await query.edit_message_caption("⚠️ سفارش پیدا نشد.")
        return

    await ctx.bot.send_message(
        chat_id=order["user_id"],
        text=(
            "❌ متأسفانه رسید پرداخت تأیید نشد.\n\n"
            "دلیل احتمالی: مبلغ اشتباه یا رسید ناخوانا\n\n"
            "برای راهنمایی با @RezaMhm در تماس باش."
        )
    )

    await query.edit_message_caption(
        query.message.caption + "\n\n❌ رد شد."
    )

    del pending_orders[order_id]

# ─── پشتیبانی ─────────────────────────────────────────────
async def support(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back_home")]]
    await query.edit_message_text(
        "🆘 پشتیبانی:\n\n"
        "📱 تلگرام: @RezaMhm\n\n"
        "⏰ ساعت پاسخگویی: ۹ صبح تا ۱۲ شب",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_plans(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="back_home")]]
    await query.edit_message_text(
        "📦 اکانت‌های فعال شما:\n\n"
        "برای مشاهده اکانت‌هات با @RezaMhm در تماس باش.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def back_home(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🛒 خرید VPN", callback_data="buy")],
        [InlineKeyboardButton("📦 پلن‌های من", callback_data="my_plans")],
        [InlineKeyboardButton("🆘 پشتیبانی", callback_data="support")],
    ]
    await query.edit_message_text(
        "👋 به ربات فروش VPN خوش اومدی!\n\n"
        "سرویس پرسرعت و پایدار با پشتیبانی ۲۴/۷\n\n"
        "یه گزینه انتخاب کن 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── main ──────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(receipt_prompt, pattern="^sent_receipt_")],
        states={WAITING_RECEIPT: [MessageHandler(filters.PHOTO | filters.Document.ALL, receive_receipt)]},
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^buy$"))
    app.add_handler(CallbackQueryHandler(select_plan, pattern="^select_plan_"))
    app.add_handler(CallbackQueryHandler(approve_order, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_order, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(my_plans, pattern="^my_plans$"))
    app.add_handler(CallbackQueryHandler(back_home, pattern="^back_home$"))

    print("✅ ربات روشنه!")
    app.run_polling()

if __name__ == "__main__":
    main()
