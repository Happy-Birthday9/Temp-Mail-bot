# ============================================================
# database.py
# TEMP MAIL TELEGRAM BOT - SQLITE DATABASE
# ============================================================

import sqlite3
from decimal import Decimal
from pathlib import Path
from threading import Lock

# Keep database file in the same folder as this file.
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "temp_mail.db"

_db_lock = Lock()


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ============================================================
# INIT
# ============================================================

def init_db():
    with _db_lock:
        conn = get_connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT,
                    balance TEXT NOT NULL DEFAULT '0',
                    referrer_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS mailboxes (
                    user_id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS email_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reward_key TEXT NOT NULL,
                    code TEXT,
                    amount TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, reward_key),
                    FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    amount TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referred_id),
                    FOREIGN KEY (referrer_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (referred_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    binance_id TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id)
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

            # Small migration for databases created by older versions.
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(email_rewards)")
            }

            if "code" not in columns:
                conn.execute(
                    "ALTER TABLE email_rewards ADD COLUMN code TEXT"
                )

            conn.commit()

        finally:
            conn.close()


# ============================================================
# HELPERS
# ============================================================

def _ensure_user(conn, user_id, username=None):
    user_id = int(user_id)

    row = conn.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if row is None:
        conn.execute(
            """
            INSERT INTO users (user_id, username, language, balance)
            VALUES (?, ?, NULL, '0')
            """,
            (user_id, username),
        )
    elif username is not None:
        conn.execute(
            """
            UPDATE users
            SET username = ?
            WHERE user_id = ?
            """,
            (username, user_id),
        )


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _balance(conn, user_id):
    row = conn.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (int(user_id),),
    ).fetchone()

    if not row:
        return Decimal("0")

    return _to_decimal(row["balance"])


# ============================================================
# USERS
# ============================================================

def save_user(user_id, username=None):
    with _db_lock:
        conn = get_connection()
        try:
            _ensure_user(conn, user_id, username)
            conn.commit()
        finally:
            conn.close()


def get_language(user_id):
    with _db_lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT language FROM users WHERE user_id = ?",
                (int(user_id),),
            ).fetchone()

            if not row:
                return None

            return row["language"]
        finally:
            conn.close()


def set_language(user_id, language):
    with _db_lock:
        conn = get_connection()
        try:
            _ensure_user(conn, user_id)
            conn.execute(
                """
                UPDATE users
                SET language = ?
                WHERE user_id = ?
                """,
                (str(language), int(user_id)),
            )
            conn.commit()
        finally:
            conn.close()


def get_all_users():
    with _db_lock:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT user_id FROM users ORDER BY user_id"
            ).fetchall()

            return [int(row["user_id"]) for row in rows]
        finally:
            conn.close()


# ============================================================
# BALANCE
# ============================================================

def get_balance(user_id):
    with _db_lock:
        conn = get_connection()
        try:
            return _balance(conn, user_id)
        finally:
            conn.close()


def _add_balance(conn, user_id, amount):
    current = _balance(conn, user_id)
    new_balance = current + _to_decimal(amount)

    conn.execute(
        """
        UPDATE users
        SET balance = ?
        WHERE user_id = ?
        """,
        (str(new_balance), int(user_id)),
    )

    return new_balance


# ============================================================
# MAILBOX
# ============================================================

def save_mailbox(user_id, email, token):
    with _db_lock:
        conn = get_connection()
        try:
            _ensure_user(conn, user_id)

            conn.execute(
                """
                INSERT INTO mailboxes (user_id, email, token)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    email = excluded.email,
                    token = excluded.token,
                    created_at = CURRENT_TIMESTAMP
                """,
                (
                    int(user_id),
                    str(email),
                    str(token),
                ),
            )

            conn.commit()

        finally:
            conn.close()


def get_mailbox(user_id):
    with _db_lock:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT email, token, created_at
                FROM mailboxes
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            if not row:
                return None

            return {
                "email": row["email"],
                "token": row["token"],
                "created_at": row["created_at"],
            }

        finally:
            conn.close()


# ============================================================
# EMAIL / CODE REWARD
# ============================================================

def add_email_reward_once(
    user_id,
    reward_key=None,
    code=None,
    amount=0,
    message_key=None,
):
    """
    Add an email/code reward only once per user + reward_key.

    Supports both:
        add_email_reward_once(user_id, reward_key, amount)
    and:
        add_email_reward_once(
            user_id=user_id,
            message_key=message_key,
            code=code,
            amount=amount,
        )

    Returns:
        (added: bool, new_balance: Decimal)
    """

    user_id = int(user_id)

    if reward_key is None:
        reward_key = message_key

    if not reward_key:
        return False, get_balance(user_id)

    reward_key = str(reward_key).strip()

    with _db_lock:
        conn = get_connection()
        try:
            _ensure_user(conn, user_id)

            exists = conn.execute(
                """
                SELECT id
                FROM email_rewards
                WHERE user_id = ? AND reward_key = ?
                """,
                (user_id, reward_key),
            ).fetchone()

            if exists:
                return False, _balance(conn, user_id)

            reward_amount = _to_decimal(amount)

            conn.execute(
                """
                INSERT INTO email_rewards
                    (user_id, reward_key, code, amount)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    reward_key,
                    None if code is None else str(code),
                    str(reward_amount),
                ),
            )

            new_balance = _add_balance(
                conn,
                user_id,
                reward_amount,
            )

            conn.commit()

            return True, new_balance

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()


def get_reward_count(user_id):
    with _db_lock:
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

            return int(row["total"] if row else 0)

        finally:
            conn.close()


# ============================================================
# REFERRAL
# ============================================================

def set_referrer(user_id, referrer_id):
    user_id = int(user_id)
    referrer_id = int(referrer_id)

    if user_id == referrer_id:
        return False

    with _db_lock:
        conn = get_connection()
        try:
            _ensure_user(conn, user_id)
            _ensure_user(conn, referrer_id)

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

            # A referrer can only be set once.
            if row["referrer_id"] is not None:
                return False

            conn.execute(
                """
                UPDATE users
                SET referrer_id = ?
                WHERE user_id = ?
                """,
                (referrer_id, user_id),
            )

            conn.commit()
            return True

        finally:
            conn.close()


def get_referrer(user_id):
    with _db_lock:
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

            if not row or row["referrer_id"] is None:
                return None

            return int(row["referrer_id"])

        finally:
            conn.close()


def get_referral_count(user_id):
    with _db_lock:
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

            return int(row["total"] if row else 0)

        finally:
            conn.close()


def add_referral_once(
    referrer_id,
    referred_id,
    amount,
):
    """
    Give referral reward exactly once for a referred user.

    Returns:
        (added: bool, new_balance: Decimal)
    """

    referrer_id = int(referrer_id)
    referred_id = int(referred_id)

    if referrer_id == referred_id:
        return False, get_balance(referrer_id)

    with _db_lock:
        conn = get_connection()
        try:
            _ensure_user(conn, referrer_id)
            _ensure_user(conn, referred_id)

            exists = conn.execute(
                """
                SELECT id
                FROM referrals
                WHERE referred_id = ?
                """,
                (referred_id,),
            ).fetchone()

            if exists:
                return False, _balance(conn, referrer_id)

            reward_amount = _to_decimal(amount)

            conn.execute(
                """
                INSERT INTO referrals
                    (referrer_id, referred_id, amount)
                VALUES (?, ?, ?)
                """,
                (
                    referrer_id,
                    referred_id,
                    str(reward_amount),
                ),
            )

            new_balance = _add_balance(
                conn,
                referrer_id,
                reward_amount,
            )

            conn.commit()

            return True, new_balance

        except Exception:
            conn.rollback()
            raise

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
    Atomically checks balance, creates a withdrawal request,
    and deducts the requested amount.

    Returns:
        withdrawal ID on success
        None on insufficient balance / invalid request
    """

    user_id = int(user_id)
    amount = _to_decimal(amount)

    if amount <= Decimal("0"):
        return None

    if not binance_id:
        return None

    with _db_lock:
        conn = get_connection()
        try:
            _ensure_user(conn, user_id)

            current = _balance(conn, user_id)

            if amount > current:
                return None

            cursor = conn.execute(
                """
                INSERT INTO withdrawals
                    (user_id, binance_id, amount, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (
                    user_id,
                    str(binance_id).strip(),
                    str(amount),
                ),
            )

            new_balance = current - amount

            conn.execute(
                """
                UPDATE users
                SET balance = ?
                WHERE user_id = ?
                """,
                (
                    str(new_balance),
                    user_id,
                ),
            )

            conn.commit()

            return int(cursor.lastrowid)

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()


# ============================================================
# OPTIONAL ADMIN / DEBUG HELPERS
# ============================================================

def get_withdrawal(withdrawal_id):
    with _db_lock:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    id,
                    user_id,
                    binance_id,
                    amount,
                    status,
                    created_at
                FROM withdrawals
                WHERE id = ?
                """,
                (int(withdrawal_id),),
            ).fetchone()

            if not row:
                return None

            return dict(row)

        finally:
            conn.close()


def get_pending_withdrawals():
    with _db_lock:
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
                WHERE status = 'pending'
                ORDER BY id ASC
                """
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()


# ============================================================
# AUTO INIT
# ============================================================

# This makes the database ready even if another module imports
# database.py before bot.main() calls init_db().
init_db()
