import asyncio
import html
import logging
import random
import re
import string

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

API_BASE = "https://api.mail.tm"

POLL_INTERVAL = 3

HTTP_TIMEOUT = 10


# =========================================================
# LOGGING
# =========================================================

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

        "copy_code":
            "📋 Copy Code",

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
            "🔄 Refresh — Check new emails\n"
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

        "copy_code":
            "📋 Code Copy করুন",

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
            "🔄 রিফ্রেশ — নতুন Email check করুন\n"
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

        "copy_code":
            "📋 Copy Code",

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
            "🔄 Refresh — Naye emails check karein\n"
            "/language — Language change karein\n"
            "/stats — Bot Statistics\n"
            "/help — Help dekhein\n"
            "/about — Bot ke baare mein",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast Temporary Email receiver.\n\n"
            "⚡ Mail.tm API se powered\n"
            "🔒 API key ki zarurat nahi",

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

        "stats":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 <b>Total Users:</b> {users}\n"
            "📧 <b>Active Mailboxes:</b> {mailboxes}\n\n"
            "⚡ <b>API:</b> Mail.tm\n"
            "🟢 <b>Status:</b> Online",
    }
}


# =========================================================
# LANGUAGE KEYBOARD
# =========================================================

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


# =========================================================
# MAIN KEYBOARD
# =========================================================

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


# =========================================================
# CODE COPY BUTTON
# =========================================================

def code_keyboard(code, lang):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t["copy_code"]
                if False else TEXT[lang]["copy_code"],
                copy_text=CopyTextButton(
                    text=str(code)
                )
            )
        ]
    ])


# =========================================================
# HELPERS
# =========================================================

def user_lang(user_id):

    lang = get_language(user_id)

    if lang not in TEXT:
        return "en"

    return lang


def safe(value):

    if value is None:
        return ""

    return html.escape(str(value))


def is_admin(user_id):

    return user_id in ADMIN_IDS


def extract_code(text):

    if not text:
        return None

    text = str(text)

    # Remove HTML tags
    clean_text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # Decode HTML entities
    clean_text = html.unescape(
        clean_text
    )

    # Normalize whitespace
    clean_text = re.sub(
        r"\s+",
        " ",
        clean_text
    ).strip()

    patterns = [

        r"(?:code|otp|verification\s*code|verify\s*code|security\s*code|pin)"
        r"\s*(?:is|:|-)?\s*(\d{4,8})",

        r"(?:verification|confirmation|security)"
        r".{0,50}?(\d{4,8})",

        r"\b(\d{6})\b",

        r"\b(\d{5})\b",

        r"\b(\d{4})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            clean_text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


def clean_body(text):

    if not text:
        return ""

    text = str(text)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = html.unescape(text)

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# HTTP API
# =========================================================

async def api_request(
    method,
    endpoint,
    token=None,
    json_data=None
):

    url = API_BASE + endpoint

    headers = {
        "Accept": "application/json",
        "User-Agent": "TempMailTelegramBot/1.0"
    }

    if json_data is not None:

        headers["Content-Type"] = (
            "application/json"
        )

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
                json=json_data
            ) as response:

                if response.status >= 400:

                    text = await response.text()

                    logger.error(
                        "Mail.tm HTTP %s: %s",
                        response.status,
                        text[:500]
                    )

                    return None

                return await response.json()

    except asyncio.TimeoutError:

        logger.error(
            "Mail.tm request timeout: %s",
            endpoint
        )

        return None

    except Exception as error:

        logger.error(
            "Mail.tm API error: %s",
            error
        )

        return None


# =========================================================
# MAIL.TM DOMAIN
# =========================================================

async def get_domain():

    data = await api_request(
        "GET",
        "/domains"
    )

    if not data:
        return None

    domains = data.get(
        "hydra:member",
        []
    )

    active_domains = [
        item.get("domain")
        for item in domains
        if item.get("domain")
        and item.get(
            "isActive",
            True
        )
    ]

    if not active_domains:
        return None

    return random.choice(
        active_domains
    )


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
                k=10
            )
        )
    )

    email = (
        f"{username}@{domain}"
    )

    password = (
        "Tmp!"
        + "".join(
            random.choices(
                string.ascii_letters
                + string.digits,
                k=18
            )
        )
    )

    account = await api_request(
        "POST",
        "/accounts",
        json_data={
            "address": email,
            "password": password
        }
    )

    if not account:
        return None

    token_data = await api_request(
        "POST",
        "/token",
        json_data={
            "address": email,
            "password": password
        }
    )

    if not token_data:
        return None

    token = token_data.get(
        "token"
    )

    account_id = account.get(
        "id"
    )

    if not token:
        return None

    return {
        "email": email,
        "password": password,
        "token": token,
        "id": account_id
    }


# =========================================================
# GET MESSAGES
# =========================================================

async def get_messages(token):

    return await api_request(
        "GET",
        "/messages",
        token=token
    )


async def get_full_message(
    token,
    message_id
):

    return await api_request(
        "GET",
        f"/messages/{message_id}",
        token=token
    )


# =========================================================
# MESSAGE CACHE
# =========================================================

seen_messages = {}


# =========================================================
# MESSAGE MEMBERS
# =========================================================

def message_members(data):

    if not data:
        return []

    return data.get(
        "hydra:member",
        []
    )


# =========================================================
# SEND MAIL
# =========================================================

async def send_mail_to_user(
    bot,
    user_id,
    mail,
    lang
):

    t = TEXT[lang]

    sender_data = mail.get(
        "from",
        {}
    )

    if isinstance(
        sender_data,
        dict
    ):

        sender = (
            sender_data.get("address")
            or sender_data.get("name")
            or "Unknown"
        )

    else:

        sender = str(
            sender_data
        )

    subject = (
        mail.get("subject")
        or "(No Subject)"
    )

    date = (
        mail.get("createdAt")
        or mail.get("date")
        or ""
    )

    text_body = (
        mail.get("text")
        or ""
    )

    html_body = (
        mail.get("html")
        or ""
    )

    intro = (
        mail.get("intro")
        or ""
    )

    body = (
        text_body
        or intro
    )

    if not body and html_body:

        body = re.sub(
            r"<[^>]+>",
            " ",
            html_body
        )

        body = html.unescape(
            body
        )

    body = clean_body(
        body
    )

    if not body:

        body = "📭 Empty message"

    message_text = t[
        "new_mail"
    ].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(date),
        body=safe(body[:2500])
    )

    try:

        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="HTML"
        )

        # Search code in text
        code = extract_code(
            body
        )

        # Search subject
        if not code:

            code = extract_code(
                subject
            )

        # Search HTML
        if not code and html_body:

            code = extract_code(
                html_body
            )

        if code:

            await bot.send_message(
                chat_id=user_id,
                text=t[
                    "verification"
                ].format(
                    code=safe(code)
                ),
                reply_markup=code_keyboard(
                    code,
                    lang
                ),
                parse_mode="HTML"
            )

    except Exception as error:

        logger.error(
            "Failed sending email to %s: %s",
            user_id,
            error
        )


# =========================================================
# GENERATE NEW EMAIL
# =========================================================

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

        return

    email = mailbox["email"]
    token = mailbox["token"]

    save_mailbox(
        user_id,
        email,
        token
    )

    # Reset cache
    seen_messages[user_id] = set()

    # Existing messages shouldn't be
    # treated as new.
    initial = await get_messages(
        token
    )

    if initial:

        for item in message_members(
            initial
        ):

            message_id = item.get(
                "id"
            )

            if message_id:

                seen_messages[
                    user_id
                ].add(
                    message_id
                )

    await loading.edit_text(
        t["created"].format(
            email=safe(email)
        ),
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
)
    # =========================================================
# PART 2 — INBOX + OTP + REFRESH + AUTO CHECKER + ADMIN
# =========================================================

# =========================================================
# HELPERS
# =========================================================

def get_user_lang(user_id):
    lang = get_language(user_id)

    if lang not in TEXT:
        return "en"

    return lang


def escape_html(value):
    if value is None:
        return ""

    return html.escape(str(value))


def extract_code(text):
    """
    Detect common OTP / verification codes.
    Supports 4, 5 and 6 digit codes.
    """

    if not text:
        return None

    text = str(text)

    patterns = [
        r"(?:verification\s*code|verification\s*pin|security\s*code|"
        r"confirmation\s*code|confirm\s*code|one[-\s]?time\s*password|"
        r"\botp\b|\bpin\b|\bcode\b)"
        r"\D{0,40}(\d{6})",

        r"(?:verification\s*code|verification\s*pin|security\s*code|"
        r"confirmation\s*code|confirm\s*code|one[-\s]?time\s*password|"
        r"\botp\b|\bpin\b|\bcode\b)"
        r"\D{0,40}(\d{5})",

        r"(?:verification\s*code|verification\s*pin|security\s*code|"
        r"confirmation\s*code|confirm\s*code|one[-\s]?time\s*password|"
        r"\botp\b|\bpin\b|\bcode\b)"
        r"\D{0,40}(\d{4})",

        r"\b\d{6}\b",
        r"\b\d{5}\b",
        r"\b\d{4}\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            if match.lastindex:
                return match.group(1)

            return match.group(0)

    return None


def clean_text(text):

    if not text:
        return ""

    text = str(text)

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# MESSAGE CACHE
# =========================================================

# user_id -> set(message_ids)
seen_messages = {}


# =========================================================
# MAIL.GW API
# =========================================================

async def api_request(
    method,
    endpoint,
    token=None,
    json_data=None
):

    url = API_BASE + endpoint

    headers = {
        "Accept": "application/json",
        "User-Agent": "TempMailTelegramBot/2.0"
    }

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    if json_data is not None:
        headers["Content-Type"] = (
            "application/json"
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
                json=json_data
            ) as response:

                if response.status >= 400:

                    error_text = await response.text()

                    logger.error(
                        "API HTTP %s: %s",
                        response.status,
                        error_text[:500]
                    )

                    return None

                return await response.json()

    except asyncio.TimeoutError:

        logger.error(
            "API timeout: %s",
            endpoint
        )

        return None

    except Exception as error:

        logger.error(
            "API error: %s",
            error
        )

        return None


# =========================================================
# DOMAIN
# =========================================================

async def get_domain():

    data = await api_request(
        "GET",
        "/domains"
    )

    if not data:
        return None

    domains = data.get(
        "hydra:member",
        []
    )

    if not domains:
        return None

    active = []

    for item in domains:

        domain = item.get(
            "domain"
        )

        is_active = item.get(
            "isActive",
            True
        )

        if domain and is_active:
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
                k=10
            )
        )
    )

    email = (
        f"{username}@{domain}"
    )

    password = (
        "Tmp!"
        + "".join(
            random.choices(
                string.ascii_letters
                + string.digits,
                k=18
            )
        )
    )

    account = await api_request(
        "POST",
        "/accounts",
        json_data={
            "address": email,
            "password": password
        }
    )

    if not account:
        return None

    token_data = await api_request(
        "POST",
        "/token",
        json_data={
            "address": email,
            "password": password
        }
    )

    if not token_data:
        return None

    token = token_data.get(
        "token"
    )

    account_id = account.get(
        "id"
    )

    if not token:
        return None

    return {
        "email": email,
        "password": password,
        "token": token,
        "id": account_id
    }


# =========================================================
# GET MESSAGES
# =========================================================

async def get_messages(token):

    return await api_request(
        "GET",
        "/messages",
        token=token
    )


# =========================================================
# GET FULL MESSAGE
# =========================================================

async def get_full_message(
    token,
    message_id
):

    return await api_request(
        "GET",
        f"/messages/{message_id}",
        token=token
    )


# =========================================================
# MESSAGE LIST
# =========================================================

def get_message_list(data):

    if not data:
        return []

    return data.get(
        "hydra:member",
        []
    )


# =========================================================
# SEND EMAIL TO USER
# =========================================================

async def send_mail_to_user(
    bot,
    user_id,
    mail,
    lang
):

    t = TEXT[lang]

    sender_data = mail.get(
        "from",
        {}
    )

    if isinstance(
        sender_data,
        dict
    ):

        sender = (
            sender_data.get("address")
            or sender_data.get("name")
            or "Unknown"
        )

    else:

        sender = str(
            sender_data
        )

    subject = (
        mail.get("subject")
        or "(No Subject)"
    )

    date = (
        mail.get("createdAt")
        or mail.get("updatedAt")
        or ""
    )

    body = (
        mail.get("text")
        or mail.get("intro")
        or ""
    )

    body = clean_text(body)

    if not body:
        body = "📭 Empty message"

    message_text = t[
        "new_mail"
    ].format(
        sender=escape_html(sender),
        subject=escape_html(subject),
        date=escape_html(date),
        body=escape_html(
            body[:3000]
        )
    )

    try:

        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="HTML"
        )

        # Search body first
        code = extract_code(body)

        # If no code, search subject
        if not code:
            code = extract_code(subject)

        if code:

            await bot.send_message(
                chat_id=user_id,
                text=t[
                    "verification"
                ].format(
                    code=escape_html(code)
                ),
                reply_markup=code_keyboard(
                    code,
                    lang
                ),
                parse_mode="HTML"
            )

    except Exception as error:

        logger.error(
            "Could not send email to %s: %s",
            user_id,
            error
        )


# =========================================================
# GENERATE NEW EMAIL
# =========================================================

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

        return

    email = mailbox["email"]
    token = mailbox["token"]

    save_mailbox(
        user_id,
        email,
        token
    )

    # Reset cache
    seen_messages[user_id] = set()

    # Existing emails should not be considered new
    initial = await get_messages(
        token
    )

    if initial:

        for item in get_message_list(
            initial
        ):

            message_id = item.get(
                "id"
            )

            if message_id:

                seen_messages[
                    user_id
                ].add(
                    message_id
                )

    await loading.edit_text(
        t["created"].format(
            email=escape_html(email)
        ),
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
    )


# =========================================================
# SHOW INBOX
# =========================================================

async def show_inbox(
    bot,
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
        mailbox["token"]
    )

    if not data:

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )

        return

    messages = get_message_list(
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

    await loading.delete()

    if user_id not in seen_messages:
        seen_messages[user_id] = set()

    # Latest 20 messages
    messages = messages[:20]

    for item in reversed(messages):

        message_id = item.get(
            "id"
        )

        if not message_id:
            continue

        full_mail = await get_full_message(
            mailbox["token"],
            message_id
        )

        if not full_mail:
            full_mail = item

        seen_messages[
            user_id
        ].add(message_id)

        await send_mail_to_user(
            bot,
            user_id,
            full_mail,
            lang
        )


# =========================================================
# INBOX COMMAND
# =========================================================

async def inbox_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = get_user_lang(
        user_id
    )

    await show_inbox(
        context.bot,
        update.message,
        user_id,
        lang
    )


# =========================================================
# REFRESH
# =========================================================

async def refresh_command(
    update,
    context
):

    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXT[lang]

    mailbox = get_mailbox(
        user_id
    )

    if not mailbox:

        await update.message.reply_text(
            t["no_mailbox"],
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML"
        )

        return

    data = await get_messages(
        mailbox["token"]
    )

    if not data:

        await update.message.reply_text(
            t["api_error"],
            parse_mode="HTML"
        )

        return

    messages = get_message_list(
        data
    )

    if not messages:

        await update.message.reply_text(
            t["empty"],
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML"
        )

        return

    if user_id not in seen_messages:
        seen_messages[user_id] = set()

    count = 0

    for item in reversed(
        messages[:20]
    ):

        message_id = item.get(
            "id"
        )

        if not message_id:
            continue

        full_mail = await get_full_message(
            mailbox["token"],
            message_id
        )

        if not full_mail:
            full_mail = item

        seen_messages[
            user_id
        ].add(message_id)

        await send_mail_to_user(
            context.bot,
            user_id,
            full_mail,
            lang
        )

        count += 1

    await update.message.reply_text(
        t["refresh_done"].format(
            count=count
        ),
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
    )


# =========================================================
# LANGUAGE COMMAND
# =========================================================

async def language_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = get_user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["language"],
        reply_markup=language_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = get_user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["help"],
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
    )


# =========================================================
# ABOUT
# =========================================================

async def about_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = get_user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["about"],
        parse_mode="HTML"
    )


# =========================================================
# STATS
# =========================================================

async def stats_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = get_user_lang(
        user_id
    )

    users = list(
        get_all_users()
    )

    total_users = len(users)

    active_mailboxes = 0

    for uid in users:

        try:

            if get_mailbox(uid):
                active_mailboxes += 1

        except Exception:
            pass

    await update.message.reply_text(
        TEXT[lang]["stats"].format(
            users=total_users,
            mailboxes=active_mailboxes
        ),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN ONLY
# =========================================================

async def admin_only(
    update
):

    user_id = update.effective_user.id

    lang = get_user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["admin_only"],
        parse_mode="HTML"
    )


# =========================================================
# ADMIN
# =========================================================

async def admin_command(
    update,
    context
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await admin_only(update)

        return

    lang = get_user_lang(
        user_id
    )

    await update.message.reply_text(
        TEXT[lang]["admin_panel"],
        parse_mode="HTML"
    )


# =========================================================
# BROADCAST
# =========================================================

async def broadcast_command(
    update,
    context
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await admin_only(update)

        return

    lang = get_user_lang(
        user_id
    )

    if not context.args:

        await update.message.reply_text(
            TEXT[lang][
                "broadcast_start"
            ],
            parse_mode="HTML"
        )

        return

    broadcast_text = " ".join(
        context.args
    )

    users = list(
        get_all_users()
    )

    sent = 0
    failed = 0

    for target_id in users:

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=broadcast_text,
                parse_mode="HTML"
            )

            sent += 1

            await asyncio.sleep(
                0.1
            )

        except Exception as error:

            logger.warning(
                "Broadcast failed %s: %s",
                target_id,
                error
            )

            failed += 1

    await update.message.reply_text(
        TEXT[lang][
            "broadcast_done"
        ].format(
            sent=sent,
            failed=failed
        ),
        parse_mode="HTML"
    )


# =========================================================
# AUTOMATIC MAIL CHECKER
# =========================================================

async def automatic_mail_checker(
    application
):

    logger.info(
        "📨 Automatic Mail Checker Started"
    )

    while True:

        try:

            users = list(
                get_all_users()
            )

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

                    data = await get_messages(
                        token
                    )

                    if not data:
                        continue

                    messages = get_message_list(
                        data
                    )

                    if user_id not in seen_messages:

                        seen_messages[
                            user_id
                        ] = set()

                    # First check:
                    # Existing emails are ignored.
                    if not seen_messages[
                        user_id
                    ]:

                        for item in messages:

                            mid = item.get(
                                "id"
                            )

                            if mid:

                                seen_messages[
                                    user_id
                                ].add(mid)

                        continue

                    new_messages = []

                    for item in messages:

                        mid = item.get(
                            "id"
                        )

                        if not mid:
                            continue

                        if mid not in seen_messages[
                            user_id
                        ]:

                            new_messages.append(
                                item
                            )

                    if not new_messages:
                        continue

                    lang = get_user_lang(
                        user_id
                    )

                    # Oldest first
                    for item in reversed(
                        new_messages
                    ):

                        mid = item.get(
                            "id"
                        )

                        seen_messages[
                            user_id
                        ].add(mid)

                        full_mail = await get_full_message(
                            token,
                            mid
                        )

                        if not full_mail:
                            full_mail = item

                        await send_mail_to_user(
                            application.bot,
                            user_id,
                            full_mail,
                            lang
                        )

                except Exception as error:

                    logger.error(
                        "Auto checker error %s: %s",
                        user_id,
                        error
                    )

            await asyncio.sleep(
                POLL_INTERVAL
            )

        except asyncio.CancelledError:

            logger.info(
                "📨 Mail checker stopped"
            )

            break

        except Exception as error:

            logger.error(
                "Mail checker error: %s",
                error
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # =====================================================
    # LANGUAGE
    # =====================================================

    if data.startswith("lang_"):

        lang = data.replace(
            "lang_",
            ""
        )

        if lang not in TEXT:
            lang = "en"

        set_language(
            user_id,
            lang
        )

        await query.edit_message_text(
            TEXT[lang]["language_ok"],
            parse_mode="HTML"
        )

        await generate_new(
            query.message,
            user_id,
            lang
        )

        return

    # =====================================================
    # GENERATE
    # =====================================================

    if data == "generate":

        lang = get_user_lang(
            user_id
        )

        await generate_new(
            query.message,
            user_id,
            lang
        )

        return

    # =====================================================
    # INBOX
    # =====================================================

    if data == "inbox":

        lang = get_user_lang(
            user_id
        )

        await show_inbox(
            context.bot,
            query.message,
            user_id,
            lang
        )

        return

    # =====================================================
    # REFRESH
    # =====================================================

    if data == "refresh":

        lang = get_user_lang(
            user_id
        )

        mailbox = get_mailbox(
            user_id
        )

        if not mailbox:

            await query.message.reply_text(
                TEXT[lang]["no_mailbox"],
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML"
            )

            return

        data_result = await get_messages(
            mailbox["token"]
        )

        if not data_result:

            await query.message.reply_text(
                TEXT[lang]["api_error"],
                parse_mode="HTML"
            )

            return

        messages = get_message_list(
            data_result
        )

        if not messages:

            await query.message.reply_text(
                TEXT[lang]["empty"],
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML"
            )

            return

        if user_id not in seen_messages:
            seen_messages[user_id] = set()

        for item in reversed(
            messages[:20]
        ):

            message_id = item.get(
                "id"
            )

            if not message_id:
                continue

            full_mail = await get_full_message(
                mailbox["token"],
                message_id
            )

            if not full_mail:
                full_mail = item

            seen_messages[
                user_id
            ].add(message_id)

            await send_mail_to_user(
                context.bot,
                user_id,
                full_mail,
                lang
            )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    logger.error(
        "Unhandled error",
        exc_info=context.error
    )


# =========================================================
# POST INIT
# =========================================================

async def post_init(
    application
):

    application.bot_data[
        "mail_checker"
    ] = asyncio.create_task(
        automatic_mail_checker(
            application
        )
    )

    logger.info(
        "🚀 Bot startup completed"
    )


# =========================================================
# POST SHUTDOWN
# =========================================================

async def post_shutdown(
    application
):

    task = application.bot_data.get(
        "mail_checker"
    )

    if task:

        task.cancel()

        try:

            await task

        except asyncio.CancelledError:

            pass


# =========================================================
# MAIN
# =========================================================

def main():

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

    # =====================================================
    # ADMIN COMMANDS
    # =====================================================

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

    # =====================================================
    # CALLBACK
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

    print(
        "🤖 Temp Mail Bot is running..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
