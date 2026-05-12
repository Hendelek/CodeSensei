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
    TOPICS = [{"title": "Основы", "description": "Синтаксис Python.", "morning_question": "Зачем нужен print()?", "evening_task": "Выведи приветствие."}]

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

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
        name TEXT DEFAULT NULL,
        topic_idx INTEGER DEFAULT 0, 
        state TEXT DEFAULT NULL,
        history TEXT DEFAULT '[]'
    )""")

# --- AI Логика ---
def ask_ai(prompt, user_id):
    user = db_get("SELECT history, name FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user else []
    name = user['name'] if user and user['name'] else "Студент"
    
    system_instruction = (
        f"Ты — мудрый Python-ментор. Студент: {name}. Твоя цель — обучение Python. "
        "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО отвечать на вопросы не по теме Python и IT. "
        "Никаких рецептов шашлыка, советов по жизни или других тем. Если спросят не про Python, "
        "вежливо скажи, что ты здесь только для обучения программированию."
        "Пиши 'ВЕРНО' только за правильный код. Стиль: лаконичный, с ☁️ и 🔴."
    )
    
    messages = [{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.4)
        answer = resp.choices[0].message.content
        
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        
        return f"{HEADER}\n\n{answer}\n\n{FOOTER}"
    except:
        return f"{HEADER}\n🌀 Ошибка связи.\n{FOOTER}"

# --- Обработчики ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db_get("SELECT name FROM users WHERE id = ?", (uid,))
    
    if not user or user['name'] is None:
        if not user:
            db_mod("INSERT INTO users (id, state) VALUES (?, ?)", (uid, 'wait_name'))
        else:
            db_mod("UPDATE users SET state = 'wait_name' WHERE id = ?", (uid,))
        await update.message.reply_text("☁️ Добро пожаловать! Как мне тебя называть?")
        return

    welcome = f"{HEADER}\n🔴 **МАСТЕР {user['name'].upper()}** 🔴\n\nПродолжим изучение Python?\n{FOOTER}"
    kbd = [[InlineKeyboardButton("📊 Прогресс", callback_data='stats')], [InlineKeyboardButton("📜 Текущая тема", callback_data='cur_topic')]]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    if user['state'] == 'wait_name':
        raw_text = update.message.text
        name_prompt = f"Извлеки только имя из этой фразы: '{raw_text}'. Если имени нет, ответь словом 'ERROR'. Если есть — напиши ОДНО имя с большой буквы."
        name_resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": name_prompt}])
        clean_name = name_resp.choices[0].message.content.strip().replace(".", "")
        
        if "ERROR" in clean_name.upper() or len(clean_name) > 20:
            await update.message.reply_text("☁️ Я не совсем понял. Пожалуйста, просто напиши свое имя.")
            return
            
        db_mod("UPDATE users SET name = ?, state = NULL WHERE id = ?", (clean_name, uid))
        await update.message.reply_text(f"Принято, {clean_name}! Нажми /start для входа в меню.")
        return

    await context.bot.send_chat_action(chat_id=uid, action=constants.ChatAction.TYPING)
    
    if update.message.voice:
        file = await context.bot.get_file(update.message.voice.file_id); path = f"{uid}.ogg"
        await file.download_to_drive(path)
        with open(path, "rb") as f:
            text = client.audio.transcriptions.create(file=(path, f.read()), model="whisper-large-v3", response_format="text")
        os.remove(path)
    else:
        text = update.message.text

    await update.message.reply_text(ask_ai(text, uid), parse_mode="Markdown")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; uid = update.effective_user.id
    user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
    await query.answer()

    if query.data == 'stats':
        text = f"{HEADER}\n👤 **Профиль: {user['name']}**\n🆙 **Этап:** {user['topic_idx']+1}/20\n{FOOTER}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)
    elif query.data == 'cur_topic':
        topic = TOPICS[user['topic_idx'] % len(TOPICS)]
        text = f"{HEADER}\n📜 **ТЕМА:** {topic['title']}\nОжидай заданий в 10:00 и 19:00.\n{FOOTER}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)

# --- ПЛАНИРОВЩИК ---
async def global_scheduler(app):
    now = datetime.now(TIMEZONE)
    if now.minute != 0: return 
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        users = conn.execute("SELECT id, topic_idx, name FROM users WHERE name IS NOT NULL").fetchall()
    
    for user in users:
        uid, idx, name = user['id'], user['topic_idx'], user['name']
        topic = TOPICS[idx % len(TOPICS)]
        if now.hour == 10:
            await app.bot.send_message(uid, f"{HEADER}\n📜 **ТЕОРИЯ ДЛЯ {name.upper()}**\n\n{topic['morning_question']}\n{FOOTER}", parse_mode="Markdown")
            db_mod("UPDATE users SET state = 'wait_theory' WHERE id = ?", (uid,))
        elif now.hour == 19:
            await app.bot.send_message(uid, f"{HEADER}\n⚔️ **ПРАКТИКА ДЛЯ {name.upper()}**\n\n{topic['evening_task']}\n{FOOTER}", parse_mode="Markdown")
            db_mod("UPDATE users SET state = 'wait_practice' WHERE id = ?", (uid,))

# --- ЗАПУСК ---
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
        await app.initialize(); await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())