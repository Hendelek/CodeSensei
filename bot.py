import os
import logging
import pytz
import json
import asyncio
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import AsyncGroq

# Импорт тем
try:
    from topics import TOPICS
except ImportError:
    TOPICS = [{"title": "Основы", "description": "База Python."}]

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

HEADER = "☁️🔴━━━━━━━━━━━━🔴☁️"
FOOTER = "━━━━━━━━━━━━━━━"

# --- DB ---
async def db_mod(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params); await db.commit()

async def db_get(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as c: return await c.fetchone()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, name TEXT DEFAULT NULL,
            topic_idx INTEGER DEFAULT 0, state TEXT DEFAULT NULL,
            history TEXT DEFAULT '[]', last_seen TEXT DEFAULT NULL
        )""")
        await db.commit()

# --- Senior Mentor AI ---
async def ask_ai(prompt, user_id):
    user = await db_get("SELECT history, name FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user and user['history'] else []
    name = user['name'] or "Студент"
    
    sys_instruction = (
        f"Role: Senior Python Mentor. Target: {name}.\n"
        "1. Только Python/IT. Оффтоп игнорируй.\n"
        "2. Жесткое ревью кода. Не хвали за плохой код.\n"
        "Style: Лаконично, профи, с ☁️ и 🔴."
    )

    try:
        resp = await client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role":"system","content":sys_instruction}]+history+[{"role":"user","content":prompt}],
            temperature=0.3
        )
        ans = resp.choices[0].message.content
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": ans})
        await db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return f"{HEADER}\n\n{ans}\n\n{FOOTER}"
    except: return "🌀 Ошибка связи."

# --- Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await db_get("SELECT name FROM users WHERE id = ?", (uid,))
    if not user or not user['name']:
        await db_mod("INSERT OR IGNORE INTO users (id, state) VALUES (?, 'wait_name')", (uid,))
        return await update.message.reply_text("☁️ Имя?")

    kbd = [[InlineKeyboardButton("📊 Прогресс", callback_data='stats')], 
           [InlineKeyboardButton("📜 Тема", callback_data='cur_topic')]]
    await update.message.reply_text(f"{HEADER}\n🔴 **МАСТЕР {user['name'].upper()}**\n\nПродолжим?\n{FOOTER}", 
                                   parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if user['state'] == 'wait_name':
        await db_mod("UPDATE users SET name = ?, state = NULL WHERE id = ?", (update.message.text[:20], uid))
        return await update.message.reply_text("Принято! /start")

    await context.bot.send_chat_action(uid, constants.ChatAction.TYPING)
    await update.message.reply_text(await ask_ai(update.message.text, uid), parse_mode="Markdown")

# --- Scheduler Setup ---
async def post_init(application):
    await init_db()
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    # Здесь можно добавить задачи планировщика
    scheduler.start()
    logger.info("Scheduler & DB Ready.")

def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).post_init(post_init).build()
    
    app.add_handlers([
        CommandHandler("start", start_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
    ])
    
    # Самый стабильный метод для Railway
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()