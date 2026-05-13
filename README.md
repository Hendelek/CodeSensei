# ☁️ CodeSensei: Advanced AI-Driven Python Mentor 🔴

An intelligent, asynchronous mentorship system for Telegram that leverages Large Language Models (LLMs) for adaptive learning. 

> **Status:** Successfully passed internal testing phases. Currently utilized by students of a programming course to automate the learning cycle.

🔗 **Production Bot:** [@Code_Sensei_bot](https://t.me/Code_Sensei_bot)

---

### 🛠 Technical Excellence

* **Adaptive Level Assessment** Implemented a **"Zero-shot" technical interview** logic. The system uses `Llama-3.3-70B` to evaluate responses and automatically assign a starting module via structured output parsing (`RESULT_INDEX`).

* **Asynchronous Engine** Built with `python-telegram-bot` and `asyncio`. All I/O operations, including API requests to Groq and database queries, are **non-blocking** to ensure high performance.

* **Persistent Storage & Context Management** Utilizes `aiosqlite` for thread-safe data persistence. It manages user states (FSM) and maintains a **6-turn sliding context window** to keep the AI focused and efficient.

* **Multimodal Interaction** Integrated `Whisper-large-v3` support for **voice message transcription**, allowing students to interact with the mentor using natural language.

* **Prompt Engineering** Engineered strict system instructions with custom branding (☁️/🔴) to prevent off-topic interactions and maintain a professional educational environment.

---

### 🧩 Key Logic & Features

1.  **AI-Driven FSM (State Machine):** Automated management of the user journey from registration to diagnostic testing and the active learning phase.
2.  **Automated Learning Cycle:**
    * 🕙 **Morning:** Theoretical block delivery based on the current topic.
    * 🕖 **Evening:** Practical coding challenge assignment to reinforce skills.
3.  **Modular Curriculum:** Educational content is decoupled into `topics.py`, allowing for seamless course scaling.

---

### 🚀 Getting Started

1.  **Environment Setup** Create a `.env` file:
    ```env
    TELEGRAM_TOKEN=your_tg_token
    GROQ_API_KEY=your_groq_key
    ```
2.  **Installation**
    ```bash
    pip install -r requirements.txt
    python bot.py
    ```

---
**☁️ Developed with a focus on pedagogical integrity and scalable architecture 🔴**
