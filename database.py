import sqlite3

DB_PATH = "codesensei.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER PRIMARY KEY,
                current_topic_index INTEGER DEFAULT 0,
                morning_done INTEGER DEFAULT 0,
                evening_done INTEGER DEFAULT 0,
                last_date TEXT,
                state TEXT
            )
        """)

def get_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM progress WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            conn.execute("INSERT INTO progress (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return {"user_id": user_id, "current_topic_index": 0, "morning_done": 0, "evening_done": 0, "state": None}
        return dict(row)

def update_user(user_id, **kwargs):
    fields = ", ".join([f"{k} = ?" for k in kwargs])
    values = list(kwargs.values()) + [user_id]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE progress SET {fields} WHERE user_id = ?", values)
        conn.commit()

def set_state(user_id, state):
    update_user(user_id, state=state)

def get_state(user_id):
    user = get_user(user_id)
    return user.get("state")