import json
import logging
import aiosqlite
from config import config

logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA temp_store=MEMORY;")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, 
                name TEXT DEFAULT NULL,
                topic_idx INTEGER DEFAULT 0, 
                state TEXT DEFAULT NULL,
                history TEXT DEFAULT '[]'
            )
        """)
        await db.commit()

async def execute_query(query: str, params: tuple = ()):
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(query, params)
        await db.commit()

async def fetch_one(query: str, params: tuple = ()):
    async with aiosqlite.connect(config.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()

async def get_user_history(user_id: int) -> list:
    user = await fetch_one("SELECT history FROM users WHERE id = ?", (user_id,))
    if not user or not user['history']:
        return []
    try:
        return json.loads(user['history'])
    except Exception:
        logger.exception(f"Ошибка парсинга истории для пользователя {user_id}")
        return []

async def save_user_history(user_id: int, history: list):
    # Храним  последние 8 сообщений контекста
    truncated = history[-8:]
    await execute_query("UPDATE users SET history = ? WHERE id = ?", (json.dumps(truncated), user_id))
