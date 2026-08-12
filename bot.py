# bot.py

import asyncio
import html
import logging
import re

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

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


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

        "code":
            "🔐 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "Tap the code above to copy it.",

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
            "Send the message you want to broadcast.",

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
            "এখন এই Email-এ message গ্রহণ করতে পারবেন।",

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

        "code":
            "🔐 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "উপরের Code-এ চাপ দিলে Copy করতে পারবেন।",

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
            "যে Message সবাইকে পাঠাতে চান সেটি পাঠান।",

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

        "code":
            "🔐 <b>Verification Code</b>\n\n"
            "<code>{code}</code>\n\n"
            "Upar diye gaye Code par tap karke copy karein.",

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
            "Jo message sabhi users ko bhejna hai, woh bhejein.",

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
# LANGUAGE BUTTONS
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
# MAIN BUTTONS
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
# API REQUEST
# =========================================================

async def api_request(
    method,
    endpoint,
    token=None
):

    url = API_BASE + endpoint

    headers = {}

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    timeout = aiohttp.ClientTimeout(
        total=8
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
                        "Smails API error: %s",
                        response.status
                    )

                    return None

                return await response.json()

    except Exception as error:

        logger.error(
            "API error: %s",
            error
        )

        return None


# =========================================================
# CREATE MAILBOX
# =========================================================

async def create_mailbox():

    return await api_request(
        "POST",
        "/mailbox"
    )


# =========================================================
# GET MESSAGES
# =========================================================

async def get_messages(token):

    return await api_request(
        "GET",
        "/mailbox/messages",
        token
    )


# =========================================================
# EXTRACT VERIFICATION CODE
# =========================================================

def extract_code(text):

    if not text:
        return None

    patterns = [
        r"\b\d{6}\b",
        r"\b\d{5}\b",
        r"\b\d{4}\b",
        r"\b[A-Z0-9]{6,8}\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(0)

    return None


# =========================================================
# SAFE TEXT
# =========================================================

def safe(value):

    if value is None:
        return ""

    return html.escape(
        str(value)
    )


# =========================================================
# GET LANGUAGE
# =========================================================

def user_lang(user_id):

    lang = get_language(
        user_id
    )

    if lang not in TEXT:
        return "en"

    return lang


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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
        update,
        user.id,
        lang
    )


# =========================================================
# GENERATE NEW
# =========================================================

async def generate_new(
    update,
    user_id,
    lang
):

    t = TEXT[lang]

    message = (
        update.callback_query.message
        if update.callback_query
        else update.message
    )

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

    email = mailbox.get(
        "address"
    )

    token = mailbox.get(
        "token"
    )

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

    await loading.edit_text(
        t["created"].format(
            email=safe(email)
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )


# =========================================================
# SHOW INBOX
# =========================================================

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
            reply_markup=main_keyboard(lang),
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

    if not messages:

        await loading.edit_text(
            t["empty"],
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )

        return

    await loading.delete()

    for item in messages[:10]:

        sender_data = item.get(
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
            item.get("subject")
            or "(No Subject)"
        )

        date = (
            item.get("createdAt")
            or ""
        )

        body = (
            item.get("intro")
            or item.get("text")
            or ""
        )

        code = extract_code(
            body
        )

        message_text = t[
            "new_mail"
        ].format(

            source="Email",

            sender=safe(
                sender
            ),

            subject=safe(
                subject
            ),

            date=safe(
                date
            ),

            body=safe(
                body[:700]
            )
        )

        buttons = []

        if code:

            buttons.append([
                InlineKeyboardButton(
                    f"📋 {code}",
                    callback_data=(
                        f"showcode:{code}"
                    )
                )
            ])

        await message.reply_text(
            message_text,
            reply_markup=(
                InlineKeyboardMarkup(
                    buttons
                )
                if buttons
                else None
            ),
            parse_mode="HTML"
        )


# =========================================================
# INBOX COMMAND
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
        lang
    )


# =========================================================
# REFRESH COMMAND
# =========================================================

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
            reply_markup=main_keyboard(lang),
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

    messages = data.get(
        "messages",
        []
    )

    await update.message.reply_text(
        t["refresh_done"].format(
            count=len(messages)
        ),
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )


# =========================================================
# LANGUAGE COMMAND
# =========================================================

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


# =========================================================
# HELP
# =========================================================

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
        reply_markup=main_keyboard(lang),
        parse_mode="HTML"
    )


# =========================================================
# ABOUT
# =========================================================

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
# ADMIN CHECK
# =========================================================

def is_admin(user_id):

    return user_id in ADMIN_IDS


# =========================================================
# ADMIN-ONLY MESSAGE
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


# =========================================================
# ADMIN COMMAND
# =========================================================

async def admin_command(
    update,
    context
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
        parse_mode="HTML"
    )


# =========================================================
# BROADCAST
# =========================================================

async def broadcast_command(
    update,
    context
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

            # Prevent Telegram flood
            await asyncio.sleep(
                0.05
            )

        except Exception as error:

            logger.warning(
                "Broadcast failed %s: %s",
                user_id,
                error
            )

            failed += 1

    await update.message.reply_text(
        TEXT[lang]["broadcast_done"].format(
            sent=sent,
            failed=failed
        ),
        parse_mode="HTML"
    )


# =========================================================
# CALLBACK
# =========================================================

async def callback_handler(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    data = query.data


    # -----------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------

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

        # Automatically create first email
        await generate_new(
            update,
            user_id,
            lang
        )

        return


    # -----------------------------------------------------
    # GENERATE
    # -----------------------------------------------------

    if data == "generate":

        lang = user_lang(
            user_id
        )

        await generate_new(
            update,
            user_id,
            lang
        )

        return


    # -----------------------------------------------------
    # INBOX
    # -----------------------------------------------------

    if data == "inbox":

        lang = user_lang(
            user_id
        )

        await show_inbox(
            query.message,
            user_id,
            lang
        )

        return


    # -----------------------------------------------------
    # REFRESH
    # -----------------------------------------------------

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

        data_result = await get_messages(
            mailbox["token"]
        )

        if not data_result:

            await query.message.reply_text(
                TEXT[lang]["api_error"],
                parse_mode="HTML"
            )

            return

        messages = data_result.get(
            "messages",
            []
        )

        await query.message.reply_text(
            TEXT[lang]["refresh_done"].format(
                count=len(messages)
            ),
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )

        return


    # -----------------------------------------------------
    # SHOW CODE
    # -----------------------------------------------------

    if data.startswith(
        "showcode:"
    ):

        code = data.split(
            ":",
            1
        )[1]

        lang = user_lang(
            user_id
        )

        await query.answer(
            TEXT[lang]["code"].format(
                code=code
            ),
            show_alert=True
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
        .build()
    )


    # User commands

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


    # Admin

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    # Supports both spellings
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


    # Inline buttons

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


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":
    main()
