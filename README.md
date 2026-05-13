☁️ CodeSensei: Advanced AI-Driven Python Mentor 🔴
An intelligent, asynchronous mentorship system for Telegram that leverages Large Language Models (LLMs) for adaptive learning.

Status: Successfully passed internal testing phases. Currently utilized by students of a programming course to automate the learning cycle.

🔗 Production Bot: @Code_Sensei_bot

🛠 Technical Architecture & Deep Dive
Asynchronous Core & Concurrency: Built on a non-blocking architecture using asyncio and python-telegram-bot (v20+). All network I/O, including Groq API calls and aiosqlite transactions, are handled within the event loop to ensure horizontal scalability and responsiveness under load.

LLM Integration & Structured Parsing: Utilizes Llama-3.3-70B via the Groq SDK for high-speed inference.

Logic: Implements a custom parser using regular expressions to extract RESULT_INDEX from the LLM's natural language evaluation.

Prompt Engineering: Dynamic system prompts are injected based on the user's state to minimize "hallucinations" and enforce a strict mentor persona.

Multimodal Data Processing: Integrated Whisper-large-v3 for STT (Speech-to-Text). The bot processes binary audio streams from Telegram, transcribes them via Groq, and feeds the resulting text into the Python analysis engine.

State Management & Data Persistence: * FSM: A persistent Finite State Machine (FSM) is implemented at the database level to track progress through registration, testing, and learning phases.

Memory Management: Implements a sliding window context (last 6 turns) stored as JSON in SQLite. This balances token consumption with the need for long-term dialogue coherence.

Automated Task Scheduling: Uses APScheduler with a CronTrigger to manage time-sensitive event delivery (theory at 10:00, practice at 19:00), synchronized with the Europe/Stockholm timezone.

🧩 System Logic & Pipeline
Diagnostic Phase: The AI generates a sequence of 3-4 adaptive questions. The final response is analyzed for technical proficiency to determine the user's starting point in the TOPICS schema.

Learning Loop: A decoupled architecture where bot.py handles the engine logic and topics.py acts as the content provider. This allows for updating the curriculum without code redeployment.

Strict Evaluation: The mentor employs "Chain-of-Thought" instructions to validate code snippets, ensuring that users don't just get the answer but understand the underlying Pythonic principles.

🚀 Development & Deployment
Environment Configuration: Uses python-dotenv for secure management of TELEGRAM_TOKEN and GROQ_API_KEY.

Installation:

Bash
pip install -r requirements.txt
python bot.py
📈 Future Engineering Goals
Dockerization: Containerizing the stack for cloud-agnostic deployment.

Sandboxed Execution: Implementing RestrictedPython or Docker-based executors to safely run and verify student-submitted code.

Vector DB Integration: Moving from sliding windows to RAG (Retrieval-Augmented Generation) for more complex documentation queries.

☁️ Engineered with a focus on pedagogical precision and system stability 🔴
