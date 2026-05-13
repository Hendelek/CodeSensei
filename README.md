# ☁️ CodeSensei: Advanced AI-Driven Python Mentor 🔴

**An intelligent, asynchronous mentorship system for Telegram that leverages LLMs for adaptive learning.**

🔗 **Live Production Bot:** [@Code_Sensei_bot](https://t.me/Code_Sensei_bot)

---

### 🚀 Deployment & Real-World Impact
* **Status:** Successfully passed comprehensive beta testing phases.
* **Active Usage:** Currently integrated and utilized by students of a professional programming course to automate their daily learning cycle.
* **Proven Stability:** The system is battle-tested with real users, ensuring high reliability in production environments.

---

### 🧩 Key Features & Functionality

* **Adaptive Diagnostic Testing** The AI mentor conducts a technical interview (3-4 questions). Based on performance, it extracts a `RESULT_INDEX` via regex to automatically assign the correct starting topic.

* **Multimodal Input Processing** Full support for text and voice messages. Voice audio is processed through `Whisper-large-v3` for transcription before technical analysis.

* **Smart Context Management** Maintains a sliding context window of the last 6 dialogue turns stored as JSON in SQLite. This preserves continuity without exceeding AI token limits.

* **Automated Learning Lifecycle** Managed by `APScheduler`. Automatically delivers theory in the morning and practical tasks in the evening.

* **Strict Mentor Persona** Engineered system prompts ensure a concise, professional personality (☁️/🔴) that ignores off-topic chatter.

---

### ⚙️ How It Works (Technical Overview)

#### 1. Input Orchestration (`handle_input`)
The system routes data based on the user's **FSM state**:
* **Registration (`wait_name`)**: Captures name for personalized interaction.
* **Diagnostic (`wait_testing`)**: Monitors for the `RESULT_INDEX` to finalize level placement.
* **Learning Mode**: Standard tutor mode utilizing session history.

#### 2. Asynchronous Persistence Layer
Built with `aiosqlite` for non-blocking database operations, crucial for handling concurrent student sessions.
* **Users Table**: Tracks IDs, names, topic progress (`topic_idx`), and FSM states.

#### 3. Decoupled Curriculum (`topics.py`)
Learning content is separated from the engine logic. Each module includes:
* **Theory**: Conceptual questions (`morning_question`).
* **Practice**: Coding challenges (`evening_task`).

---

### 🛠 Technical Stack
* **Core**: Python 3.10+, `python-telegram-bot` (v20+).
* **AI/LLM**: Groq SDK (`Llama-3.3-70b`, `Whisper-large-v3`).
* **Scheduling**: `APScheduler` synchronized with `Europe/Stockholm` timezone.
* **Database**: `aiosqlite` with JSON history serialization.
