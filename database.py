# database.py

import sqlite3
import threading
from pathlib import Path


# =========================================================
# DATABASE SETTINGS
# =========================================================

DB_FILE = Path(__file__).with_name("bot.db")

_db_lock = threading.Lock()


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

    with _db_lock:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            # -----------------------------
            # USERS
            # -----------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -----------------------------
            # MAILBOXES
            # -----------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mailboxes (
                    user_id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                )
            """)

            conn.commit()

        finally:

            conn.close()


# =========================================================
# SAVE USER
# =========================================================

def save_user(
    user_id,
    username=None
):

    with _db_lock:

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

def get_language(user_id):

    with _db_lock:

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
    user_id,
    language
):

    with _db_lock:

        conn = get_connection()

        try:

            cursor = conn.cursor()

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
    user_id,
    email,
    token
):

    with _db_lock:

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

def get_mailbox(user_id):

    with _db_lock:

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

def delete_mailbox(user_id):

    with _db_lock:

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

def get_all_users():

    with _db_lock:

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
                row["user_id"]
                for row in rows
            ]

        finally:

            conn.close()


# =========================================================
# GET USER COUNT
# =========================================================

def get_user_count():

    with _db_lock:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM users
            """)

            row = cursor.fetchone()

            return int(row["total"])

        finally:

            conn.close()


# =========================================================
# GET MAILBOX COUNT
# =========================================================

def get_mailbox_count():

    with _db_lock:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM mailboxes
            """)

            row = cursor.fetchone()

            return int(row["total"])

        finally:

            conn.close()


# =========================================================
# GET STATS
# =========================================================

def get_stats():

    return {
        "users": get_user_count(),
        "mailboxes": get_mailbox_count()
    }


# =========================================================
# AUTO INIT
# =========================================================

if __name__ == "__main__":

    init_db()

    print("✅ Database initialized successfully.")
    print(f"📁 Database: {DB_FILE}")
