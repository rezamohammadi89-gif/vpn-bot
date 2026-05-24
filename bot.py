import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = "8627485120:AAH9cntRWuOPeFyaCKIjP69_ZC_YCvrHJGY"
ADMIN_ID = 84749442
CARD_NUMBER = "6104-3387-7954-8946"
CARD_OWNER = "رضا م"

PLANS = {
    "plan_3": {"name": "۳ گیگ", "price": "۱,۰۰۰,۰۰۰ تومان"},
    "plan_6": {"name": "۶ گیگ", "price": "۱,۵۰۰,۰۰۰ تومان"},
    "plan_9": {"name": "۹ گیگ", "price": "۲,۰۰۰,۰۰۰ تومان"},
}

WAITING_RECEIPT = 1
pending_orders = {}

logging.basicConfig(level=logging.INFO)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 خرید VPN", callback_data="buy")],
        [InlineKeyboardButton("📦 پلن‌های من", callback_data="my_plans")],
        [InlineKeyboardButton("🆘 پشتیبانی", callback_data="support")],
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 به ربات فروش VPN خوش اومدی!\n\nسرویس پرسرعت با پشتیبانی ۲۴/۷\n\nیه گزینه انتخاب کن 👇",
        reply_markup=main_keyboard()
    )

async def buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 ۳ گیگ — ۱,۰۰۰,۰۰۰ تومان", callback_data="select_plan_3")],
        [InlineKeyboardButton("🚀 ۶ گیگ — ۱,۵۰۰,۰۰۰ تومان", callback_data="select_plan_6")],
        [InlineKeyboardButton("💎 ۹ گیگ — ۲,۰۰۰,۰۰۰ تومان", callback_data="select_plan_9")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_home")],
    ])
    await query.edit_message_text("📋 پلن مورد نظرت رو انتخاب کن:", reply_markup=keyboard)

async def select_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_id = query.data.replace("select_", "")
    plan = PLANS[plan_id]
    user = query.from_user
    order_id = f"{user.id}_{plan_id}"
    pending_orders[order_id] = {
        "user_id": user.id,
        "username": user.username or user.first_name,
        "plan": plan,
    }
    ctx.user_data["current_order"] = order_id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ رسید پرداخت رو فرستادم", callback_data=f"sent_{order_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data="buy")],
    ])
    await query.edit_message_text(
        f"✅ پلن: {plan['name']} — {plan['price']}\n\n"
        f"💳 شماره کارت:\n`{CARD_NUMBER}`\n"
        f"👤 به نام: {CARD_OWNER}\n\n"
        f"بعد از واریز رسید بفرست 👇",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def receipt_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.replace("sent_", "")
    ctx.user_data["current_order"] = order_id
    await query.edit_message_text("📸 عکس رسید پرداخت رو بفرست:")
    return WAITING_RECEIPT

async def receive_receipt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    order_id = ctx.user_data.get("current_order")
    if not order_id or order_id not in pending_orders:
        await update.message.reply_text("⚠️ سفارش پیدا نشد. دوباره /start بزن.")
        return ConversationHandler.END
    order = pending_orders[order_id]
    plan = order["plan"]
    user = update.effective_user
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأیید", callback_data=f"approve_{order_id}"),
        InlineKeyboardButton("❌ رد", callback_data=f"reject_{order_id}"),
    ]])
    caption = (
        f"🔔 سفارش جدید!\n"
        f"👤 {order['username']} (ID: {user.id})\n"
        f"📦 {plan['name']} — {plan['price']}\n"
        f"🔑 `{order_id}`"
    )
    if update.message.photo:
        await ctx.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id,
                                  caption=caption, reply_markup=keyboard, parse_mode="Markdown")
    elif update.message.document:
        await ctx.bot.send_document(ADMIN_ID, update.message.document.file_id,
                                     caption=caption, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ لطفاً عکس رسید بفرست.")
        return WAITING_RECEIPT
    await update.message.reply_text(
        "✅ رسید دریافت شد!\n⏳ تا ۳۰ دقیقه اکانتت فعال میشه.\n🆘 پشتیبانی: @RezaMhm"
    )
    return ConversationHandler.END

async def approve_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ فقط ادمین!", show_alert=True)
        return
    await query.answer()
    order_id = query.data.replace("approve_", "")
    order = pending_orders.get(order_id)
    if not order:
        await query.edit_message_caption("⚠️ قبلاً پردازش شده.")
        return
    await ctx.bot.send_message(ADMIN_ID,
        f"📤 اکانت رو برای {order['username']} (ID: `{order['user_id']}`) بفرست.",
        parse_mode="Markdown")
    await ctx.bot.send_message(order["user_id"],
        f"🎉 پرداخت تأیید شد!\n✅ پلن: {order['plan']['name']}\n⏳ اکانت VPN چند دقیقه دیگه میاد.\n🆘 @RezaMhm")
    await query.edit_message_caption(query.message.caption + "\n\n✅ تأیید شد.")
    del pending_orders[order_id]

async def reject_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ فقط ادمین!", show_alert=True)
        return
    await query.answer()
    order_id = query.data.replace("reject_", "")
    order = pending_orders.get(order_id)
    if not order:
        await query.edit_message_caption("⚠️ پیدا نشد.")
        return
    await ctx.bot.send_message(order["user_id"],
        "❌ رسید تأیید نشد.\nبرای راهنمایی: @RezaMhm")
    await query.edit_message_caption(query.message.caption + "\n\n❌ رد شد.")
    del pending_orders[order_id]

async def support(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🆘 پشتیبانی:\n📱 @RezaMhm\n⏰ ۹ صبح تا ۱۲ شب",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="back_home")]]))

async def my_plans(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📦 برای مشاهده اکانت‌هات با @RezaMhm در تماس باش.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="back_home")]]))

async def back_home(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👋 به ربات فروش VPN خوش اومدی!\n\nسرویس پرسرعت با پشتیبانی ۲۴/۷\n\nیه گزینه انتخاب کن 👇",
        reply_markup=main_keyboard())

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(receipt_prompt, pattern="^sent_")],
        states={WAITING_RECEIPT: [MessageHandler(filters.PHOTO | filters.Document.ALL, receive_receipt)]},
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy$"))
    app.add_handler(CallbackQueryHandler(select_plan, pattern="^select_plan_"))
    app.add_handler(CallbackQueryHandler(approve_order, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_order, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(my_plans, pattern="^my_plans$"))
    app.add_handler(CallbackQueryHandler(back_home, pattern="^back_home$"))
    print("✅ ربات روشنه!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
