import sqlite3
import bcrypt
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()

    admin = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if admin is None:
        pw_hash = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (username, password_hash, name, is_admin) VALUES (?, ?, ?, 1)",
            ("admin", pw_hash, "Administrador"),
        )
        conn.commit()
    conn.close()


def authenticate(username: str, password: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row is None:
        return None
    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return None
    return {"id": row["id"], "username": row["username"], "name": row["name"], "is_admin": bool(row["is_admin"])}


def list_users() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT id, username, name, is_admin FROM users ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username: str, password: str, name: str, is_admin: bool = False) -> bool:
    conn = _get_conn()
    try:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (username, password_hash, name, is_admin) VALUES (?, ?, ?, ?)",
            (username, pw_hash, name, int(is_admin)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM users WHERE id = ? AND username != 'admin'", (user_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def reset_password(user_id: int, new_password: str):
    conn = _get_conn()
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, user_id))
    conn.commit()
    conn.close()
