# ============================================================
# database.py
# TEMP MAIL BOT DATABASE
# SQLite database
# ============================================================

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any


# ============================================================
# SETTINGS
# ============================================================

DB_FILE = Path(__file__).with_name("temp_mail.db")


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        str(DB_FILE),
        timeout=30,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row

    # Better reliability when multiple bot tasks access SQLite.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


# ============================================================
# INIT DATABASE
# ============================================================

def init_db():
    conn = get_connection()

    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                language TEXT DEFAULT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                referred_by INTEGER DEFAULT NULL,
                referral_paid INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mailboxes (
                user_id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reward_messages (
                user_id INTEGER NOT NULL,
                message_key TEXT NOT NULL,
                code TEXT,
                amount REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, message_key),
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_user_id INTEGER NOT NULL UNIQUE,
                amount REAL NOT NULL DEFAULT 0.00158,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(referrer_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,
                FOREIGN KEY(referred_user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                binance_id TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'demo',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_reward_user
                ON reward_messages(user_id);

            CREATE INDEX IF NOT EXISTS idx_referrer
                ON referrals(referrer_id);

            CREATE INDEX IF NOT EXISTS idx_withdraw_user
                ON withdrawals(user_id);
            """
        )

        # --------------------------------------------------------
        # Safe migration for older databases.
        # --------------------------------------------------------

        _add_column_if_missing(
            conn,
            "users",
            "balance",
            "REAL NOT NULL DEFAULT 0.0"
        )

        _add_column_if_missing(
            conn,
            "users",
            "referred_by",
            "INTEGER DEFAULT NULL"
        )

        _add_column_if_missing(
            conn,
            "users",
            "referral_paid",
            "INTEGER NOT NULL DEFAULT 0"
        )

        _add_column_if_missing(
            conn,
            "users",
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

        _add_column_if_missing(
            conn,
            "users",
            "updated_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

        conn.commit()

    finally:
        conn.close()


def _add_column_if_missing(
    conn,
    table_name: str,
    column_name: str,
    definition: str
):
    columns = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing = {
        row["name"]
        for row in columns
    }

    if column_name not in existing:
        conn.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {definition}"
        )


# ============================================================
# USER
# ============================================================

def save_user(
    user_id: int,
    username: Optional[str] = None
):
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if row:
            conn.execute(
                """
                UPDATE users
                SET username = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (username, user_id)
            )
        else:
            conn.execute(
                """
                INSERT INTO users (
                    user_id,
                    username
                )
                VALUES (?, ?)
                """,
                (user_id, username)
            )

        conn.commit()

    finally:
        conn.close()


def get_user(
    user_id: int
) -> Optional[Dict[str, Any]]:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()


def get_all_users() -> List[int]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT user_id
            FROM users
            ORDER BY user_id ASC
            """
        ).fetchall()

        return [
            int(row["user_id"])
            for row in rows
        ]

    finally:
        conn.close()


# ============================================================
# LANGUAGE
# ============================================================

def get_language(
    user_id: int
) -> Optional[str]:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT language
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not row:
            return None

        return row["language"]

    finally:
        conn.close()


def set_language(
    user_id: int,
    language: str
):
    save_user(user_id)

    conn = get_connection()

    try:
        conn.execute(
            """
            UPDATE users
            SET language = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (language, user_id)
        )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# MAILBOX
# ============================================================

def save_mailbox(
    user_id: int,
    email: str,
    token: str
):
    save_user(user_id)

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
                user_id,
                email,
                token
            )
        )

        conn.commit()

    finally:
        conn.close()


def get_mailbox(
    user_id: int
) -> Optional[Dict[str, Any]]:
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
            (user_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()


def delete_mailbox(
    user_id: int
):
    conn = get_connection()

    try:
        conn.execute(
            """
            DELETE FROM mailboxes
            WHERE user_id = ?
            """,
            (user_id,)
        )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# BALANCE
# ============================================================

def get_balance(
    user_id: int
) -> float:
    save_user(user_id)

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not row:
            return 0.0

        return float(row["balance"] or 0.0)

    finally:
        conn.close()


def add_balance(
    user_id: int,
    amount: float
) -> float:
    save_user(user_id)

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
                user_id
            )
        )

        row = conn.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        conn.commit()

        return float(row["balance"])

    finally:
        conn.close()


# ============================================================
# EMAIL REWARD
# ============================================================

def reward_already_given(
    user_id: int,
    message_key: str
) -> bool:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT 1
            FROM reward_messages
            WHERE user_id = ?
              AND message_key = ?
            LIMIT 1
            """,
            (
                user_id,
                str(message_key)
            )
        ).fetchone()

        return row is not None

    finally:
        conn.close()


def add_email_reward_once(
    user_id: int,
    message_key: str,
    code: Optional[str],
    amount: float = 0.00130
):
    """
    একই user + একই message_key-এর জন্য reward একবারই দেওয়া হবে.

    Return:
        (added, new_balance)

    added=True  -> নতুন reward দেওয়া হয়েছে
    added=False -> আগে দেওয়া হয়েছিল
    """

    save_user(user_id)

    conn = get_connection()

    try:
        # Transaction শুরু।
        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute(
            """
            SELECT 1
            FROM reward_messages
            WHERE user_id = ?
              AND message_key = ?
            LIMIT 1
            """,
            (
                user_id,
                str(message_key)
            )
        ).fetchone()

        if existing:
            row = conn.execute(
                """
                SELECT balance
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            ).fetchone()

            conn.commit()

            return (
                False,
                float(row["balance"] or 0.0)
            )

        conn.execute(
            """
            INSERT INTO reward_messages (
                user_id,
                message_key,
                code,
                amount
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                str(message_key),
                str(code) if code else None,
                float(amount)
            )
        )

        conn.execute(
            """
            UPDATE users
            SET balance = balance + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                float(amount),
                user_id
            )
        )

        row = conn.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        conn.commit()

        return (
            True,
            float(row["balance"] or 0.0)
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_reward_count(
    user_id: int
) -> int:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM reward_messages
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        return int(row["total"] or 0)

    finally:
        conn.close()


# ============================================================
# REFERRAL
# ============================================================

REFERRAL_REWARD = 0.00158


def get_referrer(
    user_id: int
) -> Optional[int]:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT referred_by
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not row or row["referred_by"] is None:
            return None

        return int(row["referred_by"])

    finally:
        conn.close()


def set_referrer(
    user_id: int,
    referrer_id: int
) -> bool:
    """
    Referral শুধুমাত্র user-এর প্রথম referral হিসেবে save হবে।
    নিজের referral গ্রহণ করবে না।
    """

    if int(user_id) == int(referrer_id):
        return False

    save_user(user_id)
    save_user(referrer_id)

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT referred_by
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not row:
            conn.rollback()
            return False

        if row["referred_by"] is not None:
            conn.commit()
            return False

        conn.execute(
            """
            UPDATE users
            SET referred_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                referrer_id,
                user_id
            )
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def add_referral_once(
    referrer_id: int,
    referred_user_id: int,
    amount: float = REFERRAL_REWARD
):
    """
    একই referred user-এর জন্য referrer একবারই reward পাবে.

    Return:
        (added, new_referrer_balance)
    """

    if int(referrer_id) == int(referred_user_id):
        return (
            False,
            get_balance(referrer_id)
        )

    save_user(referrer_id)
    save_user(referred_user_id)

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute(
            """
            SELECT 1
            FROM referrals
            WHERE referred_user_id = ?
            LIMIT 1
            """,
            (referred_user_id,)
        ).fetchone()

        if existing:
            row = conn.execute(
                """
                SELECT balance
                FROM users
                WHERE user_id = ?
                """,
                (referrer_id,)
            ).fetchone()

            conn.commit()

            return (
                False,
                float(row["balance"] or 0.0)
            )

        conn.execute(
            """
            INSERT INTO referrals (
                referrer_id,
                referred_user_id,
                amount
            )
            VALUES (?, ?, ?)
            """,
            (
                referrer_id,
                referred_user_id,
                float(amount)
            )
        )

        conn.execute(
            """
            UPDATE users
            SET balance = balance + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                float(amount),
                referrer_id
            )
        )

        row = conn.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (referrer_id,)
        ).fetchone()

        conn.commit()

        return (
            True,
            float(row["balance"] or 0.0)
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_referral_count(
    user_id: int
) -> int:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM referrals
            WHERE referrer_id = ?
            """,
            (user_id,)
        ).fetchone()

        return int(row["total"] or 0)

    finally:
        conn.close()


# ============================================================
# WITHDRAWAL
# ============================================================

def create_withdrawal(
    user_id: int,
    binance_id: str,
    amount: float
) -> Optional[int]:
    """
    Demo withdrawal record তৈরি করে।

    এটি কোনো বাস্তব Binance payment পাঠায় না।
    Balance থেকে amount কাটা হবে না যদি amount <= 0
    বা balance-এর চেয়ে বেশি হয়।

    Return:
        withdrawal_id অথবা None
    """

    save_user(user_id)

    amount = float(amount)

    if amount <= 0:
        return None

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not row:
            conn.rollback()
            return None

        balance = float(row["balance"] or 0.0)

        if amount > balance:
            conn.rollback()
            return None

        cursor = conn.execute(
            """
            INSERT INTO withdrawals (
                user_id,
                binance_id,
                amount,
                status
            )
            VALUES (?, ?, ?, 'demo')
            """,
            (
                user_id,
                str(binance_id).strip(),
                amount
            )
        )

        # Demo withdrawal-এর ক্ষেত্রে balance reserve/cut করা হচ্ছে।
        conn.execute(
            """
            UPDATE users
            SET balance = balance - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                amount,
                user_id
            )
        )

        withdrawal_id = cursor.lastrowid

        conn.commit()

        return int(withdrawal_id)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_withdrawals(
    user_id: int
) -> List[Dict[str, Any]]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                user_id,
                binance_id,
                amount,
                status,
                created_at
            FROM withdrawals
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        conn.close()


# ============================================================
# STATISTICS
# ============================================================

def get_total_reward_amount() -> float:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            AS total
            FROM reward_messages
            """
        ).fetchone()

        return float(row["total"] or 0.0)

    finally:
        conn.close()


def get_total_referral_amount() -> float:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            AS total
            FROM referrals
            """
        ).fetchone()

        return float(row["total"] or 0.0)

    finally:
        conn.close()


def get_total_withdrawal_amount() -> float:
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            AS total
            FROM withdrawals
            """
        ).fetchone()

        return float(row["total"] or 0.0)

    finally:
        conn.close()


# ============================================================
# AUTO INIT
# ============================================================

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized successfully.")
    print(f"📁 Database: {DB_FILE}")
