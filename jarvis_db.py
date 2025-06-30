import psycopg2
import uuid
from datetime import datetime
import os
from dotenv import dotenv_values

# === Load PostgreSQL Configuration from .env ===


DB_CONFIG = {
    "dbname": os.environ.get("PG_DB", "jarvis"),
    "user": os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASS", ""),
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": os.environ.get("PG_PORT", "5432")
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# === Initialize Database Tables ===
def init_db():
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema='public'
        """)
        existing_tables = {row[0] for row in cursor.fetchall()}
        required_tables = {"users", "sessions", "chats", "otp_reset", "user_files"}

        if required_tables.issubset(existing_tables):
            print("⚠️ Tables already exist. Skipping creation.")
            return

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL CHECK (email ~* r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
                created_at TIMESTAMP NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                logged_in INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_reset (
                username TEXT PRIMARY KEY,
                otp TEXT,
                created_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_files (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        print("✅ PostgreSQL database initialized.")
    except Exception as e:
        print(f"❌ Error initializing DB: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# === Insert New User ===
def insert_user(username, password, email=None, is_admin=False):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        user_id = str(uuid.uuid4())
        now = datetime.now()

        cursor.execute("""
            INSERT INTO users (id, username, password, email, created_at, is_admin)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, username, password, email, now, is_admin))

        cursor.execute("""
            INSERT INTO sessions (user_id, username, logged_in, last_login)
            VALUES (%s, %s, %s, %s)
        """, (user_id, username, 0, None))

        conn.commit()
        print(f"✅ User '{username}' inserted.")
    except Exception as e:
        print(f"❌ Failed to insert user: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# === Store Chat ===
def store_chat(user_id, username, message, response):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("""
            INSERT INTO chats (user_id, username, message, response, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, username, message, response, now))
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to store chat: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# === Fetch Chat History ===
def get_chat_history(username):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message, response, timestamp FROM chats
            WHERE username = %s ORDER BY timestamp ASC
        """, (username,))
        return [{"message": row[0], "response": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
    except Exception as e:
        print(f"❌ Error fetching chat history: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# === Session Updates ===
def update_session_login(username):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions SET logged_in = 1, last_login = %s
            WHERE username = %s
        """, (datetime.now(), username))
        conn.commit()
    except Exception as e:
        print(f"❌ Login session update failed: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_session_logout(username):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET logged_in = 0 WHERE username = %s", (username,))
        conn.commit()
    except Exception as e:
        print(f"❌ Logout session update failed: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_logged_in_users():
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM sessions WHERE logged_in = 1")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"❌ Error fetching logged-in users: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_session_info(username):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE username = %s", (username,))
        return cursor.fetchone()
    except Exception as e:
        print(f"❌ Error fetching session info: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_user_by_name(username):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "password": row[2],
                "email": row[3],
                "created_at": row[4],
                "is_admin": row[5]
            }
        return None
    except Exception as e:
        print(f"❌ Error fetching user: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# === Admin Panel: View All Users ===
def get_all_users():
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, created_at, is_admin FROM users ORDER BY created_at DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# === Admin Panel: Delete User ===
def delete_user(username):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chats WHERE username = %s", (username,))
        cursor.execute("DELETE FROM otp_reset WHERE username = %s", (username,))
        cursor.execute("DELETE FROM sessions WHERE username = %s", (username,))
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# === File Management ===
def save_user_file(user_id, filename, content):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_files (user_id, filename, content)
            VALUES (%s, %s, %s)
        """, (user_id, filename, content))
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to save user file: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_user_files(user_id):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename, created_at FROM user_files
            WHERE user_id = %s ORDER BY created_at DESC
        """, (user_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Failed to fetch user files: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_file_by_name(user_id, filename):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content FROM user_files
            WHERE user_id = %s AND filename = %s
        """, (user_id, filename))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"❌ Failed to fetch file content: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

