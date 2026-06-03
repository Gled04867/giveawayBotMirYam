import sqlite3

DB_PATH = "giveaway.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            code TEXT UNIQUE,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            is_used INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

def load_codes_from_file(filepath: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    added = 0
    skipped = 0
    with open(filepath, "r") as f:
        for line in f:
            code = line.strip().upper()
            if not code:
                continue
            try:
                cursor.execute("INSERT INTO codes (code) VALUES (?)", (code,))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
    conn.commit()
    conn.close()
    return {"added": added, "skipped": skipped}

def check_code(code: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM codes WHERE code = ? AND is_used = 0", (code,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_participant(user_id: int, username: str, full_name: str, code: str) -> bool:
    """Один код = одна запись. Один человек может добавить несколько кодов."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO participants (user_id, username, full_name, code) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, code)
        )
        cursor.execute(
            "UPDATE codes SET is_used = 1 WHERE code = ?", (code,)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Код уже использован
        return False
    finally:
        conn.close()

def get_user_codes_count(user_id: int) -> int:
    """Сколько кодов зарегистрировал этот пользователь"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM participants WHERE user_id = ?", (user_id,)
    )
    result = cursor.fetchone()[0]
    conn.close()
    return result

def get_all_participants():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, code FROM participants")
    result = cursor.fetchall()
    conn.close()
    return result

def get_participants_count() -> int:
    """Количество зарегистрированных кодов"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM participants")
    result = cursor.fetchone()[0]
    conn.close()
    return result

def get_unique_users_count() -> int:
    """Количество уникальных участников"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM participants")
    result = cursor.fetchone()[0]
    conn.close()
    return result

def get_codes_count() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM codes WHERE is_used = 0")
    free = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM codes WHERE is_used = 1")
    used = cursor.fetchone()[0]
    conn.close()
    return {"free": free, "used": used}