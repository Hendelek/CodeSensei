import os
from groq import Groq
from dotenv import load_dotenv
from topics import TOPICS

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_topic(index):
    if index >= len(TOPICS):
        index = index % len(TOPICS)
    return TOPICS[index]

def generate_morning_message(topic):
    prompt = f"""
    Ты CodeSensei — строгий но справедливый учитель программирования.
    
    Тема дня: {topic['title']}
    Описание: {topic['description']}
    
    Напиши обучающее сообщение:
    1. Объясни тему просто и понятно (2-3 предложения)
    2. Покажи пример кода
    3. Задай вопрос: {topic['morning_question']}
    
    Стиль: коротко, по делу, без воды. На русском языке.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generate_evening_task(topic):
    prompt = f"""
    Ты CodeSensei — строгий учитель программирования.
    
    Тема дня: {topic['title']}
    
    Дай практическое задание: {topic['evening_task']}
    
    Напиши задание чётко и конкретно. На русском языке. Коротко.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def check_answer(topic, question, user_answer, is_evening=False):
    if is_evening:
        prompt = f"""
        Тема: {topic['title']}
        Задание: {topic['evening_task']}
        Ответ студента: {user_answer}
        
        Проверь код студента. Скажи
        Правильно или нет,Если ошибка — объясни где именно
        Покажи правильный вариант если неправильно
        
        Будь строгим но конструктивным. На русском языке. а так же простым и понятным языком.
        """
    else:
        prompt = f"""
        Тема: {topic['title']}
        Вопрос: {question}
        Ответ студента: {user_answer}
        
       Проверь код студента. Скажи
        Правильно или нет,Если ошибка — объясни где именно
        Покажи правильный вариант если неправильно
        
        Будь строгим но конструктивным. На русском языке. а так же простым и понятным языком.
        """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content