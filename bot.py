import os
import sqlite3
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable missing")

if not CHANNEL_ID:
    raise RuntimeError("CHANNEL_ID environment variable missing")

CHANNEL_ID = int(CHANNEL_ID)

DB_FILE = "files.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE,
            name TEXT,
            caption TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_file(message_id, name, caption):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO files
        (message_id, name, caption)
        VALUES (?, ?, ?)
    """, (message_id, name, caption))

    conn.commit()
    conn.close()


def search_files(query):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT message_id, name
        FROM files
        WHERE name LIKE ?
        ORDER BY id DESC
        LIMIT 10
    """, (f"%{query}%",))

    results = cur.fetchall()
    conn.close()

    return results


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "File/movie ka naam bhejo aur main database me search karunga."
    )


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
            caption
        )


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
