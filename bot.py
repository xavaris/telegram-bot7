import os
import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
TOPIC_ID = int(os.getenv("TOPIC_ID"))
VENDOR_NAMES = os.getenv("VENDOR_NAME", "").lower().split(",")

LOGO_URL = "https://i.imgur.com/51jA7M9.jpeg"

MAX_DAILY = 2

# ================= MEMORY =================

daily_counter = {}
last_group_message_id = None

# ================= STYLE MAP =================

REPLACE_MAP = {
    "a": "∆",
    "e": "€",
    "i": "!",
    "o": "0",
    "s": "$",
    "b": "BV",
    "c": "K",
    "u": "V",
}

def stylize(text):
    result = ""
    for ch in text.lower():
        result += REPLACE_MAP.get(ch, ch)
    return result.upper()

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if not user.username or user.username.lower() not in VENDOR_NAMES:
        await update.message.reply_text("❌ Nie jesteś uprawnionym vendorem.")
        return

    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"count_{i}")]
        for i in range(1, 11)
    ]

    await update.message.reply_text(
        "💣 Ile masz towarów?\n(Wybierz 1–10)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= WYBÓR ILOŚCI =================

async def choose_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    count = int(query.data.split("_")[1])
    context.user_data["count"] = count
    context.user_data["products"] = []

    await query.message.reply_text("📦 Co masz za towar?")

# ================= ZBIERANIE PRODUKTÓW =================

async def collect_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "count" not in context.user_data:
        return

    products = context.user_data["products"]
    products.append(update.message.text)

    if len(products) < context.user_data["count"]:
        await update.message.reply_text("➕ Następny towar:")
        return

    keyboard = [
        [
            InlineKeyboardButton("🔥 TAK", callback_data="publish"),
            InlineKeyboardButton("❌ NIE", callback_data="cancel"),
        ]
    ]

    await update.message.reply_text(
        "🚀 Wysłać ogłoszenie na grupę?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= PUBLIKACJA =================

async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_group_message_id

    query = update.callback_query
    await query.answer()

    user = query.from_user
    username = user.username.lower()

    today = datetime.date.today()

    if username not in daily_counter:
        daily_counter[username] = {"date": today, "count": 0}

    if daily_counter[username]["date"] != today:
        daily_counter[username] = {"date": today, "count": 0}

    if daily_counter[username]["count"] >= MAX_DAILY:
        await query.message.reply_text("❌ Limit 2 ogłoszeń dziennie osiągnięty.")
        return

    daily_counter[username]["count"] += 1

    products = context.user_data["products"]

    fire_emojis = ["💥", "🔥", "🚨", "💣", "⚡"]
    header_emoji = random.choice(fire_emojis)

    now = datetime.datetime.now().strftime("%H:%M")

    text = f"""
{header_emoji}💥💥 OSTATNIA SZANSA 💥💥{header_emoji}

⏱ {now}

🚨 OFERTA 🚨

"""

    for p in products:
        text += f"• {stylize(p)}\n"

    text += f"""

━━━━━━━━━━━━━━━━━━━━
📩 @{username}
⚠️ PISZ PO CENĘ
━━━━━━━━━━━━━━━━━━━━
"""

    # usuń stare ogłoszenie
    if last_group_message_id:
        try:
            await context.bot.delete_message(GROUP_ID, last_group_message_id)
        except:
            pass

    msg = await context.bot.send_photo(
        chat_id=GROUP_ID,
        message_thread_id=TOPIC_ID,
        photo=LOGO_URL,
        caption=text
    )

    last_group_message_id = msg.message_id

    context.user_data.clear()

    await query.message.reply_text("✅ Ogłoszenie opublikowane.")

# ================= ANULUJ =================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    await query.message.reply_text("↩️ Anulowano. /start aby zacząć ponownie.")

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choose_count, pattern="^count_"))
    app.add_handler(CallbackQueryHandler(publish, pattern="^publish$"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_products))

    print("🔥 PREMIUM MARKET BOT STARTED 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
