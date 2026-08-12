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

DB_FILE = Path("temp_mail.db")

DB_LOCK = Lock()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        DB_FILE,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

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
                    language TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ------------------------------------------------
            # MAILBOX TABLE
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

    with DB_LOCK:

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


# ============================================================
# SAVE MAILBOX
# ============================================================

def save_mailbox(
    user_id,
    email,
    token
):

    with DB_LOCK:

        conn = get_connection()

        try:

            cursor = conn.cursor()

            # User না থাকলে তৈরি
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

            # Mailbox save/update
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

            return {
                "user_id": row["user_id"],
                "email": row["email"],
                "token": row["token"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

        finally:

            conn.close()


# ============================================================
# DELETE MAILBOX
# ============================================================

def delete_mailbox(user_id):

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

    with DB_LOCK:

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


# ============================================================
# GET ALL MAILBOXES
# ============================================================

def get_all_mailboxes():

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
                ORDER BY user_id ASC
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


# ============================================================
# USER COUNT
# ============================================================

def get_user_count():

    with DB_LOCK:

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


# ============================================================
# MAILBOX COUNT
# ============================================================

def get_mailbox_count():

    with DB_LOCK:

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


# ============================================================
# CHECK USER EXISTS
# ============================================================

def user_exists(user_id):

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
# CHECK MAILBOX EXISTS
# ============================================================

def mailbox_exists(user_id):

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
# CLOSE / NO-OP
# ============================================================

def close_db():
    """
    SQLite connection প্রতি function-এ close করা হচ্ছে,
    তাই আলাদা persistent connection close করার প্রয়োজন নেই।
    """
    pass
