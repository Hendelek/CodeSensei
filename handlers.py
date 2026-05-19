import re
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import database as db
import ai_service as ai
from topics import TOPICS

router = Router()

class Registration(StatesGroup):
    wait_name = State()
    wait_testing = State()

@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    user = await db.fetch_one("SELECT name, state FROM users WHERE id = ?", (uid,))
    
    if not user:
        await db.execute_query("INSERT INTO users (id, state) VALUES (?, 'wait_name')", (uid,))
        await message.reply("☁️ Добро пожаловать! Как мне тебя называть?")
        await state.set_state(Registration.wait_name)
        return
        
    if user['name'] is None:
        await state.set_state(Registration.wait_name)
        await message.reply("☁️ Как мне тебя называть?")
        return

    if user['state'] == 'wait_test_choice':
        kbd = [
            [InlineKeyboardButton(text="📝 Пройти тест", callback_data='start_test')],
            [InlineKeyboardButton(text="⏭ Начать с нуля", callback_data='skip_test')]
        ]
        await message.reply(
            f"{ai.HEADER}\n🔴 **ВЫБОР ПУТИ**\n\nХочешь пройти тест или начнем с основ?\n{ai.FOOTER}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kbd), parse_mode="Markdown"
        )
        return

    welcome = f"{ai.HEADER}\n🔴 **МАСТЕР {user['name'].upper()}** 🔴\n\nПродолжим обучение?\n{ai.FOOTER}"
    kbd = [
        [InlineKeyboardButton(text="📊 Прогресс", callback_data='stats')], 
        [InlineKeyboardButton(text="📜 Текущая тема", callback_data='cur_topic')]
    ]
    await message.reply(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kbd))

@router.message(Registration.wait_name, F.text)
async def handle_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 40:
        await message.reply("Пожалуйста, введи настоящее имя (от 2 до 40 символов).")
        return
        
    uid = message.from_user.id
    await db.execute_query("UPDATE users SET name = ?, state = 'wait_test_choice' WHERE id = ?", (name, uid))
    await message.reply(f"Принято, {name}!")
    await start_command(message, state)

@router.callback_query(F.data == 'start_test')
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await db.execute_query("UPDATE users SET state = 'wait_testing', history = '[]' WHERE id = ?", (uid,))
    await state.set_state(Registration.wait_testing)
    
    q = await ai.ask_ai("Задай мне первый проверочный вопрос по Python.", uid, is_test=True)
    await callback.message.edit_text(f"{ai.HEADER}\n📝 **ТЕСТ**\n\n{q}\n{ai.FOOTER}", parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == 'skip_test')
async def skip_test(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await db.execute_query("UPDATE users SET topic_idx = 0, state = NULL, history = '[]' WHERE id = ?", (uid,))
    await state.clear()
    await callback.message.edit_text(f"{ai.HEADER}\n🚀 Ок, начинаем с нуля! Жми /start.\n{ai.FOOTER}", parse_mode="Markdown")
    await callback.answer()

@router.message(Registration.wait_testing, F.text)
async def handle_testing(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    response = await ai.ask_ai(message.text, uid, is_test=True)
    
    # Ищем JSON-структуру в ответе модели на финальном шаге
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    
    if json_match:
        try:
            import json
            data = json.loads(json_match.group(0))
            new_idx = int(data.get("result_index", 0))
            evaluation = data.get("evaluation", "Тест успешно завершен!")
            
            await db.execute_query("UPDATE users SET topic_idx = ?, state = NULL, history = '[]' WHERE id = ?", (new_idx, uid))
            await state.clear()
            
            await message.reply(
                f"{ai.HEADER}\n✅ **Тест окончен!**\n\nРазбор: {evaluation}\n\nТвой уровень определен. Нажми /start.\n{ai.FOOTER}", 
                parse_mode="Markdown"
            )
            return
        except Exception:
            pass # Если модель выдала кривой JSON, обрабатываем как обычный текст
            
    await message.reply(f"{ai.HEADER}\n📝 **ТЕСТ**\n\n{response}\n{ai.FOOTER}", parse_mode="Markdown")

@router.callback_query(F.data == 'stats')
async def show_stats(callback: types.CallbackQuery):
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (callback.from_user.id,))
    text = f"{ai.HEADER}\n👤 **Профиль: {user['name']}**\n🆙 **Этап:** {user['topic_idx']+1}/{len(TOPICS)}\n{ai.FOOTER}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=callback.message.reply_markup)
    await callback.answer()

@router.callback_query(F.data == 'cur_topic')
async def show_topic(callback: types.CallbackQuery):
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (callback.from_user.id,))
    topic = TOPICS[user['topic_idx'] % len(TOPICS)]
    text = f"{ai.HEADER}\n📜 **ТЕМА:** {topic['title']}\n\n{topic['description']}\n{ai.FOOTER}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=callback.message.reply_markup)
    await callback.answer()

@router.message(Command("clear"))
async def clear_command(message: types.Message):
    await db.execute_query("UPDATE users SET history = '[]' WHERE id = ?", (message.from_user.id,))
    await message.reply("🧹 Память диалога очищена.")

@router.message(Command("reset"))
async def reset_command(message: types.Message, state: FSMContext):
    await state.clear()
    await db.execute_query("DELETE FROM users WHERE id = ?", (message.from_user.id,))
    await message.reply("🚨 Прогресс удален. Нажми /start.")

@router.message(F.text)
async def handle_mentor_talk(message: types.Message):
    uid = message.from_user.id
    # Проверяем, зарегистрирован ли пользователь вообще
    user = await db.fetch_one("SELECT name FROM users WHERE id = ?", (uid,))
    if not user or not user['name']:
        await message.reply("Пожалуйста, сначала отправь /start для регистрации.")
        return
        
    response = await ai.ask_ai(message.text, uid)
    await message.reply(response, parse_mode="Markdown")