import asyncio
import html
import logging
import os
import random
import re
import string
from datetime import datetime

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

API_BASE = "https://www.1secmail.com/api/v1/"

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

    # =====================================================
    # ENGLISH
    # =====================================================

    "en": {

        "welcome":
            "👋 <b>Welcome to Temp Mail Bot!</b>\n\n"
            "📧 Create a temporary email and receive messages "
            "instantly.\n\n"
            "🔐 Verification codes can be detected automatically.\n\n"
            "🌐 Please select your preferred language:",

        "language_ok":
            "✅ <b>Language selected successfully!</b>\n\n"
            "⚡ Creating your temporary email...",

        "generating":
            "⚡ <b>Creating your temporary email...</b>",

        "created":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "     📧 <b>NEW TEMP EMAIL</b>\n"
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
            "No messages received yet.",

        "no_mailbox":
            "⚠️ <b>No temporary email found.</b>\n\n"
            "Press <b>➕ Generate New</b> first.",

        "api_error":
            "❌ <b>Something went wrong.</b>\n\n"
            "The temporary email service may be unavailable.\n"
            "Please try again later.",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> 1secmail\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "     🔐 <b>VERIFICATION CODE</b>\n"
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
            "          📚 <b>HELP</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "➕ Generate New — Create a new email\n"
            "📥 Inbox — View received emails\n"
            "🔄 Refresh — Check for new emails\n\n"
            "/language — Change language\n"
            "/stats — Bot statistics\n"
            "/help — Show help\n"
            "/about — About the bot",

        "about":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast disposable email receiver.\n\n"
            "⚡ Powered by 1secmail API\n"
            "🔒 No API key required",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Sorry! This command is available only "
            "for administrators.",

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
            "        📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 <b>Total Users:</b> {users}\n"
            "📧 <b>Active Mailboxes:</b> {mailboxes}\n\n"
            "⚡ <b>API:</b> 1secmail\n"
            "🟢 <b>Status:</b> Online",
    },


    # =====================================================
    # BANGLA
    # =====================================================

    "bn": {

        "welcome":
            "👋 <b>Temp Mail Bot-এ স্বাগতম!</b>\n\n"
            "📧 Temporary Email তৈরি করে দ্রুত Message "
            "গ্রহণ করুন।\n\n"
            "🔐 Verification Code automatically detect করা হবে।\n\n"
            "🌐 আপনার পছন্দের ভাষা নির্বাচন করুন:",

        "language_ok":
            "✅ <b>ভাষা সফলভাবে নির্বাচন করা হয়েছে!</b>\n\n"
            "⚡ আপনার Temporary Email তৈরি হচ্ছে...",

        "generating":
            "⚡ <b>আপনার Temporary Email তৈরি হচ্ছে...</b>",

        "created":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "     📧 <b>নতুন TEMP EMAIL</b>\n"
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
            "এখনো কোনো Message আসেনি।",

        "no_mailbox":
            "⚠️ <b>কোনো Temporary Email পাওয়া যায়নি।</b>\n\n"
            "প্রথমে <b>➕ নতুন তৈরি করুন</b> চাপুন।",

        "api_error":
            "❌ <b>সমস্যা হয়েছে।</b>\n\n"
            "Temporary Email service বর্তমানে unavailable হতে পারে।\n"
            "কিছুক্ষণ পর আবার চেষ্টা করুন।",

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        📨 <b>নতুন EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> 1secmail\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "     🔐 <b>VERIFICATION CODE</b>\n"
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
            "          📚 <b>HELP</b>\n"
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
            "        📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দ্রুত Temporary Email receiver।\n\n"
            "⚡ 1secmail API দ্বারা পরিচালিত\n"
            "🔒 API key প্রয়োজন নেই",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "দুঃখিত! এই Command শুধুমাত্র "
            "Administrator-এর জন্য।",

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
            "        📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 <b>Total Users:</b> {users}\n"
            "📧 <b>Active Mailboxes:</b> {mailboxes}\n\n"
            "⚡ <b>API:</b> 1secmail\n"
            "🟢 <b>Status:</b> Online",
    },


    # =====================================================
    # HINDI
    # =====================================================

    "hi": {

        "welcome":
            "👋 <b>Temp Mail Bot mein aapka swagat hai!</b>\n\n"
            "📧 Temporary Email banayein aur messages "
            "receive karein.\n\n"
            "🔐 Verification Code automatically detect hoga.\n\n"
            "🌐 Apni pasand ki language select karein:",

        "language_ok":
            "✅ <b>Language successfully select ho gayi!</b>\n\n"
            "⚡ Aapka Temporary Email create ho raha hai...",

        "generating":
            "⚡ <b>Aapka Temporary Email create ho raha hai...</b>",

        "created":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "     📧 <b>NEW TEMP EMAIL</b>\n"
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
            "        📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> 1secmail\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "     🔐 <b>VERIFICATION CODE</b>\n"
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
            "          📚 <b>HELP</b>\n"
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
            "        📧 <b>TEMP MAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Fast Temporary Email receiver.\n\n"
            "⚡ 1secmail API se powered\n"
            "🔒 API key ki zarurat nahi",

        "admin_only":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "        🔐 <b>ADMIN ONLY</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "Maaf kijiye! Yeh command sirf "
            "Administrator ke liye hai.",

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
            "        📊 <b>BOT STATS</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 <b>Total Users:</b> {users}\n"
            "📧 <b>Active Mailboxes:</b> {mailboxes}\n\n"
            "⚡ <b>API:</b> 1secmail\n"
            "🟢 <b>Status:</b> Online",
    },
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
        ],
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
            ),
        ],
        [
            InlineKeyboardButton(
                t["refresh"],
                callback_data="refresh"
            ),
        ],
        [
            InlineKeyboardButton(
                "🌐 Language",
                callback_data="language"
            ),
        ],
    ])


# =========================================================
# COPY CODE KEYBOARD
# =========================================================

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

    try:
        return int(user_id) in ADMIN_IDS
    except Exception:
        return user_id in ADMIN_IDS


def clean_body(text):

    if not text:
        return ""

    text = str(text)

    text = re.sub(
        r"\r\n?",
        "\n",
        text
    )

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# OTP DETECTOR
# =========================================================

def extract_code(text):

    if not text:
        return None

    text = str(text)

    patterns = [

        r"(?:verification\s*code|verification|verify\s*code|"
        r"security\s*code|confirmation\s*code|one[- ]time\s*code|"
        r"otp|code|pin)"
        r"\s*(?:is|:|-)?\s*(\d{6})\b",

        r"(?:verification\s*code|verification|verify\s*code|"
        r"security\s*code|confirmation\s*code|otp|code|pin)"
        r"\s*(?:is|:|-)?\s*(\d{5})\b",

        r"(?:verification\s*code|verification|verify\s*code|"
        r"security\s*code|confirmation\s*code|otp|code|pin)"
        r"\s*(?:is|:|-)?\s*(\d{4})\b",

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


# =========================================================
# HTTP REQUEST
# =========================================================

async def api_request(
    session,
    params
):

    try:

        async with session.get(
            API_BASE,
            params=params,
            timeout=HTTP_TIMEOUT,
        ) as response:

            if response.status != 200:

                text = await response.text()

                logger.error(
                    "1secmail HTTP %s: %s",
                    response.status,
                    text[:300],
                )

                return None

            return await response.json(
                content_type=None
            )

    except asyncio.TimeoutError:

        logger.error(
            "1secmail timeout"
        )

        return None

    except Exception as error:

        logger.error(
            "1secmail error: %s",
            error
        )

        return None


# =========================================================
# GENERATE TEMP EMAIL
# =========================================================

async def create_mailbox():

    domains = [
        "1secmail.com",
        "1secmail.org",
        "1secmail.net",
    ]

    login = (
        "tmp"
        + "".join(
            random.choices(
                string.ascii_lowercase
                + string.digits,
                k=12
            )
        )
    )

    domain = random.choice(domains)

    email = f"{login}@{domain}"

    return {
        "email": email,
        "login": login,
        "domain": domain,
    }


# =========================================================
# GET MESSAGE LIST
# =========================================================

async def get_messages(
    session,
    mailbox
):

    result = await api_request(
        session,
        {
            "action": "getMessages",
            "login": mailbox["login"],
            "domain": mailbox["domain"],
        },
    )

    if not isinstance(result, list):
        return []

    return result


# =========================================================
# GET FULL MESSAGE
# =========================================================

async def get_full_message(
    session,
    mailbox,
    message_id
):

    result = await api_request(
        session,
        {
            "action": "readMessage",
            "login": mailbox["login"],
            "domain": mailbox["domain"],
            "id": message_id,
        },
    )

    if not isinstance(result, dict):
        return None

    return result


# =========================================================
# MESSAGE CACHE
# =========================================================

seen_messages = {}

checker_task = None


def get_seen(user_id):

    if user_id not in seen_messages:
        seen_messages[user_id] = set()

    return seen_messages[user_id]


# =========================================================
# SEND EMAIL TO USER
# =========================================================

async def send_mail_to_user(
    bot,
    user_id,
    mail,
    lang,
):

    t = TEXT[lang]

    sender = (
        mail.get("from")
        or "Unknown"
    )

    subject = (
        mail.get("subject")
        or "(No Subject)"
    )

    date = (
        mail.get("date")
        or mail.get("timestamp")
        or ""
    )

    body = (
        mail.get("textBody")
        or mail.get("body")
        or ""
    )

    body = clean_body(body)

    if not body:

        body = (
            mail.get("htmlBody")
            or "📭 Empty message"
        )

    body = clean_body(body)

    if not body:
        body = "📭 Empty message"

    message_text = t["new_mail"].format(
        sender=safe(sender),
        subject=safe(subject),
        date=safe(date),
        body=safe(body[:3000]),
    )

    try:

        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="HTML",
        )

        code = extract_code(body)

        if not code:

            code = extract_code(
                subject
            )

        if code:

            await bot.send_message(
                chat_id=user_id,
                text=t["verification"].format(
                    code=safe(code)
                ),
                reply_markup=code_keyboard(
                    code,
                    lang
                ),
                parse_mode="HTML",
            )

    except Exception as error:

        logger.error(
            "Failed sending email to %s: %s",
            user_id,
            error,
        )


# =========================================================
# GENERATE NEW MAILBOX
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

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML",
        )

        return

    save_mailbox(
        user_id,
        mailbox["email"],
        mailbox["login"],
        mailbox["domain"],
    )

    # Reset message cache
    seen_messages[user_id] = set()

    await loading.edit_text(
        t["created"].format(
            email=safe(
                mailbox["email"]
            )
        ),
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML",
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user:
        return

    save_user(
        user.id,
        user.username or "",
    )

    lang = get_language(
        user.id
    )

    # First time user
    if not lang:

        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML",
        )

        return

    # Existing user
    await generate_new(
        update.message,
        user.id,
        lang,
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

    mailbox = get_mailbox(
        user_id
    )

    if not mailbox:

        await message.reply_text(
            t["no_mailbox"],
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML",
        )

        return

    loading = await message.reply_text(
        t["checking"],
        parse_mode="HTML",
    )

    async with aiohttp.ClientSession() as session:

        messages = await get_messages(
            session,
            mailbox
        )

        if messages is None:

            await loading.edit_text(
                t["api_error"],
                parse_mode="HTML",
            )

            return

        if not messages:

            await loading.edit_text(
                t["empty"],
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML",
            )

            return

        await loading.delete()

        seen = get_seen(user_id)

        # Show latest 20
        for item in reversed(
            messages[:20]
        ):

            message_id = item.get("id")

            if not message_id:
                continue

            full_mail = await get_full_message(
                session,
                mailbox,
                message_id
            )

            if not full_mail:
                continue

            seen.add(
                str(message_id)
            )

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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
# REFRESH
# =========================================================

async def refresh_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id
    lang = user_lang(user_id)
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
            parse_mode="HTML",
        )

        return

    async with aiohttp.ClientSession() as session:

        messages = await get_messages(
            session,
            mailbox
        )

        if messages is None:

            await update.message.reply_text(
                t["api_error"],
                parse_mode="HTML",
            )

            return

        if not messages:

            await update.message.reply_text(
                t["empty"],
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML",
            )

            return

        seen = get_seen(user_id)

        new_count = 0

        for item in reversed(
            messages[:20]
        ):

            message_id = item.get("id")

            if not message_id:
                continue

            full_mail = await get_full_message(
                session,
                mailbox,
                message_id
            )

            if not full_mail:
                continue

            seen.add(
                str(message_id)
            )

            new_count += 1

            await send_mail_to_user(
                context.bot,
                user_id,
                full_mail,
                lang,
            )

        await update.message.reply_text(
            t["refresh_done"].format(
                count=new_count
            ),
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML",
        )


# =========================================================
# LANGUAGE COMMAND
# =========================================================

async def language_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id
    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["help"],
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML",
    )


# =========================================================
# ABOUT
# =========================================================

async def about_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await admin_only(
            update
        )

        return

    lang = user_lang(user_id)
    t = TEXT[lang]

    try:

        users = list(
            get_all_users()
        )

    except Exception:

        users = []

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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await admin_only(
            update
        )

        return

    lang = user_lang(user_id)

    await update.message.reply_text(
        TEXT[lang]["admin_panel"],
        parse_mode="HTML",
    )


# =========================================================
# BROADCAST
# =========================================================

async def broadcast_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await admin_only(
            update
        )

        return

    lang = user_lang(user_id)

    if not context.args:

        await update.message.reply_text(
            TEXT[lang]["broadcast_start"],
            parse_mode="HTML",
        )

        return

    broadcast_text = " ".join(
        context.args
    )

    try:
        users = list(
            get_all_users()
        )
    except Exception:
        users = []

    sent = 0
    failed = 0

    for target_id in users:

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=broadcast_text,
                parse_mode="HTML",
            )

            sent += 1

            # Telegram flood protection
            await asyncio.sleep(
                0.08
            )

        except Exception as error:

            failed += 1

            logger.warning(
                "Broadcast failed for %s: %s",
                target_id,
                error,
            )

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

async def automatic_mail_checker(
    application
):

    logger.info(
        "📨 Automatic Mail Checker Started"
    )

    async with aiohttp.ClientSession() as session:

        while True:

            try:

                try:
                    users = list(
                        get_all_users()
                    )
                except Exception:
                    users = []

                for user_id in users:

                    try:

                        mailbox = get_mailbox(
                            user_id
                        )

                        if not mailbox:
                            continue

                        messages = await get_messages(
                            session,
                            mailbox
                        )

                        if messages is None:
                            continue

                        seen = get_seen(
                            user_id
                        )

                        # First checker run:
                        # Mark existing messages as seen.
                        if not seen:

                            for item in messages:

                                mid = item.get(
                                    "id"
                                )

                                if mid:
                                    seen.add(
                                        str(mid)
                                    )

                            continue

                        new_messages = []

                        for item in messages:

                            mid = item.get(
                                "id"
                            )

                            if not mid:
                                continue

                            mid = str(mid)

                            if mid not in seen:

                                new_messages.append(
                                    item
                                )

                        if not new_messages:
                            continue

                        lang = user_lang(
                            user_id
                        )

                        # Oldest -> newest
                        new_messages.reverse()

                        for item in new_messages:

                            mid = str(
                                item.get("id")
                            )

                            # Mark before sending
                            # to avoid duplicates.
                            seen.add(mid)

                            full_mail = await get_full_message(
                                session,
                                mailbox,
                                mid
                            )

                            if not full_mail:
                                continue

                            await send_mail_to_user(
                                application.bot,
                                user_id,
                                full_mail,
                                lang,
                            )

                    except Exception as error:

                        logger.error(
                            "Checker error for %s: %s",
                            user_id,
                            error,
                        )

                await asyncio.sleep(
                    POLL_INTERVAL
                )

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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
            "",
            1
        )

        if lang not in TEXT:
            lang = "en"

        set_language(
            user_id,
            lang
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

    # =====================================================
    # LANGUAGE BUTTON
    # =====================================================

    if data == "language":

        lang = user_lang(
            user_id
        )

        await query.message.reply_text(
            TEXT[lang]["language"],
            reply_markup=language_keyboard(),
            parse_mode="HTML",
        )

        return

    # =====================================================
    # GENERATE
    # =====================================================

    if data == "generate":

        lang = user_lang(
            user_id
        )

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

        lang = user_lang(
            user_id
        )

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

        lang = user_lang(
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
                parse_mode="HTML",
            )

            return

        async with aiohttp.ClientSession() as session:

            messages = await get_messages(
                session,
                mailbox
            )

            if messages is None:

                await query.message.reply_text(
                    TEXT[lang]["api_error"],
                    parse_mode="HTML",
                )

                return

            if not messages:

                await query.message.reply_text(
                    TEXT[lang]["empty"],
                    reply_markup=main_keyboard(
                        lang
                    ),
                    parse_mode="HTML",
                )

                return

            seen = get_seen(
                user_id
            )

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
                    session,
                    mailbox,
                    message_id
                )

                if not full_mail:
                    continue

                seen.add(
                    str(message_id)
                )

                count += 1

                await send_mail_to_user(
                    context.bot,
                    user_id,
                    full_mail,
                    lang,
                )

            await query.message.reply_text(
                TEXT[lang]["refresh_done"].format(
                    count=count
                ),
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML",
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
        "Unhandled exception:",
        exc_info=context.error,
    )


# =========================================================
# POST INIT
# =========================================================

async def post_init(
    application
):

    global checker_task

    checker_task = asyncio.create_task(
        automatic_mail_checker(
            application
        )
    )

    application.bot_data[
        "mail_checker"
    ] = checker_task

    logger.info(
        "🚀 Bot startup completed"
    )


# =========================================================
# POST SHUTDOWN
# =========================================================

async def post_shutdown(
    application
):

    global checker_task

    task = application.bot_data.get(
        "mail_checker"
    )

    if task:

        task.cancel()

        try:

            await task

        except asyncio.CancelledError:
            pass

    checker_task = None

    logger.info(
        "🛑 Bot shutdown completed"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # Initialize database
    init_db()

    # Build application
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
    # ERROR HANDLER
    # =====================================================

    application.add_error_handler(
        error_handler
    )

    print(
        "🤖 Temp Mail Bot is running..."
    )

    # =====================================================
    # START POLLING
    # =====================================================

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
