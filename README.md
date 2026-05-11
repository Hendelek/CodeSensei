# CodeSensei 🥋 @Code_Sensei_bot

AI-powered daily coding trainer. Learn one concept per day, get tested twice.

## How it works

- **10:00** — Morning lesson with explanation and theory question
- **19:00** — Evening practical coding task
- AI checks your answers and gives detailed feedback
- Topics progress from simple to complex, no jumping around

## Commands

- `/start` — Start the bot
- `/morning` — Get today's lesson
- `/evening` — Get today's practical task
- `/progress` — See your progress

## Stack

- Python 3.14
- Groq API (llama-3.3-70b)
- python-telegram-bot
- SQLite
- GitHub Actions (scheduled runs)

## Setup

1. Clone the repo
2. Install: `pip install python-telegram-bot groq python-dotenv`
3. Create `.env` with `GROQ_API_KEY` and `TELEGRAM_TOKEN`
4. Run: `python bot.py`
