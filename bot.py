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
from zoneinfo import ZoneInfo

import aiohttp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
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

DHAKA_TZ = ZoneInfo("Asia/Dhaka")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# MEMORY CACHE
# ============================================================

# user_id -> set(message ids)
SEEN_MESSAGES = {}

# user_id -> mailbox token
KNOWN_MAILBOX = {}


# ============================================================
# LANGUAGES
# ============================================================

TEXT = {

    # ========================================================
    # ENGLISH
    # ========================================================

    "en": {

        "welcome":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL BOT</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👋 <b>Welcome!</b>\n\n"
            "⚡ Fast temporary email receiver\n"
            "📩 Receive verification emails\n"
            "🔐 Verification codes are detected automatically\n\n"
            "🌐 <b>Please select your preferred language:</b>",

        "language_ok":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      ✅ <b>SUCCESS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Language selected successfully!\n\n"
            "⚡ Creating your temporary email...",

        "generating":
            "⚡ <b>Creating your temporary email...</b>",

        "created":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 <b>NEW TEMP EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n"
            "<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "You can now receive emails here.\n\n"
            "📩 New emails will be detected automatically.",

        "generate":
            "➕ Generate New",

        "inbox":
            "📥 Inbox",

        "refresh":
            "🔄 Refresh",

        "checking":
            "🔎 <b>Checking your inbox...</b>",

        "empty":
            "📭 <b>Inbox is empty.</b>\n\n"
            "No new messages received yet.",

        "no_mailbox":
            "⚠️ <b>No temporary email found.</b>\n\n"
            "Please generate a new email first.",

        "api_error":
            "❌ <b>Something went wrong.</b>\n\n"
            "Please try again later.",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Dhaka Time:</b> {date}\n\n"
            "{content}",

        "message_content":
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>VERIFICATION CODE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔢 <b>Code:</b>\n"
            "<code>{code}</code>\n\n"
            "👇 Tap the button below to copy the code.",

        "copy_code":
            "📋 Copy Code",

        "code_copied":
            "✅ Code: <code>{code}</code>",

        "language":
            "🌐 <b>Select your preferred language:</b>",

        "help":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Generate New — Create a new email\n"
            "📥 Inbox — View received emails\n"
            "🔄 Refresh — Check new emails\n\n"
            "/start — Start bot\n"
            "/language — Change language\n"
            "/inbox — Open inbox\n"
            "/refresh — Refresh inbox\n"
            "/help — Show help\n"
            "/about — About bot\n"
            "/stats — Bot statistics",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast disposable email receiver.\n\n"
            "⚡ Powered by Smails API\n"
            "🔒 No API key required",

        "stats":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 Total Users: <b>{users}</b>\n"
            "📧 Active Mailboxes: <b>{mailboxes}</b>\n"
            "⚡ Auto Inbox: <b>ON</b>\n"
            "🔄 Polling: <b>{seconds}s</b>",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Sorry! This command is available\n"
            "only for administrators.\n\n"
            "❌ You don't have permission.",

        "broadcast_start":
            "📢 <b>Broadcast Mode</b>\n\n"
            "Use:\n"
            "<code>/broadcast Your message</code>",

        "broadcast_done":
            "✅ <b>Broadcast completed!</b>\n\n"
            "📤 Sent: <b>{sent}</b>\n"
            "❌ Failed: <b>{failed}</b>",

        "admin_panel":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 You have administrator access.",
    },


    # ========================================================
    # BANGLA
    # ========================================================

    "bn": {

        "welcome":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL BOT</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👋 <b>স্বাগতম!</b>\n\n"
            "⚡ দ্রুত Temporary Email receiver\n"
            "📩 Verification Email গ্রহণ করুন\n"
            "🔐 Verification Code Automatic Detect হবে\n\n"
            "🌐 <b>আপনার পছন্দের ভাষা নির্বাচন করুন:</b>",

        "language_ok":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      ✅ <b>সফল হয়েছে</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "ভাষা সফলভাবে নির্বাচন করা হয়েছে!\n\n"
            "⚡ আপনার Temporary Email তৈরি হচ্ছে...",

        "generating":
            "⚡ <b>আপনার Temporary Email তৈরি হচ্ছে...</b>",

        "created":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 <b>নতুন TEMP EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n"
            "<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "এখন এই Email-এ Message গ্রহণ করতে পারবেন।\n\n"
            "📩 নতুন Email এলে Automatic দেখাবে।",

        "generate":
            "➕ নতুন তৈরি করুন",

        "inbox":
            "📥 ইনবক্স",

        "refresh":
            "🔄 রিফ্রেশ",

        "checking":
            "🔎 <b>আপনার Inbox check করা হচ্ছে...</b>",

        "empty":
            "📭 <b>Inbox খালি।</b>\n\n"
            "এখনো কোনো নতুন Message আসেনি।",

        "no_mailbox":
            "⚠️ <b>কোনো Temporary Email পাওয়া যায়নি।</b>\n\n"
            "প্রথমে নতুন Email তৈরি করুন।",

        "api_error":
            "❌ <b>সমস্যা হয়েছে।</b>\n\n"
            "কিছুক্ষণ পর আবার চেষ্টা করুন।",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>নতুন EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>ঢাকা সময়:</b> {date}\n\n"
            "{content}",

        "message_content":
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>VERIFICATION CODE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔢 <b>Code:</b>\n"
            "<code>{code}</code>\n\n"
            "👇 Code Copy করতে নিচের Button চাপুন।",

        "copy_code":
            "📋 Code Copy করুন",

        "code_copied":
            "✅ Code: <code>{code}</code>",

        "language":
            "🌐 <b>আপনার পছন্দের ভাষা নির্বাচন করুন:</b>",

        "help":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ নতুন তৈরি করুন — নতুন Email\n"
            "📥 ইনবক্স — আসা Email দেখুন\n"
            "🔄 রিফ্রেশ — নতুন Email check করুন\n\n"
            "/start — Bot শুরু করুন\n"
            "/language — ভাষা পরিবর্তন\n"
            "/inbox — Inbox দেখুন\n"
            "/refresh — Inbox Refresh\n"
            "/help — Help দেখুন\n"
            "/about — Bot সম্পর্কে\n"
            "/stats — Bot Statistics",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দ্রুত Temporary Email receiver।\n\n"
            "⚡ Smails API দ্বারা পরিচালিত\n"
            "🔒 API key প্রয়োজন নেই",

        "stats":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 Total Users: <b>{users}</b>\n"
            "📧 Active Mailboxes: <b>{mailboxes}</b>\n"
            "⚡ Auto Inbox: <b>ON</b>\n"
            "🔄 Checking: প্রতি <b>{seconds}s</b>",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দুঃখিত! এই Command শুধুমাত্র\n"
            "Administrator-এর জন্য।\n\n"
            "❌ আপনার অনুমতি নেই।",

        "broadcast_start":
            "📢 <b>Broadcast Mode</b>\n\n"
            "ব্যবহার করুন:\n"
            "<code>/broadcast আপনার Message</code>",

        "broadcast_done":
            "✅ <b>Broadcast সম্পন্ন!</b>\n\n"
            "📤 পাঠানো হয়েছে: <b>{sent}</b>\n"
            "❌ Failed: <b>{failed}</b>",

        "admin_panel":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 আপনার Administrator access আছে।",
    },


    # ========================================================
    # HINDI
    # ========================================================

    "hi": {

        "welcome":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL BOT</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👋 <b>Swagat hai!</b>\n\n"
            "⚡ Fast Temporary Email\n"
            "📩 Verification Email receive karein\n"
            "🔐 Verification Code automatically detect hoga\n\n"
            "🌐 <b>Apni pasand ki language select karein:</b>",

        "language_ok":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      ✅ <b>SUCCESS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Language successfully select ho gayi!\n\n"
            "⚡ Aapka Temporary Email create ho raha hai...",

        "generating":
            "⚡ <b>Aapka Temporary Email create ho raha hai...</b>",

        "created":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   📧 <b>NEW TEMP EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "📮 <b>Email:</b>\n"
            "<code>{email}</code>\n\n"
            "🟢 <b>Status:</b> Active\n\n"
            "Ab aap is Email par messages receive kar sakte hain.\n\n"
            "📩 Naya Email aate hi automatically dikhega.",

        "generate":
            "➕ Naya Generate",

        "inbox":
            "📥 Inbox",

        "refresh":
            "🔄 Refresh",

        "checking":
            "🔎 <b>Aapka Inbox check ho raha hai...</b>",

        "empty":
            "📭 <b>Inbox empty hai.</b>\n\n"
            "Abhi koi naya message nahi aaya.",

        "no_mailbox":
            "⚠️ <b>Koi Temporary Email nahi mila.</b>\n\n"
            "Pehle naya Email generate karein.",

        "api_error":
            "❌ <b>Kuch problem ho gayi.</b>\n\n"
            "Thodi der baad dobara try karein.",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Email\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Dhaka Time:</b> {date}\n\n"
            "{content}",

        "message_content":
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>VERIFICATION CODE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔢 <b>Code:</b>\n"
            "<code>{code}</code>\n\n"
            "👇 Code copy karne ke liye button dabayein.",

        "copy_code":
            "📋 Copy Code",

        "code_copied":
            "✅ Code: <code>{code}</code>",

        "language":
            "🌐 <b>Apni pasand ki language select karein:</b>",

        "help":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Naya Generate — Naya Email\n"
            "📥 Inbox — Received emails dekhein\n"
            "🔄 Refresh — Naye emails check karein\n\n"
            "/start — Bot start karein\n"
            "/language — Language change karein\n"
            "/inbox — Inbox dekhein\n"
            "/refresh — Inbox refresh karein\n"
            "/help — Help dekhein\n"
            "/about — Bot ke baare mein\n"
            "/stats — Bot Statistics",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast Temporary Email receiver.\n\n"
            "⚡ Smails API se powered\n"
            "🔒 API key ki zarurat nahi",

        "stats":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 Total Users: <b>{users}</b>\n"
            "📧 Active Mailboxes: <b>{mailboxes}</b>\n"
            "⚡ Auto Inbox: <b>ON</b>\n"
            "🔄 Checking: <b>{seconds}s</b>",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Maaf kijiye! Yeh command sirf\n"
            "Administrator ke liye hai.\n\n"
            "❌ Aapko permission nahi hai.",

        "broadcast_start":
            "📢 <b>Broadcast Mode</b>\n\n"
            "Use karein:\n"
            "<code>/broadcast Your message</code>",

        "broadcast_done":
            "✅ <b>Broadcast complete ho gaya!</b>\n\n"
            "📤 Sent: <b>{sent}</b>\n"
            "❌ Failed: <b>{failed}</b>",

        "admin_panel":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       👑 <b>ADMIN PANEL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🔐 Aapke paas Administrator access hai.",
    },
}


# ============================================================
# LANGUAGE KEYBOARD
# ============================================================

def language_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🇺🇸 English",
                callback_data="lang_en"
            )
        ],
        [
            InlineKeyboardButton(
                "🇧🇩 বাংলা",
                callback_data="lang_bn"
            )
        ],
        [
            InlineKeyboardButton(
                "🇮🇳 Hindi",
                callback_data="lang_hi"
            )
        ]
    ])


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard(lang):

    t = TEXT[lang]

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t["generate"],
                callback_data="generate"
            ),
            InlineKeyboardButton(
                t["inbox"],
                callback_data="inbox"
            )
        ],
        [
            InlineKeyboardButton(
                t["refresh"],
                callback_data="refresh"
            )
        ]
    ])


# ============================================================
# COPY BUTTON
# ============================================================

def code_keyboard(code, lang="en"):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                TEXT[lang]["copy_code"],
                copy_text=CopyTextButton(
                    text=str(code)
                )
            )
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

    if lang not in TEXT:
        return "en"

    return lang


def safe(value):

    if value is None:
        return ""

    return html.escape(str(value))


def is_admin(user_id):

    return user_id in ADMIN_IDS


# ============================================================
# DHAKA LIVE TIME
# ============================================================

def dhaka_time():

    now = datetime.now(DHAKA_TZ)

    return now.strftime(
        "%d %b %Y, %I:%M:%S %p"
    )


# ============================================================
# CODE DETECTION
# ============================================================

def extract_code(text):

    if not text:
        return None

    text = str(text)

    patterns = [

        r"(?:verification|verify|verification\s*code|otp|code)"
        r"\D{0,30}(\d{4,8})",

        r"(?:one[\s-]*time[\s-]*password)"
        r"\D{0,30}(\d{4,8})",

        r"(?:login\s*code)"
        r"\D{0,30}(\d{4,8})",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1)

    # 6 digit
    match = re.search(
        r"(?<!\d)\d{6}(?!\d)",
        text
    )

    if match:
        return match.group(0)

    # 5 digit
    match = re.search(
        r"(?<!\d)\d{5}(?!\d)",
        text
    )

    if match:
        return match.group(0)

    # 4 digit
    match = re.search(
        r"(?<!\d)\d{4}(?!\d)",
        text
    )

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
        str(item.get("subject", ""))
        + "|"
        + str(item.get("date", ""))
        + "|"
        + str(item.get("createdAt", ""))
        + "|"
        + str(item.get("from", ""))
        + "|"
        + str(item.get("intro", ""))
        + "|"
        + str(item.get("text", ""))
    )

    return raw


# ============================================================
# API REQUEST
# ============================================================

async def api_request(
    method,
    endpoint,
    token=None
):

    url = API_BASE + endpoint

    headers = {
        "Accept": "application/json"
    }

    if token:

        headers["Authorization"] = (
            f"Bearer {token}"
        )

    timeout = aiohttp.ClientTimeout(
        total=10,
        connect=4,
        sock_read=7
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.request(
                method,
                url,
                headers=headers
            ) as response:

                if response.status >= 400:

                    body = await response.text()

                    logger.error(
                        "API HTTP %s: %s",
                        response.status,
                        body[:500]
                    )

                    return None

                content_type = (
                    response.headers.get(
                        "Content-Type",
                        ""
                    )
                )

                if "json" in content_type.lower():

                    return await response.json(
                        content_type=None
                    )

                text = await response.text()

                try:

                    return json.loads(text)

                except Exception:

                    logger.error(
                        "Invalid API JSON: %s",
                        text[:500]
                    )

                    return None

    except asyncio.TimeoutError:

        logger.warning(
            "API timeout: %s",
            url
        )

        return None

    except Exception as error:

        logger.error(
            "API error: %s",
            error
        )

        return None


# ============================================================
# CREATE MAILBOX
# ============================================================

async def create_mailbox():

    return await api_request(
        "POST",
        "/mailbox"
    )


# ============================================================
# GET MESSAGES
# ============================================================

async def get_messages(token):

    return await api_request(
        "GET",
        "/mailbox/messages",
        token
    )


# ============================================================
# NORMALIZE MESSAGE LIST
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


# ============================================================
# PARSE SENDER
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

        sender = str(
            sender_data
        )

    if not sender:

        sender = (
            item.get("fromEmail")
            or item.get("senderEmail")
            or item.get("email")
            or "Unknown"
        )

    return str(sender)


# ============================================================
# PARSE MAIL
# ============================================================

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
        str(body)
    )


# ============================================================
# BUILD AUTOMATIC EMAIL MESSAGE
# ============================================================

def build_auto_mail_message(
    item,
    lang
):

    t = TEXT[lang]

    sender, subject, body = parse_mail(
        item
    )

    code = extract_code(body)

    # --------------------------------------------------------
    # CODE পাওয়া গেলে email body দেখাবে না।
    # শুধু verification code card দেখাবে।
    # --------------------------------------------------------

    if code:

        content = (
            t["verification"]
            .format(
                code=safe(code)
            )
        )

        keyboard = code_keyboard(
            code
        )

    else:

        # Code না থাকলে সাধারণ message দেখাবে
        content = (
            t["message_content"]
            .format(
                body=safe(
                    body[:1500]
                )
            )
        )

        keyboard = None

    message_text = t[
        "new_mail"
    ].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(
            dhaka_time()
        ),
        content=content
    )

    return (
        message_text,
        keyboard
    )


# ============================================================
# SEND AUTOMATIC EMAIL
# ============================================================

async def send_auto_mail(
    bot,
    user_id,
    item,
    lang
):

    message_text, keyboard = (
        build_auto_mail_message(
            item,
            lang
        )
    )

    await bot.send_message(
        chat_id=user_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============================================================
# SEND NORMAL INBOX EMAIL
# ============================================================

async def send_inbox_mail(
    bot,
    user_id,
    item,
    lang
):

    t = TEXT[lang]

    sender, subject, body = parse_mail(
        item
    )

    code = extract_code(body)

    if code:

        content = (
            t["verification"]
            .format(
                code=safe(code)
            )
        )

        keyboard = code_keyboard(
            code
        )

    else:

        content = (
            t["message_content"]
            .format(
                body=safe(
                    body[:1500]
                )
            )
        )

        keyboard = None

    message_text = t[
        "new_mail"
    ].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(
            dhaka_time()
        ),
        content=content
    )

    await bot.send_message(
        chat_id=user_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============================================================
# GENERATE NEW MAILBOX
# ============================================================

async def generate_new(
    message,
    user_id,
    lang
):

    t = TEXT[lang]

    loading = await message.reply_text(
        t["generating"],
        parse_mode="HTML"
    )

    mailbox = await create_mailbox()

    if not mailbox:

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )

        return False

    # --------------------------------------------------------
    # API response-এর বিভিন্ন possible structure
    # --------------------------------------------------------

    data = mailbox

    if isinstance(
        mailbox.get("data"),
        dict
    ):

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
            mailbox
        )

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )

        return False

    save_mailbox(
        user_id,
        email,
        token
    )

    # নতুন mailbox হলে পুরোনো mail cache clear
    SEEN_MESSAGES[user_id] = set()

    KNOWN_MAILBOX[user_id] = token

    await loading.edit_text(
        t["created"].format(
            email=safe(email)
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )

    return True


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    save_user(
        user.id,
        user.username
    )

    lang = get_language(
        user.id
    )

    # প্রথমবার
    if not lang:

        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML"
        )

        return

    lang = user_lang(
        user.id
    )

    mailbox = get_mailbox(
        user.id
    )

    if mailbox:

        await update.message.reply_text(
            TEXT[lang]["created"].format(
                email=safe(
                    mailbox.get(
                        "email",
                        ""
                    )
                )
            ),
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML"
        )

    else:

        await generate_new(
            update.message,
            user.id,
            lang
        )


# ============================================================
# INBOX
# ============================================================

async def show_inbox(
    message,
    user_id,
    lang
):

    t = TEXT[lang]

    mailbox = get_mailbox(
        user_id
    )

    if not mailbox:

        await message.reply_text(
            t["no_mailbox"],
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML"
        )

        return

    loading = await message.reply_text(
        t["checking"],
        parse_mode="HTML"
    )

    data = await get_messages(
        mailbox.get("token")
    )

    if not data:

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )

        return

    messages = extract_messages(
        data
    )

    if not messages:

        await loading.edit_text(
            t["empty"],
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML"
        )

        return

    try:

        await loading.delete()

    except Exception:
        pass

    # Latest first
    messages = list(
        reversed(messages)
    )

    for item in messages[:MAX_MESSAGES]:

        try:

            await send_inbox_mail(
                message.get_bot(),
                user_id,
                item,
                lang
            )

        except Exception as error:

            logger.error(
                "Inbox message error: %s",
                error
            )

    # Inbox শেষ হলে button সহ ছোট footer
    await message.reply_text(
        "━━━━━━━━━━━━━━━━━━\n"
        "📥 <b>Inbox</b>\n"
        "━━━━━━━━━━━━━━━━━━",
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
    )


# ============================================================
# REFRESH
# ============================================================

async def refresh_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    await show_inbox(
        update.message,
        user_id,
        lang
    )


# ============================================================
# INBOX COMMAND
# ============================================================

async def inbox_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    await show_inbox(
        update.message,
        user_id,
        lang
    )


# ============================================================
# LANGUAGE
# ============================================================

async def language_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["language"],
        reply_markup=language_keyboard(),
        parse_mode="HTML"
    )


# ============================================================
# HELP
# ============================================================

async def help_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["help"],
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
    )


# ============================================================
# ABOUT
# ============================================================

async def about_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["about"],
        parse_mode="HTML"
    )


# ============================================================
# STATS
# ============================================================

async def stats_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    try:

        users = get_all_users()

        total_users = len(
            users
        )

        total_mailboxes = 0

        for uid in users:

            try:

                mailbox = get_mailbox(
                    uid
                )

                if mailbox:
                    total_mailboxes += 1

            except Exception:
                continue

    except Exception as error:

        logger.error(
            "Stats error: %s",
            error
        )

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

    lang = user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["admin_only"],
        parse_mode="HTML"
    )


async def admin_command(
    update,
    context
):

    if not is_admin(
        update.effective_user.id
    ):

        await admin_only(
            update
        )

        return

    lang = user_lang(
        update.effective_user.id
    )

    await update.message.reply_text(
        TEXT[lang]["admin_panel"],
        parse_mode="HTML"
    )


# ============================================================
# BROADCAST
# ============================================================

async def broadcast_command(
    update,
    context
):

    if not is_admin(
        update.effective_user.id
    ):

        await admin_only(
            update
        )

        return

    lang = user_lang(
        update.effective_user.id
    )

    if not context.args:

        await update.message.reply_text(
            TEXT[lang]["broadcast_start"],
            parse_mode="HTML"
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
                parse_mode="HTML"
            )

            sent += 1

            await asyncio.sleep(
                0.05
            )

        except Exception:

            failed += 1

    await update.message.reply_text(
        TEXT[lang]["broadcast_done"].format(
            sent=sent,
            failed=failed
        ),
        parse_mode="HTML"
    )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(
    update,
    context
):

    query = update.callback_query

    user_id = query.from_user.id

    data = query.data or ""

    # ========================================================
    # LANGUAGE
    # ========================================================

    if data.startswith("lang_"):

        lang = data.replace(
            "lang_",
            ""
        )

        if lang not in TEXT:
            lang = "en"

        await query.answer()

        set_language(
            user_id,
            lang
        )

        try:

            await query.edit_message_text(
                TEXT[lang]["language_ok"],
                parse_mode="HTML"
            )

        except Exception:
            pass

        # Language select করার পর automatic email generate
        await generate_new(
            query.message,
            user_id,
            lang
        )

        return

    # ========================================================
    # GENERATE
    # ========================================================

    if data == "generate":

        await query.answer()

        lang = user_lang(
            user_id
        )

        await generate_new(
            query.message,
            user_id,
            lang
        )

        return

    # ========================================================
    # INBOX
    # ========================================================

    if data == "inbox":

        await query.answer()

        lang = user_lang(
            user_id
        )

        await show_inbox(
            query.message,
            user_id,
            lang
        )

        return

    # ========================================================
    # REFRESH
    # ========================================================

    if data == "refresh":

        await query.answer()

        lang = user_lang(
            user_id
        )

        await show_inbox(
            query.message,
            user_id,
            lang
        )

        return

    # ========================================================
    # COPY FALLBACK
    # ========================================================

    if data.startswith("copy:"):

        code = data.split(
            ":",
            1
        )[1]

        lang = user_lang(
            user_id
        )

        await query.answer(
            TEXT[lang]["code_copied"].format(
                code=safe(code)
            ),
            show_alert=True
        )

        return

    await query.answer()


# ============================================================
# AUTOMATIC INBOX JOB
# ============================================================

async def auto_inbox_job(
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        users = get_all_users()

    except Exception as error:

        logger.error(
            "Could not load users: %s",
            error
        )

        return

    for user_id in users:

        try:

            mailbox = get_mailbox(
                user_id
            )

            if not mailbox:
                continue

            token = mailbox.get(
                "token"
            )

            if not token:
                continue

            # ------------------------------------------------
            # New mailbox detect
            # ------------------------------------------------

            if KNOWN_MAILBOX.get(
                user_id
            ) != token:

                KNOWN_MAILBOX[
                    user_id
                ] = token

                SEEN_MESSAGES[
                    user_id
                ] = set()

            # ------------------------------------------------
            # Get messages
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Seen list
            # ------------------------------------------------

            seen = SEEN_MESSAGES.setdefault(
                user_id,
                set()
            )

            lang = user_lang(
                user_id
            )

            # Oldest first
            for item in messages:

                message_id = get_message_id(
                    item
                )

                if not message_id:
                    continue

                if message_id in seen:
                    continue

                # Mark before sending
                seen.add(
                    message_id
                )

                try:

                    await send_auto_mail(
                        context.bot,
                        user_id,
                        item,
                        lang
                    )

                    logger.info(
                        "📩 New email sent automatically -> %s",
                        user_id
                    )

                except Exception as error:

                    logger.error(
                        "Auto send error user=%s: %s",
                        user_id,
                        error
                    )

            # ------------------------------------------------
            # Memory limit
            # ------------------------------------------------

            if len(seen) > 200:

                SEEN_MESSAGES[
                    user_id
                ] = set(
                    list(seen)[-100:]
                )

        except Exception as error:

            logger.error(
                "Auto inbox error user=%s: %s",
                user_id,
                error
            )

        # API load কমানোর জন্য
        await asyncio.sleep(
            0.05
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context
):

    logger.error(
        "Unhandled error",
        exc_info=context.error
    )


# ============================================================
# POST INIT
# ============================================================

async def post_init(
    application
):

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
        name="auto-inbox"
    )

    logger.info(
        "📩 Automatic inbox started: every %s seconds",
        POLL_SECONDS
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # Database initialize
    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ========================================================
    # USER COMMANDS
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "inbox",
            inbox_command
        )
    )

    application.add_handler(
        CommandHandler(
            "refresh",
            refresh_command
        )
    )

    application.add_handler(
        CommandHandler(
            "language",
            language_command
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    application.add_handler(
        CommandHandler(
            "about",
            about_command
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats_command
        )
    )

    # ========================================================
    # ADMIN COMMANDS
    # ========================================================

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    application.add_handler(
        CommandHandler(
            "broadcast",
            broadcast_command
        )
    )

    application.add_handler(
        CommandHandler(
            "boardchat",
            broadcast_command
        )
    )

    # ========================================================
    # CALLBACK
    # ========================================================

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # ========================================================
    # ERROR
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    print(
        "🤖 Temp Mail Bot is running..."
    )

    print(
        f"📩 Auto inbox: every {POLL_SECONDS}s"
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
