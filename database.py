# ============================================================
# database.py
# TEMP MAIL TELEGRAM BOT DATABASE
# ============================================================

import sqlite3
import threading
from decimal import Decimal


# ============================================================
# SETTINGS
# ============================================================

DB_NAME = "temp_mail_bot.db"

_db_lock = threading.RLock()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        DB_NAME,
        timeout=30,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    # Foreign key support
    conn.execute("PRAGMA foreign_keys = ON")

    # Better SQLite performance
    conn.execute("PRAGMA journal_mode = WAL")

    return conn


# ============================================================
# INIT DATABASE
# ============================================================

def init_db():
    with _db_lock:
        conn = get_connection()

        try:
            cursor = conn.cursor()

            # ------------------------------------------------
            # USERS
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT DEFAULT NULL,
                    balance TEXT NOT NULL DEFAULT '0',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ------------------------------------------------
            # MAILBOXES
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mailboxes (
                    user_id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
                )
            """)

            # ------------------------------------------------
            # EMAIL REWARDS
            #
            # One message_key can only reward once for a user.
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    user_id INTEGER NOT NULL,
                    message_key TEXT NOT NULL,
                    code TEXT,
                    amount TEXT NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(user_id, message_key),

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
                )
            """)

            # ------------------------------------------------
            # REFERRALS
            #
            # A referred user can only be rewarded once.
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    amount TEXT NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(referred_id),

                    FOREIGN KEY (referrer_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

                    FOREIGN KEY (referred_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
                )
            """)

            # ------------------------------------------------
            # WITHDRAWALS
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    user_id INTEGER NOT NULL,
                    binance_id TEXT NOT NULL,
                    amount TEXT NOT NULL,

                    status TEXT NOT NULL DEFAULT 'pending',

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
                )
            """)

            # ------------------------------------------------
            # REFERRER
            #
            # Stores who referred each user.
            # ------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_referrers (
                    user_id INTEGER PRIMARY KEY,
                    referrer_id INTEGER NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
                )
            """)

            conn.commit()

        finally:
            conn.close()


# ============================================================
# USER
# ============================================================

def save_user(user_id, username=None):
    """
    Create user if not exists.
    If user already exists, update username.
    """

    with _db_lock:
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
                    username = excluded.username
                """,
                (
                    int(user_id),
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
    with _db_lock:
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

    with _db_lock:
        conn = get_connection()

        try:
            conn.execute(
                """
                UPDATE users
                SET language = ?
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
    """
    Save/update the current mailbox for user.
    """

    save_user(user_id)

    with _db_lock:
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
                SELECT
                    user_id,
                    email,
                    token,
                    created_at
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
# ALL USERS
# ============================================================

def get_all_users():
    with _db_lock:
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
# BALANCE HELPERS
# ============================================================

def get_balance(user_id):
    save_user(user_id)

    with _db_lock:
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
                return Decimal("0")

            try:
                return Decimal(str(row["balance"]))

            except Exception:
                return Decimal("0")

        finally:
            conn.close()


def _get_balance_decimal(conn, user_id):
    row = conn.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id = ?
        """,
        (int(user_id),),
    ).fetchone()

    if not row:
        return Decimal("0")

    try:
        return Decimal(str(row["balance"]))

    except Exception:
        return Decimal("0")


def _set_balance(conn, user_id, amount):
    conn.execute(
        """
        UPDATE users
        SET balance = ?
        WHERE user_id = ?
        """,
        (
            str(Decimal(amount)),
            int(user_id),
        ),
    )


def add_balance(user_id, amount):
    """
    Generic balance addition.
    """

    save_user(user_id)

    amount = Decimal(str(amount))

    with _db_lock:
        conn = get_connection()

        try:
            current = _get_balance_decimal(
                conn,
                user_id,
            )

            new_balance = current + amount

            _set_balance(
                conn,
                user_id,
                new_balance,
            )

            conn.commit()

            return new_balance

        finally:
            conn.close()


# ============================================================
# EMAIL CODE REWARD
# ============================================================

def add_email_reward_once(
    user_id,
    message_key,
    code,
    amount,
):
    """
    Add email verification-code reward ONLY ONCE.

    If the same user + message_key already received reward,
    nothing is added.

    Returns:
        (added, new_balance)
    """

    save_user(user_id)

    amount = Decimal(str(amount))

    message_key = str(message_key)

    with _db_lock:
        conn = get_connection()

        try:
            # ------------------------------------------------
            # Check duplicate first
            # ------------------------------------------------

            existing = conn.execute(
                """
                SELECT id
                FROM email_rewards
                WHERE user_id = ?
                  AND message_key = ?
                LIMIT 1
                """,
                (
                    int(user_id),
                    message_key,
                ),
            ).fetchone()

            if existing:
                current = _get_balance_decimal(
                    conn,
                    user_id,
                )

                return False, current

            # ------------------------------------------------
            # Current balance
            # ------------------------------------------------

            current = _get_balance_decimal(
                conn,
                user_id,
            )

            new_balance = current + amount

            # ------------------------------------------------
            # Insert reward record
            # ------------------------------------------------

            try:
                conn.execute(
                    """
                    INSERT INTO email_rewards (
                        user_id,
                        message_key,
                        code,
                        amount
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        int(user_id),
                        message_key,
                        str(code),
                        str(amount),
                    ),
                )

            except sqlite3.IntegrityError:
                # Another request inserted it first.
                current = _get_balance_decimal(
                    conn,
                    user_id,
                )

                conn.rollback()

                return False, current

            # ------------------------------------------------
            # Add balance
            # ------------------------------------------------

            _set_balance(
                conn,
                user_id,
                new_balance,
            )

            conn.commit()

            return True, new_balance

        finally:
            conn.close()


# ============================================================
# EMAIL REWARD COUNT
# ============================================================

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

            return int(row["total"] or 0)

        finally:
            conn.close()


# ============================================================
# REFERRER
# ============================================================

def set_referrer(user_id, referrer_id):
    """
    Set referrer only once.

    Returns:
        True  -> referrer successfully saved
        False -> already has referrer / invalid
    """

    save_user(user_id)
    save_user(referrer_id)

    user_id = int(user_id)
    referrer_id = int(referrer_id)

    if user_id == referrer_id:
        return False

    with _db_lock:
        conn = get_connection()

        try:
            existing = conn.execute(
                """
                SELECT referrer_id
                FROM user_referrers
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if existing:
                return False

            # ------------------------------------------------
            # Save only once
            # ------------------------------------------------

            try:
                conn.execute(
                    """
                    INSERT INTO user_referrers (
                        user_id,
                        referrer_id
                    )
                    VALUES (?, ?)
                    """,
                    (
                        user_id,
                        referrer_id,
                    ),
                )

            except sqlite3.IntegrityError:
                conn.rollback()
                return False

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
                FROM user_referrers
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchone()

            if not row:
                return None

            return int(row["referrer_id"])

        finally:
            conn.close()


# ============================================================
# REFERRAL REWARD
# ============================================================

def add_referral_once(
    referrer_id,
    referred_id,
    amount,
):
    """
    Add referral reward only once.

    The same referred user can never generate
    referral reward twice.

    Returns:
        (added, new_balance)
    """

    save_user(referrer_id)
    save_user(referred_id)

    referrer_id = int(referrer_id)
    referred_id = int(referred_id)

    amount = Decimal(str(amount))

    if referrer_id == referred_id:
        return False, get_balance(referrer_id)

    with _db_lock:
        conn = get_connection()

        try:
            # ------------------------------------------------
            # Check existing referral
            # ------------------------------------------------

            existing = conn.execute(
                """
                SELECT id
                FROM referrals
                WHERE referred_id = ?
                LIMIT 1
                """,
                (referred_id,),
            ).fetchone()

            if existing:
                current = _get_balance_decimal(
                    conn,
                    referrer_id,
                )

                return False, current

            current = _get_balance_decimal(
                conn,
                referrer_id,
            )

            new_balance = current + amount

            # ------------------------------------------------
            # Insert referral
            # ------------------------------------------------

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
                        str(amount),
                    ),
                )

            except sqlite3.IntegrityError:
                current = _get_balance_decimal(
                    conn,
                    referrer_id,
                )

                conn.rollback()

                return False, current

            # ------------------------------------------------
            # Add reward
            # ------------------------------------------------

            _set_balance(
                conn,
                referrer_id,
                new_balance,
            )

            conn.commit()

            return True, new_balance

        finally:
            conn.close()


# ============================================================
# REFERRAL COUNT
# ============================================================

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
    Create withdrawal and deduct balance ATOMICALLY.

    Important:
    - Minimum withdrawal is $1.00
    - Balance must be sufficient
    - Balance is deducted before transaction commits
    - If anything fails, balance remains unchanged

    Returns:
        withdrawal_id
        OR None on failure
    """

    save_user(user_id)

    user_id = int(user_id)

    amount = Decimal(str(amount))

    if amount < Decimal("1.00"):
        return None

    if amount <= Decimal("0"):
        return None

    binance_id = str(binance_id).strip()

    if not binance_id:
        return None

    if len(binance_id) > 100:
        return None

    with _db_lock:
        conn = get_connection()

        try:
            # ------------------------------------------------
            # BEGIN TRANSACTION
            # ------------------------------------------------

            conn.execute("BEGIN IMMEDIATE")

            current = _get_balance_decimal(
                conn,
                user_id,
            )

            # ------------------------------------------------
            # Insufficient balance
            # ------------------------------------------------

            if current < amount:
                conn.rollback()
                return None

            # ------------------------------------------------
            # Calculate remaining balance
            # ------------------------------------------------

            remaining = current - amount

            # ------------------------------------------------
            # Deduct balance FIRST
            # ------------------------------------------------

            _set_balance(
                conn,
                user_id,
                remaining,
            )

            # ------------------------------------------------
            # Create withdrawal record
            # ------------------------------------------------

            cursor = conn.execute(
                """
                INSERT INTO withdrawals (
                    user_id,
                    binance_id,
                    amount,
                    status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    binance_id,
                    str(amount),
                    "pending",
                ),
            )

            withdrawal_id = cursor.lastrowid

            # ------------------------------------------------
            # Commit everything together
            # ------------------------------------------------

            conn.commit()

            return int(withdrawal_id)

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

            return None

        finally:
            conn.close()


# ============================================================
# OPTIONAL: GET WITHDRAWAL
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


# ============================================================
# OPTIONAL: GET USER WITHDRAWALS
# ============================================================

def get_user_withdrawals(user_id):
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
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (int(user_id),),
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

        finally:
            conn.close()


# ============================================================
# OPTIONAL: UPDATE WITHDRAWAL STATUS
# ============================================================

def update_withdrawal_status(
    withdrawal_id,
    status,
):
    """
    Example status:
        pending
        approved
        rejected
        paid

    Note:
    This function does NOT automatically refund a rejected
    withdrawal. If you want rejection refund logic, handle it
    separately.
    """

    allowed = {
        "pending",
        "approved",
        "rejected",
        "paid",
    }

    status = str(status).lower().strip()

    if status not in allowed:
        return False

    with _db_lock:
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
                    int(withdrawal_id),
                ),
            )

            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()


# ============================================================
# DATABASE READY
# ============================================================

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized successfully.")
    print(f"📁 Database file: {DB_NAME}")
