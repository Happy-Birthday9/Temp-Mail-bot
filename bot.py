# ============================================================
# bot.py
# TEMP MAIL TELEGRAM BOT
#
# - Temporary mailbox
# - Auto inbox polling
# - OTP/code detection
# - Email rewards
# - Referral rewards + notification
# - Withdraw: Binance ID / BEP20
# - Minimum withdrawal: $1.00
# - Admin approve/reject withdrawal
# ============================================================

import asyncio
import html
import json
import logging
import re
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, ADMIN_IDS
from database import (
    init_db,
    save_user,
    get_language,
    set_language,
    save_mailbox,
    get_mailbox,
    get_all_users,
)

# ============================================================
# SETTINGS
# ============================================================

API_BASE = "https://smails.dev/api"

POLL_SECONDS = 1
MAX_MESSAGES = 3

EMAIL_REWARD = 1
REFERRAL_REWARD = 0.00158

MIN_WITHDRAW = 1.00

DHAKA_TZ = ZoneInfo("Asia/Dhaka")
REWARD_DB = "rewards.db"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SEEN_MESSAGES = {}
KNOWN_MAILBOX = {}

# ============================================================
# REWARD DATABASE
# ============================================================

def reward_db():
    conn = sqlite3.connect(REWARD_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_reward_db():
    conn = reward_db()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS reward_users (
            user_id INTEGER PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            total_referrals INTEGER NOT NULL DEFAULT 0,
            total_email_rewards INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rewarded_messages (  
            user_id INTEGER NOT NULL,  
            message_id TEXT NOT NULL,  
            code TEXT,  
            amount REAL NOT NULL,  
            created_at TEXT NOT NULL,  
            PRIMARY KEY (user_id, message_id)  
        );  

        CREATE TABLE IF NOT EXISTS referrals (  
            referred_user_id INTEGER PRIMARY KEY,  
            referrer_user_id INTEGER NOT NULL,  
            reward REAL NOT NULL,  
            created_at TEXT NOT NULL  
        );  

        CREATE TABLE IF NOT EXISTS withdraw_requests (  
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            user_id INTEGER NOT NULL,  
            method TEXT NOT NULL,  
            destination TEXT NOT NULL,  
            amount REAL NOT NULL,  
            status TEXT NOT NULL DEFAULT 'PENDING',  
            created_at TEXT NOT NULL,  
            processed_at TEXT  
        );  
        """)
        conn.commit()
    finally:
        conn.close()


def ensure_reward_user(user_id):
    conn = reward_db()
    try:
        row = conn.execute(
            "SELECT user_id FROM reward_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if not row:
            conn.execute(
                """
                INSERT INTO reward_users
                (user_id, balance, referral_code, created_at)
                VALUES (?, 0, ?, ?)
                """,
                (
                    user_id,
                    str(user_id),
                    datetime.now(DHAKA_TZ).isoformat(),
                ),
            )
            conn.commit()
    finally:
        conn.close()


def get_balance(user_id):
    ensure_reward_user(user_id)
    conn = reward_db()
    try:
        row = conn.execute(
            "SELECT balance FROM reward_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return float(row["balance"]) if row else 0.0
    finally:
        conn.close()


def get_total_referrals(user_id):
    ensure_reward_user(user_id)
    conn = reward_db()
    try:
        row = conn.execute(
            "SELECT total_referrals FROM reward_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["total_referrals"]) if row else 0
    finally:
        conn.close()


def add_email_reward(user_id, message_id, code):
    ensure_reward_user(user_id)

    conn = reward_db()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO rewarded_messages
            (user_id, message_id, code, amount, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                str(message_id),
                str(code) if code else None,
                EMAIL_REWARD,
                datetime.now(DHAKA_TZ).isoformat(),
            ),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return False

        conn.execute(
            """
            UPDATE reward_users
            SET balance = balance + ?,
                total_email_rewards = total_email_rewards + 1
            WHERE user_id = ?
            """,
            (EMAIL_REWARD, user_id),
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def create_referral(referrer_id, referred_user_id):
    if not referrer_id or not referred_user_id:
        return False

    if int(referrer_id) == int(referred_user_id):
        return False

    ensure_reward_user(referrer_id)
    ensure_reward_user(referred_user_id)

    conn = reward_db()
    try:
        existing = conn.execute(
            """
            SELECT referred_user_id
            FROM referrals
            WHERE referred_user_id = ?
            """,
            (referred_user_id,),
        ).fetchone()

        if existing:
            return False

        row = conn.execute(
            """
            SELECT referred_by
            FROM reward_users
            WHERE user_id = ?
            """,
            (referred_user_id,),
        ).fetchone()

        if row and row["referred_by"]:
            return False

        conn.execute(
            """
            INSERT INTO referrals
            (referred_user_id, referrer_user_id, reward, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                referred_user_id,
                referrer_id,
                REFERRAL_REWARD,
                datetime.now(DHAKA_TZ).isoformat(),
            ),
        )

        conn.execute(
            """
            UPDATE reward_users
            SET referred_by = ?
            WHERE user_id = ?
            """,
            (referrer_id, referred_user_id),
        )

        conn.execute(
            """
            UPDATE reward_users
            SET balance = balance + ?,
                total_referrals = total_referrals + 1
            WHERE user_id = ?
            """,
            (REFERRAL_REWARD, referrer_id),
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

# ============================================================
# WITHDRAW DATABASE
# ============================================================

def create_withdraw_request(user_id, method, destination, amount):
    """
    Creates a pending withdrawal and deducts the amount atomically.
    Balance becomes 0 when the full balance is withdrawn.
    """
    ensure_reward_user(user_id)

    amount = float(amount)

    conn = reward_db()
    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT balance
            FROM reward_users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        balance = float(row["balance"]) if row else 0.0

        if balance < MIN_WITHDRAW:
            conn.rollback()
            return None, "MINIMUM"

        if amount <= 0 or amount > balance:
            conn.rollback()
            return None, "BALANCE"

        cursor = conn.execute(
            """
            INSERT INTO withdraw_requests
            (user_id, method, destination, amount, status, created_at)
            VALUES (?, ?, ?, ?, 'PENDING', ?)
            """,
            (
                user_id,
                str(method),
                str(destination),
                amount,
                datetime.now(DHAKA_TZ).isoformat(),
            ),
        )

        request_id = cursor.lastrowid

        conn.execute(
            """
            UPDATE reward_users
            SET balance = balance - ?
            WHERE user_id = ?
            """,
            (amount, user_id),
        )

        conn.commit()
        return request_id, "OK"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_withdraw_request(request_id):
    conn = reward_db()
    try:
        return conn.execute(
            """
            SELECT *
            FROM withdraw_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()
    finally:
        conn.close()


def update_withdraw_status(request_id, status):
    conn = reward_db()
    try:
        cursor = conn.execute(
            """
            UPDATE withdraw_requests
            SET status = ?,
                processed_at = ?
            WHERE id = ?
              AND status = 'PENDING'
            """,
            (
                status,
                datetime.now(DHAKA_TZ).isoformat(),
                request_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def refund_withdraw(request_id):
    """
    Used only when an admin rejects a request.
    The withdrawn amount is returned to the user's balance.
    """
    conn = reward_db()
    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT user_id, amount, status
            FROM withdraw_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()

        if not row or row["status"] != "PENDING":
            conn.rollback()
            return False

        conn.execute(
            """
            UPDATE reward_users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (float(row["amount"]), int(row["user_id"])),
        )

        conn.execute(
            """
            UPDATE withdraw_requests
            SET status = 'REJECTED',
                processed_at = ?
            WHERE id = ?
              AND status = 'PENDING'
            """,
            (
                datetime.now(DHAKA_TZ).isoformat(),
                request_id,
            ),
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

# ============================================================
# LANGUAGES
# ============================================================

TEXT = {
    "en": {
        "welcome": "📧 <b>TEMP MAIL BOT</b>\n\n👋 Welcome!\n\n⚡ Fast temporary email receiver\n📩 Receive verification emails\n🔐 Codes are detected automatically.\n\n🌐 Select your language:",
        "language_ok": "✅ <b>Language selected!</b>\n\n⚡ Creating your temporary email...",
        "generating": "⚡ <b>Creating your temporary email...</b>",
        "created": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧  NEW TEMP EMAIL\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "📩 New emails will be detected automatically."
        ),
        "generate": "➕ Generate New",
        "inbox": "📥 Inbox",
        "refresh": "🔄 Refresh",
        "refer_btn": "👥 Refer System",
        "checking": "🔎 <b>Checking your inbox...</b>",
        "empty": "📭 <b>Inbox is empty.</b>\n\nNo messages received yet.",
        "no_mailbox": "⚠️ <b>No temporary email found.</b>\n\nPlease generate a new email first.",
        "api_error": "❌ <b>Something went wrong.</b>\n\nPlease try again later.",
        "new_mail": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📨 NEW EMAIL\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Dhaka Time:</b> {date}\n\n"
            "{content}"
        ),
        "earned": "💰 <b>You earned:</b> <code>{amount}</code>",
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": "🔐 <b>VERIFICATION CODE</b>\n\n🔢 <b>Code:</b> <code>{code}</code>",
        "copy_code": "📋 Copy Code",
        "language": "🌐 <b>Select your language:</b>",
        "help": "📚 <b>HELP</b>\n\n➕ Generate New — Create email\n📥 Inbox — View emails\n🔄 Refresh — Check emails\n👥 Refer System — Refer & earn\n💰 /balance — Check balance\n💸 /withdraw — Withdraw\n\n/start — Start\n/language — Language\n/inbox — Inbox\n/refresh — Refresh\n/help — Help\n/about — About\n/stats — Statistics",
        "about": "📧 <b>TEMP MAIL</b>\n\nFast disposable email receiver.\n\n⚡ Powered by Smails API\n🔒 No API key required",
        "stats": "📊 <b>BOT STATS</b>\n\n👥 Total Users: <b>{users}</b>\n📧 Active Mailboxes: <b>{mailboxes}</b>\n⚡ Auto Inbox: <b>ON</b>\n🔄 Polling: <b>{seconds}s</b>",
        "admin_only": "🔐 <b>ADMIN ONLY</b>\n\nThis command is available only for administrators.",
        "broadcast_start": "📢 <b>Broadcast Mode</b>\n\nUse:\n<code>/broadcast Your message</code>",
        "broadcast_done": "✅ <b>Broadcast completed!</b>\n\n📤 Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        "admin_panel": "👑 <b>ADMIN PANEL</b>\n\n🔐 You have administrator access.",
        "refer": "👥 <b>REFER & EARN</b>\n\n💰 Per successful referral: <b>{reward}</b>\n👥 Total referrals: <b>{refs}</b>\n\n🔗 <b>Your referral link:</b>\n<code>{link}</code>",
        "balance": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      💰 BALANCE\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 Balance: <b>{balance}</b>\n"
            "👥 Referrals: <b>{refs}</b>\n"
            "📩 Email rewards: <b>{email_reward}</b>\n\n"
            "💸 Minimum withdrawal: <b>${minimum:.2f}</b>"
        ),
        "withdraw_button": "💸 Withdraw",
        "withdraw_choose": "💸 <b>Withdraw</b>\n\nPlease select Withdraw method:",
        "withdraw_amount": "💵 <b>Withdraw Amount</b>\n\nYour balance: <b>${balance:.5f}</b>\n\nSend the amount you want to withdraw:",
        "withdraw_address": "📥 <b>{method}</b>\n\nSend your Binance ID or BEP20 address:",
        "withdraw_invalid": "⚠️ Invalid value. Please try again.",
        "withdraw_min": "⚠️ <b>Minimum withdrawal is $1.00.</b>\n\nYour current balance: <b>${balance:.5f}</b>",
        "withdraw_balance": "⚠️ <b>Insufficient balance.</b>\n\nYour current balance: <b>${balance:.5f}</b>",
        "withdraw_sent": "✅ <b>Withdrawal request submitted!</b>\n\n💵 Amount: <b>${amount:.5f}</b>\n💳 Method: <b>{method}</b>\n📥 Destination: <code>{destination}</code>\n\n⏳ Waiting for admin approval.",
        "withdraw_congratulations": "🎉 <b>Congratulations!</b>\n\nYour withdrawal of <b>${amount:.5f}</b> has been approved.\n\n💳 Method: <b>{method}</b>\n📥 Destination: <code>{destination}</code>",
        "withdraw_rejected": "❌ <b>Withdrawal Rejected</b>\n\nYour withdrawal request of <b>${amount:.5f}</b> was rejected.\n\n💰 The amount has been returned to your balance.",
        "admin_withdraw": "💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n🆔 Request ID: <code>#{request_id}</code>\n👤 User ID: <code>{user_id}</code>\n💵 Amount: <b>${amount:.5f}</b>\n💳 Method: <b>{method}</b>\n📥 Destination:\n<code>{destination}</code>\n\n🕐 {date}",
        "approve": "✅ Accept",
        "reject": "❌ Reject",
    },
    "bn": {
        "welcome": "📧 <b>TEMP MAIL BOT</b>\n\n👋 স্বাগতম!\n\n⚡ দ্রুত Temporary Email receiver\n📩 Verification Email গ্রহণ করুন\n🔐 Code automatically detect হবে।\n\n🌐 ভাষা নির্বাচন করুন:",
        "language_ok": "✅ <b>ভাষা নির্বাচন সফল!</b>\n\n⚡ Temporary Email তৈরি হচ্ছে...",
        "generating": "⚡ <b>Temporary Email তৈরি হচ্ছে...</b>",
        "created": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 নতুন TEMP EMAIL\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "📩 নতুন Email এলে Automatic দেখাবে।"
        ),
        "generate": "➕ নতুন তৈরি করুন",
        "inbox": "📥 ইনবক্স",
        "refresh": "🔄 রিফ্রেশ",
        "refer_btn": "👥 রেফার সিস্টেম",
        "checking": "🔎 <b>আপনার Inbox check করা হচ্ছে...</b>",
        "empty": "📭 <b>Inbox খালি।</b>\n\nএখনো কোনো Message আসেনি।",
        "no_mailbox": "⚠️ <b>কোনো Temporary Email পাওয়া যায়নি।</b>\n\nপ্রথমে নতুন Email তৈরি করুন।",
        "api_error": "❌ <b>সমস্যা হয়েছে।</b>\n\nকিছুক্ষণ পর আবার চেষ্টা করুন।",
        "new_mail": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📨 নতুন EMAIL\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>ঢাকা সময়:</b> {date}\n\n"
            "{content}"
        ),
        "earned": "💰 <b>আপনি পেয়েছেন:</b> <code>{amount}</code>",
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": "🔐 <b>VERIFICATION CODE</b>\n\n🔢 <b>Code:</b> <code>{code}</code>",
        "copy_code": "📋 Code Copy করুন",
        "language": "🌐 <b>আপনার ভাষা নির্বাচন করুন:</b>",
        "help": "📚 <b>HELP</b>\n\n➕ নতুন তৈরি করুন — নতুন Email\n📥 ইনবক্স — Email দেখুন\n🔄 রিফ্রেশ — নতুন Email check\n👥 রেফার সিস্টেম — Refer & earn\n💰 /balance — Balance\n💸 /withdraw — Withdraw\n\n/start — Start\n/language — ভাষা\n/inbox — Inbox\n/refresh — Refresh\n/help — Help\n/about — About\n/stats — Statistics",
        "about": "📧 <b>TEMP MAIL</b>\n\nদ্রুত Temporary Email receiver।\n\n⚡ Smails API দ্বারা পরিচালিত\n🔒 API key প্রয়োজন নেই",
        "stats": "📊 <b>BOT STATS</b>\n\n👥 Total Users: <b>{users}</b>\n📧 Active Mailboxes: <b>{mailboxes}</b>\n⚡ Auto Inbox: <b>ON</b>\n🔄 Checking: <b>{seconds}s</b>",
        "admin_only": "🔐 <b>ADMIN ONLY</b>\n\nএই Command শুধুমাত্র Administrator-এর জন্য।",
        "broadcast_start": "📢 <b>Broadcast Mode</b>\n\nব্যবহার করুন:\n<code>/broadcast আপনার Message</code>",
        "broadcast_done": "✅ <b>Broadcast সম্পন্ন!</b>\n\n📤 পাঠানো হয়েছে: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        "admin_panel": "👑 <b>ADMIN PANEL</b>\n\n🔐 আপনার Administrator access আছে।",
        "refer": "👥 <b>REFER & EARN</b>\n\n💰 প্রতি সফল Refer: <b>{reward}</b>\n👥 মোট Refer: <b>{refs}</b>\n\n🔗 <b>আপনার Referral Link:</b>\n<code>{link}</code>",
        "balance": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      💰 BALANCE\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 Balance: <b>{balance}</b>\n"
            "👥 Referrals: <b>{refs}</b>\n"
            "📩 Email rewards: <b>{email_reward}</b>\n\n"
            "💸 Minimum withdrawal: <b>${minimum:.2f}</b>"
        ),
        "withdraw_button": "💸 Withdraw",
        "withdraw_choose": "💸 <b>Withdraw</b>\n\nPlease selected Withdraw method:",
        "withdraw_amount": "💵 <b>Withdraw Amount</b>\n\nআপনার Balance: <b>${balance:.5f}</b>\n\nযত টাকা Withdraw করবেন amount পাঠান:",
        "withdraw_address": "📥 <b>{method}</b>\n\nআপনার Binance ID অথবা BEP20 address পাঠান:",
        "withdraw_invalid": "⚠️ সঠিক তথ্য দিন। আবার চেষ্টা করুন।",
        "withdraw_min": "⚠️ <b>Minimum withdrawal $1.00.</b>\n\nআপনার বর্তমান Balance: <b>${balance:.5f}</b>",
        "withdraw_balance": "⚠️ <b>Balance পর্যাপ্ত নয়।</b>\n\nআপনার বর্তমান Balance: <b>${balance:.5f}</b>",
        "withdraw_sent": "✅ <b>Withdrawal request পাঠানো হয়েছে!</b>\n\n💵 Amount: <b>${amount:.5f}</b>\n💳 Method: <b>{method}</b>\n📥 Destination: <code>{destination}</code>\n\n⏳ Admin approval-এর অপেক্ষায়।",
        "withdraw_congratulations": "🎉 <b>Congratulations!</b>\n\nআপনার <b>${amount:.5f}</b> Withdrawal approved হয়েছে।\n\n💳 Method: <b>{method}</b>\n📥 Destination: <code>{destination}</code>",
        "withdraw_rejected": "❌ <b>Withdrawal Rejected</b>\n\nআপনার <b>${amount:.5f}</b> Withdrawal reject হয়েছে।\n\n💰 Amount আপনার Balance-এ ফেরত দেওয়া হয়েছে।",
        "admin_withdraw": "💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n🆔 Request ID: <code>#{request_id}</code>\n👤 User ID: <code>{user_id}</code>\n💵 Amount: <b>${amount:.5f}</b>\n💳 Method: <b>{method}</b>\n📥 Destination:\n<code>{destination}</code>\n\n🕐 {date}",
        "approve": "✅ Accept",
        "reject": "❌ Reject",
    },
    "hi": {
        "welcome": "📧 <b>TEMP MAIL BOT</b>\n\n👋 Swagat hai!\n\n⚡ Fast temporary email receiver\n📩 Verification emails receive karein\n🔐 Code automatically detect hoga.\n\n🌐 Language select karein:",
        "language_ok": "✅ <b>Language selected!</b>\n\n⚡ Temporary Email create ho raha hai...",
        "generating": "⚡ <b>Temporary Email create ho raha hai...</b>",
        "created": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 NEW TEMP EMAIL\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "📩 New emails automatically dikhenge."
        ),
        "generate": "➕ Naya Generate",
        "inbox": "📥 Inbox",
        "refresh": "🔄 Refresh",
        "refer_btn": "👥 Refer System",
        "checking": "🔎 <b>Inbox check ho raha hai...</b>",
        "empty": "📭 <b>Inbox empty hai.</b>",
        "no_mailbox": "⚠️ <b>Koi Temporary Email nahi mila.</b>\n\nPehle naya Email generate karein.",
        "api_error": "❌ <b>Kuch problem ho gayi.</b>\n\nBaad mein try karein.",
        "new_mail": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📨 NEW EMAIL\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Dhaka Time:</b> {date}\n\n"
            "{content}"
        ),
        "earned": "💰 <b>You earned:</b> <code>{amount}</code>",
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": "🔐 <b>VERIFICATION CODE</b>\n\n🔢 <b>Code:</b> <code>{code}</code>",
        "copy_code": "📋 Copy Code",
        "language": "🌐 <b>Language select karein:</b>",
        "help": "📚 <b>HELP</b>\n\n➕ Naya Generate — Email\n📥 Inbox — Emails\n🔄 Refresh — Check\n👥 Refer System — Refer & earn\n💰 /balance — Balance\n💸 /withdraw — Withdraw\n\n/start /language /inbox /refresh /help /about /stats",
        "about": "📧 <b>TEMP MAIL</b>\n\nFast Temporary Email receiver.\n\n⚡ Smails API se powered",
        "stats": "📊 <b>BOT STATS</b>\n\n👥 Total Users: <b>{users}</b>\n📧 Active Mailboxes: <b>{mailboxes}</b>\n⚡ Auto Inbox: <b>ON</b>\n🔄 Checking: <b>{seconds}s</b>",
        "admin_only": "🔐 <b>ADMIN ONLY</b>\n\nYeh command sirf administrator ke liye hai.",
        "broadcast_start": "📢 <b>Broadcast Mode</b>\n\nUse: <code>/broadcast Your message</code>",
        "broadcast_done": "✅ <b>Broadcast completed!</b>\n\n📤 Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        "admin_panel": "👑 <b>ADMIN PANEL</b>\n\n🔐 Administrator access active.",
        "refer": "👥 <b>REFER & EARN</b>\n\n💰 Per successful referral: <b>{reward}</b>\n👥 Total referrals: <b>{refs}</b>\n\n🔗 <b>Your referral link:</b>\n<code>{link}</code>",
        "balance": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      💰 BALANCE\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 Balance: <b>{balance}</b>\n"
            "👥 Referrals: <b>{refs}</b>\n"
            "📩 Email rewards: <b>{email_reward}</b>\n\n"
            "💸 Minimum withdrawal: <b>${minimum:.2f}</b>"
        ),
        "withdraw_button": "💸 Withdraw",
        "withdraw_choose": "💸 <b>Withdraw</b>\n\nPlease select Withdraw method:",
        "withdraw_amount": "💵 <b>Withdraw Amount</b>\n\nYour balance: <b>${balance:.5f}</b>\n\nSend withdrawal amount:",
        "withdraw_address": "📥 <b>{method}</b>\n\nSend Binance ID or BEP20 address:",
        "withdraw_invalid": "⚠️ Invalid value. Please try again.",
        "withdraw_min": "⚠️ <b>Minimum withdrawal is $1.00.</b>\n\nCurrent balance: <b>${balance:.5f}</b>",
        "withdraw_balance": "⚠️ <b>Insufficient balance.</b>\n\nCurrent balance: <b>${balance:.5f}</b>",
        "withdraw_sent": "✅ <b>Withdrawal request submitted!</b>\n\n💵 Amount: <b>${amount:.5f}</b>\n💳 Method: <b>{method}</b>\n📥 Destination: <code>{destination}</code>\n\n⏳ Waiting for admin approval.",
        "withdraw_congratulations": "🎉 <b>Congratulations!</b>\n\nYour withdrawal of <b>${amount:.5f}</b> has been approved.\n\n💳 Method: <b>{method}</b>\n📥 Destination: <code>{destination}</code>",
        "withdraw_rejected": "❌ <b>Withdrawal Rejected</b>\n\nYour withdrawal of <b>${amount:.5f}</b> was rejected.\n\n💰 Amount returned to your balance.",
        "admin_withdraw": "💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n🆔 Request ID: <code>#{request_id}</code>\n👤 User ID: <code>{user_id}</code>\n💵 Amount: <b>${amount:.5f}</b>\n💳 Method: <b>{method}</b>\n📥 Destination:\n<code>{destination}</code>\n\n🕐 {date}",
        "approve": "✅ Accept",
        "reject": "❌ Reject",
    },
}

# ============================================================
# KEYBOARDS
# ============================================================

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn")],
        [InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_hi")],
    ])


def main_keyboard(lang):
    t = TEXT[lang]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t["generate"], callback_data="generate"),
            InlineKeyboardButton(t["inbox"], callback_data="inbox"),
        ],
        [InlineKeyboardButton(t["refresh"], callback_data="refresh")],
    ])


def reply_main_keyboard(lang):
    t = TEXT[lang]
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t["generate"]), KeyboardButton(t["inbox"])],
            [KeyboardButton(t["refresh"]), KeyboardButton(t["refer_btn"])],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def code_keyboard(code, lang):
    t = TEXT[lang]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t["generate"], callback_data="generate"),
            InlineKeyboardButton(
                t["copy_code"],
                copy_text=CopyTextButton(text=str(code)),
            ),
        ],
        [InlineKeyboardButton(t["refresh"], callback_data="refresh")],
    ])


def balance_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            TEXT[lang]["withdraw_button"],
            callback_data="withdraw",
        )]
    ])


def withdraw_method_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆔 Binance ID", callback_data="withdraw_method_binance")],
        [InlineKeyboardButton("🔐 BEP20", callback_data="withdraw_method_bep20")],
    ])


def admin_withdraw_keyboard(request_id, lang="en"):
    t = TEXT[lang]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t["approve"],
                callback_data=f"withdraw_accept:{request_id}",
            ),
            InlineKeyboardButton(
                t["reject"],
                callback_data=f"withdraw_reject:{request_id}",
            ),
        ]
    ])

# ============================================================
# HELPERS
# ============================================================

def user_lang(user_id):
    try:
        lang = get_language(user_id)
    except Exception:
        lang = None
    return lang if lang in TEXT else "en"


def safe(value):
    if value is None:
        return ""
    return html.escape(str(value))


def is_admin(user_id):
    return user_id in ADMIN_IDS


def dhaka_time():
    return datetime.now(DHAKA_TZ).strftime("%d %b %Y, %I:%M:%S %p")

# ============================================================
# CODE DETECTION
# ============================================================

def extract_code(text):
    if not text:
        return None

    text = str(text)

    patterns = [
        r"(?:verification|verify|verification\s*code|verification\s*number|otp|one[\s-]*time[\s-]*password|login\s*code|security\s*code|confirmation\s*code)\D{0,40}(\d{4,8})",
        r"(?:code|pin)\D{0,20}(\d{4,8})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    for length in (6, 5, 4):
        match = re.search(
            rf"(?<!\d)\d{{{length}}}(?!\d)",
            text,
        )
        if match:
            return match.group(0)

    return None


def get_message_id(item):
    for value in (
        item.get("id"),
        item.get("messageId"),
        item.get("_id"),
        item.get("uid"),
    ):
        if value is not None:
            return str(value)

    raw = "|".join([
        str(item.get("subject", "")),
        str(item.get("date", "")),
        str(item.get("createdAt", "")),
        str(item.get("from", "")),
        str(item.get("intro", "")),
        str(item.get("text", "")),
        str(item.get("body", "")),
        str(item.get("content", "")),
    ])
    return raw

# ============================================================
# API
# ============================================================

async def api_request(method, endpoint, token=None):
    url = API_BASE + endpoint
    headers = {"Accept": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = aiohttp.ClientTimeout(
        total=10,
        connect=4,
        sock_read=7,
    )

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method,
                url,
                headers=headers,
            ) as response:

                if response.status >= 400:
                    body = await response.text()
                    logger.error(
                        "API HTTP %s: %s",
                        response.status,
                        body[:500],
                    )
                    return None

                content_type = response.headers.get("Content-Type", "")

                if "json" in content_type.lower():
                    return await response.json(content_type=None)

                text = await response.text()

                try:
                    return json.loads(text)
                except Exception:
                    logger.error(
                        "Invalid API JSON: %s",
                        text[:500],
                    )
                    return None

    except asyncio.TimeoutError:
        logger.warning("API timeout: %s", url)
        return None

    except Exception as error:
        logger.error("API error: %s", error)
        return None


async def create_mailbox():
    return await api_request("POST", "/mailbox")


async def get_messages(token):
    return await api_request(
        "GET",
        "/mailbox/messages",
        token,
    )

# ============================================================
# MESSAGE PARSING
# ============================================================

def extract_messages(data):
    if not data:
        return []

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    messages = data.get("messages")
    if isinstance(messages, list):
        return messages

    nested = data.get("data")

    if isinstance(nested, dict):
        messages = nested.get("messages")
        if isinstance(messages, list):
            return messages

    if isinstance(nested, list):
        return nested

    return []


def parse_sender(item):
    sender_data = (
        item.get("from")
        or item.get("sender")
        or item.get("senderAddress")
        or item.get("fromAddress")
        or ""
    )

    if isinstance(sender_data, dict):
        sender = (
            sender_data.get("address")
            or sender_data.get("email")
            or sender_data.get("mail")
            or sender_data.get("name")
            or ""
        )
    else:
        sender = str(sender_data)

    if not sender:
        sender = (
            item.get("fromEmail")
            or item.get("senderEmail")
            or item.get("email")
            or "Unknown"
        )

    return str(sender)


def parse_mail(item):
    sender = parse_sender(item)
    subject = item.get("subject") or "(No Subject)"

    body = (
        item.get("text")
        or item.get("body")
        or item.get("intro")
        or item.get("content")
        or item.get("html")
        or ""
    )

    if isinstance(body, dict):
        body = (
            body.get("text")
            or body.get("plain")
            or body.get("content")
            or ""
        )

    return str(sender), str(subject), str(body)

# ============================================================
# BUILD EMAIL MESSAGE
# ============================================================

def build_mail_message(item, lang, reward_added):
    t = TEXT[lang]

    sender, subject, body = parse_mail(item)

    code = extract_code(
        f"{subject}\n{body}"
    )

    if code:
        amount = EMAIL_REWARD if reward_added else 0.0

        content = (
            t["verification"].format(code=safe(code))
            + "\n\n"
            + t["earned"].format(
                amount=f"{amount:.5f}"
            )
        )

        keyboard = code_keyboard(code, lang)

    else:
        content = t["message_content"].format(
            body=safe(body[:1500])
        )
        keyboard = main_keyboard(lang)

    message_text = t["new_mail"].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(dhaka_time()),
        content=content,
    )

    return message_text, keyboard, code

# ============================================================
# SEND EMAIL
# ============================================================

async def send_auto_mail(bot, user_id, item, lang):
    message_id = get_message_id(item)

    code = extract_code(
        f"{item.get('subject', '')}\n"
        f"{item.get('text', '')}\n"
        f"{item.get('body', '')}\n"
        f"{item.get('intro', '')}\n"
        f"{item.get('content', '')}"
    )

    reward_added = False

    if code and message_id:
        reward_added = add_email_reward(
            user_id,
            message_id,
            code,
        )

    message_text, keyboard, _ = build_mail_message(
        item,
        lang,
        reward_added,
    )

    await bot.send_message(
        chat_id=user_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def send_inbox_mail(bot, user_id, item, lang):
    message_id = get_message_id(item)

    code = extract_code(
        f"{item.get('subject', '')}\n"
        f"{item.get('text', '')}\n"
        f"{item.get('body', '')}\n"
        f"{item.get('intro', '')}\n"
        f"{item.get('content', '')}"
    )

    reward_added = False

    if code and message_id:
        reward_added = add_email_reward(
            user_id,
            message_id,
            code,
        )

    message_text, keyboard, _ = build_mail_message(
        item,
        lang,
        reward_added,
    )

    await bot.send_message(
        chat_id=user_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

# ============================================================
# GENERATE MAILBOX
# ============================================================

async def generate_new(message, user_id, lang):
    t = TEXT[lang]

    loading = await message.reply_text(
        t["generating"],
        parse_mode="HTML",
    )

    mailbox = await create_mailbox()

    if not mailbox:
        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML",
        )
        return False

    data = mailbox

    if isinstance(mailbox.get("data"), dict):
        data = mailbox["data"]

    email = (
        data.get("address")
        or data.get("email")
        or mailbox.get("address")
        or mailbox.get("email")
    )

    token = (
        data.get("token")
        or data.get("accessToken")
        or mailbox.get("token")
        or mailbox.get("accessToken")
    )

    if not email or not token:
        logger.error(
            "Mailbox response missing email/token: %s",
            mailbox,
        )
        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML",
        )
        return False

    save_mailbox(
        user_id,
        email,
        token,
    )

    SEEN_MESSAGES[user_id] = set()
    KNOWN_MAILBOX[user_id] = token

    ensure_reward_user(user_id)

    await loading.edit_text(
        t["created"].format(
            email=safe(email)
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML",
    )

    await message.reply_text(
        "📩 Receive Codes & Earn Rewards! 💰",
        reply_markup=reply_main_keyboard(lang),
    )

    return True

# ============================================================
# START / REFERRAL
# ============================================================

async def start(update, context):
    user = update.effective_user

    if not user or not update.message:
        return

    user_id = user.id

    save_user(
        user_id,
        user.username,
    )

    ensure_reward_user(user_id)

    # Referral
    if context.args:
        try:
            referrer_id = int(
                str(context.args[0]).strip()
            )

            if referrer_id != user_id:
                referral_created = create_referral(
                    referrer_id,
                    user_id,
                )

                if referral_created:
                    try:
                        new_balance = get_balance(
                            referrer_id
                        )
                        total_refs = get_total_referrals(
                            referrer_id
                        )

                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=(
                                "🎉 <b>NEW REFERRAL!</b>\n\n"
                                "👤 New user joined!\n\n"
                                "💰 <b>Referral Bonus:</b>\n"
                                f"<code>+{REFERRAL_REWARD:.5f}</code>\n\n"
                                "💵 <b>Your Balance:</b>\n"
                                f"<code>{new_balance:.5f}</code>\n\n"
                                "👥 <b>Total Referrals:</b>\n"
                                f"<code>{total_refs}</code>\n\n"
                                "✅ Bonus has been added!"
                            ),
                            parse_mode="HTML",
                        )

                    except Exception as error:
                        logger.warning(
                            "Referral notification failed: %s",
                            error,
                        )

        except Exception as error:
            logger.warning(
                "Referral processing error: %s",
                error,
            )

    lang = get_language(user_id)

    if not lang:
        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML",
        )
        return

    lang = user_lang(user_id)

    mailbox = get_mailbox(user_id)

    if mailbox:
        await update.message.reply_text(
            TEXT[lang]["created"].format(
                email=safe(
                    mailbox.get("email", "")
                )
            ),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )

        await update.message.reply_text(
            "📩 Receive Codes & Earn Rewards! 💰",
            reply_markup=reply_main_keyboard(lang),
        )

    else:
        await generate_new(
            update.message,
            user_id,
            lang,
        )

# ============================================================
# INBOX
# ============================================================

async def show_inbox(message, user_id, lang):
    t = TEXT[lang]

    mailbox = get_mailbox(user_id)

    if not mailbox:
        await message.reply_text(
            t["no_mailbox"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )
        return

    loading = await message.reply_text(
        t["checking"],
        parse_mode="HTML",
    )

    data = await get_messages(
        mailbox.get("token")
    )

    if not data:
        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML",
        )
        return

    messages = extract_messages(data)

    if not messages:
        await loading.edit_text(
            t["empty"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )
        return

    try:
        await loading.delete()
    except Exception:
        pass

    messages = list(reversed(messages))

    for item in messages[:MAX_MESSAGES]:
        try:
            await send_inbox_mail(
                message.get_bot(),
                user_id,
                item,
                lang,
            )
        except Exception as error:
            logger.error(
                "Inbox message error: %s",
                error,
            )

# ============================================================
# COMMANDS
# ============================================================

async def refresh_command(update, context):
    user_id = update.effective_user.id
    await show_inbox(
        update.message,
        user_id,
        user_lang(user_id),
    )


async def inbox_command(update, context):
    user_id = update.effective_user.id
    await show_inbox(
        update.message,
        user_id,
        user_lang(user_id),
    )


async def language_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["language"],
        reply_markup=language_keyboard(),
        parse_mode="HTML",
    )


async def help_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["help"],
        reply_markup=main_keyboard(lang),
        parse_mode="HTML",
    )


async def about_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["about"],
        parse_mode="HTML",
    )

# ============================================================
# REFER
# ============================================================

async def refer_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    ensure_reward_user(user_id)

    try:
        bot_username = context.bot.username

        if not bot_username:
            me = await context.bot.get_me()
            bot_username = me.username

        link = (
            f"https://t.me/{bot_username}"
            f"?start={user_id}"
        )

        refs = get_total_referrals(user_id)

        await update.message.reply_text(
            TEXT[lang]["refer"].format(
                reward=f"{REFERRAL_REWARD:.5f}",
                refs=refs,
                link=safe(link),
            ),
            parse_mode="HTML",
        )

    except Exception as error:
        logger.error(
            "Refer error: %s",
            error,
        )
        await update.message.reply_text(
            TEXT[lang]["api_error"],
            parse_mode="HTML",
        )

# ============================================================
# BALANCE
# ============================================================

async def balance_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    balance = get_balance(user_id)
    refs = get_total_referrals(user_id)

    await update.message.reply_text(
        TEXT[lang]["balance"].format(
            balance=f"{balance:.5f}",
            refs=refs,
            email_reward=f"{EMAIL_REWARD:.5f}",
            minimum=MIN_WITHDRAW,
        ),
        reply_markup=balance_keyboard(lang),
        parse_mode="HTML",
    )

# ============================================================
# WITHDRAW
# ============================================================

async def withdraw_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    t = TEXT[lang]

    balance = get_balance(user_id)

    if balance < MIN_WITHDRAW:
        await update.message.reply_text(
            t["withdraw_min"].format(
                balance=balance
            ),
            parse_mode="HTML",
        )
        return

    context.user_data.pop("withdraw_method", None)
    context.user_data.pop("withdraw_amount", None)
    context.user_data.pop("waiting_withdraw_destination", None)

    await update.message.reply_text(
        t["withdraw_choose"],
        reply_markup=withdraw_method_keyboard(lang),
        parse_mode="HTML",
    )


async def withdraw_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    lang = user_lang(user_id)
    t = TEXT[lang]

    await query.answer()

    balance = get_balance(user_id)

    if balance < MIN_WITHDRAW:
        await query.message.reply_text(
            t["withdraw_min"].format(
                balance=balance
            ),
            parse_mode="HTML",
        )
        return

    await query.message.reply_text(
        t["withdraw_choose"],
        reply_markup=withdraw_method_keyboard(lang),
        parse_mode="HTML",
    )


async def choose_withdraw_method(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    lang = user_lang(user_id)
    t = TEXT[lang]

    await query.answer()

    balance = get_balance(user_id)

    if balance < MIN_WITHDRAW:
        await query.message.reply_text(
            t["withdraw_min"].format(
                balance=balance
            ),
            parse_mode="HTML",
        )
        return

    if query.data == "withdraw_method_binance":
        method = "Binance ID"
    else:
        method = "BEP20"

    # User's full balance will be withdrawn.
    context.user_data["withdraw_method"] = method
    context.user_data["withdraw_amount"] = balance
    context.user_data["waiting_withdraw_destination"] = True

    await query.message.reply_text(
        t["withdraw_address"].format(
            method=method
        ),
        parse_mode="HTML",
    )

# ============================================================
# SEND WITHDRAWAL REQUEST TO ADMIN
# ============================================================

async def notify_admins_about_withdraw(
    bot,
    request_id,
    user_id,
    method,
    destination,
    amount,
):
    admin_text = TEXT["en"]["admin_withdraw"].format(
        request_id=request_id,
        user_id=user_id,
        amount=amount,
        method=safe(method),
        destination=safe(destination),
        date=dhaka_time(),
    )

    keyboard = admin_withdraw_keyboard(
        request_id,
        "en",
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as error:
            logger.error(
                "Could not notify admin %s: %s",
                admin_id,
                error,
            )

# ============================================================
# TEXT HANDLER
# ============================================================

async def text_handler(update, context):
    user = update.effective_user

    if not user or not update.message:
        return

    user_id = user.id
    lang = user_lang(user_id)
    t = TEXT[lang]
    text = update.message.text.strip()

    # --------------------------------------------
    # WITHDRAW DESTINATION
    # --------------------------------------------
    if context.user_data.get(
        "waiting_withdraw_destination"
    ):
        method = context.user_data.get(
            "withdraw_method"
        )
        amount = float(
            context.user_data.get(
                "withdraw_amount",
                0,
            )
        )

        if method not in (
            "Binance ID",
            "BEP20",
        ):
            context.user_data.clear()
            await update.message.reply_text(
                t["withdraw_invalid"],
                parse_mode="HTML",
            )
            return

        destination = text

        # Basic validation
        if not destination or len(destination) > 150:
            await update.message.reply_text(
                t["withdraw_invalid"],
                parse_mode="HTML",
            )
            return

        if method == "BEP20":
            if not re.fullmatch(
                r"0x[a-fA-F0-9]{40}",
                destination,
            ):
                await update.message.reply_text(
                    "⚠️ Invalid BEP20 address.\n\n"
                    "Example format: <code>0x...</code>",
                    parse_mode="HTML",
                )
                return

        # Binance ID is intentionally kept flexible.
        if method == "Binance ID":
            if not re.fullmatch(
                r"[A-Za-z0-9._@-]{3,100}",
                destination,
            ):
                await update.message.reply_text(
                    t["withdraw_invalid"],
                    parse_mode="HTML",
                )
                return

        current_balance = get_balance(user_id)

        if current_balance < MIN_WITHDRAW:
            context.user_data.clear()
            await update.message.reply_text(
                t["withdraw_min"].format(
                    balance=current_balance
                ),
                parse_mode="HTML",
            )
            return

        # Always withdraw current full balance.
        amount = current_balance

        request_id, result = create_withdraw_request(
            user_id,
            method,
            destination,
            amount,
        )

        if result == "MINIMUM":
            context.user_data.clear()
            await update.message.reply_text(
                t["withdraw_min"].format(
                    balance=current_balance
                ),
                parse_mode="HTML",
            )
            return

        if result != "OK" or not request_id:
            await update.message.reply_text(
                t["api_error"],
                parse_mode="HTML",
            )
            return

        context.user_data.clear()

        await update.message.reply_text(
            t["withdraw_sent"].format(
                amount=amount,
                method=safe(method),
                destination=safe(destination),
            ),
            parse_mode="HTML",
        )

        await notify_admins_about_withdraw(
            context.bot,
            request_id,
            user_id,
            method,
            destination,
            amount,
        )

        return

    # --------------------------------------------
    # NORMAL REPLY KEYBOARD
    # --------------------------------------------

    if text in [
        t["generate"],
        "➕ Generate New",
        "➕ নতুন তৈরি করুন",
        "➕ Naya Generate",
    ]:
        await generate_new(
            update.message,
            user_id,
            lang,
        )
        return

    if text in [
        t["inbox"],
        "📥 Inbox",
        "📥 ইনবক্স",
    ]:
        await show_inbox(
            update.message,
            user_id,
            lang,
        )
        return

    if text in [
        t["refresh"],
        "🔄 Refresh",
        "🔄 রিফ্রেশ",
    ]:
        await show_inbox(
            update.message,
            user_id,
            lang,
        )
        return

    if text in [
        t["refer_btn"],
        "👥 Refer System",
        "👥 রেফার সিস্টেম",
        "/refer",
    ]:
        await refer_command(
            update,
            context,
        )
        return

# ============================================================
# ADMIN WITHDRAW PROCESSING
# ============================================================

async def admin_withdraw_action(update, context):
    query = update.callback_query

    if not is_admin(query.from_user.id):
        await query.answer(
            "Admin only.",
            show_alert=True,
        )
        return

    data = query.data or ""

    try:
        action, request_id_text = data.split(
            ":",
            1,
        )
        request_id = int(request_id_text)
    except Exception:
        await query.answer(
            "Invalid request.",
            show_alert=True,
        )
        return

    request = get_withdraw_request(
        request_id
    )

    if not request:
        await query.answer(
            "Request not found.",
            show_alert=True,
        )
        return

    user_id = int(request["user_id"])
    amount = float(request["amount"])
    method = str(request["method"])
    destination = str(request["destination"])
    current_status = str(request["status"])

    # Already processed
    if current_status != "PENDING":
        await query.answer(
            f"Already {current_status}.",
            show_alert=True,
        )
        return

    if action == "withdraw_accept":
        success = update_withdraw_status(
            request_id,
            "APPROVED",
        )

        if not success:
            await query.answer(
                "Request already processed.",
                show_alert=True,
            )
            return

        await query.answer(
            "Withdrawal approved.",
            show_alert=True,
        )

        try:
            user_lang_code = user_lang(user_id)

            await context.bot.send_message(
                chat_id=user_id,
                text=TEXT[user_lang_code][
                    "withdraw_congratulations"
                ].format(
                    amount=amount,
                    method=safe(method),
                    destination=safe(destination),
                ),
                parse_mode="HTML",
            )

        except Exception as error:
            logger.error(
                "Approval notification failed: %s",
                error,
            )

        try:
            await query.edit_message_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        try:
            await query.message.reply_text(
                f"✅ Request #{request_id} approved."
            )
        except Exception:
            pass

        # IMPORTANT:
        # This only approves the internal request.
        # It does NOT send real Binance/BEP20 funds.
        # Real automatic payout needs a payment provider/API.

        return

    if action == "withdraw_reject":
        success = refund_withdraw(
            request_id
        )

        if not success:
            await query.answer(
                "Request already processed.",
                show_alert=True,
            )
            return

        await query.answer(
            "Withdrawal rejected and refunded.",
            show_alert=True,
        )

        try:
            user_lang_code = user_lang(user_id)

            await context.bot.send_message(
                chat_id=user_id,
                text=TEXT[user_lang_code][
                    "withdraw_rejected"
                ].format(
                    amount=amount
                ),
                parse_mode="HTML",
            )

        except Exception as error:
            logger.error(
                "Reject notification failed: %s",
                error,
            )

        try:
            await query.edit_message_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        try:
            await query.message.reply_text(
                f"❌ Request #{request_id} rejected and refunded."
            )
        except Exception:
            pass

# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data or ""

    # Admin withdrawal actions
    if data.startswith("withdraw_accept:") or data.startswith(
        "withdraw_reject:"
    ):
        await admin_withdraw_action(
            update,
            context,
        )
        return

    # Withdraw method
    if data in (
        "withdraw_method_binance",
        "withdraw_method_bep20",
    ):
        await choose_withdraw_method(
            update,
            context,
        )
        return

    # Language
    if data.startswith("lang_"):
        lang = data.replace(
            "lang_",
            "",
            1,
        )

        if lang not in TEXT:
            lang = "en"

        await query.answer()

        set_language(
            user_id,
            lang,
        )

        ensure_reward_user(
            user_id
        )

        try:
            await query.edit_message_text(
                TEXT[lang]["language_ok"],
                parse_mode="HTML",
            )
        except Exception:
            pass

        await generate_new(
            query.message,
            user_id,
            lang,
        )
        return

    # Generate
    if data == "generate":
        await query.answer()
        lang = user_lang(user_id)

        await generate_new(
            query.message,
            user_id,
            lang,
        )
        return

    # Inbox
    if data == "inbox":
        await query.answer()
        lang = user_lang(user_id)

        await show_inbox(
            query.message,
            user_id,
            lang,
        )
        return

    # Refresh
    if data == "refresh":
        await query.answer()
        lang = user_lang(user_id)

        await show_inbox(
            query.message,
            user_id,
            lang,
        )
        return

    # Withdraw
    if data == "withdraw":
        await withdraw_callback(
            update,
            context,
        )
        return

    await query.answer()

# ============================================================
# STATS
# ============================================================

async def stats_command(update, context):
    user_id = update.effective_user.id

    # Admin only
    if not is_admin(user_id):
        await update.message.reply_text(
            "🚫 <b>Access Denied!</b>\n\n"
            "⚠️ This command is available for administrators only.",
            parse_mode="HTML",
        )
        return

    lang = user_lang(user_id)

    try:
        users = get_all_users()
        total_users = len(users)
        total_mailboxes = 0

        for uid in users:
            try:
                mailbox = get_mailbox(uid)
                if mailbox:
                    total_mailboxes += 1
            except Exception:
                continue

    except Exception as error:
        logger.error("Stats error: %s", error)
        total_users = 0
        total_mailboxes = 0

    await update.message.reply_text(
        TEXT[lang]["stats"].format(
            users=total_users,
            mailboxes=total_mailboxes,
            seconds=POLL_SECONDS,
        ),
        parse_mode="HTML",
                )
# ============================================================
# ADMIN
# ============================================================

async def admin_only(update):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["admin_only"],
        parse_mode="HTML",
    )


async def admin_command(update, context):
    if not is_admin(
        update.effective_user.id
    ):
        await admin_only(update)
        return

    lang = user_lang(
        update.effective_user.id
    )

    await update.message.reply_text(
        TEXT[lang]["admin_panel"],
        parse_mode="HTML",
    )


async def broadcast_command(update, context):
    if not is_admin(
        update.effective_user.id
    ):
        await admin_only(update)
        return

    lang = user_lang(
        update.effective_user.id
    )

    if not context.args:
        await update.message.reply_text(
            TEXT[lang]["broadcast_start"],
            parse_mode="HTML",
        )
        return

    broadcast_text = " ".join(
        context.args
    )

    users = get_all_users()
    sent = 0
    failed = 0

    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=broadcast_text,
                parse_mode="HTML",
            )
            sent += 1
            await asyncio.sleep(0.05)

        except Exception:
            failed += 1

    await update.message.reply_text(
        TEXT[lang]["broadcast_done"].format(
            sent=sent,
            failed=failed,
        ),
        parse_mode="HTML",
    )

# ============================================================
# AUTOMATIC INBOX
# ============================================================

async def auto_inbox_job(context):
    try:
        users = get_all_users()

    except Exception as error:
        logger.error(
            "Could not load users: %s",
            error,
        )
        return

    for user_id in users:
        try:
            mailbox = get_mailbox(
                user_id
            )

            if not mailbox:
                continue

            token = mailbox.get("token")

            if not token:
                continue

            if KNOWN_MAILBOX.get(user_id) != token:
                KNOWN_MAILBOX[user_id] = token
                SEEN_MESSAGES[user_id] = set()

            data = await get_messages(
                token
            )

            if not data:
                continue

            messages = extract_messages(
                data
            )

            if not messages:
                continue

            seen = SEEN_MESSAGES.setdefault(
                user_id,
                set(),
            )

            lang = user_lang(
                user_id
            )

            for item in messages:
                message_id = get_message_id(
                    item
                )

                if not message_id:
                    continue

                if message_id in seen:
                    continue

                seen.add(message_id)

                try:
                    await send_auto_mail(
                        context.bot,
                        user_id,
                        item,
                        lang,
                    )

                    logger.info(
                        "New email sent automatically -> %s",
                        user_id,
                    )

                except Exception as error:
                    logger.error(
                        "Auto send error user=%s: %s",
                        user_id,
                        error,
                    )

            if len(seen) > 200:
                SEEN_MESSAGES[user_id] = set(
                    list(seen)[-100:]
                )

        except Exception as error:
            logger.error(
                "Auto inbox error user=%s: %s",
                user_id,
                error,
            )

        await asyncio.sleep(0.05)

# ============================================================
# ERROR
# ============================================================

async def error_handler(update, context):
    logger.error(
        "Unhandled error",
        exc_info=context.error,
    )

# ============================================================
# POST INIT
# ============================================================

async def post_init(application):
    init_reward_db()

    if not application.job_queue:
        logger.error(
            "JobQueue unavailable."
        )
        logger.error(
            "Install: python-telegram-bot[job-queue]"
        )
        return

    application.job_queue.run_repeating(
        auto_inbox_job,
        interval=POLL_SECONDS,
        first=2,
        name="auto-inbox",
    )

    logger.info(
        "Automatic inbox started: every %s seconds",
        POLL_SECONDS,
    )

# ============================================================
# MAIN
# ============================================================

def main():
    init_db()
    init_reward_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )
    application.add_handler(
        CommandHandler("inbox", inbox_command)
    )
    application.add_handler(
        CommandHandler("refresh", refresh_command)
    )
    application.add_handler(
        CommandHandler("language", language_command)
    )
    application.add_handler(
        CommandHandler("help", help_command)
    )
    application.add_handler(
        CommandHandler("about", about_command)
    )
    application.add_handler(
        CommandHandler("stats", stats_command)
    )
    application.add_handler(
        CommandHandler("refer", refer_command)
    )
    application.add_handler(
        CommandHandler("balance", balance_command)
    )
    application.add_handler(
        CommandHandler("withdraw", withdraw_command)
    )
    application.add_handler(
        CommandHandler("admin", admin_command)
    )
    application.add_handler(
        CommandHandler("broadcast", broadcast_command)
    )
    application.add_handler(
        CommandHandler("boardchat", broadcast_command)
    )

    # Callback
    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    # Error handler
    application.add_error_handler(
        error_handler
    )

    print("🤖 Temp Mail Bot is running...")
    print(
        f"📩 Auto inbox: every {POLL_SECONDS}s"
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
