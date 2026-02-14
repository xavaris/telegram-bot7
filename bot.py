import os
import time
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
VENDOR_IDS = [int(x) for x in os.getenv("VENDOR_ID").split(",")]

TARGET_GROUP = -1003831965198
TARGET_TOPIC = 42

# ================= MEMORY =================
LAST_ADS = {}
USER_LIMITS = {}

DAILY_LIMIT = 2
DAY_SECONDS = 86400

# ================= SZYFR =================
MAP = {
    "a": "@", "e": "3", "i": "!",
    "o": "0", "s": "$", "y": "¥",
    "k": "K", "l": "1", "t": "7", "g": "9"
}

OFFER_EMOJIS = ["📦", "🎁", "🛒", "💼", "📬", "🧰"]

def encode(text):
    return "".join(MAP.get(c.lower(), c).upper() for c in text)

# ================= KEYBOARDS =================
def amount_keyboard():
    rows, row = [], []
    for i in range(1,11):
        row.append(InlineKeyboardButton(str(i), callback_data=f"AMOUNT_{i}"))
        if len(row)==5:
            rows.append(row)
            row=[]
    rows.append(row)
    return InlineKeyboardMarkup(rows)

def confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ TAK", callback_data="SEND_YES"),
            InlineKeyboardButton("❌ NIE", callback_data="SEND_NO")
        ]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id not in VENDOR_IDS:
        await update.message.reply_text("⛔ Brak uprawnień do dodawania ogłoszeń.")
        return

    context.user_data.clear()
    await update.message.reply_text(
        "🛒 Ile masz towarów? (1–10)",
        reply_markup=amount_keyboard()
    )

# ================= AMOUNT =================
async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    context.user_data["amount"] = int(q.data.split("_")[1])
    context.user_data["products"] = []

    await q.message.reply_text("Co masz za towar? (1)")

# ================= PRODUCTS =================
async def product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id not in VENDOR_IDS:
        return

    if "amount" not in context.user_data:
        return

    context.user_data["products"].append(encode(update.message.text))

    count = len(context.user_data["products"])
    total = context.user_data["amount"]

    if count < total:
        await update.message.reply_text(f"Co masz za towar? ({count+1}/{total})")
    else:
        await update.message.reply_text(
            "📤 Wysłać ogłoszenie na grupę?",
            reply_markup=confirm_keyboard()
        )

# ================= CONFIRM =================
async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    now = time.time()

    if user_id not in VENDOR_IDS:
        return

    if user_id in USER_LIMITS:
        first, count = USER_LIMITS[user_id]
        if now-first < DAY_SECONDS and count >= DAILY_LIMIT:
            await q.message.reply_text("⛔ Limit 2 ogłoszeń na 24h.")
            return
        if now-first >= DAY_SECONDS:
            USER_LIMITS[user_id] = [now,0]
    else:
        USER_LIMITS[user_id] = [now,0]

    if q.data == "SEND_NO":
        context.user_data.clear()
        await start(update, context)
        return

    emoji = random.choice(OFFER_EMOJIS)
    time_now = datetime.now().strftime("%H:%M")
    contact = f"@{q.from_user.username}"

    text = (
        "          ┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "          ┃  ☠️ OSTATNIA SZANSA  ┃\n"
        "          ┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"                🕒 {time_now}\n\n"
        f"                {emoji} OFERTA\n\n"
        "          ━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    for p in context.user_data["products"]:
        text += f"                • {p}\n"

    text += (
        "          ━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"                📩 {contact}"
    )

    if user_id in LAST_ADS:
        try:
            await context.bot.delete_message(TARGET_GROUP, LAST_ADS[user_id])
        except:
            pass

    USER_LIMITS[user_id][1] += 1

    msg = await context.bot.send_message(
        chat_id=TARGET_GROUP,
        message_thread_id=TARGET_TOPIC,
        text=text
    )

    LAST_ADS[user_id] = msg.message_id
    context.user_data.clear()

    await q.message.reply_text("✅ Ogłoszenie wysłane!")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(amount_handler, pattern="^AMOUNT_"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern="^SEND_"))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, product_handler))

    print("PREMIUM VENDOR BOT STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
