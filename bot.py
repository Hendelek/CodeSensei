import os
import logging
import pytz
import json
import asyncio
import aiosqlite
import re
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import AsyncGroq

# Темы обучения
try:
    from topics import TOPICS
except ImportError:
    TOPICS = [{"title": "Основы", "description": "Базовый Python.", "morning_question": "Что такое PEP8?", "evening_task": "Напиши print."}]

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

HEADER = "☁️🔴━━━━━━━━━━━━🔴☁️"
FOOTER = "━━━━━━━━━━━━━━━"

# --- Database Layer ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, 
            name TEXT DEFAULT NULL,
            topic_idx INTEGER DEFAULT 0, 
            state TEXT DEFAULT NULL,
            history TEXT DEFAULT '[]',
            last_seen TEXT DEFAULT NULL
        )""")
        await db.commit()

async def db_mod(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()

async def db_get(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()

# --- AI Engine (Senior Prompt) ---
async def ask_ai(prompt, user_id):
    user = await db_get("SELECT history, name FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user and user['history'] else []
    name = user['name'] or "Студент"
    
    sys_instruction = (
        f"Role: Senior Python Mentor / Tech Lead. Target Student: {name}.\n"
        "Strict Rules:\n"
        "1. Domain Isolation: Только Python, SQL и архитектура ПО. Оффтоп режь сразу.\n"
        "2. Code Quality: Проводи жесткое код-ревью. Ошибки в синтаксисе или стиле (PEP8) — повод для критики.\n"
        "3. Tone: Профессиональный, лаконичный, без воды.\n"
        "4. Structure: Всегда используй ☁️ и 🔴 для визуального выделения блоков."
    )

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instruction}] + history + [{"role": "user", "content": prompt}],
            temperature=0.3
        )
        answer = response.choices[0].message.content
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        await db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return f"{HEADER}\n\n{answer}\n\n{FOOTER}"
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "🌀 Ошибка нейросети. Попробуй позже."

# --- Scheduler Jobs ---
async def send_daily_update(context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, topic_idx FROM users WHERE name IS NOT NULL") as cursor:
            users = await cursor.fetchall()
            for user in users:
                topic = TOPICS[user['topic_idx'] % len(TOPICS)]
                text = f"{HEADER}\n🔴 **УТРЕННИЙ КВИЗ**\n\n{topic['morning_question']}\n{FOOTER}"
                try: await context.bot.send_message(chat_id=user['id'], text=text, parse_mode="Markdown")
                except: pass

# --- Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await db_get("SELECT name FROM users WHERE id = ?", (uid,))
    
    if not user or not user['name']:
        await db_mod("INSERT OR IGNORE INTO users (id, state) VALUES (?, 'wait_name')", (uid,))
        return await update.message.reply_text("☁️ Senior Mentor на связи. Для начала работы представься:")

    kbd = [[InlineKeyboardButton("📊 Мой прогресс", callback_data='stats')], 
           [InlineKeyboardButton("📜 Текущий модуль", callback_data='cur_topic')]]
    
    msg = f"{HEADER}\n🔴 **МАСТЕР {user['name'].upper()}**\n\nГотов к код-ревью или продолжим теорию?\n{FOOTER}"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    await db_mod("UPDATE users SET last_seen = ? WHERE id = ?", (now, uid))
    
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    if user['state'] == 'wait_name':
        name = update.message.text[:20].strip()
        await db_mod("UPDATE users SET name = ?, state = NULL WHERE id = ?", (name, uid))
        return await update.message.reply_text(f"🔴 Доступ разрешен, {name}. Жми /start.")

    await context.bot.send_chat_action(chat_id=uid, action=constants.ChatAction.TYPING)
    await update.message.reply_text(await ask_ai(update.message.text, uid), parse_mode="Markdown")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = update.effective_user.id
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    await q.answer()

    if q.data == 'stats':
        txt = f"{HEADER}\n👤 **ПРОФИЛЬ:** {user['name']}\n🆙 **ЭТАП:** {user['topic_idx']+1}\n{FOOTER}"
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=q.message.reply_markup)
    elif q.data == 'cur_topic':
        t = TOPICS[user['topic_idx'] % len(TOPICS)]
        txt = f"{HEADER}\n📜 **МОДУЛЬ:** {t['title']}\n\n{t['description']}\n{FOOTER}"
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=q.message.reply_markup)

# --- Start Engine ---
def main():
    # Создаем цикл вручную для стабильности Railway
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())

    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    # Настройка планировщика
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_daily_update, 'cron', hour=9, minute=0, args=[app])
    scheduler.start()

    app.add_handlers([
        CommandHandler("start", start_command),
        CommandHandler("reset", lambda u, c: loop.run_until_complete(db_mod("DELETE FROM users WHERE id = ?", (u.effective_user.id,)))),
        CallbackQueryHandler(callback_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
    ])
    
    logger.info("Бот запущен...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()