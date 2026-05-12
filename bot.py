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

# Загрузка тем
try:
    from topics import TOPICS
except ImportError:
    TOPICS = []

load_dotenv()
logging.basicConfig(level=logging.INFO)
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

# --- AI Логика (Текст + Голос) ---
def ask_ai(prompt, user_id):
    user = db_get("SELECT history FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user else []
    
    system_instruction = "Ты — Python-ментор. Отвечай кратко и по делу. Если ответ верный, начни со слова ВЕРНО."
    messages = [{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.3)
        answer = resp.choices[0].message.content
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return answer
    except: return "Ошибка AI. Попробуй позже."

async def transcribe_voice(voice_file_path):
    try:
        with open(voice_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(voice_file_path, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        return transcription
    except Exception as e:
        logger.error(f"Voice error: {e}")
        return None

# --- Команды и Интерфейс ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db_get("SELECT id FROM users WHERE id = ?", (uid,)):
        db_mod("INSERT INTO users (id) VALUES (?)", (uid,))
    
    welcome = (
        "🤖 **CodeSensei приветствует тебя!**\n\n"
        "Я помогу тебе дойти с 1 до 20 уровня в Python.\n"
        "🔹 10:00 — Теория\n🔹 19:00 — Практика\n"
        "🔹 Отправляй текст или **голос** — я всё пойму."
    )
    kbd = [[InlineKeyboardButton("📊 Моя статистика", callback_data='stats')]]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    user = db_get("SELECT topic_idx FROM users WHERE id = ?", (uid,))
    
    lvl = user['topic_idx'] + 1
    progress = "🔥" * (lvl if lvl <= 10 else 10)
    
    text = (
        f"👤 **Профиль кодера**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🆙 **Уровень:** {lvl} / 20\n"
        f"📈 **Прогресс:** {progress}\n"
        f"✅ **Тем пройдено:** {user['topic_idx']}"
    )
    if query:
        await query.answer()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=query.message.reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

# --- Обработка сообщений ---
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
    if not user: return

    # Если пришел голос
    if update.message.voice:
        await context.bot.send_chat_action(uid, constants.ChatAction.TYPING)
        file = await context.bot.get_file(update.message.voice.file_id)
        path = f"{uid}_voice.ogg"
        await file.download_to_drive(path)
        text = await transcribe_voice(path)
        os.remove(path)
        if not text:
            await update.message.reply_text("Не удалось распознать голос.")
            return
        await update.message.reply_text(f"🎤 _Ты сказал:_ {text}", parse_mode="Markdown")
    else:
        text = update.message.text

    # Логика обучения
    topic = TOPICS[user['topic_idx'] % len(TOPICS)]
    if user['state'] in ['wait_theory', 'wait_practice']:
        prompt = f"Проверь ответ на тему '{topic['title']}': {text}. Если верно, начни с ВЕРНО."
        feedback = ask_ai(prompt, uid)
        await update.message.reply_text(feedback)
        if "ВЕРНО" in feedback.upper():
            new_idx = user['topic_idx'] + (1 if user['state'] == 'wait_practice' else 0)
            db_mod("UPDATE users SET topic_idx = ?, state = NULL WHERE id = ?", (new_idx, uid))
    else:
        await update.message.reply_text(ask_ai(text, uid))

# --- Запуск ---
async def main():
    init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    # Здесь можно добавить global_scheduler из прошлого кода для рассылки
    scheduler.start()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CallbackQueryHandler(stats_handler, pattern='^stats$'))
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_input))
    
    print("Бот запущен...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())