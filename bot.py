import asyncio
import logging
import pytz
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
import database as db
from handlers import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Europe/Stockholm")

async def main():
    # Инициализация асинхронной БД с PRAGMA
    await db.init_db()
    
    # Инициализация бота на aiogram 3
    bot = Bot(token=config.telegram_token.get_secret_value())
    dp = Dispatcher()
    dp.include_router(router)
    
    # Инициализация шедулера (если нужен для джоб)
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    # scheduler.add_job(...)
    scheduler.start()
    
    logger.info("Бот успешно запущен!")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")