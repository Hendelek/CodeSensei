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
    TOPICS = [{"title": "Основы", "description": "Вход в мир шиноби. Изучаем базовый синтаксис.", "morning_question": "Зачем нужен print()?", "evening_task": "Выведи свое имя на экран"}]

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
    user = db_get("SELECT history, topic_idx FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user else []
    topic_idx = user['topic_idx'] if user else 0
    current_topic = TOPICS[topic_idx % len(TOPICS)]['title'] if TOPICS else "Основы"
    
    system_instruction = (
        f"Ты — профессиональный Python-ментор в стиле Акацуки. Твой ученик: Артём. Уровень: {topic_idx + 1}/20. "
        f"Текущая техника (тема): {current_topic}. Оформляй красиво: разделители, ☁️ и 🔴. "
        "Если ответ верный, начни со слова ВЕРНО."
    )
    
    messages = [{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.5)
        answer = resp.choices[0].message.content
        styled_answer = f"{HEADER}\n\n{answer}\n\n{FOOTER}"
        
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return styled_answer
    except:
        return "🌀 Техника прервана. Попробуй позже."

# --- Обработчики кнопок ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    user = db_get("SELECT topic_idx FROM users WHERE id = ?", (uid,))
    idx = user['topic_idx'] if user else 0

    await query.answer() # Это «размораживает» интерфейс

    if query.data == 'stats':
        lvl = idx + 1
        progress = "🔴" * (lvl % 6) + "☁️" * (5 - (lvl % 6))
        text = (
            f"{HEADER}\n👤 **Профиль: Шиноби Артём**\n━━━━━━━━━━━━━━\n"
            f"🆙 **Ранг:** {lvl} / 20\n✅ **Миссий:** {idx}\n📈 **Прогресс:** [{progress}]\n{FOOTER}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)

    elif query.data == 'cur_topic':
        topic = TOPICS[idx % len(TOPICS)]
        text = (
            f"{HEADER}\n📜 **ТЕКУЩАЯ ТЕХНИКА**\n━━━━━━━━━━━━━━\n"
            f"🔹 **Название:** {topic['title']}\n"
            f"📝 **Суть:** {topic.get('description', 'Изучение основ контроля чакры Python.')}\n\n"
            f"Ожидай свиток с заданием по расписанию.\n{FOOTER}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)

# --- Остальные функции ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db_get("SELECT id FROM users WHERE id = ?", (uid,)):
        db_mod("INSERT INTO users (id) VALUES (?)", (uid,))
    
    welcome = (
        f"{HEADER}\n🔴 **ДОБРО ПОЖАЛОВАТЬ В АКАЦУКИ** 🔴\n\n"
        "Артём, твой путь начинается здесь.\n\n"
        "📜 **Миссии:** 10:00 (Теория) | 19:00 (Практика).\n{FOOTER}"
    )
    kbd = [[InlineKeyboardButton("📊 Ранг Шиноби", callback_data='stats')], 
           [InlineKeyboardButton("📜 Текущая техника", callback_data='cur_topic')]]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    await context.bot.send_chat_action(chat_id=uid, action=constants.ChatAction.TYPING)
    text = update.message.text
    
    # Логика проверки ответов
    topic = TOPICS[user['topic_idx'] % len(TOPICS)]
    if user['state'] in ['wait_theory', 'wait_practice']:
        prompt = f"Проверь ответ на технику '{topic['title']}': {text}. Если верно, начни с ВЕРНО."
        feedback = ask_ai(prompt, uid)
        await update.message.reply_text(feedback, parse_mode="Markdown")
        if "ВЕРНО" in feedback.upper():
            new_idx = user['topic_idx'] + (1 if user['state'] == 'wait_practice' else 0)
            db_mod("UPDATE users SET topic_idx = ?, state = NULL WHERE id = ?", (new_idx, uid))
    else:
        await update.message.reply_text(ask_ai(text, uid), parse_mode="Markdown")

async def main():
    init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    await app.initialize()
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.start()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(callback_handler)) # Единый обработчик для всех кнопок
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    
    print("Бот запущен...")
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())