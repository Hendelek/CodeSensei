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
    TOPICS = [{"title": "Основы", "description": "Введение в Python", "morning_question": "Зачем нужен print()?", "evening_task": "Выведи свое имя на экран"}]

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

# --- База данных ---
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
        f"Ты — профессиональный Python-ментор. Твой ученик: Артём. Уровень: {topic_idx + 1}/20. "
        f"Текущая тема: {current_topic}. Твоя задача: обучать, проверять код и отвечать на вопросы по IT. "
        "Если студент дает правильный ответ на учебную задачу, начни сообщение строго со слова ВЕРНО. "
        "В обычном диалоге веди себя как дружелюбный наставник, не используй 'ВЕРНО' просто так."
    )
    
    messages = [{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.4)
        answer = resp.choices[0].message.content
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return answer
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Извини, я призадумался. Попробуй еще раз через минуту."

async def transcribe_voice(voice_file_path):
    try:
        with open(voice_file_path, "rb") as file:
            return client.audio.transcriptions.create(file=(voice_file_path, file.read()), model="whisper-large-v3", response_format="text")
    except: return None

# --- Обработчики команд ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db_get("SELECT id FROM users WHERE id = ?", (uid,)):
        db_mod("INSERT INTO users (id) VALUES (?)", (uid,))
    
    welcome = (
        "🤖 **CodeSensei на связи!**\n\n"
        "Артем, я твой проводник в мир Python. Мы пройдем 20 уровней мастерства.\n"
        "📍 Расписание: 10:00 (Теория) и 19:00 (Практика).\n"
        "💬 Можешь писать мне вопросы или присылать голосовые."
    )
    kbd = [[InlineKeyboardButton("📊 Статистика", callback_data='stats')], [InlineKeyboardButton("📖 Текущая тема", callback_data='cur_topic')]]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    user = db_get("SELECT topic_idx FROM users WHERE id = ?", (uid,))
    
    idx = user['topic_idx'] if user else 0
    progress = "🔥" * ((idx % 10) + 1)
    
    text = (
        f"👤 **Профиль: Артем**\n━━━━━━━━━━━━━━\n"
        f"🆙 **Уровень:** {idx + 1} / 20\n"
        f"✅ **Пройдено тем:** {idx}\n"
        f"📈 **Прогресс:** {progress}"
    )
    if query:
        await query.answer()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

# --- Основной обработчик сообщений ---
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    await context.bot.send_chat_action(chat_id=uid, action=constants.ChatAction.TYPING)

    if update.message.voice:
        file = await context.bot.get_file(update.message.voice.file_id)
        path = f"{uid}_voice.ogg"; await file.download_to_drive(path)
        text = await transcribe_voice(path)
        os.remove(path)
        if not text: return await update.message.reply_text("Не удалось распознать голос.")
        await update.message.reply_text(f"🎤 _Ты сказал:_ {text}", parse_mode="Markdown")
    else:
        text = update.message.text

    topic = TOPICS[user['topic_idx'] % len(TOPICS)]
    if user['state'] in ['wait_theory', 'wait_practice']:
        prompt = f"Проверь ответ на задание по теме '{topic['title']}': {text}. Если верно, начни с ВЕРНО."
        feedback = ask_ai(prompt, uid)
        await update.message.reply_text(feedback)
        if "ВЕРНО" in feedback.upper():
            new_idx = user['topic_idx'] + (1 if user['state'] == 'wait_practice' else 0)
            db_mod("UPDATE users SET topic_idx = ?, state = NULL WHERE id = ?", (new_idx, uid))
    else:
        await update.message.reply_text(ask_ai(text, uid))

# --- Планировщик ---
async def global_scheduler(app):
    now = datetime.now(TIMEZONE)
    if now.minute != 0: return 
    
    with sqlite3.connect(DB_PATH) as conn:
        users = conn.execute("SELECT id, topic_idx FROM users").fetchall()
    
    for uid, idx in users:
        topic = TOPICS[idx % len(TOPICS)]
        if now.hour == 10:
            msg = f"📚 **Теория (Уровень {idx+1}): {topic['title']}**\n\n{topic['morning_question']}"
            await app.bot.send_message(uid, msg, parse_mode="Markdown")
            db_mod("UPDATE users SET state = 'wait_theory' WHERE id = ?", (uid,))
        elif now.hour == 19:
            msg = f"💻 **Практика (Уровень {idx+1}): {topic['title']}**\n\n{topic['evening_task']}"
            await app.bot.send_message(uid, msg, parse_mode="Markdown")
            db_mod("UPDATE users SET state = 'wait_practice' WHERE id = ?", (uid,))

# --- Main ---
async def main():
    init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    await app.initialize()
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(global_scheduler, 'interval', minutes=1, args=[app])
    scheduler.start()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CallbackQueryHandler(stats_handler, pattern='^stats$'))
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_input))
    
    print("Бот запущен...")
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())