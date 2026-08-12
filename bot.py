# bot.py

import asyncio
import html
import logging
import re
from urllib.parse import unquote

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

CHECK_INTERVAL = 3
MAX_MESSAGES = 10

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

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> {source}\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "🔐 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "👇 Tap the button below to copy/view the code.",

        "copy_code":
            "📋 Copy Code",

        "code_copied":
            "📋 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "Press and hold the code to copy it.",

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
            "/about — About the bot\n"
            "/stats — Bot statistics",

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

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>নতুন EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> {source}\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "🔐 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "👇 Code copy/view করতে নিচের Button চাপুন।",

        "copy_code":
            "📋 Code Copy করুন",

        "code_copied":
            "📋 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "Code-এর উপর চাপ দিয়ে ধরে রাখলে Copy করতে পারবেন।",

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
            "/about — Bot সম্পর্কে\n"
            "/stats — Bot statistics",

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

        "new_mail":
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "       📨 <b>NEW EMAIL</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "🌐 <b>Source:</b> {source}\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "💬 <b>Message:</b>\n"
            "{body}",

        "verification":
            "🔐 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "👇 Code ko copy/view karne ke liye button dabayein.",

        "copy_code":
            "📋 Copy Code",

        "code_copied":
            "📋 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "Code par press karke hold karein aur Copy karein.",

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
            "/about — Bot ke baare mein\n"
            "/stats — Bot statistics",

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

    # Telegram bots cannot directly write to the
    # user's system clipboard.
    # The code is shown in a Telegram <code> field
    # and can be copied by the user.

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

    return html.escape(
        str(value)
    )


def is_admin(user_id):

    return user_id in ADMIN_IDS


# =========================================================
# OTP / CODE DETECTOR
# =========================================================

def extract_code(*values):

    text = " ".join(
        str(v)
        for v in values
        if v
    )

    if not text:
        return None

    try:
        text = html.unescape(text)
        text = unquote(text)

        # Remove HTML tags
        text = re.sub(
            r"<[^>]+>",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

    except Exception:
        pass

    patterns = [

        # OTP / verification code
        r"(?:otp|verification|verify|passcode|security)"
        r"(?:\s+code)?"
        r"\s*(?:is|:|-|=)?\s*"
        r"(\d{4,8})\b",

        # code: 123456
        r"(?:code)\s*[:=\-]?\s*(\d{4,8})\b",

        # 123 456
        r"\b(\d{3}\s\d{3})\b",

        # 123-456
        r"\b(\d{3}-\d{3})\b",

        # six digit fallback
        r"\b(\d{6})\b",

        # five digit fallback
        r"\b(\d{5})\b",

        # four digit fallback
        r"\b(\d{4})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            code = match.group(1)

            code = re.sub(
                r"[\s-]",
                "",
                code
            )

            return code

    return None


# =========================================================
# API
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
        total=8,
        connect=3,
        sock_read=6
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

                    logger.error(
                        "API HTTP %s: %s",
                        response.status,
                        endpoint
                    )

                    return None

                try:

                    return await response.json(
                        content_type=None
                    )

                except Exception:

                    raw = await response.text()

                    logger.error(
                        "API returned non-JSON: %s",
                        raw[:500]
                    )

                    return None

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


async def create_mailbox():

    return await api_request(
        "POST",
        "/mailbox"
    )


async def get_messages(token):

    return await api_request(
        "GET",
        "/mailbox/messages",
        token
    )


# =========================================================
# MESSAGE HELPERS
# =========================================================

def get_message_id(item):

    return (
        item.get("id")
        or item.get("messageId")
        or item.get("uid")
        or item.get("createdAt")
        or (
            str(item.get("subject", "")) +
            "|" +
            str(item.get("from", ""))
        )
    )


def get_sender(item):

    sender_data = item.get(
        "from",
        {}
    )

    if isinstance(
        sender_data,
        dict
    ):

        return (
            sender_data.get("address")
            or sender_data.get("email")
            or sender_data.get("name")
            or "Unknown"
        )

    return str(
        sender_data or "Unknown"
    )


def get_body(item):

    parts = [

        item.get("text"),

        item.get("html"),

        item.get("body"),

        item.get("content"),

        item.get("intro"),

        item.get("snippet"),

        item.get("plainText"),

        item.get("textBody"),

        item.get("htmlBody"),
    ]

    return "\n".join(
        str(x)
        for x in parts
        if x
    )


def build_email_message(
    item,
    lang
):

    t = TEXT[lang]

    sender = get_sender(item)

    subject = (
        item.get("subject")
        or "(No Subject)"
    )

    date = (
        item.get("createdAt")
        or item.get("date")
        or item.get("timestamp")
        or ""
    )

    body = get_body(item)

    code = extract_code(

        item.get("subject"),

        item.get("intro"),

        item.get("text"),

        item.get("html"),

        item.get("body"),

        item.get("content"),

        item.get("plainText"),

        item.get("textBody"),

        item.get("htmlBody"),
    )

    # Clean HTML for display
    clean_body = html.unescape(
        str(body)
    )

    clean_body = re.sub(
        r"<[^>]+>",
        " ",
        clean_body
    )

    clean_body = re.sub(
        r"\s+",
        " ",
        clean_body
    ).strip()

    if not clean_body:

        clean_body = "(No message body)"

    message_text = t[
        "new_mail"
    ].format(
        source="Email",
        sender=safe(sender),
        subject=safe(subject),
        date=safe(date),
        body=safe(
            clean_body[:700]
        )
    )

    return (
        message_text,
        code
    )


async def send_email_to_user(
    bot,
    chat_id,
    item,
    lang
):

    message_text, code = (
        build_email_message(
            item,
            lang
        )
    )

    await bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode="HTML"
    )

    if code:

        await bot.send_message(
            chat_id=chat_id,
            text=TEXT[lang][
                "verification"
            ].format(
                code=safe(code)
            ),
            reply_markup=code_keyboard(
                code
            ),
            parse_mode="HTML"
        )


# =========================================================
# GENERATE
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

        return False

    email = (
        mailbox.get("address")
        or mailbox.get("email")
        or mailbox.get("mail")
    )

    token = (
        mailbox.get("token")
        or mailbox.get("id")
        or mailbox.get("key")
    )

    if not email or not token:

        logger.error(
            "Invalid mailbox response: %s",
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

    await loading.edit_text(
        t["created"].format(
            email=safe(email)
        ),
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
    )

    return True


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
# INBOX
# =========================================================

async def show_inbox(
    message,
    user_id,
    lang,
    bot=None
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

    messages = data.get(
        "messages",
        []
    )

    if not isinstance(
        messages,
        list
    ):

        messages = []

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

    for item in messages[:MAX_MESSAGES]:

        await send_email_to_user(
            bot or message.get_bot(),
            message.chat_id,
            item,
            lang
        )


# =========================================================
# COMMANDS
# =========================================================

async def inbox_command(
    update,
    context
):

    user_id = (
        update.effective_user.id
    )

    lang = user_lang(
        user_id
    )

    await show_inbox(
        update.message,
        user_id,
        lang,
        context.bot
    )


async def refresh_command(
    update,
    context
):

    user_id = (
        update.effective_user.id
    )

    lang = user_lang(
        user_id
    )

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

    loading = await update.message.reply_text(
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

    messages = data.get(
        "messages",
        []
    )

    if not isinstance(
        messages,
        list
    ):

        messages = []

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

    for item in messages[:MAX_MESSAGES]:

        await send_email_to_user(
            context.bot,
            user_id,
            item,
            lang
        )

    await update.message.reply_text(
        t["refresh_done"].format(
            count=len(messages)
        ),
        reply_markup=main_keyboard(
            lang
        ),
        parse_mode="HTML"
    )


async def language_command(
    update,
    context
):

    user_id = (
        update.effective_user.id
    )

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

    user_id = (
        update.effective_user.id
    )

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


async def about_command(
    update,
    context
):

    user_id = (
        update.effective_user.id
    )

    lang = user_lang(
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

    user_id = (
        update.effective_user.id
    )

    lang = user_lang(
        user_id
    )

    if not is_admin(
        user_id
    ):

        await admin_only(
            update
        )

        return

    users = get_all_users()

    total_users = len(users)

    active_mailboxes = 0

    for uid in users:

        try:

            mailbox = get_mailbox(
                uid
            )

            if mailbox:
                active_mailboxes += 1

        except Exception:
            pass

    text = (
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "       📊 <b>BOT STATS</b>\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "👥 <b>Total Users:</b> "
        f"{total_users}\n\n"
        "📧 <b>Active Mailboxes:</b> "
        f"{active_mailboxes}\n\n"
        "🤖 <b>Status:</b> 🟢 Online\n"
        "⚡ <b>Auto Inbox:</b> Enabled\n"
        "🔐 <b>Admin:</b> Authorized"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ADMIN
# =========================================================

async def admin_only(
    update
):

    user_id = (
        update.effective_user.id
    )

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
        TEXT[lang][
            "broadcast_done"
        ].format(
            sent=sent,
            failed=failed
        ),
        parse_mode="HTML"
    )


# =========================================================
# AUTOMATIC INBOX
# =========================================================

seen_messages = {}


async def automatic_mail_checker(
    context
):

    users = get_all_users()

    for user_id in users:

        try:

            mailbox = get_mailbox(
                user_id
            )

            if not mailbox:
                continue

            data = await get_messages(
                mailbox["token"]
            )

            if not data:
                continue

            messages = data.get(
                "messages",
                []
            )

            if not isinstance(
                messages,
                list
            ):
                continue

            if not messages:
                continue

            current_ids = {
                get_message_id(item)
                for item in messages
            }

            # First check after bot restart:
            # don't send old messages again.
            if user_id not in seen_messages:

                seen_messages[
                    user_id
                ] = current_ids

                continue

            known = seen_messages[
                user_id
            ]

            new_messages = []

            for item in messages:

                mid = get_message_id(
                    item
                )

                if mid in known:
                    continue

                known.add(mid)

                new_messages.append(
                    item
                )

            if not new_messages:
                continue

            lang = user_lang(
                user_id
            )

            for item in reversed(
                new_messages
            ):

                try:

                    await send_email_to_user(
                        context.bot,
                        user_id,
                        item,
                        lang
                    )

                except Exception as error:

                    logger.error(
                        "Could not send new email to %s: %s",
                        user_id,
                        error
                    )

        except Exception as error:

            logger.error(
                "Automatic checker error: %s",
                error
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

    user_id = (
        query.from_user.id
    )

    data = query.data


    # LANGUAGE

    if data.startswith(
        "lang_"
    ):

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
            query.message,
            user_id,
            lang,
            context.bot
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
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML"
            )

            return

        loading = await query.message.reply_text(
            TEXT[lang]["checking"],
            parse_mode="HTML"
        )

        data_result = await get_messages(
            mailbox["token"]
        )

        if not data_result:

            await loading.edit_text(
                TEXT[lang]["api_error"],
                parse_mode="HTML"
            )

            return

        messages = data_result.get(
            "messages",
            []
        )

        if not messages:

            await loading.edit_text(
                TEXT[lang]["empty"],
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML"
            )

            return

        await loading.delete()

        for item in messages[
            :MAX_MESSAGES
        ]:

            await send_email_to_user(
                context.bot,
                user_id,
                item,
                lang
            )

        return


    # COPY CODE

    if data.startswith(
        "copy:"
    ):

        code = data.split(
            ":",
            1
        )[1]

        lang = user_lang(
            user_id
        )

        await query.answer(
            TEXT[lang][
                "code_copied"
            ].format(
                code=safe(code)
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
        "Unhandled error",
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
        .build()
    )


    # Commands

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

    # /boardchat kept as requested
    application.add_handler(
        CommandHandler(
            "boardchat",
            broadcast_command
        )
    )


    # Inline buttons

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )


    # Error handler

    application.add_error_handler(
        error_handler
    )


    # Automatic inbox checker
    # Runs every 3 seconds.

    if application.job_queue:

        application.job_queue.run_repeating(
            automatic_mail_checker,
            interval=CHECK_INTERVAL,
            first=5
        )

    else:

        logger.error(
            "JobQueue is unavailable. "
            "Install python-telegram-bot[job-queue]."
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
