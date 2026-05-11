import os
from datetime import date
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from database import init_db, get_user, update_user, get_state, set_state
from ai import get_topic, generate_morning_message, generate_evening_task, check_answer

load_dotenv()

WAITING_MORNING_ANSWER = "morning"
WAITING_EVENING_ANSWER = "evening"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    await update.message.reply_text(
        "👋 Привет! Я CodeSensei — твой ежедневный тренер по программированию.\n\n"
        "Каждый день в 10:00 я буду присылать тему дня и вопрос.\n"
        "Вечером в 19:00 — практическое задание.\n\n"
        "Команды:\n"
        "/morning — получить утреннее задание\n"
        "/evening — получить вечернее задание\n"
        "/progress — твой прогресс"
    )

async def morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    topic = get_topic(user["current_topic_index"])
    message = generate_morning_message(topic)
    await update.message.reply_text(f"🌅 *Тема дня: {topic['title']}*\n\n{message}", parse_mode="Markdown")
    set_state(user_id, WAITING_MORNING_ANSWER)
    update_user(user_id, morning_done=0, last_date=str(date.today()))

async def evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    topic = get_topic(user["current_topic_index"])
    task = generate_evening_task(topic)
    await update.message.reply_text(f"🌙 *Вечернее задание: {topic['title']}*\n\n{task}", parse_mode="Markdown")
    set_state(user_id, WAITING_EVENING_ANSWER)

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    topic = get_topic(user["current_topic_index"])
    await update.message.reply_text(
        f"📊 *Твой прогресс:*\n\n"
        f"Текущая тема: {topic['title']}\n"
        f"Тема #{user['current_topic_index'] + 1} из 8\n"
        f"Последний день: {user['last_date'] or 'ещё не начинал'}",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    topic = get_topic(user["current_topic_index"])
    state = get_state(user_id)

    if state == WAITING_MORNING_ANSWER:
        answer = check_answer(topic, topic["morning_question"], update.message.text)
        await update.message.reply_text(f"📝 *Проверка:*\n\n{answer}", parse_mode="Markdown")
        update_user(user_id, morning_done=1)
        set_state(user_id, None)

    elif state == WAITING_EVENING_ANSWER:
        answer = check_answer(topic, topic["evening_task"], update.message.text, is_evening=True)
        await update.message.reply_text(f"✅ *Результат:*\n\n{answer}", parse_mode="Markdown")
        update_user(user_id, evening_done=1, current_topic_index=user["current_topic_index"] + 1)
        set_state(user_id, None)
        await update.message.reply_text("🎯 Тема пройдена! Завтра в 10:00 новая тема.")

    else:
        await update.message.reply_text("Используй /morning или /evening для заданий.")

def main():
    init_db()
    token = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("morning", morning))
    app.add_handler(CommandHandler("evening", evening))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("CodeSensei запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()