# ☁️ CodeSensei: Advanced AI-Driven Python Mentor 🔴

An intelligent mentorship system for Telegram that leverages Large Language Models (LLMs) for adaptive learning and multimodal interaction. This project demonstrates proficiency in asynchronous programming, AI-driven data validation, and process automation.

🔗 **Production Bot:** [@Code_Sensei_bot](https://t.me/Code_Sensei_bot)

---

### 🛠 Technical Excellence (Under the Hood)

* **Smart Identity Validation:** Implemented an AI-powered onboarding system. Instead of simple string capture, the bot uses **Llama-3.3-70B** to extract real names from natural language input, effectively filtering out "noise" or non-name responses.
* **Multimodal Processing:** Integrated **Whisper-large-v3** via Groq API. The system handles voice messages by transcribing audio to text before performing technical analysis on the code provided.
* **Prompt Engineering & Context Guarding:** Engineered strict system instructions to keep the AI within the educational context (Python), preventing "off-topic" conversations and ensuring professional interaction.
* **Asynchronous Engine:** Built with `python-telegram-bot` and `asyncio`. API requests and task scheduling run concurrently to ensure high performance and zero blocking.
* **Persistent Storage:** Utilizes **SQLite3** for managing user profiles, state machines (FSM), and conversation history with a 6-turn sliding context window.

---

### 🧩 Key Logic & Features

1.  **AI-Driven FSM (State Machine):** Automated state management (Wait_Name, Wait_Theory, Wait_Practice) to ensure a structured user journey.
2.  **Automated Learning Cycle:**
    * 🕙 **10:00** — Theoretical block delivery.
    * 🕖 **19:00** — Practical coding challenge assignment.
3.  **Strict Code Evaluation:** Automated code validation that triggers a `VERNO` (Correct) flag only when the user provides a technically sound solution.

---

### ⚙️ Quick Start

1.  **Environment Setup:**
    Create a `.env` file:
    ```env
    TELEGRAM_TOKEN=your_tg_token
    GROQ_API_KEY=your_groq_key
    ```
2.  **Installation:**
    ```bash
    pip install -r requirements.txt
    python bot.py
    ```

---

### 📈 Future Roadmap
* **Dockerization:** Containerizing the application for seamless deployment.
* **Database Scaling:** Moving to PostgreSQL for high-concurrency support.
* **Sandboxed Execution:** Implementing isolated code execution to test user-submitted snippets in real-time.

---
**☁️ Developed with a focus on data integrity and user experience 🔴**
