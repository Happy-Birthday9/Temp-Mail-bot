import sqlite3
from pathlib import Path
from typing import Optional, Dict, List


# =========================================================
# DATABASE SETTINGS
# =========================================================

DB_FILE = Path(__file__).resolve().parent / "bot.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    conn = sqlite3.connect(
        DB_FILE,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# INIT DATABASE
# =========================================================

def init_db():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # -------------------------------------------------
        # USERS TABLE
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                language TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -------------------------------------------------
        # MAILBOXES TABLE
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mailboxes (
                user_id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
        """)

        # -------------------------------------------------
        # INDEX
        # -------------------------------------------------

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_language
            ON users(language)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mailboxes_token
            ON mailboxes(token)
        """)

        conn.commit()

    finally:

        conn.close()


# =========================================================
# SAVE USER
# =========================================================

def save_user(
    user_id: int,
    username: Optional[str] = None
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (
                user_id,
                username
            )
            VALUES (?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                username = excluded.username,
                updated_at = CURRENT_TIMESTAMP
        """, (
            int(user_id),
            username
        ))

        conn.commit()

    finally:

        conn.close()


# =========================================================
# GET LANGUAGE
# =========================================================

def get_language(
    user_id: int
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT language
            FROM users
            WHERE user_id = ?
        """, (
            int(user_id),
        ))

        row = cursor.fetchone()

        if not row:
            return None

        return row["language"]

    finally:

        conn.close()


# =========================================================
# SET LANGUAGE
# =========================================================

def set_language(
    user_id: int,
    language: str
):

    if language not in (
        "en",
        "bn",
        "hi"
    ):
        language = "en"

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # User না থাকলে আগে তৈরি করবে
        cursor.execute("""
            INSERT INTO users (
                user_id,
                language
            )
            VALUES (?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                language = excluded.language,
                updated_at = CURRENT_TIMESTAMP
        """, (
            int(user_id),
            language
        ))

        conn.commit()

    finally:

        conn.close()


# =========================================================
# SAVE MAILBOX
# =========================================================

def save_mailbox(
    user_id: int,
    email: str,
    token: str
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO mailboxes (
                user_id,
                email,
                token
            )
            VALUES (?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                email = excluded.email,
                token = excluded.token,
                updated_at = CURRENT_TIMESTAMP
        """, (
            int(user_id),
            str(email),
            str(token)
        ))

        conn.commit()

    finally:

        conn.close()


# =========================================================
# GET MAILBOX
# =========================================================

def get_mailbox(
    user_id: int
) -> Optional[Dict]:

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                user_id,
                email,
                token,
                created_at,
                updated_at
            FROM mailboxes
            WHERE user_id = ?
        """, (
            int(user_id),
        ))

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "user_id": row["user_id"],
            "email": row["email"],
            "token": row["token"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    finally:

        conn.close()


# =========================================================
# DELETE MAILBOX
# =========================================================

def delete_mailbox(
    user_id: int
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM mailboxes
            WHERE user_id = ?
        """, (
            int(user_id),
        ))

        conn.commit()

    finally:

        conn.close()


# =========================================================
# GET ALL USERS
# =========================================================

def get_all_users() -> List[int]:

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id
            FROM users
            ORDER BY user_id ASC
        """)

        rows = cursor.fetchall()

        return [
            int(row["user_id"])
            for row in rows
        ]

    finally:

        conn.close()


# =========================================================
# GET ALL MAILBOXES
# =========================================================

def get_all_mailboxes():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                user_id,
                email,
                token,
                created_at,
                updated_at
            FROM mailboxes
            ORDER BY updated_at DESC
        """)

        rows = cursor.fetchall()

        return [
            {
                "user_id": row["user_id"],
                "email": row["email"],
                "token": row["token"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    finally:

        conn.close()


# =========================================================
# COUNT USERS
# =========================================================

def count_users() -> int:

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            AS total
            FROM users
        """)

        row = cursor.fetchone()

        return int(row["total"])

    finally:

        conn.close()


# =========================================================
# COUNT MAILBOXES
# =========================================================

def count_mailboxes() -> int:

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            AS total
            FROM mailboxes
        """)

        row = cursor.fetchone()

        return int(row["total"])

    finally:

        conn.close()


# =========================================================
# DATABASE TEST
# =========================================================

if __name__ == "__main__":

    init_db()

    print("================================")
    print("✅ Database initialized")
    print(f"📁 Database: {DB_FILE}")
    print(f"👥 Users: {count_users()}")
    print(f"📧 Mailboxes: {count_mailboxes()}")
    print("================================")
