# ============================================================
# bot.py
# TEMP MAIL TELEGRAM BOT (Fully Fixed)
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

POLL_SECONDS = 3
MAX_MESSAGES = 10

EMAIL_REWARD = 0.00130
REFERRAL_REWARD = 0.00158

DHAKA_TZ = ZoneInfo("Asia/Dhaka")
REWARD_DB = "rewards.db"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# MEMORY CACHE
# ============================================================

SEEN_MESSAGES = {}
KNOWN_MAILBOX = {}

# ============================================================
# REWARD DATABASE
# ============================================================

def reward_db():
    conn = sqlite3.connect(REWARD_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_reward_db():
    conn = reward_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reward_users (
                user_id INTEGER PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                total_referrals INTEGER NOT NULL DEFAULT 0,
                total_email_rewards INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rewarded_messages (
                user_id INTEGER NOT NULL,
                message_id TEXT NOT NULL,
                code TEXT,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, message_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                referred_user_id INTEGER PRIMARY KEY,
                referrer_user_id INTEGER NOT NULL,
                reward REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                binance_id TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'DEMO_RECORDED',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def ensure_reward_user(user_id):
    conn = reward_db()
    try:
        row = conn.execute(
            "SELECT user_id FROM reward_users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if not row:
            referral_code = str(user_id)
            conn.execute(
                """
                INSERT INTO reward_users
                (user_id, balance, referral_code, created_at)
                VALUES (?, 0, ?, ?)
                """,
                (user_id, referral_code, datetime.now(DHAKA_TZ).isoformat())
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
            (user_id,)
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
            (user_id,)
        ).fetchone()
        return int(row["total_referrals"]) if row else 0
    finally:
        conn.close()


def add_email_reward(user_id, message_id, code):
    ensure_reward_user(user_id)
    message_id = str(message_id)
    conn = reward_db()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO rewarded_messages
            (user_id, message_id, code, amount, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, message_id, str(code) if code else None, EMAIL_REWARD, datetime.now(DHAKA_TZ).isoformat())
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
            (EMAIL_REWARD, user_id)
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
            "SELECT referred_user_id FROM referrals WHERE referred_user_id = ?",
            (referred_user_id,)
        ).fetchone()
        if existing:
            return False
        row = conn.execute(
            "SELECT referred_by FROM reward_users WHERE user_id = ?",
            (referred_user_id,)
        ).fetchone()
        if row and row["referred_by"]:
            return False
        conn.execute(
            """
            INSERT INTO referrals
            (referred_user_id, referrer_user_id, reward, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (referred_user_id, referrer_id, REFERRAL_REWARD, datetime.now(DHAKA_TZ).isoformat())
        )
        conn.execute(
            "UPDATE reward_users SET referred_by = ? WHERE user_id = ?",
            (referrer_id, referred_user_id)
        )
        conn.execute(
            """
            UPDATE reward_users
            SET balance = balance + ?,
                total_referrals = total_referrals + 1
            WHERE user_id = ?
            """,
            (REFERRAL_REWARD, referrer_id)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_withdraw_request(user_id, binance_id, amount):
    ensure_reward_user(user_id)
    conn = reward_db()
    try:
        conn.execute(
            """
            INSERT INTO withdraw_requests
            (user_id, binance_id, amount, status, created_at)
            VALUES (?, ?, ?, 'DEMO_RECORDED', ?)
            """,
            (user_id, str(binance_id), float(amount), datetime.now(DHAKA_TZ).isoformat())
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# LANGUAGES
# ============================================================

TEXT = {
    "en": {
        "welcome": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL BOT</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👋 <b>Welcome!</b>\n\n"
            "⚡ Fast temporary email receiver\n"
            "📩 Receive verification emails\n"
            "🔐 Verification codes are detected automatically\n\n"
            "🌐 <b>Please select your preferred language:</b>"
        ),
        "language_ok": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      ✅ <b>SUCCESS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Language selected successfully!\n\n"
            "⚡ Creating your temporary email..."
        ),
        "generating": "⚡ <b>Creating your temporary email...</b>",
        "created": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 <b>NEW TEMP EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n"
            "<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "You can now receive emails here.\n\n"
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
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Dhaka Time:</b> {date}\n\n"
            "{content}"
        ),
        "earned": "💰 <b>Your earned:</b> <code>{amount}</code>",
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": "🔐 <b>VERIFICATION CODE</b>\n\n🔢 <b>Code:</b> <code>{code}</code>",
        "copy_code": "📋 Copy Code",
        "code_copied": "✅ Code: <code>{code}</code>",
        "language": "🌐 <b>Select your preferred language:</b>",
        "help": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Generate New — Create a new email\n"
            "📥 Inbox — View received emails\n"
            "🔄 Refresh — Check new emails\n"
            "👥 Refer System — Referral system\n"
            "💰 /balance — Check balance\n\n"
            "/start — Start bot\n"
            "/language — Change language\n"
            "/inbox — Open inbox\n"
            "/refresh — Refresh inbox\n"
            "/help — Show help\n"
            "/about — About bot\n"
            "/stats — Bot statistics"
        ),
        "about": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast disposable email receiver.\n\n"
            "⚡ Powered by Smails API\n"
            "🔒 No API key required"
        ),
        "stats": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 Total Users: <b>{users}</b>\n"
            "📧 Active Mailboxes: <b>{mailboxes}</b>\n"
            "⚡ Auto Inbox: <b>ON</b>\n"
            "🔄 Polling: <b>{seconds}s</b>"
        ),
        "admin_only": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Sorry! This command is available\n"
            "only for administrators."
        ),
        "broadcast_start": "📢 <b>Broadcast Mode</b>\n\nUse:\n<code>/broadcast Your message</code>",
        "broadcast_done": "✅ <b>Broadcast completed!</b>\n\n📤 Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        "admin_panel": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 You have administrator access."
        ),
        "refer": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👥 <b>REFER & EARN</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💰 Per successful referral: <b>{reward}</b>\n"
            "👥 Total referrals: <b>{refs}</b>\n\n"
            "🔗 <b>Your referral link:</b>\n"
            "<code>{link}</code>\n\n"
            "Share the link with your friends."
        ),
        "balance": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       💰 <b>BALANCE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 Balance: <b>{balance}</b>\n"
            "👥 Referrals: <b>{refs}</b>\n"
            "📩 Email rewards: <b>{email_reward}</b>"
        ),
        "withdraw_button": "💸 Withdraw",
        "withdraw_prompt": "💸 <b>Withdraw</b>\n\nSend your Binance ID:",
        "withdraw_invalid": "⚠️ Please send a valid Binance ID.",
        "withdraw_recorded": (
            "✅ <b>Withdrawal request recorded.</b>\n\n"
            "💵 Amount: <b>{amount}</b>\n"
            "🆔 Binance ID: <code>{binance_id}</code>\n\n"
            "🧪 <b>Demo mode:</b> No real payment has been sent."
        ),
    },
    "bn": {
        "welcome": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL BOT</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👋 <b>স্বাগতম!</b>\n\n"
            "⚡ দ্রুত Temporary Email receiver\n"
            "📩 Verification Email গ্রহণ করুন\n"
            "🔐 Verification Code Automatic Detect হবে\n\n"
            "🌐 <b>আপনার পছন্দের ভাষা নির্বাচন করুন:</b>"
        ),
        "language_ok": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      ✅ <b>সফল হয়েছে</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "ভাষা সফলভাবে নির্বাচন করা হয়েছে!\n\n"
            "⚡ আপনার Temporary Email তৈরি হচ্ছে..."
        ),
        "generating": "⚡ <b>আপনার Temporary Email তৈরি হচ্ছে...</b>",
        "created": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 <b>নতুন TEMP EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n"
            "<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "এখন এই Email-এ Message গ্রহণ করতে পারবেন।\n\n"
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
            "       📨 <b>নতুন EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>ঢাকা সময়:</b> {date}\n\n"
            "{content}"
        ),
        "earned": "💰 <b>Your earned:</b> <code>{amount}</code>",
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": "🔐 <b>VERIFICATION CODE</b>\n\n🔢 <b>Code:</b> <code>{code}</code>",
        "copy_code": "📋 Code Copy করুন",
        "code_copied": "✅ Code: <code>{code}</code>",
        "language": "🌐 <b>আপনার পছন্দের ভাষা নির্বাচন করুন:</b>",
        "help": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ নতুন তৈরি করুন — নতুন Email\n"
            "📥 ইনবক্স — আসা Email দেখুন\n"
            "🔄 রিফ্রেশ — নতুন Email check করুন\n"
            "👥 রেফার সিস্টেম — Refer করুন\n"
            "💰 /balance — Balance দেখুন\n\n"
            "/start — Bot শুরু করুন\n"
            "/language — ভাষা পরিবর্তন\n"
            "/inbox — Inbox দেখুন\n"
            "/refresh — Inbox Refresh\n"
            "/help — Help দেখুন\n"
            "/about — Bot সম্পর্কে\n"
            "/stats — Bot Statistics"
        ),
        "about": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দ্রুত Temporary Email receiver।\n\n"
            "⚡ Smails API দ্বারা পরিচালিত\n"
            "🔒 API key প্রয়োজন নেই"
        ),
        "stats": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 Total Users: <b>{users}</b>\n"
            "📧 Active Mailboxes: <b>{mailboxes}</b>\n"
            "⚡ Auto Inbox: <b>ON</b>\n"
            "🔄 Checking: প্রতি <b>{seconds}s</b>"
        ),
        "admin_only": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দুঃখিত! এই Command শুধুমাত্র\n"
            "Administrator-এর জন্য।"
        ),
        "broadcast_start": "📢 <b>Broadcast Mode</b>\n\nব্যবহার করুন:\n<code>/broadcast আপনার Message</code>",
        "broadcast_done": "✅ <b>Broadcast সম্পন্ন!</b>\n\n📤 পাঠানো হয়েছে: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        "admin_panel": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 আপনার Administrator access আছে।"
        ),
        "refer": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👥 <b>REFER & EARN</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💰 প্রতি সফল Refer: <b>{reward}</b>\n"
            "👥 মোট Refer: <b>{refs}</b>\n\n"
            "🔗 <b>আপনার Referral Link:</b>\n"
            "<code>{link}</code>\n\n"
            "বন্ধুদের সাথে Link share করুন।"
        ),
        "balance": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       💰 <b>BALANCE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 Balance: <b>{balance}</b>\n"
            "👥 Referrals: <b>{refs}</b>\n"
            "📩 Email rewards: <b>{email_reward}</b>"
        ),
        "withdraw_button": "💸 Withdraw",
        "withdraw_prompt": "💸 <b>Withdraw</b>\n\nআপনার Binance ID পাঠান:",
        "withdraw_invalid": "⚠️ সঠিক Binance ID পাঠান।",
        "withdraw_recorded": (
            "✅ <b>Withdrawal request record হয়েছে।</b>\n\n"
            "💵 Amount: <b>{amount}</b>\n"
            "🆔 Binance ID: <code>{binance_id}</code>\n\n"
            "🧪 <b>Demo mode:</b> কোনো real payment পাঠানো হয়নি।"
        ),
    },
    "hi": {
        "welcome": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL BOT</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👋 <b>Swagat hai!</b>\n\n"
            "⚡ Fast Temporary Email\n"
            "📩 Verification Email receive karein\n"
            "🔐 Verification Code automatically detect hoga\n\n"
            "🌐 <b>Apni pasand ki language select karein:</b>"
        ),
        "language_ok": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      ✅ <b>SUCCESS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Language successfully select ho gayi!\n\n"
            "⚡ Aapka Temporary Email create ho raha hai..."
        ),
        "generating": "⚡ <b>Aapka Temporary Email create ho raha hai...</b>",
        "created": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 <b>NEW TEMP EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n"
            "<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "Ab aap is Email par messages receive kar sakte hain.\n\n"
            "📩 Naya Email aate hi automatically dikhega."
        ),
        "generate": "➕ Naya Generate",
        "inbox": "📥 Inbox",
        "refresh": "🔄 Refresh",
        "refer_btn": "👥 Refer System",
        "checking": "🔎 <b>Aapka Inbox check ho raha hai...</b>",
        "empty": "📭 <b>Inbox empty hai.</b>\n\nAbhi koi naya message nahi aaya.",
        "no_mailbox": "⚠️ <b>Koi Temporary Email nahi mila.</b>\n\nPehle naya Email generate karein.",
        "api_error": "❌ <b>Kuch problem ho gayi.</b>\n\nThodi der baad dobara try karein.",
        "new_mail": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Dhaka Time:</b> {date}\n\n"
            "{content}"
        ),
        "earned": "💰 <b>Your earned:</b> <code>{amount}</code>",
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": "🔐 <b>VERIFICATION CODE</b>\n\n🔢 <b>Code:</b> <code>{code}</code>",
        "copy_code": "📋 Copy Code",
        "code_copied": "✅ Code: <code>{code}</code>",
        "language": "🌐 <b>Apni pasand ki language select karein:</b>",
        "help": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Naya Generate — Naya Email\n"
            "📥 Inbox — Received emails dekhein\n"
            "🔄 Refresh — Naye emails check karein\n"
            "👥 Refer System — Referral system\n"
            "💰 /balance — Balance dekhein\n\n"
            "/start — Bot start karein\n"
            "/language — Language change karein\n"
            "/inbox — Inbox dekhein\n"
            "/refresh — Inbox refresh karein\n"
            "/help — Help dekhein\n"
            "/about — Bot ke baare mein\n"
            "/stats — Bot Statistics"
        ),
        "about": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast Temporary Email receiver.\n\n"
            "⚡ Smails API se powered\n"
            "🔒 API key ki zarurat nahi"
        ),
        "stats": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 Total Users: <b>{users}</b>\n"
            "📧 Active Mailboxes: <b>{mailboxes}</b>\n"
            "⚡ Auto Inbox: <b>ON</b>\n"
            "🔄 Checking: <b>{seconds}s</b>"
        ),
        "admin_only": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Maaf kijiye! Yeh command sirf\n"
            "Administrator ke liye hai."
        ),
        "broadcast_start": "📢 <b>Broadcast Mode</b>\n\nUse karein:\n<code>/broadcast Your message</code>",
        "broadcast_done": "✅ <b>Broadcast complete ho gaya!</b>\n\n📤 Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
        "admin_panel": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 Aapke paas Administrator access hai."
        ),
        "refer": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👥 <b>REFER & EARN</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💰 Per successful referral: <b>{reward}</b>\n"
            "👥 Total referrals: <b>{refs}</b>\n\n"
            "🔗 <b>Your referral link:</b>\n"
            "<code>{link}</code>\n\n"
            "Link apne friends ke saath share karein."
        ),
        "balance": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       💰 <b>BALANCE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 Balance: <b>{balance}</b>\n"
            "👥 Referrals: <b>{refs}</b>\n"
            "📩 Email rewards: <b>{email_reward}</b>"
        ),
        "withdraw_button": "💸 Withdraw",
        "withdraw_prompt": "💸 <b>Withdraw</b>\n\nApna Binance ID bhejein:",
        "withdraw_invalid": "⚠️ Please send a valid Binance ID.",
        "withdraw_recorded": (
            "✅ <b>Withdrawal request recorded.</b>\n\n"
            "💵 Amount: <b>{amount}</b>\n"
            "🆔 Binance ID: <code>{binance_id}</code>\n\n"
            "🧪 <b>Demo mode:</b> Koi real payment nahi bheja gaya."
        ),
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
        [
            InlineKeyboardButton(t["refresh"], callback_data="refresh"),
        ],
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
                copy_text=CopyTextButton(text=str(code))
            ),
        ],
        [
            InlineKeyboardButton(t["refresh"], callback_data="refresh"),
        ],
    ])


def balance_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TEXT[lang]["withdraw_button"], callback_data="withdraw")]
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
        r"(?:verification|verify|verification\s*code|otp|code)\D{0,30}(\d{4,8})",
        r"(?:one[\s-]*time[\s-]*password)\D{0,30}(\d{4,8})",
        r"(?:login\s*code)\D{0,30}(\d{4,8})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    for digits in (6, 5, 4):
        match = re.search(rf"(?<!\d)\d{{{digits}}}(?!\d)", text)
        if match:
            return match.group(0)
    return None


# ============================================================
# MESSAGE ID
# ============================================================

def get_message_id(item):
    possible = [
        item.get("id"),
        item.get("messageId"),
        item.get("_id"),
        item.get("uid"),
    ]
    for value in possible:
        if value is not None:
            return str(value)
    raw = (
        str(item.get("subject", "")) + "|"
        + str(item.get("date", "")) + "|"
        + str(item.get("createdAt", "")) + "|"
        + str(item.get("from", "")) + "|"
        + str(item.get("intro", "")) + "|"
        + str(item.get("text", "")) + "|"
        + str(item.get("body", "")) + "|"
        + str(item.get("content", ""))
    )
    return raw


# ============================================================
# API
# ============================================================

async def api_request(method, endpoint, token=None):
    url = API_BASE + endpoint
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    timeout = aiohttp.ClientTimeout(total=10, connect=4, sock_read=7)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, headers=headers) as response:
                if response.status >= 400:
                    body = await response.text()
                    logger.error("API HTTP %s: %s", response.status, body[:500])
                    return None
                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type.lower():
                    return await response.json(content_type=None)
                text = await response.text()
                try:
                    return json.loads(text)
                except Exception:
                    logger.error("Invalid API JSON: %s", text[:500])
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
    return await api_request("GET", "/mailbox/messages", token)


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
        body = body.get("text") or body.get("plain") or body.get("content") or ""
    return str(sender), str(subject), str(body)


# ============================================================
# BUILD EMAIL MESSAGE
# ============================================================

def build_mail_message(item, lang, reward_added):
    t = TEXT[lang]
    sender, subject, body = parse_mail(item)
    code = extract_code(f"{subject}\n{body}")
    if code:
        amount = EMAIL_REWARD if reward_added else 0.0
        content = t["earned"].format(amount=f"{amount:.5f}")
        keyboard = code_keyboard(code, lang)
    else:
        content = t["message_content"].format(body=safe(body[:1500]))
        keyboard = main_keyboard(lang)
    message_text = t["new_mail"].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(dhaka_time()),
        content=content,
    )
    return message_text, keyboard, code


# ============================================================
# SEND AUTOMATIC EMAIL
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
        reward_added = add_email_reward(user_id, message_id, code)
    message_text, keyboard, _ = build_mail_message(item, lang, reward_added)
    await bot.send_message(
        chat_id=user_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============================================================
# SEND INBOX EMAIL
# ============================================================

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
        reward_added = add_email_reward(user_id, message_id, code)
    message_text, keyboard, _ = build_mail_message(item, lang, reward_added)
    await bot.send_message(
        chat_id=user_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============================================================
# GENERATE NEW MAILBOX
# ============================================================

async def generate_new(message, user_id, lang):
    t = TEXT[lang]
    loading = await message.reply_text(t["generating"], parse_mode="HTML")
    mailbox = await create_mailbox()
    if not mailbox:
        await loading.edit_text(t["api_error"], parse_mode="HTML")
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
        logger.error("Mailbox response missing email/token: %s", mailbox)
        await loading.edit_text(t["api_error"], parse_mode="HTML")
        return False
    save_mailbox(user_id, email, token)
    SEEN_MESSAGES[user_id] = set()
    KNOWN_MAILBOX[user_id] = token
    ensure_reward_user(user_id)
    await loading.edit_text(
        t["created"].format(email=safe(email)),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )
    # Reply Keyboard পাঠানো
    await message.reply_text("📩 Receive Codes & Earn Rewards! 💰", reply_markup=reply_main_keyboard(lang))
    return True


# ============================================================
# START
# ============================================================

async def start(update, context):
    user = update.effective_user
    if not user:
        return
    save_user(user.id, user.username)
    ensure_reward_user(user.id)
    if context.args:
        ref_code = str(context.args[0]).strip()
        try:
            referrer_id = int(ref_code)
            if referrer_id != user.id:
                create_referral(referrer_id, user.id)
        except Exception as error:
            logger.warning("Referral processing error: %s", error)
    lang = get_language(user.id)
    if not lang:
        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML"
        )
        return
    lang = user_lang(user.id)
    mailbox = get_mailbox(user.id)
    if mailbox:
        await update.message.reply_text(
            TEXT[lang]["created"].format(email=safe(mailbox.get("email", ""))),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )
        await update.message.reply_text("⬇️ মেনু", reply_markup=reply_main_keyboard(lang))
    else:
        await generate_new(update.message, user.id, lang)


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
            parse_mode="HTML"
        )
        return
    loading = await message.reply_text(t["checking"], parse_mode="HTML")
    data = await get_messages(mailbox.get("token"))
    if not data:
        await loading.edit_text(t["api_error"], parse_mode="HTML")
        return
    messages = extract_messages(data)
    if not messages:
        await loading.edit_text(
            t["empty"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )
        return
    try:
        await loading.delete()
    except Exception:
        pass
    messages = list(reversed(messages))
    for item in messages[:MAX_MESSAGES]:
        try:
            await send_inbox_mail(message.get_bot(), user_id, item, lang)
        except Exception as error:
            logger.error("Inbox message error: %s", error)


# ============================================================
# COMMANDS
# ============================================================

async def refresh_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    await show_inbox(update.message, user_id, lang)


async def inbox_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    await show_inbox(update.message, user_id, lang)


async def language_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    await update.message.reply_text(
        TEXT[lang]["language"],
        reply_markup=language_keyboard(),
        parse_mode="HTML"
    )


async def help_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    await update.message.reply_text(
        TEXT[lang]["help"],
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )


async def about_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    await update.message.reply_text(
        TEXT[lang]["about"],
        parse_mode="HTML"
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
        link = f"https://t.me/{bot_username}?start={user_id}"
        refs = get_total_referrals(user_id)
        await update.message.reply_text(
            TEXT[lang]["refer"].format(
                reward=f"{REFERRAL_REWARD:.5f}",
                refs=refs,
                link=safe(link)
            ),
            parse_mode="HTML"
        )
    except Exception as error:
        logger.error("Refer error: %s", error)
        await update.message.reply_text(TEXT[lang]["api_error"], parse_mode="HTML")


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
        ),
        reply_markup=balance_keyboard(lang),
        parse_mode="HTML"
    )


# ============================================================
# WITHDRAW + TEXT HANDLER (সব বাটন এখানে হ্যান্ডল)
# ============================================================

async def withdraw_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    lang = user_lang(user_id)
    await query.answer()
    context.user_data["waiting_binance_id"] = True
    await query.message.reply_text(
        TEXT[lang]["withdraw_prompt"],
        parse_mode="HTML"
    )


async def text_handler(update, context):
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return
    user_id = user.id
    lang = user_lang(user_id)
    t = TEXT[lang]
    text = update.message.text.strip()

    # ---------- Binance ID (Withdraw) ----------
    if context.user_data.get("waiting_binance_id"):
        binance_id = text
        if not binance_id or len(binance_id) > 100:
            await update.message.reply_text(t["withdraw_invalid"], parse_mode="HTML")
            return
        context.user_data["waiting_binance_id"] = False
        amount = get_balance(user_id)
        create_withdraw_request(user_id, binance_id, amount)
        await update.message.reply_text(
            t["withdraw_recorded"].format(
                amount=f"{amount:.5f}",
                binance_id=safe(binance_id),
            ),
            parse_mode="HTML"
        )
        return

    # ---------- Reply Keyboard বাটন ----------
    if text in [t["generate"], "➕ Generate New", "➕ নতুন তৈরি করুন", "➕ Naya Generate"]:
        await generate_new(update.message, user_id, lang)
        return

    if text in [t["inbox"], "📥 Inbox", "📥 ইনবক্স"]:
        await show_inbox(update.message, user_id, lang)
        return

    if text in [t["refresh"], "🔄 Refresh", "🔄 রিফ্রেশ"]:
        await show_inbox(update.message, user_id, lang)
        return

    if text in [t["refer_btn"], "👥 Refer System", "👥 রেফার সিস্টেম", "/refer"]:
        try:
            bot_username = context.bot.username
            if not bot_username:
                me = await context.bot.get_me()
                bot_username = me.username
            link = f"https://t.me/{bot_username}?start={user_id}"
            refs = get_total_referrals(user_id)
            await update.message.reply_text(
                t["refer"].format(
                    reward=f"{REFERRAL_REWARD:.5f}",
                    refs=refs,
                    link=safe(link)
                ),
                parse_mode="HTML"
            )
        except Exception as error:
            logger.error("Refer error: %s", error)
            await update.message.reply_text(t["api_error"], parse_mode="HTML")
        return


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data or ""

    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        if lang not in TEXT:
            lang = "en"
        await query.answer()
        set_language(user_id, lang)
        ensure_reward_user(user_id)
        try:
            await query.edit_message_text(TEXT[lang]["language_ok"], parse_mode="HTML")
        except Exception:
            pass
        await generate_new(query.message, user_id, lang)
        return

    if data == "generate":
        await query.answer()
        lang = user_lang(user_id)
        await generate_new(query.message, user_id, lang)
        return

    if data == "inbox":
        await query.answer()
        lang = user_lang(user_id)
        await show_inbox(query.message, user_id, lang)
        return

    if data == "refresh":
        await query.answer()
        lang = user_lang(user_id)
        await show_inbox(query.message, user_id, lang)
        return

    if data == "withdraw":
        await withdraw_callback(update, context)
        return

    await query.answer()


# ============================================================
# STATS
# ============================================================

async def stats_command(update, context):
    user_id = update.effective_user.id
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
            seconds=POLL_SECONDS
        ),
        parse_mode="HTML"
    )


# ============================================================
# ADMIN
# ============================================================

async def admin_only(update):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    await update.message.reply_text(TEXT[lang]["admin_only"], parse_mode="HTML")


async def admin_command(update, context):
    if not is_admin(update.effective_user.id):
        await admin_only(update)
        return
    lang = user_lang(update.effective_user.id)
    await update.message.reply_text(TEXT[lang]["admin_panel"], parse_mode="HTML")


async def broadcast_command(update, context):
    if not is_admin(update.effective_user.id):
        await admin_only(update)
        return
    lang = user_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text(TEXT[lang]["broadcast_start"], parse_mode="HTML")
        return
    broadcast_text = " ".join(context.args)
    users = get_all_users()
    sent = 0
    failed = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=broadcast_text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await update.message.reply_text(
        TEXT[lang]["broadcast_done"].format(sent=sent, failed=failed),
        parse_mode="HTML"
    )


# ============================================================
# AUTOMATIC INBOX
# ============================================================

async def auto_inbox_job(context):
    try:
        users = get_all_users()
    except Exception as error:
        logger.error("Could not load users: %s", error)
        return
    for user_id in users:
        try:
            mailbox = get_mailbox(user_id)
            if not mailbox:
                continue
            token = mailbox.get("token")
            if not token:
                continue
            if KNOWN_MAILBOX.get(user_id) != token:
                KNOWN_MAILBOX[user_id] = token
                SEEN_MESSAGES[user_id] = set()
            data = await get_messages(token)
            if not data:
                continue
            messages = extract_messages(data)
            if not messages:
                continue
            seen = SEEN_MESSAGES.setdefault(user_id, set())
            lang = user_lang(user_id)
            for item in messages:
                message_id = get_message_id(item)
                if not message_id:
                    continue
                if message_id in seen:
                    continue
                seen.add(message_id)
                try:
                    await send_auto_mail(context.bot, user_id, item, lang)
                    logger.info("📩 New email sent automatically -> %s", user_id)
                except Exception as error:
                    logger.error("Auto send error user=%s: %s", user_id, error)
            if len(seen) > 200:
                SEEN_MESSAGES[user_id] = set(list(seen)[-100:])
        except Exception as error:
            logger.error("Auto inbox error user=%s: %s", user_id, error)
        await asyncio.sleep(0.05)


# ============================================================
# ERROR
# ============================================================

async def error_handler(update, context):
    logger.error("Unhandled error", exc_info=context.error)


# ============================================================
# POST INIT
# ============================================================

async def post_init(application):
    init_reward_db()
    if not application.job_queue:
        logger.error("JobQueue unavailable.")
        logger.error("Install: python-telegram-bot[job-queue]")
        return
    application.job_queue.run_repeating(
        auto_inbox_job,
        interval=POLL_SECONDS,
        first=2,
        name="auto-inbox"
    )
    logger.info("📩 Automatic inbox started: every %s seconds", POLL_SECONDS)
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

    # ---------------- COMMAND HANDLERS ----------------
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
        CommandHandler("admin", admin_command)
    )

    application.add_handler(
        CommandHandler("broadcast", broadcast_command)
    )

    application.add_handler(
        CommandHandler("boardchat", broadcast_command)
    )

    # ---------------- CALLBACK HANDLER ----------------
    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    # ---------------- TEXT HANDLER ----------------
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    # ---------------- ERROR HANDLER ----------------
    application.add_error_handler(error_handler)

    print("🤖 Temp Mail Bot is running...")
    print(f"📩 Auto inbox: every {POLL_SECONDS}s")

    # ---------------- START BOT ----------------
    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
