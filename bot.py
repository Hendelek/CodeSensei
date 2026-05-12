import os
import sqlite3
import logging
import pytz
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import Groq

# Загрузка учебных тем
try:
    from topics import TOPICS
except ImportError:
    TOPICS = [{"title": "Основы", "description": "Первые шаги в мастерстве. Синтаксис.", "morning_question": "Зачем нужен print()?", "evening_task": "Выведи свое имя на экран"}]

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

# --- Стилизация ---
HEADER = "☁️🔴━━━━━━━━━━━━🔴☁️"
FOOTER = "━━━━━━━━━━━━━━━"

def db_mod(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(query, params); conn.commit()

def db_get(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, params).fetchone()

def init_db():
    db_mod("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        topic_idx INTEGER DEFAULT 0, 
        state TEXT DEFAULT NULL,
        history TEXT DEFAULT '[]'
    )""")

# --- AI Логика ---
def ask_ai(prompt, user_id):
    user = db_get("SELECT history, topic_idx, state FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user else []
    topic_idx = user['topic_idx'] if user else 0
    state = user['state'] if user else None
    current_topic = TOPICS[topic_idx % len(TOPICS)]['title'] if TOPICS else "Основы"
    
    system_instruction = (
        f"Ты — мудрый Python-ментор. Студент: Артём. Этап: {topic_idx + 1}/20. Тема: {current_topic}. "
        "Твои обязанности: присылать теорию в 10:00 и практику в 19:00. "
        f"СЕЙЧАС ТВОЙ СТАТУС: {state if state else 'Ожидание диалога'}. "
        "Пиши 'ВЕРНО' в начале сообщения ТОЛЬКО если пользователь дал правильный технический ответ на задачу. "
        "Стиль: лаконичный, визуально оформлен ☁️ и 🔴. Никаких прямых упоминаний организаций."
    )
    
    messages = [{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.4)
        answer = resp.choices[0].message.content
        styled_answer = f"{HEADER}\n\n{answer}\n\n{FOOTER}"
        
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return styled_answer
    except:
        return f"{HEADER}\n🌀 Связь прервана. Повтори попытку позже.\n{FOOTER}"

# --- Обработчики ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    user = db_get("SELECT topic_idx FROM users WHERE id = ?", (uid,))
    idx = user['topic_idx'] if user else 0
    await query.answer()

    if query.data == 'stats':
        lvl = idx + 1
        progress = "🔴" * (lvl % 6) + "☁️" * (5 - (lvl % 6))
        text = f"{HEADER}\n👤 **Профиль: Артём**\n━━━━━━━━━━━━━━\n🆙 **Этап:** {lvl}/20\n✅ **Завершено:** {idx}\n📈 **Прогресс:** [{progress}]\n{FOOTER}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)
    elif query.data == 'cur_topic':
        topic = TOPICS[idx % len(TOPICS)]
        text = f"{HEADER}\n📜 **ТЕКУЩИЙ ЭТАП**\n━━━━━━━━━━━━━━\n🔹 **Тема:** {topic['title']}\n📝 **Суть:** {topic.get('description', 'Основы Python.')}\n\nОжидай новых указаний в 10:00 и 19:00.\n{FOOTER}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    await context.bot.send_chat_action(chat_id=uid, action=constants.ChatAction.TYPING)
    
    # Обработка голосового сообщения
    if update.message.voice:
        file = await context.bot.get_file(update.message.voice.file_id)
        path = f"{uid}_voice.ogg"
        await file.download_to_drive(path)
        with open(path, "rb") as f:
            text = client.audio.transcriptions.create(file=(path, f.read()), model="whisper-large-v3", response_format="text")
        os.remove(path)
    else:
        text = update.message.text

    topic = TOPICS[user['topic_idx'] % len(TOPICS)]
    if user['state'] in ['wait_theory', 'wait_practice']:
        prompt = f"Проверь ответ по теме '{topic['title']}': {text}. Если верно, начни с ВЕРНО."
        feedback = ask_ai(prompt, uid)
        await update.message.reply_text(feedback, parse_mode="Markdown")
        if "ВЕРНО" in feedback.upper():
            new_idx = user['topic_idx'] + (1 if user['state'] == 'wait_practice' else 0)
            db_mod("UPDATE users SET topic_idx = ?, state = NULL WHERE id = ?", (new_idx, uid))
    else:
        await update.message.reply_text(ask_ai(text, uid), parse_mode="Markdown")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db_get("SELECT id FROM users WHERE id = ?", (uid,)):
        db_mod("INSERT INTO users (id) VALUES (?)", (uid,))
    
    welcome = f"{HEADER}\n🔴 **ТВОЙ ПУТЬ НАЧИНАЕТСЯ** 🔴\n\nАртём, я помогу тебе отточить навыки владения кодом.\n\n📜 **Указания:** 10:00 (Теория) | 19:00 (Практика).\n{FOOTER}"
    kbd = [[InlineKeyboardButton("📊 Мой прогресс", callback_data='stats')], [InlineKeyboardButton("📜 Текущая тема", callback_data='cur_topic')]]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

# --- Планировщик и Запуск ---
async def global_scheduler(app):
    now = datetime.now(TIMEZONE)
    if now.minute != 0: return 
    with sqlite3.connect(DB_PATH) as conn:
        users = conn.execute("SELECT id, topic_idx FROM users").fetchall()
    for uid, idx in users:
        topic = TOPICS[idx % len(TOPICS)]
        if now.hour == 10:
            await app.bot.send_message(uid, f"{HEADER}\n📜 **СВИТОК ТЕОРИИ: {topic['title']}**\n\n{topic['morning_question']}\n\n{FOOTER}", parse_mode="Markdown")
            db_mod("UPDATE users SET state = 'wait_theory' WHERE id = ?", (uid,))
        elif now.hour == 19:
            await app.bot.send_message(uid, f"{HEADER}\n⚔️ **ПРАКТИЧЕСКИЙ БОЙ: {topic['title']}**\n\n{topic['evening_task']}\n\n{FOOTER}", parse_mode="Markdown")
            db_mod("UPDATE users SET state = 'wait_practice' WHERE id = ?", (uid,))

async def main():
    init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_input))
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(global_scheduler, 'interval', minutes=1, args=[app])
    scheduler.start()
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())