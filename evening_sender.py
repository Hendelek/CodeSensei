import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from database import init_db, get_user
from ai import get_topic, generate_evening_task

load_dotenv()

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_evening():
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    init_db()
    
    user = get_user(int(CHAT_ID))
    topic = get_topic(user["current_topic_index"])
    task = generate_evening_task(topic)
    
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"🌙 *Вечернее задание: {topic['title']}*\n\n{task}",
        parse_mode="Markdown"
    )
    print(f"Вечернее задание отправлено — тема: {topic['title']}")

if __name__ == "__main__":
    asyncio.run(send_evening())