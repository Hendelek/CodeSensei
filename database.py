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
        # Добавить колонку если её нет
        try:
            conn.execute("ALTER TABLE progress ADD COLUMN state TEXT")
        except:
            pass

def get_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT * FROM progress WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            conn.execute("INSERT INTO progress (user_id) VALUES (?)", (user_id,))
            return {"user_id": user_id, "current_topic_index": 0, "morning_done": 0, "evening_done": 0, "last_date": None}
        return {"user_id": row[0], "current_topic_index": row[1], "morning_done": row[2], "evening_done": row[3], "last_date": row[4]}

def update_user(user_id, **kwargs):
    fields = ", ".join([f"{k} = ?" for k in kwargs])
    values = list(kwargs.values()) + [user_id]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE progress SET {fields} WHERE user_id = ?", values)
        
def get_state(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT state FROM progress WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row and row[0] else None

def set_state(user_id, state):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE progress SET state = ? WHERE user_id = ?", (state, user_id))