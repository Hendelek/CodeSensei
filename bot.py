import os
import sqlite3
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

# Загрузка учебных тем
try:
    from topics import TOPICS
except ImportError:
    TOPICS = [{"title": "Основы", "description": "База Python.", "morning_question": "Зачем?", "evening_task": "Код."}]

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиентов и констант
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

HEADER = "☁️🔴━━━━━━━━━━━━🔴☁️"
FOOTER = "━━━━━━━━━━━━━━━"

# --- БД (добавлена колонка активности) ---
async def db_mod(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()

async def db_get(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()

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
        try: await db.execute("ALTER TABLE users ADD COLUMN last_seen TEXT")
        except: pass
        await db.commit()

# --- AI Логика с поддержкой теста ---
async def ask_ai(prompt, user_id, is_test=False):
    user = await db_get("SELECT history, name FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user and user['history'] else []
    name = user['name'] or "Студент"
    
    if is_test:
        sys_msg = (f"Ты проводишь тест для {name}. Задай 1 сложный вопрос по Python. "
                   f"После 3 ответов напиши строго: 'RESULT_INDEX: n', где n (от 0 до {len(TOPICS)-1}) — индекс темы.")
    else:
        sys_msg = f"Ты — строгий Python-ментор для {name}. Игнорируй оффтоп. Стиль: лаконичный, с ☁️ и 🔴."

    messages = [{"role": "system", "content": sys_msg}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = await client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.3)
        ans = resp.choices[0].message.content
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": ans})
        await db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return ans if is_test else f"{HEADER}\n\n{ans}\n\n{FOOTER}"
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "🌀 Ошибка связи."

# --- Админ-панель ---
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        act_24 = (await (await db.execute("SELECT COUNT(*) FROM users WHERE last_seen > datetime('now', '-1 day')")).fetchone())[0]
    await update.message.reply_text(f"{HEADER}\n📊 **СТАТИСТИКА**\n\n👥 Всего: {total}\n🔥 Активны (24ч): {act_24}\n{FOOTER}")

# --- Обработчики ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await db_get("SELECT name, state FROM users WHERE id = ?", (uid,))
    
    if not user or not user['name']:
        if not user: await db_mod("INSERT INTO users (id, state) VALUES (?, ?)", (uid, 'wait_name'))
        else: await db_mod("UPDATE users SET state = 'wait_name' WHERE id = ?", (uid,))
        await update.message.reply_text("☁️ Добро пожаловать! Как мне тебя называть?")
        return

    # Предложение пройти тест
    if user['state'] == 'wait_test_choice':
        kbd = [[InlineKeyboardButton("📝 Пройти тест", callback_data='start_test')],
               [InlineKeyboardButton("⏭ Начать с нуля", callback_data='skip_test')]]
        await update.message.reply_text(f"{HEADER}\n🔴 **ВЫБОР УРОВНЯ**\n\nХочешь пройти тест для определения уровня или начнем с основ?\n{FOOTER}", 
                                       reply_markup=InlineKeyboardMarkup(kbd), parse_mode="Markdown")
        return

    # Стартовое меню БЕЗ кнопки очистки
    kbd = [[InlineKeyboardButton("📊 Прогресс", callback_data='stats')], 
           [InlineKeyboardButton("📜 Текущая тема", callback_data='cur_topic')]]
    await update.message.reply_text(f"{HEADER}\n🔴 **МАСТЕР {user['name'].upper()}**\n\nПродолжим?\n{FOOTER}", 
                                   reply_markup=InlineKeyboardMarkup(kbd), parse_mode="Markdown")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    # Обновляем время активности
    now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    await db_mod("UPDATE users SET last_seen = ? WHERE id = ?", (now, uid))
    
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    if user['state'] == 'wait_name':
        name = update.message.text[:20].strip()
        await db_mod("UPDATE users SET name = ?, state = 'wait_test_choice' WHERE id = ?", (name, uid))
        return await start_command(update, context)

    await context.bot.send_chat_action(chat_id=uid, action=constants.ChatAction.TYPING)
    
    if user['state'] == 'wait_testing':
        res = await ask_ai(update.message.text, uid, is_test=True)
        if "RESULT_INDEX:" in res:
            idx = int(re.findall(r'RESULT_INDEX: (\d+)', res)[0])
            await db_mod("UPDATE users SET topic_idx = ?, state = NULL, history = '[]' WHERE id = ?", (idx, uid))
            await update.message.reply_text(f"{HEADER}\n✅ Тест пройден! Твой уровень определен. Жми /start.\n{FOOTER}")
        else:
            await update.message.reply_text(f"{HEADER}\n📝 **ТЕСТ**\n\n{res}\n{FOOTER}")
        return

    # Обычный ввод (текст или голос)
    text = update.message.text or "Голосовое сообщение" # Упрощено для краткости
    await update.message.reply_text(await ask_ai(text, uid), parse_mode="Markdown")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = update.effective_user.id
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    await q.answer()

    if q.data == 'start_test':
        await db_mod("UPDATE users SET state = 'wait_testing', history = '[]' WHERE id = ?", (uid,))
        txt = await ask_ai("Начни вступительный тест.", uid, is_test=True)
        await q.edit_message_text(f"{HEADER}\n📝 **ТЕСТ**\n\n{txt}\n{FOOTER}")
    elif q.data == 'skip_test':
        await db_mod("UPDATE users SET topic_idx = 0, state = NULL WHERE id = ?", (uid,))
        await q.edit_message_text("🚀 Ок, начинаем с азов! Жми /start.")
    elif q.data == 'stats':
        await q.edit_message_text(f"👤 {user['name']}\n🆙 Этап: {user['topic_idx']+1}/{len(TOPICS)}")
    elif q.data == 'cur_topic':
        t = TOPICS[user['topic_idx'] % len(TOPICS)]
        await q.edit_message_text(f"📜 {t['title']}\n\n{t['description']}")

# --- Планировщик и запуск ---
async def main():
    await init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    app.add_handlers([
        CommandHandler("start", start_command),
        CommandHandler("admin", admin_stats),
        CommandHandler("reset", lambda u, c: db_mod("DELETE FROM users WHERE id = ?", (u.effective_user.id,))),
        CallbackQueryHandler(callback_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
    ])
    
    # Запуск через polling (безопасно для Railway)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    # Держим цикл живым
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass