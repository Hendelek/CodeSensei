# ☁️ CodeSensei: AI-Driven Python Mentorship System 🔴

A production-ready Telegram bot designed to automate the Python learning path using a modern asynchronous architecture and LLM integration.

🔗 **Live Demo:** [@Code_Sensei_bot](https://t.me/Code_Sensei_bot)

---

### 🛠 Technical Stack & Architecture

* **LLM Orchestration:** Powered by **Llama-3.3-70B** (via Groq API) for real-time contextual feedback and code validation.
* **Multimodal Interaction:** Integrated **Whisper-large-v3** for high-accuracy Speech-to-Text (STT) processing, allowing users to interact via voice.
* **Asynchronous Core:** Built on `python-telegram-bot` with a fully non-blocking architecture to ensure high responsiveness during heavy API I/O operations.
* **Persistence & State Management:** Implemented an FSM (Finite State Machine) using **SQLite3** to track user progress, learning stages, and conversation history.
* **Automated Job Scheduling:** Managed by **APScheduler** with timezone-aware (`pytz`) triggers for daily content delivery.
* **Cloud Infrastructure:** Optimized for **Railway** deployment with robust signal handling and update queue management (`drop_pending_updates`).

---

### 🧩 Engineering Highlights

1.  **Contextual Memory Buffer:** Implements a sliding window history (storing the last 6 interactions) to maintain pedagogical context for the LLM.
2.  **Zero-Shot Validation Logic:** Utilizes advanced prompt engineering to distinguish between casual dialogue and technical solutions, triggering a "VERNO" (Correct) flag only upon successful logic validation.
3.  **Resilience & Error Handling:** Built-in conflict resolution for Telegram bot sessions and automated recovery protocols for API rate limits or network disruptions.
4.  **Modular Syllabus:** Decoupled educational content (`topics.py`) from the core logic, allowing for easy expansion of the curriculum.

---

### ⚙️ Development Environment
```env
TELEGRAM_TOKEN=your_token_here
GROQ_API_KEY=your_key_here
PYTHON_VERSION=3.10
