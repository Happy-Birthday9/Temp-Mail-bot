# ============================================================
# database.py
# TEMP MAIL TELEGRAM BOT DATABASE
# ============================================================

import sqlite3
from pathlib import Path
from threading import Lock


# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "temp_mail.db"

DB_LOCK = Lock()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create a new SQLite connection.
    """
    conn = sqlite3.connect(
        DB_FILE,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE INITIALIZE
# ============================================================

def init_db():
    """
    Create required database tables.
    """

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            # ------------------------------------------------
            # USERS TABLE
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ------------------------------------------------
            # MAILBOXES TABLE
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mailboxes (
                    user_id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
                )
            """)

            # ------------------------------------------------
            # INDEXES
            # ------------------------------------------------

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_users_language
                ON users(language)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_mailboxes_token
                ON mailboxes(token)
            """)

            conn.commit()

        finally:

            conn.close()


# ============================================================
# SAVE USER
# ============================================================

def save_user(
    user_id,
    username=None
):
    """
    Save a Telegram user.

    Existing user হলে username update করবে।
    New user হলে language NULL থাকবে।
    """

    with DB_LOCK:

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


# ============================================================
# GET LANGUAGE
# ============================================================

def get_language(user_id):
    """
    Return user's selected language.

    Return:
        'en'
        'bn'
        'hi'
        None
    """

    with DB_LOCK:

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


# ============================================================
# SET LANGUAGE
# ============================================================

def set_language(
    user_id,
    language
):
    """
    Save user's selected language.
    """

    allowed_languages = {
        "en",
        "bn",
        "hi"
    }

    if language not in allowed_languages:
        language = "en"

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            # User না থাকলে আগে create
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


# ============================================================
# SAVE MAILBOX
# ============================================================

def save_mailbox(
    user_id,
    email,
    token
):
    """
    Save or update temporary mailbox.

    One user = one active mailbox.
    """

    if not email:
        raise ValueError(
            "Email cannot be empty."
        )

    if not token:
        raise ValueError(
            "Mailbox token cannot be empty."
        )

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            # Ensure user exists
            cursor.execute("""
                INSERT INTO users (
                    user_id
                )
                VALUES (?)

                ON CONFLICT(user_id)
                DO NOTHING
            """, (
                int(user_id),
            ))

            # Save mailbox
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


# ============================================================
# GET MAILBOX
# ============================================================

def get_mailbox(user_id):
    """
    Return user's mailbox.

    Example:
    {
        "user_id": 123456,
        "email": "example@mail.com",
        "token": "xxxxx",
        "created_at": "...",
        "updated_at": "..."
    }

    If no mailbox:
        return None
    """

    with DB_LOCK:

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

            return dict(row)

        finally:

            conn.close()


# ============================================================
# DELETE MAILBOX
# ============================================================

def delete_mailbox(user_id):
    """
    Delete user's current mailbox.
    """

    with DB_LOCK:

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


# ============================================================
# GET ALL USERS
# ============================================================

def get_all_users():
    """
    Return all Telegram user IDs.

    Used by:
        - auto inbox
        - statistics
        - broadcast
    """

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id
                FROM users
                ORDER BY user_id
            """)

            rows = cursor.fetchall()

            return [
                int(row["user_id"])
                for row in rows
            ]

        finally:

            conn.close()


# ============================================================
# GET ALL MAILBOXES
# ============================================================

def get_all_mailboxes():
    """
    Return all active mailboxes.

    Useful for admin/statistics.
    """

    with DB_LOCK:

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
                ORDER BY user_id
            """)

            rows = cursor.fetchall()

            return [
                dict(row)
                for row in rows
            ]

        finally:

            conn.close()


# ============================================================
# COUNT USERS
# ============================================================

def count_users():
    """
    Return total registered users.
    """

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM users
            """)

            return cursor.fetchone()[0]

        finally:

            conn.close()


# ============================================================
# COUNT MAILBOXES
# ============================================================

def count_mailboxes():
    """
    Return total active mailboxes.
    """

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM mailboxes
            """)

            return cursor.fetchone()[0]

        finally:

            conn.close()


# ============================================================
# USER EXISTS
# ============================================================

def user_exists(user_id):
    """
    Check whether user exists.
    """

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT 1
                FROM users
                WHERE user_id = ?
                LIMIT 1
            """, (
                int(user_id),
            ))

            return cursor.fetchone() is not None

        finally:

            conn.close()


# ============================================================
# MAILBOX EXISTS
# ============================================================

def mailbox_exists(user_id):
    """
    Check whether user has an active mailbox.
    """

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT 1
                FROM mailboxes
                WHERE user_id = ?
                LIMIT 1
            """, (
                int(user_id),
            ))

            return cursor.fetchone() is not None

        finally:

            conn.close()


# ============================================================
# GET USERS BY LANGUAGE
# ============================================================

def get_users_by_language(language):
    """
    Return users who selected a specific language.
    """

    allowed_languages = {
        "en",
        "bn",
        "hi"
    }

    if language not in allowed_languages:
        return []

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id
                FROM users
                WHERE language = ?
                ORDER BY user_id
            """, (
                language,
            ))

            rows = cursor.fetchall()

            return [
                int(row["user_id"])
                for row in rows
            ]

        finally:

            conn.close()


# ============================================================
# CLOSE / CLEANUP
# ============================================================

def close_db():
    """
    SQLite connections are opened per operation,
    so there is no persistent connection to close.

    This function is kept for compatibility.
    """
    pass


# ============================================================
# AUTO INITIALIZE
# ============================================================

if __name__ == "__main__":

    init_db()

    print(
        "✅ Database initialized successfully."
    )

    print(
        f"📁 Database file: {DB_FILE}"
    )

    print(
        f"👥 Users: {count_users()}"
    )

    print(
        f"📧 Mailboxes: {count_mailboxes()}"
    )
