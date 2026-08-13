# database.py
# ============================================================
# TEMP MAIL BOT - DATABASE
# SQLite database
# ============================================================

import sqlite3
import threading
import uuid
from decimal import Decimal
from pathlib import Path


# ============================================================
# SETTINGS
# ============================================================

DB_FILE = Path("temp_mail_bot.db")

DB_LOCK = threading.RLock()


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        DB_FILE,
        timeout=30,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


# ============================================================
# INIT DATABASE
# ============================================================

def init_db():
    with DB_LOCK:
        conn = get_connection()

        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT DEFAULT NULL,

                    balance REAL DEFAULT 0,

                    referral_count INTEGER DEFAULT 0,
                    reward_count INTEGER DEFAULT 0,

                    referrer_id INTEGER DEFAULT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );


                CREATE TABLE IF NOT EXISTS mailboxes (
                    user_id INTEGER PRIMARY KEY,

                    email TEXT,
                    token TEXT,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY(user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );


                CREATE TABLE IF NOT EXISTS email_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    user_id INTEGER NOT NULL,

                    reward_key TEXT NOT NULL,

                    amount REAL NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(user_id, reward_key),

                    FOREIGN KEY(user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );


                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,

                    amount REAL NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(referred_id),

                    FOREIGN KEY(referrer_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE,

                    FOREIGN KEY(referred_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );


                CREATE TABLE IF NOT EXISTS withdrawals (
                    id TEXT PRIMARY KEY,

                    user_id INTEGER NOT NULL,

                    binance_id TEXT NOT NULL,

                    amount REAL NOT NULL,

                    status TEXT DEFAULT 'pending',

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY(user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );


                CREATE INDEX IF NOT EXISTS idx_email_rewards_user
                ON email_rewards(user_id);


                CREATE INDEX IF NOT EXISTS idx_referrals_referrer
                ON referrals(referrer_id);


                CREATE INDEX IF NOT EXISTS idx_withdrawals_user
                ON withdrawals(user_id);
                """
            )

            conn.commit()

        finally:
            conn.close()


# ============================================================
# USER
# ============================================================

def save_user(user_id, username=None):
    user_id = int(user_id)

    with DB_LOCK:
        conn = get_connection()

        try:
            conn.execute(
                """
                INSERT INTO users (
                    user_id,
                    username
                )
                VALUES (?, ?)

                ON CONFLICT(user_id)
                DO UPDATE SET
                    username = excluded.username,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    username,
                ),
            )

            conn.commit()

        finally:
            conn.close()


# ============================================================
# LANGUAGE
# ============================================================

def get_language(user_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT language
                FROM users
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            if not row:
                return None

            return row["language"]

        finally:
            conn.close()


def set_language(user_id, language):
    save_user(user_id)

    with DB_LOCK:
        conn = get_connection()

        try:
            conn.execute(
                """
                UPDATE users
                SET language = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (
                    language,
                    int(user_id),
                ),
            )

            conn.commit()

        finally:
            conn.close()


# ============================================================
# MAILBOX
# ============================================================

def save_mailbox(user_id, email, token):
    save_user(user_id)

    with DB_LOCK:
        conn = get_connection()

        try:
            conn.execute(
                """
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
                """,
                (
                    int(user_id),
                    email,
                    token,
                ),
            )

            conn.commit()

        finally:
            conn.close()


def get_mailbox(user_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT
                    user_id,
                    email,
                    token,
                    created_at,
                    updated_at
                FROM mailboxes
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            if not row:
                return None

            return dict(row)

        finally:
            conn.close()


# ============================================================
# USERS
# ============================================================

def get_all_users():
    with DB_LOCK:
        conn = get_connection()

        try:
            rows = conn.execute(
                """
                SELECT user_id
                FROM users
                ORDER BY user_id
                """
            ).fetchall()

            return [
                int(row["user_id"])
                for row in rows
            ]

        finally:
            conn.close()


# ============================================================
# BALANCE
# ============================================================

def get_balance(user_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT balance
                FROM users
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            if not row:
                return 0.0

            return float(row["balance"] or 0)

        finally:
            conn.close()


def add_balance(user_id, amount):
    save_user(user_id)

    amount = Decimal(str(amount))

    with DB_LOCK:
        conn = get_connection()

        try:
            conn.execute(
                """
                UPDATE users
                SET balance = balance + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (
                    float(amount),
                    int(user_id),
                ),
            )

            conn.commit()

            row = conn.execute(
                """
                SELECT balance
                FROM users
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            return float(row["balance"])

        finally:
            conn.close()


# ============================================================
# EMAIL CODE REWARD
# ============================================================

def add_email_reward_once(
    user_id,
    reward_key,
    amount,
):
    """
    একই email/code reward_key থেকে
    একই user দ্বিতীয়বার reward পাবে না।

    Returns:
        (added, new_balance)
    """

    save_user(user_id)

    amount = Decimal(str(amount))

    with DB_LOCK:
        conn = get_connection()

        try:
            try:
                conn.execute(
                    """
                    INSERT INTO email_rewards (
                        user_id,
                        reward_key,
                        amount
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        int(user_id),
                        str(reward_key),
                        float(amount),
                    ),
                )

            except sqlite3.IntegrityError:
                row = conn.execute(
                    """
                    SELECT balance
                    FROM users
                    WHERE user_id = ?
                    """,
                    (int(user_id),),
                ).fetchone()

                return (
                    False,
                    float(row["balance"] or 0),
                )

            conn.execute(
                """
                UPDATE users
                SET balance = balance + ?,
                    reward_count = reward_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (
                    float(amount),
                    int(user_id),
                ),
            )

            conn.commit()

            row = conn.execute(
                """
                SELECT balance
                FROM users
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            return (
                True,
                float(row["balance"] or 0),
            )

        finally:
            conn.close()


def get_reward_count(user_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM email_rewards
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            return int(row["total"] or 0)

        finally:
            conn.close()


# ============================================================
# REFERRAL
# ============================================================

def get_referrer(user_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT referrer_id
                FROM users
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            if not row:
                return None

            return row["referrer_id"]

        finally:
            conn.close()


def set_referrer(user_id, referrer_id):
    """
    User-এর প্রথম referrer শুধু একবার সেট হবে।

    Returns:
        True  = নতুন referrer accepted
        False = already has referrer / invalid
    """

    user_id = int(user_id)
    referrer_id = int(referrer_id)

    if user_id == referrer_id:
        return False

    save_user(user_id)
    save_user(referrer_id)

    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT referrer_id
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if not row:
                return False

            if row["referrer_id"] is not None:
                return False

            conn.execute(
                """
                UPDATE users
                SET referrer_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (
                    referrer_id,
                    user_id,
                ),
            )

            conn.commit()

            return True

        finally:
            conn.close()


def add_referral_once(
    referrer_id,
    referred_id,
    amount,
):
    """
    একই referred user-এর জন্য
    referral reward দ্বিতীয়বার দেওয়া হবে না.

    Returns:
        (added, new_balance)
    """

    referrer_id = int(referrer_id)
    referred_id = int(referred_id)

    if referrer_id == referred_id:
        return False, get_balance(referrer_id)

    save_user(referrer_id)
    save_user(referred_id)

    amount = Decimal(str(amount))

    with DB_LOCK:
        conn = get_connection()

        try:
            try:
                conn.execute(
                    """
                    INSERT INTO referrals (
                        referrer_id,
                        referred_id,
                        amount
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        referrer_id,
                        referred_id,
                        float(amount),
                    ),
                )

            except sqlite3.IntegrityError:
                row = conn.execute(
                    """
                    SELECT balance
                    FROM users
                    WHERE user_id = ?
                    """,
                    (referrer_id,),
                ).fetchone()

                return (
                    False,
                    float(row["balance"] or 0),
                )

            conn.execute(
                """
                UPDATE users
                SET balance = balance + ?,
                    referral_count = referral_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (
                    float(amount),
                    referrer_id,
                ),
            )

            conn.commit()

            row = conn.execute(
                """
                SELECT balance
                FROM users
                WHERE user_id = ?
                """,
                (referrer_id,),
            ).fetchone()

            return (
                True,
                float(row["balance"] or 0),
            )

        finally:
            conn.close()


def get_referral_count(user_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM referrals
                WHERE referrer_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            return int(row["total"] or 0)

        finally:
            conn.close()


# ============================================================
# WITHDRAWAL
# ============================================================

def create_withdrawal(
    user_id,
    binance_id,
    amount,
):
    """
    Withdrawal তৈরি করার সময় একই transaction-এর মধ্যে
    balance থেকে টাকা কেটে নেয়।

    Minimum withdrawal check bot.py-তে করা হচ্ছে।
    এখানেও safety check রাখা হয়েছে।

    Returns:
        withdrawal ID অথবা None
    """

    user_id = int(user_id)
    amount = Decimal(str(amount))

    if amount <= 0:
        return None

    if amount < Decimal("1.00"):
        return None

    with DB_LOCK:
        conn = get_connection()

        try:
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                """
                SELECT balance
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if not row:
                conn.rollback()
                return None

            current_balance = Decimal(
                str(row["balance"] or 0)
            )

            if amount > current_balance:
                conn.rollback()
                return None

            withdrawal_id = uuid.uuid4().hex[:12].upper()

            # Balance কাটবে
            cursor = conn.execute(
                """
                UPDATE users
                SET balance = balance - ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                  AND balance >= ?
                """,
                (
                    float(amount),
                    user_id,
                    float(amount),
                ),
            )

            if cursor.rowcount != 1:
                conn.rollback()
                return None

            # Withdrawal record
            conn.execute(
                """
                INSERT INTO withdrawals (
                    id,
                    user_id,
                    binance_id,
                    amount,
                    status
                )
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (
                    withdrawal_id,
                    user_id,
                    str(binance_id),
                    float(amount),
                ),
            )

            conn.commit()

            return withdrawal_id

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

            raise

        finally:
            conn.close()


# ============================================================
# OPTIONAL ADMIN / WITHDRAWAL HELPERS
# ============================================================

def get_withdrawal(withdrawal_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT *
                FROM withdrawals
                WHERE id = ?
                """,
                (str(withdrawal_id),),
            ).fetchone()

            if not row:
                return None

            return dict(row)

        finally:
            conn.close()


def get_user_withdrawals(user_id):
    with DB_LOCK:
        conn = get_connection()

        try:
            rows = conn.execute(
                """
                SELECT *
                FROM withdrawals
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (int(user_id),),
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

        finally:
            conn.close()


def get_pending_withdrawals():
    with DB_LOCK:
        conn = get_connection()

        try:
            rows = conn.execute(
                """
                SELECT *
                FROM withdrawals
                WHERE status = 'pending'
                ORDER BY created_at ASC
                """
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

        finally:
            conn.close()


def update_withdrawal_status(
    withdrawal_id,
    status,
):
    allowed = {
        "pending",
        "processing",
        "paid",
        "rejected",
        "cancelled",
    }

    if status not in allowed:
        return False

    with DB_LOCK:
        conn = get_connection()

        try:
            cursor = conn.execute(
                """
                UPDATE withdrawals
                SET status = ?
                WHERE id = ?
                """,
                (
                    status,
                    str(withdrawal_id),
                ),
            )

            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()


# ============================================================
# STARTUP
# ============================================================

init_db()
