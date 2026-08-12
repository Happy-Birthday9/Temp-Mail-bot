# database.py

import sqlite3
from pathlib import Path


DB_FILE = Path("bot.db")


def get_connection():
    conn = sqlite3.connect(
        DB_FILE,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    # Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Temporary mailboxes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mailboxes (
            user_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USER
# =========================================================

def save_user(user_id, username=None):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (
            user_id,
            username
        )
        VALUES (?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username
    """, (
        user_id,
        username
    ))

    conn.commit()
    conn.close()


def get_language(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT language
        FROM users
        WHERE user_id = ?
    """, (
        user_id,
    ))

    row = cursor.fetchone()

    conn.close()

    if row:
        return row["language"]

    return None


def set_language(
    user_id,
    language
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET language = ?
        WHERE user_id = ?
    """, (
        language,
        user_id
    ))

    conn.commit()
    conn.close()


# =========================================================
# MAILBOX
# =========================================================

def save_mailbox(
    user_id,
    email,
    token
):

    conn = get_connection()

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
            created_at = CURRENT_TIMESTAMP
    """, (
        user_id,
        email,
        token
    ))

    conn.commit()
    conn.close()


def get_mailbox(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            email,
            token,
            created_at
        FROM mailboxes
        WHERE user_id = ?
    """, (
        user_id,
    ))

    row = cursor.fetchone()

    conn.close()

    if row:

        return {
            "email": row["email"],
            "token": row["token"],
            "created_at": row["created_at"]
        }

    return None


def delete_mailbox(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM mailboxes
        WHERE user_id = ?
    """, (
        user_id,
    ))

    conn.commit()
    conn.close()


# =========================================================
# USER COUNT
# =========================================================

def get_user_count():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM users
    """)

    row = cursor.fetchone()

    conn.close()

    return row["total"]


# =========================================================
# ALL USERS
# =========================================================

def get_all_users():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id
        FROM users
    """)

    rows = cursor.fetchall()

    conn.close()

    return [
        row["user_id"]
        for row in rows
  ]
