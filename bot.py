import os
import sqlite3
import logging
import pytz
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, constants
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import Groq

# Загрузка учебных тем
try:
    from topics import TOPICS
except ImportError:
    TOPICS = []

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

# --- Работа с базой данных ---
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

# --- Взаимодействие с AI ---
def ask_ai(prompt, user_id):
    user = db_get("SELECT history FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user else []
    
    system_instruction = (
        "Ты — профессиональный ментор по программированию на Python. "
        "Твоя задача: помогать студенту осваивать теорию и практику. "
        "Отвечай кратко, конструктивно и только по теме IT. "
        "Если студент совершил ошибку в коде, подробно объясни причину и дай верное решение."
    )
    
    messages = [{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.3)
        answer = resp.choices[0].message.content
        
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-8:]), user_id))
        
        return answer
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Произошла ошибка при обращении к AI. Попробуйте позже."

# --- Рассылка учебных модулей ---
async def send_module(context, user_id, mode):
    user = db_get("SELECT * FROM users WHERE id = ?", (user_id,))
    if not TOPICS or not user: return
    
    topic = TOPICS[user['topic_idx'] % len(TOPICS)]
    
    if mode == "morning":
        msg = f"📚 **Тема дня: {topic['title']}**\n\n{topic['description']}\n\n**Вопрос:** {topic['morning_question']}"
        db_mod("UPDATE users SET state = 'wait_theory' WHERE id = ?", (user_id,))
    else:
        msg = f"💻 **Вечерняя практика: {topic['title']}**\n\n**Задание:** {topic['evening_task']}"
        db_mod("UPDATE users SET state = 'wait_practice' WHERE id = ?", (user_id,))
    
    await context.bot.send_message(user_id, msg, parse_mode="Markdown")

async def global_scheduler(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    with sqlite3.connect(DB_PATH) as conn:
        users = conn.execute("SELECT id FROM users").fetchall()
    
    for (uid,) in users:
        # Проверка времени для Стокгольма
        if now.hour == 10 and now.minute == 0: await send_module(context, uid, "morning")
        if now.hour == 19 and now.minute == 0: await send_module(context, uid, "evening")

# --- Обработка сообщений ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid = update.effective_user.id
    user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
    
    if not user:
        db_mod("INSERT INTO users (id) VALUES (?)", (uid,))
        user = db_get("SELECT * FROM users WHERE id = ?", (uid,))
        await send_module(context, uid, "morning")
        return

    text = update.message.text
    topic = TOPICS[user['topic_idx'] % len(TOPICS)]
    await context.bot.send_chat_action(uid, constants.ChatAction.TYPING)

    if user['state'] in ['wait_theory', 'wait_practice']:
        prompt = f"Проверь ответ студента на {'вопрос' if user['state']=='wait_theory' else 'задачу'} по теме '{topic['title']}': {text}. Если ответ верный, начни сообщение строго со слова ВЕРНО."
        feedback = ask_ai(prompt, uid)
        await update.message.reply_text(feedback)
        
        if "ВЕРНО" in feedback.upper():
            new_idx = user['topic_idx'] + (1 if user['state'] == 'wait_practice' else 0)
            db_mod("UPDATE users SET topic_idx = ?, state = NULL WHERE id = ?", (new_idx, uid))
    else:
        response = ask_ai(text, uid)
        await update.message.reply_text(response)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db_get("SELECT * FROM users WHERE id = ?", (uid,)):
        db_mod("INSERT INTO users (id) VALUES (?)", (uid,))
    await update.message.reply_text("Система обучения запущена. Ожидайте материалы в 10:00 и 19:00.")

async def main():
    init_db()
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not found!")
        return

    # Создаем приложение
    app = ApplicationBuilder().token(token).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Запускаем планировщик
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(global_scheduler, 'interval', minutes=1, args=[app])
    scheduler.start()
    
    print("Бот запущен...")
    
    # Инициализируем и запускаем бота
    # Метод run_polling сам создаст нужный цикл событий
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Чтобы скрипт не завершался
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    # Для Windows/Railway важно правильно запустить цикл
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass