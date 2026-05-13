# ☁️ CodeSensei: Advanced AI-Driven Python Mentor 🔴

**An intelligent, asynchronous mentorship system for Telegram that leverages Large Language Models (LLMs) for adaptive learning.**

> 🚀 **Current Status:** Successfully passed internal testing phases. Currently utilized by students of a programming course to automate the learning cycle.

🔗 **Production Bot:** [@Code_Sensei_bot](https://t.me/Code_Sensei_bot)

---

### 🛠 Technical Architecture & Deep Dive

#### ⚡ Asynchronous Core & Concurrency
Built on a non-blocking architecture using `asyncio` and `python-telegram-bot` (v20+). All network I/O, including **Groq API** calls and **aiosqlite** transactions, are handled within the event loop to ensure high responsiveness under load.

#### 🧠 LLM Integration & Structured Parsing
* **Core Engine:** Utilizes `Llama-3.3-70B` via the Groq SDK for high-speed inference.
* **Logic:** Implements a custom parser using regular expressions to extract `RESULT_INDEX` from the LLM's natural language evaluation.
* **Prompt Engineering:** Dynamic system prompts are injected based on the user's state to enforce a strict mentor persona and prevent "hallucinations".

#### 🎙 Multimodal Data Processing
Integrated `Whisper-large-v3` for **Speech-to-Text (STT)**. The bot processes binary audio streams from Telegram, transcribes them via Groq, and feeds the resulting text into the Python analysis engine.

#### 💾 State Management & Persistence
* **FSM (Finite State Machine):** A persistent state machine is implemented at the database level to track progress from registration to active learning.
* **Memory Management:** Implements a **sliding window context** (last 6 turns) stored as JSON in SQLite to balance token efficiency with dialogue coherence.

#### ⏰ Automated Task Scheduling
Uses **APScheduler** with a `CronTrigger` to manage time-sensitive event delivery:
* 🕙 **10:00** — Theoretical block delivery.
* 🕖 **19:00** — Practical coding challenge assignment.
* *Synchronized with `Europe/Stockholm` timezone.*

---

### 🧩 System Logic & Pipeline

1.  **Diagnostic Phase:** The AI generates a sequence of adaptive questions. Final response is analyzed for technical proficiency to determine the user's starting point in the `TOPICS` schema.
2.  **Learning Loop:** A decoupled architecture where `bot.py` handles the engine logic and `topics.py` acts as the content provider, allowing curriculum updates without code redeployment.
3.  **Evaluation:** The mentor employs "Chain-of-Thought" instructions to validate code snippets, ensuring users understand Pythonic principles.

---

### 📈 Future Engineering Goals
* 🐳 **Dockerization:** Containerizing the stack for cloud-agnostic deployment.
* 🛡 **Sandboxed Execution:** Implementing isolated environments to safely execute and verify student-submitted code.
* 📚 **Vector DB Integration:** Moving to RAG (Retrieval-Augmented Generation) for complex documentation queries.

---
**☁️ Engineered with a focus on pedagogical precision and system stability 🔴**

Vector DB Integration: Moving from sliding windows to RAG (Retrieval-Augmented Generation) for more complex documentation queries.

☁️ Engineered with a focus on pedagogical precision and system stability 🔴
