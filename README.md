☁️ CodeSensei: Advanced AI-Driven Python Mentor 🔴
An intelligent, asynchronous mentorship system for Telegram that leverages LLMs for adaptive learning.

🔗 Live Production Bot: @Code_Sensei_bot

🚀 Deployment & Real-World Impact
Status: Successfully passed comprehensive beta testing phases.

Active Usage: Currently integrated and utilized by students of a professional programming course to automate their daily learning cycle.

Production-Ready Stability: Fully refactored to a modern, decoupled architecture capable of handling high concurrent loads with bulletproof stability.

🧩 Key Features & Functionality
Adaptive Diagnostic Testing: The AI mentor conducts a technical interview (4 structured questions). Upon completion, the system extracts evaluation metrics and a starting topic index using secure JSON parsing.

Smart Context Management: Maintains an optimized sliding context window of the last 6 dialogue turns stored as JSON in SQLite. This preserves continuity without exceeding AI token limits.

Automated Learning Lifecycle: Managed by APScheduler. Automatically delivers theory in the morning (morning_question) and practical tasks in the evening (evening_task) synchronized with the Europe/Stockholm timezone.

Strict Mentor Persona: Robust system prompts ensure a concise, professional personality (☁️/🔴) that ignores off-topic chatter and keeps the student focused.

⚙️ How It Works (Technical Overview)
1. Robust Routing & State Machine
Built on aiogram's native Finite State Machine (FSM) and independent Routers. The codebase is completely decoupled:

Registration (wait_name): Captures and validates user names.

Diagnostic (wait_testing): Orchestrates the entry exam and safely parses AI outputs.

Learning Mode: Standard asynchronous interaction with the mentor persona.

2. High-Performance Persistence Layer
Utilizes aiosqlite for non-blocking database operations. The database configuration is highly optimized for concurrent multi-user environments using advanced SQLite configurations:

WAL Mode (Write-Ahead Logging) enabled for safe, concurrent read/write operations.

In-Memory Temporary Storage and tuned cache size for lightning-fast query execution.

3. Decoupled Curriculum
Learning content is completely isolated from the engine logic inside topics.py. Each module includes structured conceptual theory and practical coding challenges.

🛠 Technical Stack
Framework: Python 3.10+, aiogram 3.x (Router & FSM-driven architecture).

Configuration & Validation: Pydantic Settings v2 (strict environment variable validation at runtime).

AI/LLM Integration: Groq SDK (llama-3.3-70b-versatile).

Scheduling: APScheduler.

Database: aiosqlite with customized performance PRAGMAs.

📁 Project Structure
Plaintext
├── .env                  # Environment variables
├── config.py             # Pydantic environment validation settings
├── database.py           # Database connection, initialization, and PRAGMA tweaks
├── ai_service.py         # Groq API integration and prompt engineering
├── handlers.py           # Main Telegram routers, commands, and FSM logic
├── topics.py             # Decoupled educational curriculum
├── bot.py                # Application entrypoint & scheduler execution
└── requirements.txt      # Project dependencies
