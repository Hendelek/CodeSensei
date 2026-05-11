import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from database import init_db, get_user, update_user
from ai import get_topic, generate_morning_message

load_dotenv()

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_morning():
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    init_db()
    
    user = get_user(int(CHAT_ID))
    topic = get_topic(user["current_topic_index"])
    message = generate_morning_message(topic)
    
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"🌅 *Тема дня: {topic['title']}*\n\n{message}",
        parse_mode="Markdown"
    )
    print(f"Утреннее сообщение отправлено — тема: {topic['title']}")

if __name__ == "__main__":
    asyncio.run(send_morning())