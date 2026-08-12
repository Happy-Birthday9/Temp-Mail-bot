# ============================================================
# bot.py
# TEMP MAIL TELEGRAM BOT
# ============================================================

import asyncio
import html
import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import aiohttp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
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
    get_balance,
    add_email_reward_once,
    get_reward_count,
    get_referral_count,
    set_referrer,
    get_referrer,
    add_referral_once,
    create_withdrawal,
)

from reward import (
    REFERRAL_REWARD,
    EMAIL_CODE_REWARD,
    format_reward,
)

# ============================================================
# SETTINGS
# ============================================================

API_BASE = "https://smails.dev/api"
POLL_SECONDS = 3
MAX_MESSAGES = 10
MIN_WITHDRAW = Decimal("1.00")
DHAKA_TZ = ZoneInfo("Asia/Dhaka")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# user_id -> set(message ids)
SEEN_MESSAGES = {}

# user_id -> mailbox token
KNOWN_MAILBOX = {}

# user_id -> withdraw state
WITHDRAW_STATE = {}

# ============================================================
# TEXT
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
        "refer": "👥 Refer System",
        "balance": "💰 Balance",
        "withdraw": "💸 Withdraw",
        "checking": "🔎 <b>Checking your inbox...</b>",
        "empty": (
            "📭 <b>Inbox is empty.</b>\n\n"
            "No new messages received yet."
        ),
        "no_mailbox": (
            "⚠️ <b>No temporary email found.</b>\n\n"
            "Please generate a new email first."
        ),
        "api_error": (
            "❌ <b>Something went wrong.</b>\n\n"
            "Please try again later."
        ),
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
        "message_content": (
            "💬 <b>Message:</b>\n"
            "{body}"
        ),
        "verification": (
            "🔐 <b>Verification Code:</b>\n"
            "<code>{code}</code>\n\n"
            "💰 <b>You earned:</b> $0.00130"
        ),
        "copy_code": "📋 Copy Code",
        "inbox_footer": "━━━━━━━━━━━━━━━━━━\n📥 <b>Inbox</b>\n━━━━━━━━━━━━━━━━━━",
        "refer_title": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      👥 <b>REFER & EARN</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        ),
        "refer_body": (
            "💰 প্রতি সফল Refer: <b>$0.00158</b>\n"
            "👥 মোট Refer: <b>{count}</b>\n\n"
            "🔗 <b>Your Referral Link:</b>\n"
            "<code>{link}</code>\n\n"
            "বন্ধুদের সাথে Link share করুন।"
        ),
        "balance_text": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        💰 <b>BALANCE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 <b>Current Balance:</b> ${balance}\n"
            "👥 <b>Total Refers:</b> {referrals}\n"
            "📧 <b>Code Rewards:</b> {codes}\n\n"
            "Minimum Withdrawal: <b>$1.00</b>"
        ),
        "send_binance": (
            "💸 <b>Withdraw</b>\n\n"
            "Send your <b>Binance ID</b>:"
        ),
        "send_amount": (
            "💰 Send the withdrawal amount.\n\n"
            "Minimum: <b>$1.00</b>\n"
            "Available: <b>${balance}</b>"
        ),
        "invalid_amount": "❌ Please send a valid amount.",
        "min_withdraw": "❌ Minimum withdrawal is <b>$1.00</b>.",
        "insufficient": "❌ Insufficient balance.",
        "withdraw_success": (
            "✅ <b>Withdrawal Request Submitted</b>\n\n"
            "💸 Amount: <b>${amount}</b>\n"
            "🆔 Binance ID: <code>{binance}</code>\n"
            "💰 Remaining Balance: <b>${balance}</b>\n\n"
            "📨 Your withdrawal request has been submitted to the admin."
        ),
        "withdraw_failed": "❌ Withdrawal request failed. Please try again.",
        "cancelled": "❌ Withdrawal cancelled.",
        "help": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Generate New — Create a new email\n"
            "📥 Inbox — View received emails\n"
            "🔄 Refresh — Check new emails\n"
            "👥 /refer — Refer & Earn\n"
            "💰 /balance — Check balance\n"
            "💸 Withdraw — Request withdrawal\n\n"
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
            "Sorry! This command is available only for administrators."
        ),
        "broadcast_start": (
            "📢 <b>Broadcast Mode</b>\n\n"
            "Use:\n<code>/broadcast Your message</code>"
        ),
        "broadcast_done": (
            "✅ <b>Broadcast completed!</b>\n\n"
            "📤 Sent: <b>{sent}</b>\n"
            "❌ Failed: <b>{failed}</b>"
        ),
        "admin_panel": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 You have administrator access."
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
        "refer": "👥 Refer System",
        "balance": "💰 Balance",
        "withdraw": "💸 Withdraw",
        "checking": "🔎 <b>আপনার Inbox check করা হচ্ছে...</b>",
        "empty": "📭 <b>Inbox খালি।</b>\n\nএখনো কোনো নতুন Message আসেনি।",
        "no_mailbox": (
            "⚠️ <b>কোনো Temporary Email পাওয়া যায়নি।</b>\n\n"
            "প্রথমে নতুন Email তৈরি করুন।"
        ),
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
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": (
            "🔐 <b>Verification Code:</b>\n"
            "<code>{code}</code>\n\n"
            "💰 <b>You earned:</b> $0.00130"
        ),
        "copy_code": "📋 Code Copy করুন",
        "inbox_footer": "━━━━━━━━━━━━━━━━━━\n📥 <b>Inbox</b>\n━━━━━━━━━━━━━━━━━━",
        "refer_title": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      👥 <b>REFER & EARN</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        ),
        "refer_body": (
            "💰 প্রতি সফল Refer: <b>$0.00158</b>\n"
            "👥 মোট Refer: <b>{count}</b>\n\n"
            "🔗 <b>আপনার Referral Link:</b>\n"
            "<code>{link}</code>\n\n"
            "বন্ধুদের সাথে Link share করুন।"
        ),
        "balance_text": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        💰 <b>BALANCE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 <b>বর্তমান Balance:</b> ${balance}\n"
            "👥 <b>মোট Refer:</b> {referrals}\n"
            "📧 <b>Code Reward:</b> {codes}\n\n"
            "Minimum Withdrawal: <b>$1.00</b>"
        ),
        "send_binance": "💸 <b>Withdraw</b>\n\nআপনার <b>Binance ID</b> পাঠান:",
        "send_amount": (
            "💰 এখন withdrawal amount পাঠান।\n\n"
            "Minimum: <b>$1.00</b>\n"
            "Available: <b>${balance}</b>"
        ),
        "invalid_amount": "❌ সঠিক amount দিন।",
        "min_withdraw": "❌ Minimum withdrawal হলো <b>$1.00</b>।",
        "insufficient": "❌ আপনার Balance যথেষ্ট নয়।",
        "withdraw_success": (
            "✅ <b>Withdrawal Request Submitted</b>\n\n"
            "💸 Amount: <b>${amount}</b>\n"
            "🆔 Binance ID: <code>{binance}</code>\n"
            "💰 Remaining Balance: <b>${balance}</b>\n\n"
            "📨 আপনার withdrawal request admin-এর কাছে পাঠানো হয়েছে।"
        ),
        "withdraw_failed": "❌ Withdrawal request failed। আবার চেষ্টা করুন।",
        "cancelled": "❌ Withdrawal cancelled.",
        "help": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ নতুন তৈরি করুন — নতুন Email\n"
            "📥 ইনবক্স — আসা Email দেখুন\n"
            "🔄 রিফ্রেশ — নতুন Email check করুন\n"
            "👥 /refer — Refer & Earn\n"
            "💰 /balance — Balance দেখুন\n"
            "💸 Withdraw — Demo withdrawal\n\n"
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
            "দুঃখিত! এই Command শুধুমাত্র Administrator-এর জন্য।"
        ),
        "broadcast_start": (
            "📢 <b>Broadcast Mode</b>\n\n"
            "ব্যবহার করুন:\n<code>/broadcast আপনার Message</code>"
        ),
        "broadcast_done": (
            "✅ <b>Broadcast সম্পন্ন!</b>\n\n"
            "📤 পাঠানো হয়েছে: <b>{sent}</b>\n"
            "❌ Failed: <b>{failed}</b>"
        ),
        "admin_panel": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 আপনার Administrator access আছে।"
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
        "refer": "👥 Refer System",
        "balance": "💰 Balance",
        "withdraw": "💸 Withdraw",
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
        "message_content": "💬 <b>Message:</b>\n{body}",
        "verification": (
            "🔐 <b>Verification Code:</b>\n"
            "<code>{code}</code>\n\n"
            "💰 <b>You earned:</b> $0.00130"
        ),
        "copy_code": "📋 Copy Code",
        "inbox_footer": "━━━━━━━━━━━━━━━━━━\n📥 <b>Inbox</b>\n━━━━━━━━━━━━━━━━━━",
        "refer_title": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      👥 <b>REFER & EARN</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        ),
        "refer_body": (
            "💰 प्रति सफल Refer: <b>$0.00158</b>\n"
            "👥 कुल Refer: <b>{count}</b>\n\n"
            "🔗 <b>Your Referral Link:</b>\n"
            "<code>{link}</code>\n\n"
            "दोस्तों के साथ Link share करें।"
        ),
        "balance_text": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        💰 <b>BALANCE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "💵 <b>Current Balance:</b> ${balance}\n"
            "👥 <b>Total Refers:</b> {referrals}\n"
            "📧 <b>Code Rewards:</b> {codes}\n\n"
            "Minimum Withdrawal: <b>$1.00</b>"
        ),
        "send_binance": "💸 <b>Withdraw</b>\n\nApna <b>Binance ID</b> bhejein:",
        "send_amount": (
            "💰 Withdrawal amount bhejein.\n\n"
            "Minimum: <b>$1.00</b>\n"
            "Available: <b>${balance}</b>"
        ),
        "invalid_amount": "❌ Valid amount bhejein.",
        "min_withdraw": "❌ Minimum withdrawal <b>$1.00</b> hai.",
        "insufficient": "❌ Insufficient balance.",
        "withdraw_success": (
            "✅ <b>Withdrawal Request Submitted</b>\n\n"
            "💸 Amount: <b>${amount}</b>\n"
            "🆔 Binance ID: <code>{binance}</code>\n"
            "💰 Remaining Balance: <b>${balance}</b>\n\n"
            "📨 Demo withdrawal request recorded."
        ),
        "withdraw_failed": "❌ Withdrawal request failed. Dobara try karein.",
        "cancelled": "❌ Withdrawal cancelled.",
        "help": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Naya Generate — Naya Email\n"
            "📥 Inbox — Received emails dekhein\n"
            "🔄 Refresh — Naye emails check karein\n"
            "👥 /refer — Refer & Earn\n"
            "💰 /balance — Balance dekhein\n"
            "💸 Withdraw — Demo withdrawal\n\n"
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
            "Maaf kijiye! Yeh command sirf Administrator ke liye hai."
        ),
        "broadcast_start": (
            "📢 <b>Broadcast Mode</b>\n\n"
            "Use karein:\n<code>/broadcast Your message</code>"
        ),
        "broadcast_done": (
            "✅ <b>Broadcast complete ho gaya!</b>\n\n"
            "📤 Sent: <b>{sent}</b>\n"
            "❌ Failed: <b>{failed}</b>"
        ),
        "admin_panel": (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 Aapke paas Administrator access hai."
        ),
    },
}

# ============================================================
# KEYBOARDS
# Main screen: exactly 3 buttons
# 1) Generate New + Refresh
# 2) Refer System
# ============================================================

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn")],
        [InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_hi")],
    ])


def main_keyboard(lang):
    """
    Telegram Reply Keyboard:
    এই keyboard-টি message/input box-এর নিচে থাকে,
    inline message-এর ভিতরে নয়।
    """
    t = TEXT[lang]

    return ReplyKeyboardMarkup(
        [
            [
                t["generate"],
                t["refresh"],
            ],
            [
                t["refer"],
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
        input_field_placeholder="Select an option...",
    )


def balance_keyboard(lang):
    t = TEXT[lang]

    return ReplyKeyboardMarkup(
        [
            [t["withdraw"]],
            [t["generate"], t["refresh"]],
            [t["refer"]],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def copy_code_keyboard(code, lang):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                TEXT[lang]["copy_code"],
                copy_text=CopyTextButton(text=str(code)),
            )
        ]
    ])


# ============================================================
# MAIN REPLY-KEYBOARD BUTTONS
# ============================================================

async def start_withdraw_message(message, user_id, lang):
    """Withdraw শুরু করবে ReplyKeyboard-এর button থেকে."""
    current = Decimal(str(get_balance(user_id)))

    if current < MIN_WITHDRAW:
        await message.reply_text(
            (
                "❌ <b>Minimum Withdrawal: $1.00</b>\n\n"
                f"💰 Your current balance: <b>${fmt_money(current)}</b>\n"
                "আপনার balance $1.00 হলে withdrawal করতে পারবেন।"
            ),
            reply_markup=balance_keyboard(lang),
            parse_mode="HTML",
        )
        return

    WITHDRAW_STATE[user_id] = {
        "step": "binance",
        "binance_id": None,
    }

    await message.reply_text(
        TEXT[lang]["send_binance"],
        reply_markup=ReplyKeyboardMarkup(
            [["/cancel"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
        parse_mode="HTML",
    )


async def main_button_handler(update, context):
    """
    Main custom keyboard-এর button click handle করে।
    Button-গুলো Telegram-এর input field-এর নিচে দেখাবে।
    """
    user = update.effective_user
    message = update.message

    if not user or not message or not message.text:
        return

    value = message.text.strip()
    user_id = user.id
    lang = user_lang(user_id)

    t = TEXT[lang]

    # Generate New
    if value == t["generate"]:
        await generate_new(message, user_id, lang)
        return

    # Refresh
    if value == t["refresh"]:
        await show_inbox(message, user_id, lang)
        return

    # Refer System
    if value == t["refer"]:
        await show_refer(message, user_id, lang)
        return

    # Withdraw
    if value == t["withdraw"]:
        await start_withdraw_message(message, user_id, lang)
        return

    # If not a known button, do nothing here so the next
    # text handler can process withdrawal input.
    return


# ============================================================
# HELPERS
# ============================================================


# ============================================================

def user_lang(user_id):
    try:
        lang = get_language(user_id)
    except Exception:
        lang = None
    return lang if lang in TEXT else "en"


def safe(value):
    return html.escape("" if value is None else str(value))


def is_admin(user_id):
    return user_id in ADMIN_IDS


def dhaka_time():
    return datetime.now(DHAKA_TZ).strftime("%d %b %Y, %I:%M:%S %p")


def fmt_money(value):
    try:
        return f"{Decimal(str(value)):.8f}".rstrip("0").rstrip(".")
    except Exception:
        return "0"

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
    for value in (
        item.get("id"),
        item.get("messageId"),
        item.get("_id"),
        item.get("uid"),
    ):
        if value is not None:
            return str(value)

    raw = (
        str(item.get("subject", ""))
        + "|" + str(item.get("date", ""))
        + "|" + str(item.get("createdAt", ""))
        + "|" + str(item.get("from", ""))
        + "|" + str(item.get("intro", ""))
        + "|" + str(item.get("text", ""))
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

                content_type = response.headers.get(
                    "Content-Type",
                    "",
                )

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

# ============================================================
# MAIL PARSING
# ============================================================

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

    subject = (
        item.get("subject")
        or "(No Subject)"
    )

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

    return (
        str(sender),
        str(subject),
        str(body),
    )

# ============================================================
# EMAIL DISPLAY
# ============================================================

def build_mail(item, lang):
    t = TEXT[lang]

    sender, subject, body = parse_mail(item)
    code = extract_code(body)

    if code:
        content = t["verification"].format(
            code=safe(code),
        )
        keyboard = copy_code_keyboard(
            code,
            lang,
        )
    else:
        content = t["message_content"].format(
            body=safe(body[:1500]),
        )
        keyboard = None

    text = t["new_mail"].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(dhaka_time()),
        content=content,
    )

    return text, keyboard, code


async def send_inbox_mail(bot, user_id, item, lang):
    text, keyboard, code = build_mail(item, lang)

    await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    # Code reward: exactly once for this user + message.
    if code:
        message_key = get_message_id(item)
        try:
            added, new_balance = add_email_reward_once(
                user_id=user_id,
                message_key=message_key,
                code=code,
                amount=float(EMAIL_CODE_REWARD),
            )
            if added:
                logger.info(
                    "Code reward $%s added to user %s. Balance=%s",
                    EMAIL_CODE_REWARD,
                    user_id,
                    new_balance,
                )
        except Exception as error:
            logger.error(
                "Email reward error user=%s: %s",
                user_id,
                error,
            )

# ============================================================
# GENERATE
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

    await loading.edit_text(
        t["created"].format(
            email=safe(email),
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML",
    )

    return True

# ============================================================
# REFERRAL
# ============================================================

async def make_referral_link(bot, user_id):
    me = await bot.get_me()
    username = me.username

    if not username:
        return f"tg://user?id={user_id}"

    return f"https://t.me/{username}?start={user_id}"


async def show_refer(message, user_id, lang):
    t = TEXT[lang]
    count = get_referral_count(user_id)
    link = await make_referral_link(message.get_bot(), user_id)

    text = (
        t["refer_title"]
        + t["refer_body"].format(
            count=count,
            link=safe(link),
        )
    )

    await message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard(lang),
    )


async def process_referral(user_id, payload):
    if not payload:
        return

    try:
        referrer_id = int(payload)
    except (TypeError, ValueError):
        return

    if referrer_id == user_id:
        return

    try:
        # Only the first referrer is accepted.
        accepted = set_referrer(
            user_id,
            referrer_id,
        )

        if not accepted:
            return

        added, new_balance = add_referral_once(
            referrer_id,
            user_id,
            float(REFERRAL_REWARD),
        )

        if added:
            logger.info(
                "Referral reward $%s -> %s",
                REFERRAL_REWARD,
                referrer_id,
            )

    except Exception as error:
        logger.error(
            "Referral processing error: %s",
            error,
        )

# ============================================================
# START
# ============================================================

async def start(update, context):
    user = update.effective_user

    if not user:
        return

    save_user(
        user.id,
        user.username,
    )

    payload = None
    if context.args:
        payload = context.args[0]

    if payload:
        await process_referral(
            user.id,
            payload,
        )

    lang = get_language(user.id)

    if not lang:
        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML",
        )
        return

    lang = user_lang(user.id)

    mailbox = get_mailbox(user.id)

    if mailbox:
        await update.message.reply_text(
            TEXT[lang]["created"].format(
                email=safe(mailbox.get("email", "")),
            ),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )
    else:
        await generate_new(
            update.message,
            user.id,
            lang,
        )

# ============================================================
# BALANCE
# ============================================================

async def balance_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    current = get_balance(user_id)
    referrals = get_referral_count(user_id)
    codes = get_reward_count(user_id)

    await update.message.reply_text(
        TEXT[lang]["balance_text"].format(
            balance=fmt_money(current),
            referrals=referrals,
            codes=codes,
        ),
        reply_markup=balance_keyboard(lang),
        parse_mode="HTML",
    )

# ============================================================
# WITHDRAW
# ============================================================

async def start_withdraw(query, user_id, lang):
    current = Decimal(str(get_balance(user_id)))

    if current < MIN_WITHDRAW:
        await query.answer(
            "Minimum withdrawal is $1.00.",
            show_alert=True,
        )
        return

    WITHDRAW_STATE[user_id] = {
        "step": "binance",
        "binance_id": None,
    }

    await query.answer()

    await query.message.reply_text(
        TEXT[lang]["send_binance"],
        reply_markup=ReplyKeyboardMarkup(
            [["/cancel"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
        parse_mode="HTML",
    )


async def handle_withdraw_text(update, context):
    user = update.effective_user

    if not user:
        return

    user_id = user.id
    state = WITHDRAW_STATE.get(user_id)

    if not state:
        return

    lang = user_lang(user_id)
    value = (update.message.text or "").strip()

    if value.lower() in {"/cancel", "cancel"}:
        WITHDRAW_STATE.pop(user_id, None)
        await update.message.reply_text(
            TEXT[lang]["cancelled"],
            parse_mode="HTML",
        )
        return

    if state["step"] == "binance":
        if not value or len(value) > 100:
            await update.message.reply_text(
                "❌ Please send a valid Binance ID.",
            )
            return

        state["binance_id"] = value
        state["step"] = "amount"

        current = get_balance(user_id)

        await update.message.reply_text(
            TEXT[lang]["send_amount"].format(
                balance=fmt_money(current),
            ),
            parse_mode="HTML",
        )
        return

    if state["step"] == "amount":
        try:
            amount = Decimal(value.replace("$", "").strip())
        except Exception:
            await update.message.reply_text(
                TEXT[lang]["invalid_amount"],
                parse_mode="HTML",
            )
            return

        if amount < MIN_WITHDRAW:
            await update.message.reply_text(
                TEXT[lang]["min_withdraw"],
                parse_mode="HTML",
            )
            return

        current = Decimal(str(get_balance(user_id)))

        if amount > current:
            await update.message.reply_text(
                TEXT[lang]["insufficient"],
                parse_mode="HTML",
            )
            return

        try:
            withdrawal_id = create_withdrawal(
                user_id=user_id,
                binance_id=state["binance_id"],
                amount=float(amount),
            )
        except Exception as error:
            logger.error(
                "Withdrawal error user=%s: %s",
                user_id,
                error,
            )
            withdrawal_id = None

        if not withdrawal_id:
            await update.message.reply_text(
                TEXT[lang]["withdraw_failed"],
                parse_mode="HTML",
            )
            return

        WITHDRAW_STATE.pop(user_id, None)

        remaining = get_balance(user_id)

        # Notify configured admins about the withdrawal request.
        admin_notice = (
            "💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"💰 Amount: <b>${fmt_money(amount)}</b>\n"
            f"🆔 Binance ID: <code>{safe(state['binance_id'])}</code>\n"
            f"🧾 Request ID: <code>{withdrawal_id}</code>\n"
            f"💵 Remaining Balance: <b>${fmt_money(remaining)}</b>"
        )

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_notice,
                    parse_mode="HTML",
                )
            except Exception as error:
                logger.error(
                    "Admin withdrawal notification failed admin=%s: %s",
                    admin_id,
                    error,
                )

        await update.message.reply_text(
            TEXT[lang]["withdraw_success"].format(
                amount=fmt_money(amount),
                binance=safe(state["binance_id"]),
                balance=fmt_money(remaining),
            ),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
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
        mailbox.get("token"),
    )

    if not data:
        await loading.edit_text(
            t["api_error"],
            reply_markup=main_keyboard(lang),
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

    await message.reply_text(
        t["inbox_footer"],
        reply_markup=main_keyboard(lang),
        parse_mode="HTML",
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


async def refer_command(update, context):
    user_id = update.effective_user.id
    await show_refer(
        update.message,
        user_id,
        user_lang(user_id),
    )


async def language_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang].get(
            "language",
            "🌐 Select your language:",
        ),
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


async def stats_command(update, context):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    try:
        users = get_all_users()
        total_users = len(users)

        total_mailboxes = 0

        for uid in users:
            try:
                if get_mailbox(uid):
                    total_mailboxes += 1
            except Exception:
                pass

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
    if not is_admin(update.effective_user.id):
        await admin_only(update)
        return

    lang = user_lang(update.effective_user.id)

    await update.message.reply_text(
        TEXT[lang]["admin_panel"],
        parse_mode="HTML",
    )


async def broadcast_command(update, context):
    if not is_admin(update.effective_user.id):
        await admin_only(update)
        return

    lang = user_lang(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            TEXT[lang]["broadcast_start"],
            parse_mode="HTML",
        )
        return

    broadcast_text = " ".join(context.args)
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
# CALLBACK
# ============================================================

async def callback_handler(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data or ""

    # --------------------------------------------------------
    # LANGUAGE
    # --------------------------------------------------------

    if data.startswith("lang_"):
        lang = data.replace("lang_", "")

        if lang not in TEXT:
            lang = "en"

        await query.answer()

        set_language(
            user_id,
            lang,
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

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    if data == "generate":
        await query.answer()

        lang = user_lang(user_id)

        await generate_new(
            query.message,
            user_id,
            lang,
        )
        return

    # --------------------------------------------------------
    # REFRESH
    # --------------------------------------------------------

    if data == "refresh":
        await query.answer()

        lang = user_lang(user_id)

        await show_inbox(
            query.message,
            user_id,
            lang,
        )
        return

    # --------------------------------------------------------
    # REFER
    # --------------------------------------------------------

    if data == "refer":
        await query.answer()

        await show_refer(
            query.message,
            user_id,
            user_lang(user_id),
        )
        return

    # --------------------------------------------------------
    # BALANCE
    # --------------------------------------------------------

    if data == "balance":
        await query.answer()

        lang = user_lang(user_id)
        current = get_balance(user_id)
        referrals = get_referral_count(user_id)
        codes = get_reward_count(user_id)

        await query.message.reply_text(
            TEXT[lang]["balance_text"].format(
                balance=fmt_money(current),
                referrals=referrals,
                codes=codes,
            ),
            reply_markup=balance_keyboard(lang),
            parse_mode="HTML",
        )
        return

    # --------------------------------------------------------
    # WITHDRAW
    # --------------------------------------------------------

    if data == "withdraw":
        await start_withdraw(
            query,
            user_id,
            user_lang(user_id),
        )
        return

    await query.answer()

# ============================================================
# AUTO INBOX
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

            seen = SEEN_MESSAGES.setdefault(
                user_id,
                set(),
            )

            lang = user_lang(user_id)

            for item in messages:
                message_id = get_message_id(item)

                if not message_id:
                    continue

                if message_id in seen:
                    continue

                # Mark before sending to prevent duplicate auto-send.
                seen.add(message_id)

                try:
                    await send_inbox_mail(
                        context.bot,
                        user_id,
                        item,
                        lang,
                    )

                    logger.info(
                        "📩 New email sent automatically -> %s",
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
    if not application.job_queue:
        logger.error(
            "JobQueue unavailable. Install: "
            "python-telegram-bot[job-queue]"
        )
        return

    application.job_queue.run_repeating(
        auto_inbox_job,
        interval=POLL_SECONDS,
        first=2,
        name="auto-inbox",
    )

    logger.info(
        "📩 Automatic inbox started: every %s seconds",
        POLL_SECONDS,
    )

# ============================================================
# MAIN
# ============================================================

def main():
    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # User commands
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
        CommandHandler("refer", refer_command)
    )
    application.add_handler(
        CommandHandler("balance", balance_command)
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

    # Admin commands
    application.add_handler(
        CommandHandler("admin", admin_command)
    )
    application.add_handler(
        CommandHandler("broadcast", broadcast_command)
    )
    application.add_handler(
        CommandHandler("boardchat", broadcast_command)
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    # Main ReplyKeyboard buttons.
    # This is intentionally before the generic text handler so
    # Generate/Refresh/Refer/Withdraw are treated as buttons.
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND
            & filters.Regex(
                r"^(?:"
                + "|".join(
                    re.escape(label)
                    for label in sorted(
                        {
                            TEXT[lang][key]
                            for lang in TEXT
                            for key in (
                                "generate",
                                "refresh",
                                "refer",
                                "withdraw",
                            )
                        },
                        key=len,
                        reverse=True,
                    )
                )
                + r")$"
            ),
            main_button_handler,
        )
    )

    # Withdraw text input
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_withdraw_text,
        )
    )

    application.add_error_handler(error_handler)

    print("🤖 Temp Mail Bot is running...")
    print(f"📩 Auto inbox: every {POLL_SECONDS}s")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
