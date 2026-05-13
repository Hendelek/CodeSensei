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
from groq import AsyncGroq

# Загрузка учебных тем
try:
    from topics import TOPICS
except ImportError:
    TOPICS = [{"title": "Основы", "description": "База Python."}]

load_dotenv()
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TIMEZONE = pytz.timezone("Europe/Stockholm")
DB_PATH = "mentor_bot.db"

HEADER = "☁️🔴━━━━━━━━━━━━🔴☁️"
FOOTER = "━━━━━━━━━━━━━━━"

# --- БД ---
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

# --- AI ---
async def ask_ai(prompt, user_id, is_test=False):
    user = await db_get("SELECT history, name FROM users WHERE id = ?", (user_id,))
    history = json.loads(user['history']) if user and user['history'] else []
    name = user['name'] or "Студент"
    
    if is_test:
        sys = f"Проведи тест для {name}. Задай 1 вопрос. После 3 ответов напиши строго: RESULT_INDEX: n"
    else:
        sys = f"Ты строгий Python-ментор для {name}. Пиши кратко, используй ☁️ и 🔴."

    try:
        resp = await client.chat.completions.create(model="llama-3.3-70b-versatile", 
                                                  messages=[{"role":"system","content":sys}]+history+[{"role":"user","content":prompt}],
                                                  temperature=0.3)
        ans = resp.choices[0].message.content
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": ans})
        await db_mod("UPDATE users SET history = ? WHERE id = ?", (json.dumps(history[-6:]), user_id))
        return ans if is_test else f"{HEADER}\n\n{ans}\n\n{FOOTER}"
    except: return "🌀 Ошибка AI."

# --- Команды ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await db_get("SELECT name, state FROM users WHERE id = ?", (uid,))
    
    if not user or not user['name']:
        await db_mod("INSERT OR IGNORE INTO users (id, state) VALUES (?, 'wait_name')", (uid,))
        await update.message.reply_text("☁️ Привет! Как тебя зовут?")
        return

    welcome = f"{HEADER}\n🔴 **МАСТЕР {user['name'].upper()}** 🔴\n\nПродолжим обучение?\n{FOOTER}"
    kbd = [[InlineKeyboardButton("📊 Прогресс", callback_data='stats')], 
           [InlineKeyboardButton("📜 Текущая тема", callback_data='cur_topic')]]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"{HEADER}\n📜 **КОМАНДЫ:**\n\n/start — Меню\n/reset — Сброс\n/admin — Стата\n{FOOTER}"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        act = (await (await db.execute("SELECT COUNT(*) FROM users WHERE last_seen > datetime('now','-1 day')")).fetchone())[0]
    await update.message.reply_text(f"{HEADER}\n📊 **АДМИНКА**\n\nВсего: {total}\nАктивны: {act}\n{FOOTER}", parse_mode="Markdown")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    await db_mod("UPDATE users SET last_seen = ? WHERE id = ?", (now, uid))
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    
    if user['state'] == 'wait_name':
        name = update.message.text[:20].strip()
        await db_mod("UPDATE users SET name = ?, state = NULL WHERE id = ?", (name, uid))
        await update.message.reply_text(f"Принято, {name}! Жми /start.")
        return

    await context.bot.send_chat_action(uid, constants.ChatAction.TYPING)
    await update.message.reply_text(await ask_ai(update.message.text, uid), parse_mode="Markdown")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = update.effective_user.id
    user = await db_get("SELECT * FROM users WHERE id = ?", (uid,))
    await q.answer()

    if q.data == 'stats':
        txt = f"{HEADER}\n👤 **{user['name']}**\n🆙 **Тема:** {user['topic_idx']+1}\n{FOOTER}"
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=q.message.reply_markup)
    elif q.data == 'cur_topic':
        t = TOPICS[user['topic_idx'] % len(TOPICS)]
        txt = f"{HEADER}\n📜 **{t['title']}**\n\n{t['description']}\n{FOOTER}"
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=q.message.reply_markup)

async def main():
    await init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handlers([
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("admin", admin_stats),
        CommandHandler("reset", lambda u, c: db_mod("DELETE FROM users WHERE id = ?", (u.effective_user.id,))),
        CallbackQueryHandler(callback_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
    ])
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())