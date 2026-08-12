import asyncio
import html
import logging
import re
from typing import Any

import aiohttp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

API_BASE = "https://smails.dev/api"

# Automatic inbox check interval
POLL_SECONDS = 4

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# RUNTIME MAILBOX CACHE
# =========================================================

# {
#   user_id: {
#       "token": "...",
#       "seen": {"message-id-1", "message-id-2"}
#   }
# }

MAILBOX_CACHE = {}

CACHE_LOCK = asyncio.Lock()


# =========================================================
# LANGUAGE TEXT
# =========================================================

TEXT = {

    "en": {

        "welcome":
            "👋 <b>Welcome to Temp Mail Bot!</b>\n\n"
            "Select your preferred language:",

        "language_ok":
            "✅ <b>Language selected successfully!</b>",

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

        "new_email":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> {source}\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "code":
            "🔐 <b>VERIFICATION CODE</b>\n\n"
            "<code>{code}</code>\n\n"
            "📋 Press and hold the code to copy it.",

        "copy_code":
            "📋 Copy Code",

        "code_popup":
            "📋 Verification Code\n\n{code}",

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
            "/help — Show help\n"
            "/about — About the bot",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast disposable email receiver.\n\n"
            "⚡ Powered by Smails API\n"
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
    },


    "bn": {

        "welcome":
            "👋 <b>Temp Mail Bot-এ স্বাগতম!</b>\n\n"
            "আপনার পছন্দের ভাষা নির্বাচন করুন:",

        "language_ok":
            "✅ <b>ভাষা সফলভাবে নির্বাচন করা হয়েছে!</b>",

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

        "new_email":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>নতুন EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> {source}\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "code":
            "🔐 <b>VERIFICATION CODE</b>\n\n"
            "<code>{code}</code>\n\n"
            "📋 Code-এর উপর চাপ দিয়ে ধরে রাখলে Copy করতে পারবেন।",

        "copy_code":
            "📋 Code Copy",

        "code_popup":
            "📋 Verification Code\n\n{code}",

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
            "/help — Help দেখুন\n"
            "/about — Bot সম্পর্কে",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দ্রুত Temporary Email receiver।\n\n"
            "⚡ Smails API দ্বারা পরিচালিত\n"
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
    },


    "hi": {

        "welcome":
            "👋 <b>Temp Mail Bot mein aapka swagat hai!</b>\n\n"
            "Apni pasand ki language select karein:",

        "language_ok":
            "✅ <b>Language successfully select ho gayi!</b>",

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

        "new_email":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> {source}\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "code":
            "🔐 <b>VERIFICATION CODE</b>\n\n"
            "<code>{code}</code>\n\n"
            "📋 Code par press karke hold karein aur Copy karein.",

        "copy_code":
            "📋 Copy Code",

        "code_popup":
            "📋 Verification Code\n\n{code}",

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
            "/help — Help dekhein\n"
            "/about — Bot ke baare mein",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "      📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast Temporary Email receiver.\n\n"
            "⚡ Smails API se powered\n"
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
    }
}


# =========================================================
# KEYBOARDS
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


def code_keyboard(code):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📋 Copy Code",
                callback_data=f"copy:{code}"
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


def clean_html(text):

    if not text:
        return ""

    text = re.sub(
        r"<style.*?</style>",
        " ",
        text,
        flags=re.I | re.S
    )

    text = re.sub(
        r"<script.*?</script>",
        " ",
        text,
        flags=re.I | re.S
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_code(text):

    if not text:
        return None

    text = clean_html(text)

    # Highest priority:
    # OTP / verification / code + number
    priority_patterns = [

        r"(?:verification|verify|verification\s+code)"
        r"\D{0,30}([0-9]{4,8})",

        r"(?:otp|one[-\s]?time\s+password)"
        r"\D{0,30}([0-9]{4,8})",

        r"(?:security\s+code|login\s+code)"
        r"\D{0,30}([0-9]{4,8})",

        r"(?:code)"
        r"\D{0,20}([0-9]{4,8})",
    ]

    for pattern in priority_patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            return match.group(1)


    # Common 6-digit OTP
    matches = re.findall(
        r"(?<!\d)\d{6}(?!\d)",
        text
    )

    if matches:

        return matches[0]


    # 4 or 5 digit code
    matches = re.findall(
        r"(?<!\d)\d{4,5}(?!\d)",
        text
    )

    if matches:

        return matches[0]


    return None


def message_list(data):

    if not data:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        for key in (
            "messages",
            "data",
            "items",
            "results"
        ):

            value = data.get(key)

            if isinstance(value, list):

                return value

    return []


def get_message_id(item):

    if not isinstance(item, dict):
        return None

    return (
        item.get("id")
        or item.get("_id")
        or item.get("messageId")
    )


def get_sender(item):

    sender = (
        item.get("from")
        or item.get("sender")
        or ""
    )

    if isinstance(sender, dict):

        return (
            sender.get("address")
            or sender.get("email")
            or sender.get("name")
            or "Unknown"
        )

    return str(sender)


def get_subject(item):

    return (
        item.get("subject")
        or "(No Subject)"
    )


def get_date(item):

    return (
        item.get("createdAt")
        or item.get("date")
        or item.get("receivedAt")
        or ""
    )


def get_body(item):

    if not isinstance(item, dict):
        return ""

    body = (
        item.get("text")
        or item.get("body")
        or item.get("content")
        or item.get("html")
        or item.get("intro")
        or ""
    )

    if isinstance(body, dict):

        body = (
            body.get("text")
            or body.get("content")
            or body.get("html")
            or ""
        )

    return clean_html(str(body))


# =========================================================
# HTTP API
# =========================================================

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
        total=10
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

                text = await response.text()

                if response.status >= 400:

                    logger.error(
                        "Smails API %s %s: %s",
                        response.status,
                        endpoint,
                        text[:500]
                    )

                    return None

                try:

                    return await response.json()

                except Exception:

                    logger.error(
                        "Invalid JSON from Smails: %s",
                        text[:500]
                    )

                    return None

    except Exception as error:

        logger.error(
            "API request error: %s",
            error
        )

        return None


async def create_mailbox():

    return await api_request(
        "POST",
        "/mailbox"
    )


async def list_messages(token):

    return await api_request(
        "GET",
        "/mailbox/messages",
        token
    )


async def read_message(
    token,
    message_id
):

    return await api_request(
        "GET",
        f"/mailbox/messages/{message_id}",
        token
    )


# =========================================================
# LOAD FULL MESSAGE
# =========================================================

async def get_full_message(
    token,
    item
):

    message_id = get_message_id(item)

    if not message_id:

        return item

    full = await read_message(
        token,
        message_id
    )

    if not full:

        return item

    if isinstance(full, dict):

        # Some APIs return {"message": {...}}
        if isinstance(
            full.get("message"),
            dict
        ):

            return full["message"]

    return full


# =========================================================
# SEND EMAIL TO TELEGRAM
# =========================================================

async def send_email_message(
    bot,
    chat_id,
    lang,
    item
):

    t = TEXT[lang]

    sender = get_sender(item)

    subject = get_subject(item)

    date = get_date(item)

    body = get_body(item)

    if not body:

        body = "(No readable message body)"

    body = body[:2500]

    message_text = t[
        "new_email"
    ].format(
        source="Email",
        sender=safe(sender),
        subject=safe(subject),
        date=safe(date),
        body=safe(body)
    )

    await bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="HTML"
    )

    # Detect verification code
    code = extract_code(body)

    # If code is in subject instead
    if not code:

        code = extract_code(
            subject
        )

    if code:

        await bot.send_message(
            chat_id=chat_id,
            text=t["code"].format(
                code=safe(code)
            ),
            reply_markup=code_keyboard(
                code
            ),
            parse_mode="HTML"
        )

    return code


# =========================================================
# PREPARE EXISTING MESSAGES
# =========================================================

async def initialize_seen(
    user_id,
    token
):

    data = await list_messages(
        token
    )

    items = message_list(data)

    seen = set()

    for item in items:

        message_id = get_message_id(
            item
        )

        if message_id:

            seen.add(
                str(message_id)
            )

    async with CACHE_LOCK:

        MAILBOX_CACHE[
            user_id
        ] = {
            "token": token,
            "seen": seen
        }

    logger.info(
        "Mailbox initialized user=%s existing=%s",
        user_id,
        len(seen)
    )


# =========================================================
# GENERATE NEW MAILBOX
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


    email = (
        mailbox.get("address")
        or mailbox.get("email")
    )

    token = mailbox.get("token")


    if not email or not token:

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )

        return


    save_mailbox(
        user_id,
        email,
        token
    )


    # Important:
    # Existing inbox messages are marked as seen.
    # Only future messages will be automatically sent.
    await initialize_seen(
        user_id,
        token
    )


    await loading.edit_text(
        t["created"].format(
            email=safe(email)
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )


# =========================================================
# INBOX
# =========================================================

async def show_inbox(
    bot,
    chat_id,
    user_id,
    lang
):

    t = TEXT[lang]

    mailbox = get_mailbox(
        user_id
    )

    if not mailbox:

        await bot.send_message(
            chat_id=chat_id,
            text=t["no_mailbox"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )

        return


    loading = await bot.send_message(
        chat_id=chat_id,
        text=t["checking"],
        parse_mode="HTML"
    )


    data = await list_messages(
        mailbox["token"]
    )

    if not data:

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )

        return


    items = message_list(data)


    await loading.delete()


    if not items:

        await bot.send_message(
            chat_id=chat_id,
            text=t["empty"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )

        return


    for item in items[:20]:

        full_item = await get_full_message(
            mailbox["token"],
            item
        )

        try:

            await send_email_message(
                bot,
                chat_id,
                lang,
                full_item
            )

        except Exception as error:

            logger.error(
                "Inbox message error: %s",
                error
            )


# =========================================================
# AUTOMATIC MAIL CHECKER
# =========================================================

async def automatic_mail_checker(
    application
):

    logger.info(
        "📡 Automatic mail checker started"
    )


    while True:

        try:

            # Make a snapshot so dictionary changes
            # don't break iteration.
            async with CACHE_LOCK:

                mailboxes = list(
                    MAILBOX_CACHE.items()
                )


            for user_id, info in mailboxes:

                token = info.get(
                    "token"
                )

                if not token:
                    continue


                try:

                    data = await list_messages(
                        token
                    )

                    if not data:
                        continue


                    items = message_list(
                        data
                    )


                    async with CACHE_LOCK:

                        cache = MAILBOX_CACHE.get(
                            user_id
                        )

                        if not cache:
                            continue

                        seen = cache[
                            "seen"
                        ]


                    for item in items:

                        message_id = get_message_id(
                            item
                        )

                        if not message_id:
                            continue


                        message_id = str(
                            message_id
                        )


                        # Already sent
                        if message_id in seen:
                            continue


                        # Mark seen BEFORE sending.
                        # This prevents duplicate messages
                        # if Telegram/API is slow.
                        async with CACHE_LOCK:

                            cache = MAILBOX_CACHE.get(
                                user_id
                            )

                            if not cache:
                                continue

                            if message_id in cache["seen"]:
                                continue

                            cache["seen"].add(
                                message_id
                            )


                        # Read full email
                        full_item = await get_full_message(
                            token,
                            item
                        )


                        lang = user_lang(
                            user_id
                        )


                        # Automatically send email
                        await send_email_message(
                            application.bot,
                            user_id,
                            lang,
                            full_item
                        )


                        logger.info(
                            "📨 New mail sent to user=%s id=%s",
                            user_id,
                            message_id
                        )


                except Exception as error:

                    logger.error(
                        "Checker user=%s error: %s",
                        user_id,
                        error
                    )


            await asyncio.sleep(
                POLL_SECONDS
            )


        except asyncio.CancelledError:

            logger.info(
                "Automatic checker stopped"
            )

            break


        except Exception as error:

            logger.error(
                "Checker error: %s",
                error
            )

            await asyncio.sleep(
                POLL_SECONDS
            )


# =========================================================
# STARTUP
# =========================================================

async def post_init(
    application
):

    # Start automatic background checker
    application.create_task(
        automatic_mail_checker(
            application
        )
    )

    logger.info(
        "🤖 Bot startup complete"
    )


# =========================================================
# START
# =========================================================

async def start(
    update,
    context
):

    user = update.effective_user

    save_user(
        user.id,
        user.username
    )

    lang = get_language(
        user.id
    )


    if not lang:

        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML"
        )

        return


    await generate_new(
        update.message,
        user.id,
        lang
    )


# =========================================================
# COMMANDS
# =========================================================

async def inbox_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    await show_inbox(
        context.bot,
        update.effective_chat.id,
        user_id,
        lang
    )


async def refresh_command(
    update,
    context
):

    user_id = update.effective_user.id

    lang = user_lang(
        user_id
    )

    mailbox = get_mailbox(
        user_id
    )

    if not mailbox:

        await update.message.reply_text(
            TEXT[lang]["no_mailbox"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )

        return


    data = await list_messages(
        mailbox["token"]
    )


    if not data:

        await update.message.reply_text(
            TEXT[lang]["api_error"],
            parse_mode="HTML"
        )

        return


    items = message_list(
        data
    )


    await update.message.reply_text(
        TEXT[lang]["refresh_done"].format(
            count=len(items)
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )


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
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )


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


# =========================================================
# ADMIN
# =========================================================

async def admin_only(
    update
):

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


# =========================================================
# CALLBACKS
# =========================================================

async def callback_handler(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    data = query.data


    # LANGUAGE

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


    # GENERATE

    if data == "generate":

        lang = user_lang(
            user_id
        )

        await generate_new(
            query.message,
            user_id,
            lang
        )

        return


    # INBOX

    if data == "inbox":

        lang = user_lang(
            user_id
        )

        await show_inbox(
            context.bot,
            query.message.chat_id,
            user_id,
            lang
        )

        return


    # REFRESH

    if data == "refresh":

        lang = user_lang(
            user_id
        )

        mailbox = get_mailbox(
            user_id
        )

        if not mailbox:

            await query.message.reply_text(
                TEXT[lang]["no_mailbox"],
                reply_markup=main_keyboard(lang),
                parse_mode="HTML"
            )

            return


        data_result = await list_messages(
            mailbox["token"]
        )


        if not data_result:

            await query.message.reply_text(
                TEXT[lang]["api_error"],
                parse_mode="HTML"
            )

            return


        items = message_list(
            data_result
        )


        await query.message.reply_text(
            TEXT[lang]["refresh_done"].format(
                count=len(items)
            ),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )

        return


    # COPY CODE

    if data.startswith("copy:"):

        code = data.split(
            ":",
            1
        )[1]

        lang = user_lang(
            user_id
        )

        await query.answer(
            TEXT[lang]["code_popup"].format(
                code=code
            ),
            show_alert=True
        )

        return


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update,
    context
):

    logger.error(
        "Unhandled error:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    init_db()


    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )


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


    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )


    application.add_error_handler(
        error_handler
    )


    print(
        "🤖 Temp Mail Bot is running..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":

    main()
