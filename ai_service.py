import json
import logging
import re
from groq import AsyncGroq
from config import config
from topics import TOPICS
import database as db

logger = logging.getLogger(__name__)
client = AsyncGroq(api_key=config.groq_api_key.get_secret_value())

HEADER = "☁️🔴━━━━━━━━━━━━🔴☁️"
FOOTER = "━━━━━━━━━━━━━━━"

async def ask_ai(prompt: str, user_id: int, is_test: bool = False) -> str:
    user = await db.fetch_one("SELECT name FROM users WHERE id = ?", (user_id,))
    name = user['name'] if user and user['name'] else "Студент"
    history = await db.get_user_history(user_id)
    
    if is_test:
        # Считаем текущий шаг по количеству реплик юзера в истории теста
        user_messages = [m for m in history if m["role"] == "user"]
        step = len(user_messages) + 1
        
        system_instruction = (
            f"Ты проводишь вступительный тест по Python для студента {name}. "
            f"Текущий шаг теста: {step} из 4.\n"
            "Если шаг < 4: задай ровно один короткий технический вопрос по Python.\n"
            "Если шаг = 4: проанализируй все ответы и верни строго JSON-формат:\n"
            f'{{"evaluation": "краткий фидбек", "result_index": число от 0 до {len(TOPICS)-1}}}\n'
            "Не пиши ничего, кроме этого JSON-объекта."
        )
    else:
        system_instruction = (
            f"Ты — строгий Python-ментор. Студент: {name}. Цель — обучение Python. "
            "Игнорируй темы, не связанные с программированием. Отвечай лаконично, структурировано."
        )
        
    messages = [{"role": "system", "content": system_instruction}] + history + [{"role": "user", "content": prompt}]
    
    try:
        resp = await client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=messages, 
            temperature=0.3
        )
        answer = resp.choices[0].message.content
        
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
        await db.save_user_history(user_id, history)
        
        return answer if is_test else f"{HEADER}\n\n{answer}\n\n{FOOTER}"
    except Exception:
        logger.exception("Ошибка при запросе к Groq API")
        return "🌀 Ошибка связи с ментором."