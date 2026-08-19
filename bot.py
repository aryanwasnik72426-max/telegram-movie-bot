import os
import sqlite3
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

PORT = int(os.environ.get("PORT", 8000))
DB_FILE = "files.db"

app = Flask(__name__)

bot_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .updater(None)
    .build()
)


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            message_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            caption TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_file(message_id, name, caption):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR REPLACE INTO files
        (message_id, name, caption)
        VALUES (?, ?, ?)
        """,
        (message_id, name, caption),
    )

    conn.commit()
    conn.close()


def search_files(query):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT message_id, name
        FROM files
        WHERE name LIKE ?
        ORDER BY message_id DESC
        LIMIT 10
        """,
        (f"%{query}%",),
    )

    results = cur.fetchall()
    conn.close()

    return results


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Apne authorized database me file/movie name search karo."
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    results = search_files(query)

    if not results:
        await update.message.reply_text(
            "❌ Matching file nahi mili."
        )
        return

    for message_id, name in results:
        try:
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=message_id,
            )
        except Exception as e:
            print("Copy error:", e)


async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post

    if not message:
        return

    if message.chat.id != CHANNEL_ID:
        return

    name = ""

    if message.document:
        name = message.document.file_name or ""

    elif message.video:
        name = message.video.file_name or ""

    elif message.audio:
        name = message.audio.file_name or ""

    caption = message.caption or ""

    if not name:
        name = caption

    if name:
        save_file(
            message.message_id,
            name,
            caption,
        )


@app.get("/")
def home():
    return "Telegram bot is running!"


@app.post(f"/webhook/{BOT_TOKEN}")
async def webhook():
    data = request.get_json(force=True)

    update = Update.de_json(
        data,
        bot_app.bot,
    )

    await bot_app.process_update(update)

    return "OK"


async def setup():
    init_db()

    bot_app.add_handler(
        CommandHandler("start", start)
    )

    bot_app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST,
            channel_post,
        )
    )

    bot_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            search,
        )
    )

    await bot_app.initialize()

    await bot_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(setup())

    app.run(
        host="0.0.0.0",
        port=PORT,
    )
    bot_app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST,
            channel_post,
        )
    )

    bot_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            search,
        )
    )

    await bot_app.initialize()

    await bot_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(setup())

    app.run(
        host="0.0.0.0",
        port=PORT,
    )        )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    results = search_files(query)

    if not results:
        await update.message.reply_text(
            "❌ Database me matching file nahi mili."
        )
        return

    for message_id, name in results:
        try:
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=message_id
            )
        except Exception as e:
            print("Copy error:", e)


def main():
    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    # Channel ke naye posts ko database me save karega
    app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST,
            channel_post
        )
    )

    # User jo naam/type karega usse search karega
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            search
        )
    )

    print("Bot started...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
