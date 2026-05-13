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
# Исправленный импорт
from google import genai 

# Загрузка учебных тем
try:
    from topics import TOPICS
except ImportError:
    TOPICS = [{"title": "Основы", "description": "База Python.", "morning_question": "Зачем нужен print()?", "evening_task": "Выведи приветствие."}]

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиента Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

HEADER = "☁️🔴━━━━━━━━━━━━🔴☁️"
FOOTER = "━━━━━━━━━━━━━━━"

# --- Асинхронная БД ---
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
    await db_mod("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        name TEXT DEFAULT NULL,
        topic_idx INTEGER DEFAULT 0, 
        state TEXT DEFAULT NULL,
        history TEXT DEFAULT '[]'
    )""")

# --- AI Логика (Gemini) ---
async def ask_ai(prompt, user_id, is_test=False):
    user = await db_get("SELECT history, name FROM users WHERE id = ?", (user_id,))
    try:
        history = json.loads(user['history']) if user and user['history'] else []
    except:
        history = []
    
    name = user['name'] if user and user['name'] else "Студент"
    
    if is_test:
        system_instruction = (
            f"Ты проводишь вступительный тест для студента {name}. Задавай по одному техническому вопросу по Python. "
            "После 3-4 ответов ты должен оценить уровень и прислать строгое сообщение: 'RESULT_INDEX: n', "
            f"где n — число от 0 до {len(TOPICS)-1}. Выбирай индекс темы на основе знаний."
        )
    else:
        system_instruction = (
            f"Ты — строгий Python-ментор. Студент: {name}. Цель — обучение Python. "
            "Игнорируй оффтоп. Стиль: лаконичный, с ☁️ и 🔴."
        )
    
    # Форматирование под новый SDK
    contents = []
    # Добавляем историю (последние 6 сообщений для экономии лимитов 429)
    for msg in history[-6:]:
        contents.append({
            "role": "model" if msg["role"] == "assistant" else "user",
            "parts": [{"text": msg["content"]}]
        })
    
    # Добавляем системную инструкцию и текущий промпт
    contents.append({"role": "user", "parts": [{"text": f"{system_instruction}\n\n{prompt}"}]})

    try:
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=contents)
        answer = resp.text
        
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        await db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-8:]), user_id))
        return answer if is_test else f"{HEADER}\n\n{answer}\n\n{FOOTER}"
    except Exception as e:
        logger.error(f"AI Error: {e}")
        if "429" in str(e):
            return "🌀 Ошибка: Лимиты запросов. Подожди минуту."
        return "🌀 Ошибка связи."

# --- Обработчики команд ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await db_get("SELECT name, state FROM users WHERE id = ?", (uid,))
    
    if not user or user['name'] is None:
        if not user:
            await db_mod("INSERT INTO users (id, state) VALUES (?, ?)", (uid, 'wait_name'))
        else:
            await db_mod("UPDATE users SET state = 'wait_name' WHERE id = ?", (uid,))
        await update.message.reply_text("☁️ Добро пожаловать! Как мне тебя называть?")
        return

    if user['state'] == 'wait_test_choice':
        kbd = [[InlineKeyboardButton("📝 Пройти тест", callback_data='start_test')],
               [InlineKeyboardButton("⏭ Начать с нуля", callback_data='skip_test')]]
        await update.message.reply_text(
            f"{HEADER}\n🔴 **ВЫБОР ПУТИ**\n\nХочешь пройти тест или начнем с основ?\n{FOOTER}",
            reply_markup=InlineKeyboardMarkup(kbd), parse_mode="Markdown")
        return

    welcome = f"{HEADER}\n🔴 **МАСТЕР {user['name'].upper()}** 🔴\n\nПродолжим обучение?\n{FOOTER}"
    kbd = [[InlineKeyboardButton("📊 Прогресс", callback_data='stats')], 
           [InlineKeyboardButton("📜 Текущая тема", callback_data='cur_topic')]]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    if user['state'] == 'wait_name':
        name = update.message.text[:20].strip()
        await db_mod("UPDATE users SET name = ?, state = 'wait_test_choice' WHERE id = ?", (name, uid))
        await update.message.reply_text(f"Принято, {name}!")
        return await start_command(update, context)

    await context.bot.send_chat_action(chat_id=uid, action=constants.ChatAction.TYPING)
    text = update.message.text 

    if user['state'] == 'wait_testing':
        response = await ask_ai(text, uid, is_test=True)
        if "RESULT_INDEX:" in response:
            idx = re.findall(r'RESULT_INDEX: (\d+)', response)
            new_idx = int(idx[0]) if idx else 0
            await db_mod("UPDATE users SET topic_idx = ?, state = NULL, history = '[]' WHERE id = ?", (new_idx, uid))
            await update.message.reply_text(f"{HEADER}\n✅ Тест окончен! Нажми /start.\n{FOOTER}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"{HEADER}\n📝 **ТЕСТ**\n\n{response}\n{FOOTER}", parse_mode="Markdown")
        return

    await update.message.reply_text(await ask_ai(text, uid), parse_mode="Markdown")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; uid = update.effective_user.id
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    await query.answer()

    if query.data == 'start_test':
        await db_mod("UPDATE users SET state = 'wait_testing', history = '[]' WHERE id = ?", (uid,))
        q = await ask_ai("Задай мне первый проверочный вопрос по Python.", uid, is_test=True)
        await query.edit_message_text(f"{HEADER}\n📝 **ТЕСТ**\n\n{q}\n{FOOTER}", parse_mode="Markdown")
    
    elif query.data == 'skip_test':
        await db_mod("UPDATE users SET topic_idx = 0, state = NULL WHERE id = ?", (uid,))
        await query.edit_message_text(f"{HEADER}\n🚀 Ок, начинаем с нуля! Жми /start.\n{FOOTER}", parse_mode="Markdown")

    elif query.data == 'stats':
        text = f"{HEADER}\n👤 **Профиль: {user['name']}**\n🆙 **Этап:** {user['topic_idx']+1}/{len(TOPICS)}\n{FOOTER}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)
    
    elif query.data == 'cur_topic':
        topic = TOPICS[user['topic_idx'] % len(TOPICS)]
        text = f"{HEADER}\n📜 **ТЕМА:** {topic['title']}\n\n{topic['description']}\n{FOOTER}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"{HEADER}\n📜 **КОМАНДЫ:**\n\n/start — Меню\n/clear — Очистить чат\n/reset — Полный сброс\n{FOOTER}"
    await update.message.reply_text(text, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db_mod("UPDATE users SET history = '[]' WHERE id = ?", (update.effective_user.id,))
    await update.message.reply_text("🧹 Память диалога очищена.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db_mod("DELETE FROM users WHERE id = ?", (update.effective_user.id,))
    await update.message.reply_text("🚨 Прогресс удален. Нажми /start.")

async def main():
    await init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    app.add_handlers([
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("clear", clear_command),
        CommandHandler("reset", reset_command),
        CallbackQueryHandler(callback_handler),
        MessageHandler(filters.TEXT, handle_input)
    ])
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.start()
    
    async with app:
        await app.initialize(); await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())