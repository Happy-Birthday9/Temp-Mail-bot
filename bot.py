import asyncio
import html
import logging
import random
import re
import string
from typing import Optional

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


# =========================================================
# SETTINGS
# =========================================================

# Mail.tm API
API_BASE = "https://api.mail.tm"

POLL_INTERVAL = 5
HTTP_TIMEOUT = 15

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# LANGUAGES
# =========================================================

TEXT = {
    "en": {
        "welcome":
            "👋 <b>Welcome to Temp Mail Bot!</b>\n\n"
            "📧 Create a temporary email and receive verification codes instantly.\n\n"
            "🌐 Please select your preferred language:",

        "language_ok":
            "✅ <b>Language selected successfully!</b>\n\n"
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
            "You can now receive emails here.",

        "generate": "➕ Generate New",
        "inbox": "📥 Inbox",
        "refresh": "🔄 Refresh",

        "checking":
            "🔎 <b>Checking your inbox...</b>",

        "empty":
            "📭 <b>Inbox is empty.</b>\n\n"
            "No new messages received yet.",

        "no_mailbox":
            "⚠️ <b>No temporary email found.</b>\n\n"
            "Press <b>➕ Generate New</b> first.",

        "api_error":
            "❌ <b>Something went wrong.</b>\n\n"
            "Please try again later.",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Mail.tm\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>VERIFICATION CODE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "<code>{code}</code>\n\n"
            "👇 Tap the button below to copy the code.",

        "copy_code": "📋 Copy Code",

        "refresh_done":
            "🔄 <b>Inbox refreshed!</b>\n\n"
            "📨 Messages found: <b>{count}</b>",

        "language":
            "🌐 <b>Select your preferred language:</b>",

        "help":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Generate New — Create a new email\n"
            "📥 Inbox — View received emails\n"
            "🔄 Refresh — Check new emails\n\n"
            "/language — Change language\n"
            "/stats — Bot statistics\n"
            "/help — Show help\n"
            "/about — About the bot",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast disposable email receiver.\n\n"
            "⚡ Powered by Mail.tm API\n"
            "🔒 No API key required",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Sorry! This command is available only for administrators.\n\n"
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

        "stats":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 <b>Total Users:</b> {users}\n"
            "📧 <b>Active Mailboxes:</b> {mailboxes}\n\n"
            "⚡ <b>API:</b> Mail.tm\n"
            "🟢 <b>Status:</b> Online",
    },

    "bn": {
        "welcome":
            "👋 <b>Temp Mail Bot-এ স্বাগতম!</b>\n\n"
            "📧 Temporary Email তৈরি করে দ্রুত Verification Code গ্রহণ করুন।\n\n"
            "🌐 আপনার পছন্দের ভাষা নির্বাচন করুন:",

        "language_ok":
            "✅ <b>ভাষা সফলভাবে নির্বাচন করা হয়েছে!</b>\n\n"
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
            "এখন এই Email-এ Message গ্রহণ করতে পারবেন।",

        "generate": "➕ নতুন তৈরি করুন",
        "inbox": "📥 ইনবক্স",
        "refresh": "🔄 রিফ্রেশ",

        "checking":
            "🔎 <b>আপনার Inbox check করা হচ্ছে...</b>",

        "empty":
            "📭 <b>Inbox খালি।</b>\n\n"
            "এখনো কোনো নতুন Message আসেনি।",

        "no_mailbox":
            "⚠️ <b>কোনো Temporary Email পাওয়া যায়নি।</b>\n\n"
            "প্রথমে <b>➕ নতুন তৈরি করুন</b> চাপুন।",

        "api_error":
            "❌ <b>সমস্যা হয়েছে।</b>\n\n"
            "কিছুক্ষণ পর আবার চেষ্টা করুন।",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>নতুন EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Mail.tm\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>VERIFICATION CODE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "<code>{code}</code>\n\n"
            "👇 Code Copy করতে নিচের Button চাপুন।",

        "copy_code": "📋 Code Copy করুন",

        "refresh_done":
            "🔄 <b>Inbox Refresh হয়েছে!</b>\n\n"
            "📨 পাওয়া Message: <b>{count}</b>",

        "language":
            "🌐 <b>আপনার পছন্দের ভাষা নির্বাচন করুন:</b>",

        "help":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ নতুন তৈরি করুন — নতুন Email\n"
            "📥 ইনবক্স — আসা Email দেখুন\n"
            "🔄 রিফ্রেশ — নতুন Email check করুন\n\n"
            "/language — ভাষা পরিবর্তন\n"
            "/stats — Bot Statistics\n"
            "/help — Help দেখুন\n"
            "/about — Bot সম্পর্কে",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দ্রুত Temporary Email receiver।\n\n"
            "⚡ Mail.tm API দ্বারা পরিচালিত\n"
            "🔒 API key প্রয়োজন নেই",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দুঃখিত! এই Command শুধুমাত্র Administrator-এর জন্য।\n\n"
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

        "stats":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 <b>Total Users:</b> {users}\n"
            "📧 <b>Active Mailboxes:</b> {mailboxes}\n\n"
            "⚡ <b>API:</b> Mail.tm\n"
            "🟢 <b>Status:</b> Online",
    },

    "hi": {
        "welcome":
            "👋 <b>Temp Mail Bot mein aapka swagat hai!</b>\n\n"
            "📧 Temporary Email banayein aur Verification Code receive karein.\n\n"
            "🌐 Apni pasand ki language select karein:",

        "language_ok":
            "✅ <b>Language successfully select ho gayi!</b>\n\n"
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
            "Ab aap is Email par messages receive kar sakte hain.",

        "generate": "➕ Naya Generate",
        "inbox": "📥 Inbox",
        "refresh": "🔄 Refresh",

        "checking":
            "🔎 <b>Aapka Inbox check ho raha hai...</b>",

        "empty":
            "📭 <b>Inbox empty hai.</b>\n\n"
            "Abhi koi naya message nahi aaya.",

        "no_mailbox":
            "⚠️ <b>Koi Temporary Email nahi mila.</b>\n\n"
            "Pehle <b>➕ Naya Generate</b> press karein.",

        "api_error":
            "❌ <b>Kuch problem ho gayi.</b>\n\n"
            "Thodi der baad dobara try karein.",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> Mail.tm\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>VERIFICATION CODE</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "<code>{code}</code>\n\n"
            "👇 Code copy karne ke liye button dabayein.",

        "copy_code": "📋 Copy Code",

        "refresh_done":
            "🔄 <b>Inbox refresh ho gaya!</b>\n\n"
            "📨 Messages mile: <b>{count}</b>",

        "language":
            "🌐 <b>Apni pasand ki language select karein:</b>",

        "help":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Naya Generate — Naya Email\n"
            "📥 Inbox — Received emails dekhein\n"
            "🔄 Refresh — Naye emails check karein\n\n"
            "/language — Language change karein\n"
            "/stats — Bot Statistics\n"
            "/help — Help dekhein\n"
            "/about — Bot ke baare mein",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast Temporary Email receiver.\n\n"
            "⚡ Mail.tm se powered\n"
            "🔒 API key ki zarurat nahi",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Maaf kijiye! Yeh command sirf Administrator ke liye hai.\n\n"
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

        "stats":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 <b>Total Users:</b> {users}\n"
            "📧 <b>Active Mailboxes:</b> {mailboxes}\n\n"
            "⚡ <b>API:</b> Mail.tm\n"
            "🟢 <b>Status:</b> Online",
    },
}


# =========================================================
# KEYBOARDS
# =========================================================

def language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🇺🇸 English",
                callback_data="lang_en",
            )
        ],
        [
            InlineKeyboardButton(
                "🇧🇩 বাংলা",
                callback_data="lang_bn",
            )
        ],
        [
            InlineKeyboardButton(
                "🇮🇳 Hindi",
                callback_data="lang_hi",
            )
        ],
    ])


def main_keyboard(lang):
    t = TEXT[lang]

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t["generate"],
                callback_data="generate",
            ),
            InlineKeyboardButton(
                t["inbox"],
                callback_data="inbox",
            ),
        ],
        [
            InlineKeyboardButton(
                t["refresh"],
                callback_data="refresh",
            )
        ],
    ])


def code_keyboard(code, lang):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                TEXT[lang]["copy_code"],
                copy_text=CopyTextButton(
                    text=str(code)
                ),
            )
        ]
    ])


# =========================================================
# HELPERS
# =========================================================

def safe(value):
    if value is None:
        return ""

    return html.escape(str(value))


def user_lang(user_id):
    try:
        lang = get_language(user_id)
    except Exception:
        lang = None

    if lang not in TEXT:
        return "en"

    return lang


def is_admin(user_id):
    try:
        return int(user_id) in [
            int(x) for x in ADMIN_IDS
        ]
    except Exception:
        return False


def get_users_list():
    try:
        users = get_all_users()

        if users is None:
            return []

        return list(users)

    except Exception as error:
        logger.error(
            "Could not get users: %s",
            error,
        )
        return []


def extract_code(text):
    if not text:
        return None

    text = str(text)

    patterns = [
        r"(?:verification\s*code|verification|verify|security\s*code|one[- ]?time\s*password|otp|code|pin)"
        r"\D{0,40}(\d{8})",

        r"(?:verification\s*code|verification|verify|security\s*code|one[- ]?time\s*password|otp|code|pin)"
        r"\D{0,40}(\d{7})",

        r"(?:verification\s*code|verification|verify|security\s*code|one[- ]?time\s*password|otp|code|pin)"
        r"\D{0,40}(\d{6})",

        r"(?:verification\s*code|verification|verify|security\s*code|one[- ]?time\s*password|otp|code|pin)"
        r"\D{0,40}(\d{5})",

        r"(?:verification\s*code|verification|verify|security\s*code|one[- ]?time\s*password|otp|code|pin)"
        r"\D{0,40}(\d{4})",

        r"\b\d{8}\b",
        r"\b\d{7}\b",
        r"\b\d{6}\b",
        r"\b\d{5}\b",
        r"\b\d{4}\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            if match.lastindex:
                return match.group(1)

            return match.group(0)

    return None


def clean_body(text):
    if not text:
        return ""

    text = str(text)

    text = re.sub(
        r"\r\n?",
        "\n",
        text,
    )

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text,
    )

    return text.strip()


def message_members(data):
    if not data:
        return []

    return data.get(
        "hydra:member",
        data.get("member", []),
    )


# =========================================================
# HTTP API
# =========================================================

async def api_request(
    method,
    endpoint,
    token=None,
    json_data=None,
):
    url = API_BASE + endpoint

    headers = {
        "Accept": "application/json",
        "User-Agent": "TempMailTelegramBot/2.0",
    }

    if json_data is not None:
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    timeout = aiohttp.ClientTimeout(
        total=HTTP_TIMEOUT
    )

    try:
        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.request(
                method,
                url,
                headers=headers,
                json=json_data,
            ) as response:

                if response.status >= 400:
                    error_text = await response.text()

                    logger.error(
                        "Mail API HTTP %s: %s",
                        response.status,
                        error_text[:500],
                    )

                    return None

                try:
                    return await response.json(
                        content_type=None
                    )
                except Exception:
                    return None

    except asyncio.TimeoutError:
        logger.error(
            "API timeout: %s",
            endpoint,
        )
        return None

    except Exception as error:
        logger.error(
            "API error: %s",
            error,
        )
        return None


# =========================================================
# DOMAIN
# =========================================================

async def get_domain():
    data = await api_request(
        "GET",
        "/domains",
    )

    if not data:
        return None

    domains = data.get(
        "hydra:member",
        []
    )

    active = []

    for item in domains:
        domain = item.get("domain")

        if not domain:
            continue

        if item.get("isActive", True):
            active.append(domain)

    if not active:
        return None

    return random.choice(active)


# =========================================================
# CREATE MAILBOX
# =========================================================

async def create_mailbox():
    domain = await get_domain()

    if not domain:
        return None

    username = (
        "user-"
        + "".join(
            random.choices(
                string.ascii_lowercase
                + string.digits,
                k=12,
            )
        )
    )

    email = f"{username}@{domain}"

    password = (
        "Tmp!"
        + "".join(
            random.choices(
                string.ascii_letters
                + string.digits,
                k=20,
            )
        )
    )

    account = await api_request(
        "POST",
        "/accounts",
        json_data={
            "address": email,
            "password": password,
        },
    )

    if not account:
        return None

    token_data = await api_request(
        "POST",
        "/token",
        json_data={
            "address": email,
            "password": password,
        },
    )

    if not token_data:
        return None

    token = token_data.get("token")

    if not token:
        return None

    return {
        "email": email,
        "password": password,
        "token": token,
        "id": account.get("id"),
    }


# =========================================================
# MAIL API
# =========================================================

async def get_messages(token):
    return await api_request(
        "GET",
        "/messages",
        token=token,
    )


async def get_full_message(
    token,
    message_id,
):
    return await api_request(
        "GET",
        f"/messages/{message_id}",
        token=token,
    )


# =========================================================
# CACHE
# =========================================================

seen_messages = {}

mailbox_locks = {}


def get_user_lock(user_id):
    if user_id not in mailbox_locks:
        mailbox_locks[user_id] = asyncio.Lock()

    return mailbox_locks[user_id]


# =========================================================
# SEND EMAIL
# =========================================================

async def send_mail_to_user(
    bot,
    user_id,
    mail,
    lang,
):
    t = TEXT[lang]

    sender_data = mail.get(
        "from",
        {}
    )

    if isinstance(sender_data, dict):
        sender = (
            sender_data.get("address")
            or sender_data.get("name")
            or "Unknown"
        )
    else:
        sender = str(sender_data)

    subject = (
        mail.get("subject")
        or "(No Subject)"
    )

    date = (
        mail.get("createdAt")
        or mail.get("date")
        or ""
    )

    body = (
        mail.get("text")
        or mail.get("intro")
        or ""
    )

    body = clean_body(body)

    if not body:
        body = "📭 Empty message"

    message_text = t["new_mail"].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(date),
        body=safe(body[:3500]),
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="HTML",
        )

        code = extract_code(body)

        if not code:
            code = extract_code(subject)

        if code:
            await bot.send_message(
                chat_id=user_id,
                text=t["verification"].format(
                    code=safe(code)
                ),
                reply_markup=code_keyboard(
                    code,
                    lang,
                ),
                parse_mode="HTML",
            )

    except Exception as error:
        logger.error(
            "Could not send email to %s: %s",
            user_id,
            error,
        )


# =========================================================
# GENERATE NEW
# =========================================================

async def generate_new(
    message,
    user_id,
    lang,
):
    t = TEXT[lang]

    loading = await message.reply_text(
        t["generating"],
        parse_mode="HTML",
    )

    mailbox = await create_mailbox()

    if not mailbox:
        try:
            await loading.edit_text(
                t["api_error"],
                parse_mode="HTML",
            )
        except Exception:
            pass

        return False

    save_mailbox(
        user_id,
        mailbox["email"],
        mailbox["token"],
    )

    seen_messages[user_id] = set()

    # Mark already-existing messages as seen.
    initial = await get_messages(
        mailbox["token"]
    )

    if initial:
        for item in message_members(initial):
            mid = item.get("id")

            if mid:
                seen_messages[user_id].add(mid)

    try:
        await loading.edit_text(
            t["created"].format(
                email=safe(mailbox["email"])
            ),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )
    except Exception:
        pass

    return True


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not user or not update.message:
        return

    save_user(
        user.id,
        user.username,
    )

    lang = get_language(user.id)

    # FIRST TIME USER
    if not lang:
        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML",
        )
        return

    # EXISTING USER
    await generate_new(
        update.message,
        user.id,
        user_lang(user.id),
    )


# =========================================================
# INBOX
# =========================================================

async def show_inbox(
    message,
    user_id,
    lang,
    bot,
):
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
        mailbox["token"]
    )

    if not data:
        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML",
        )
        return

    messages = message_members(data)

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

    if user_id not in seen_messages:
        seen_messages[user_id] = set()

    # Inbox manually requested:
    # show latest messages, including OTP.
    latest = messages[:20]

    for item in reversed(latest):
        mid = item.get("id")

        if not mid:
            continue

        full_mail = await get_full_message(
            mailbox["token"],
            mid,
        )

        if not full_mail:
            full_mail = item

        seen_messages[user_id].add(mid)

        await send_mail_to_user(
            bot,
            user_id,
            full_mail,
            lang,
        )


# =========================================================
# INBOX COMMAND
# =========================================================

async def inbox_command(
    update,
    context,
):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await show_inbox(
        update.message,
        user_id,
        lang,
        context.bot,
    )


# =========================================================
# REFRESH COMMAND
# =========================================================

async def refresh_command(
    update,
    context,
):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    t = TEXT[lang]

    mailbox = get_mailbox(user_id)

    if not mailbox:
        await update.message.reply_text(
            t["no_mailbox"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )
        return

    data = await get_messages(
        mailbox["token"]
    )

    if not data:
        await update.message.reply_text(
            t["api_error"],
            parse_mode="HTML",
        )
        return

    messages = message_members(data)

    if not messages:
        await update.message.reply_text(
            t["empty"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )
        return

    if user_id not in seen_messages:
        seen_messages[user_id] = set()

    count = 0

    for item in reversed(messages[:20]):
        mid = item.get("id")

        if not mid:
            continue

        full_mail = await get_full_message(
            mailbox["token"],
            mid,
        )

        if not full_mail:
            full_mail = item

        seen_messages[user_id].add(mid)

        await send_mail_to_user(
            context.bot,
            user_id,
            full_mail,
            lang,
        )

        count += 1

    await update.message.reply_text(
        t["refresh_done"].format(
            count=count
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML",
    )


# =========================================================
# LANGUAGE
# =========================================================

async def language_command(
    update,
    context,
):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["language"],
        reply_markup=language_keyboard(),
        parse_mode="HTML",
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update,
    context,
):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["help"],
        reply_markup=main_keyboard(lang),
        parse_mode="HTML",
    )


# =========================================================
# ABOUT
# =========================================================

async def about_command(
    update,
    context,
):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["about"],
        parse_mode="HTML",
    )


# =========================================================
# STATS
# =========================================================

async def stats_command(
    update,
    context,
):
    user_id = update.effective_user.id
    lang = user_lang(user_id)
    t = TEXT[lang]

    users = get_users_list()

    total_users = len(users)
    active_mailboxes = 0

    for uid in users:
        try:
            if get_mailbox(uid):
                active_mailboxes += 1
        except Exception:
            pass

    await update.message.reply_text(
        t["stats"].format(
            users=total_users,
            mailboxes=active_mailboxes,
        ),
        parse_mode="HTML",
    )


# =========================================================
# ADMIN ONLY
# =========================================================

async def admin_only(update):
    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["admin_only"],
        parse_mode="HTML",
    )


# =========================================================
# ADMIN
# =========================================================

async def admin_command(
    update,
    context,
):
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


# =========================================================
# BROADCAST
# =========================================================

async def broadcast_command(
    update,
    context,
):
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

    users = get_users_list()

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

            await asyncio.sleep(0.1)

        except Exception as error:
            logger.warning(
                "Broadcast failed for %s: %s",
                user_id,
                error,
            )
            failed += 1

    await update.message.reply_text(
        TEXT[lang]["broadcast_done"].format(
            sent=sent,
            failed=failed,
        ),
        parse_mode="HTML",
    )


# =========================================================
# AUTOMATIC MAIL CHECKER
# =========================================================

async def automatic_mail_checker(application):
    logger.info(
        "📨 Automatic Mail Checker Started"
    )

    while True:
        try:
            users = get_users_list()

            for user_id in users:
                try:
                    mailbox = get_mailbox(user_id)

                    if not mailbox:
                        continue

                    token = mailbox.get("token")

                    if not token:
                        continue

                    async with get_user_lock(user_id):

                        data = await get_messages(token)

                        if not data:
                            continue

                        messages = message_members(data)

                        if user_id not in seen_messages:
                            seen_messages[user_id] = set()

                        # First check:
                        # don't send old messages.
                        if not seen_messages[user_id]:
                            for item in messages:
                                mid = item.get("id")

                                if mid:
                                    seen_messages[user_id].add(mid)

                            continue

                        new_messages = []

                        for item in messages:
                            mid = item.get("id")

                            if not mid:
                                continue

                            if mid not in seen_messages[user_id]:
                                new_messages.append(item)

                        if not new_messages:
                            continue

                        lang = user_lang(user_id)

                        # oldest -> newest
                        for item in reversed(new_messages):
                            mid = item.get("id")

                            seen_messages[user_id].add(mid)

                            full_mail = await get_full_message(
                                token,
                                mid,
                            )

                            if not full_mail:
                                full_mail = item

                            await send_mail_to_user(
                                application.bot,
                                user_id,
                                full_mail,
                                lang,
                            )

                except Exception as error:
                    logger.error(
                        "Automatic check error for %s: %s",
                        user_id,
                        error,
                    )

            await asyncio.sleep(POLL_INTERVAL)

        except asyncio.CancelledError:
            logger.info(
                "Automatic Mail Checker stopped"
            )
            break

        except Exception as error:
            logger.error(
                "Mail checker error: %s",
                error,
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update,
    context,
):
    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    user_id = query.from_user.id
    data = query.data

    # =====================================================
    # LANGUAGE
    # =====================================================

    if data.startswith("lang_"):
        lang = data.replace(
            "lang_",
            "",
            1,
        )

        if lang not in TEXT:
            lang = "en"

        set_language(
            user_id,
            lang,
        )

        # Edit language selection message.
        try:
            await query.edit_message_text(
                TEXT[lang]["language_ok"],
                parse_mode="HTML",
            )
        except Exception:
            pass

        # Create email.
        await generate_new(
            query.message,
            user_id,
            lang,
        )

        return

    # =====================================================
    # GENERATE
    # =====================================================

    if data == "generate":
        lang = user_lang(user_id)

        await generate_new(
            query.message,
            user_id,
            lang,
        )

        return

    # =====================================================
    # INBOX
    # =====================================================

    if data == "inbox":
        lang = user_lang(user_id)

        await show_inbox(
            query.message,
            user_id,
            lang,
            context.bot,
        )

        return

    # =====================================================
    # REFRESH
    # =====================================================

    if data == "refresh":
        lang = user_lang(user_id)
        t = TEXT[lang]

        mailbox = get_mailbox(user_id)

        if not mailbox:
            await query.message.reply_text(
                t["no_mailbox"],
                reply_markup=main_keyboard(lang),
                parse_mode="HTML",
            )
            return

        data_result = await get_messages(
            mailbox["token"]
        )

        if not data_result:
            await query.message.reply_text(
                t["api_error"],
                parse_mode="HTML",
            )
            return

        messages = message_members(
            data_result
        )

        if not messages:
            await query.message.reply_text(
                t["empty"],
                reply_markup=main_keyboard(lang),
                parse_mode="HTML",
            )
            return

        if user_id not in seen_messages:
            seen_messages[user_id] = set()

        count = 0

        for item in reversed(messages[:20]):
            message_id = item.get("id")

            if not message_id:
                continue

            full_mail = await get_full_message(
                mailbox["token"],
                message_id,
            )

            if not full_mail:
                full_mail = item

            seen_messages[user_id].add(
                message_id
            )

            await send_mail_to_user(
                context.bot,
                user_id,
                full_mail,
                lang,
            )

            count += 1

        await query.message.reply_text(
            t["refresh_done"].format(
                count=count
            ),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML",
        )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context,
):
    logger.error(
        "Unhandled error",
        exc_info=context.error,
    )


# =========================================================
# STARTUP
# =========================================================

async def post_init(application):
    task = asyncio.create_task(
        automatic_mail_checker(application)
    )

    application.bot_data[
        "mail_checker"
    ] = task

    logger.info(
        "🚀 Bot startup completed"
    )


# =========================================================
# SHUTDOWN
# =========================================================

async def post_shutdown(application):
    task = application.bot_data.get(
        "mail_checker"
    )

    if not task:
        return

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


# =========================================================
# MAIN
# =========================================================

def main():
    # Database initialize
    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # =====================================================
    # USER COMMANDS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "inbox",
            inbox_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "refresh",
            refresh_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "language",
            language_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "about",
            about_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats_command,
        )
    )

    # =====================================================
    # ADMIN COMMANDS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "broadcast",
            broadcast_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "boardchat",
            broadcast_command,
        )
    )

    # =====================================================
    # CALLBACKS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # =====================================================
    # ERROR
    # =====================================================

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "🤖 Temp Mail Bot is starting..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
