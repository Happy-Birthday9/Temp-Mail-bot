import logging
import re
import html
import aiohttp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from config import BOT_TOKEN, ADMIN_IDS
from database import (
    init_db,
    get_language,
    set_language,
    save_mailbox,
    get_mailbox,
    save_user
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# =========================================================
# API
# =========================================================

SMAILS_API = "https://smails.dev/api"


# =========================================================
# LANGUAGE TEXT
# =========================================================

TEXT = {

    "en": {

        "welcome":
            "👋 <b>Welcome to Temp Mail Bot!</b>\n\n"
            "Please select your preferred language:",

        "language_success":
            "✅ <b>Language selected successfully!</b>",

        "mail_created":
            "🎉 <b>Temporary Email Created!</b>\n\n"
            "📧 <b>Your Email:</b>\n"
            "<code>{email}</code>\n\n"
            "⏳ <b>Status:</b> Active\n\n"
            "You can now use this email to receive messages.",

        "generate":
            "➕ Generate New",

        "inbox":
            "📥 Inbox",

        "refresh":
            "🔄 Refresh",

        "generating":
            "⏳ <b>Generating a new temporary email...</b>",

        "inbox_loading":
            "📥 <b>Loading your inbox...</b>",

        "refreshing":
            "🔄 <b>Refreshing your inbox...</b>",

        "no_mail":
            "📭 <b>No new messages.</b>\n\n"
            "Your inbox is currently empty.",

        "new_mail":
            "📨 <b>New Message</b>\n\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "{body}",

        "read_more":
            "📖 Read Full Message",

        "copy_code":
            "📋 Copy Code: {code}",

        "code_found":
            "🔐 <b>Verification Code:</b>\n\n"
            "<code>{code}</code>",

        "no_mailbox":
            "⚠️ <b>No temporary email found.</b>\n\n"
            "Please press <b>➕ Generate New</b> first.",

        "api_error":
            "❌ <b>Something went wrong.</b>\n\n"
            "Please try again in a moment.",

        "language_select":
            "🌐 <b>Please select your preferred language:</b>",

        "admin_only":
            "🔐 <b>ADMIN ONLY</b>\n\n"
            "Sorry! This command is available only "
            "for administrators.\n\n"
            "You don't have permission to use this command.",

        "help":
            "📚 <b>Help</b>\n\n"
            "➕ Generate New — Create a new temporary email\n"
            "📥 Inbox — View received messages\n"
            "🔄 Refresh — Check for new messages\n"
            "/language — Change language\n"
            "/help — Show help",

        "about":
            "📧 <b>Temp Mail Bot</b>\n\n"
            "Fast temporary email receiver.\n"
            "Powered by Smails API.",

        "stats":
            "📊 <b>Your Statistics</b>\n\n"
            "User ID: <code>{user_id}</code>\n"
            "Mailbox: {mailbox}"

    },


    "bn": {

        "welcome":
            "👋 <b>Temp Mail Bot-এ স্বাগতম!</b>\n\n"
            "আপনার পছন্দের ভাষা নির্বাচন করুন:",

        "language_success":
            "✅ <b>ভাষা সফলভাবে নির্বাচন করা হয়েছে!</b>",

        "mail_created":
            "🎉 <b>Temporary Email তৈরি হয়েছে!</b>\n\n"
            "📧 <b>আপনার Email:</b>\n"
            "<code>{email}</code>\n\n"
            "⏳ <b>Status:</b> Active\n\n"
            "এখন এই Email-এ message গ্রহণ করতে পারবেন।",

        "generate":
            "➕ নতুন তৈরি করুন",

        "inbox":
            "📥 ইনবক্স",

        "refresh":
            "🔄 রিফ্রেশ",

        "generating":
            "⏳ <b>নতুন Temporary Email তৈরি হচ্ছে...</b>",

        "inbox_loading":
            "📥 <b>আপনার Inbox লোড হচ্ছে...</b>",

        "refreshing":
            "🔄 <b>আপনার Inbox রিফ্রেশ হচ্ছে...</b>",

        "no_mail":
            "📭 <b>কোনো নতুন Message নেই।</b>\n\n"
            "আপনার Inbox বর্তমানে খালি।",

        "new_mail":
            "📨 <b>নতুন Message</b>\n\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "{body}",

        "read_more":
            "📖 পুরো Message দেখুন",

        "copy_code":
            "📋 Code Copy করুন: {code}",

        "code_found":
            "🔐 <b>Verification Code:</b>\n\n"
            "<code>{code}</code>",

        "no_mailbox":
            "⚠️ <b>কোনো Temporary Email পাওয়া যায়নি।</b>\n\n"
            "প্রথমে <b>➕ নতুন তৈরি করুন</b> Button চাপুন।",

        "api_error":
            "❌ <b>সমস্যা হয়েছে।</b>\n\n"
            "কিছুক্ষণ পর আবার চেষ্টা করুন।",

        "language_select":
            "🌐 <b>আপনার পছন্দের ভাষা নির্বাচন করুন:</b>",

        "admin_only":
            "🔐 <b>শুধুমাত্র ADMIN</b>\n\n"
            "দুঃখিত! এই Command শুধুমাত্র "
            "Administrator-এর জন্য।\n\n"
            "আপনার এই Command ব্যবহার করার অনুমতি নেই।",

        "help":
            "📚 <b>Help</b>\n\n"
            "➕ নতুন তৈরি করুন — নতুন Temporary Email\n"
            "📥 ইনবক্স — আসা Message দেখুন\n"
            "🔄 রিফ্রেশ — নতুন Message check করুন\n"
            "/language — ভাষা পরিবর্তন\n"
            "/help — Help দেখুন",

        "about":
            "📧 <b>Temp Mail Bot</b>\n\n"
            "দ্রুত Temporary Email receiver।\n"
            "Smails API দ্বারা পরিচালিত।",

        "stats":
            "📊 <b>আপনার Statistics</b>\n\n"
            "User ID: <code>{user_id}</code>\n"
            "Mailbox: {mailbox}"

    },


    # Roman Hindi
    "hi": {

        "welcome":
            "👋 <b>Temp Mail Bot mein aapka swagat hai!</b>\n\n"
            "Apni pasand ki language select karein:",

        "language_success":
            "✅ <b>Language successfully select ho gayi!</b>",

        "mail_created":
            "🎉 <b>Temporary Email create ho gaya!</b>\n\n"
            "📧 <b>Aapka Email:</b>\n"
            "<code>{email}</code>\n\n"
            "⏳ <b>Status:</b> Active\n\n"
            "Ab aap is Email par messages receive kar sakte hain.",

        "generate":
            "➕ Naya Generate",

        "inbox":
            "📥 Inbox",

        "refresh":
            "🔄 Refresh",

        "generating":
            "⏳ <b>Naya Temporary Email generate ho raha hai...</b>",

        "inbox_loading":
            "📥 <b>Aapka Inbox load ho raha hai...</b>",

        "refreshing":
            "🔄 <b>Aapka Inbox refresh ho raha hai...</b>",

        "no_mail":
            "📭 <b>Koi naya message nahi hai.</b>\n\n"
            "Aapka inbox abhi empty hai.",

        "new_mail":
            "📨 <b>Naya Message</b>\n\n"
            "👤 <b>From:</b> {sender}\n"
            "📌 <b>Subject:</b> {subject}\n"
            "🕐 <b>Date:</b> {date}\n\n"
            "{body}",

        "read_more":
            "📖 Full Message Padhein",

        "copy_code":
            "📋 Code Copy Karein: {code}",

        "code_found":
            "🔐 <b>Verification Code:</b>\n\n"
            "<code>{code}</code>",

        "no_mailbox":
            "⚠️ <b>Koi Temporary Email nahi mila.</b>\n\n"
            "Pehle <b>➕ Naya Generate</b> button press karein.",

        "api_error":
            "❌ <b>Kuch problem ho gayi.</b>\n\n"
            "Thodi der baad dobara try karein.",

        "language_select":
            "🌐 <b>Apni pasand ki language select karein:</b>",

        "admin_only":
            "🔐 <b>ADMIN ONLY</b>\n\n"
            "Maaf kijiye! Yeh command sirf "
            "Administrator ke liye hai.\n\n"
            "Aapko is command ko use karne ki permission nahi hai.",

        "help":
            "📚 <b>Help</b>\n\n"
            "➕ Naya Generate — Naya Temporary Email banayein\n"
            "📥 Inbox — Received messages dekhein\n"
            "🔄 Refresh — Naye messages check karein\n"
            "/language — Language change karein\n"
            "/help — Help dekhein",

        "about":
            "📧 <b>Temp Mail Bot</b>\n\n"
            "Fast Temporary Email receiver.\n"
            "Smails API se powered.",

        "stats":
            "📊 <b>Aapke Statistics</b>\n\n"
            "User ID: <code>{user_id}</code>\n"
            "Mailbox: {mailbox}"

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
# HTTP SESSION
# =========================================================

async def api_request(
    method,
    endpoint,
    token=None
):

    url = SMAILS_API + endpoint

    headers = {}

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    timeout = aiohttp.ClientTimeout(
        total=8
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        async with session.request(
            method,
            url,
            headers=headers
        ) as response:

            if response.status >= 400:
                return None

            return await response.json()


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
# GET ONE MESSAGE
# =========================================================

async def get_message(
    token,
    message_id
):

    return await api_request(
        "GET",
        f"/mailbox/messages/{message_id}",
        token
    )


# =========================================================
# EXTRACT CODE
# =========================================================

def extract_code(text):

    if not text:
        return None

    patterns = [

        r"\b\d{6}\b",
        r"\b\d{4,8}\b",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:
            return match.group(0)

    return None


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    user_id = user.id

    save_user(
        user_id,
        user.username
    )

    lang = get_language(
        user_id
    )

    if not lang:

        await update.message.reply_text(
            TEXT["en"]["welcome"],
            reply_markup=language_keyboard(),
            parse_mode="HTML"
        )

        return

    await generate_email(
        update,
        user_id,
        lang
    )


# =========================================================
# GENERATE EMAIL
# =========================================================

async def generate_email(
    update,
    user_id,
    lang
):

    t = TEXT[lang]

    if update.callback_query:

        message = (
            update.callback_query.message
        )

    else:

        message = update.message


    loading = await message.reply_text(
        t["generating"],
        parse_mode="HTML"
    )

    try:

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


        save_mailbox(
            user_id,
            email,
            token
        )


        await loading.edit_text(
            t["mail_created"].format(
                email=html.escape(
                    email
                )
            ),
            reply_markup=main_keyboard(
                lang
            ),
            parse_mode="HTML"
        )

    except Exception as e:

        logger.error(
            "Generate error: %s",
            e
        )

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )


# =========================================================
# INBOX
# =========================================================

async def show_inbox(
    update,
    user_id,
    lang
):

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


    token = mailbox["token"]

    loading = await update.message.reply_text(
        t["inbox_loading"],
        parse_mode="HTML"
    )

    try:

        data = await get_messages(
            token
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
                t["no_mail"],
                reply_markup=main_keyboard(lang),
                parse_mode="HTML"
            )

            return


        await loading.delete()


        # Show latest 10 messages

        for msg in messages[:10]:

            sender = (
                msg.get("from")
                or "Unknown"
            )

            if isinstance(
                sender,
                dict
            ):

                sender = (
                    sender.get("address")
                    or sender.get("name")
                    or "Unknown"
                )


            subject = (
                msg.get("subject")
                or "(No Subject)"
            )

            date = (
                msg.get("createdAt")
                or ""
            )


            body_preview = (
                msg.get("intro")
                or ""
            )


            code = extract_code(
                body_preview
            )


            text = t["new_mail"].format(

                sender=html.escape(
                    str(sender)
                ),

                subject=html.escape(
                    str(subject)
                ),

                date=html.escape(
                    str(date)
                ),

                body=html.escape(
                    str(body_preview)[:500]
                )
            )


            buttons = []


            if code:

                buttons.append([

                    InlineKeyboardButton(
                        t["copy_code"].format(
                            code=code
                        ),
                        callback_data=(
                            f"code_{code}"
                        )
                    )

                ])


            await update.message.reply_text(
                text,
                reply_markup=(
                    InlineKeyboardMarkup(
                        buttons
                    )
                    if buttons
                    else None
                ),
                parse_mode="HTML"
            )


    except Exception as e:

        logger.error(
            "Inbox error: %s",
            e
        )

        await loading.edit_text(
            t["api_error"],
            parse_mode="HTML"
        )


# =========================================================
# COMMAND: INBOX
# =========================================================

async def inbox_command(
    update,
    context
):

    user_id = (
        update.effective_user.id
    )

    lang = (
        get_language(user_id)
        or "en"
    )

    await show_inbox(
        update,
        user_id,
        lang
    )


# =========================================================
# REFRESH
# =========================================================

async def refresh_inbox(
    update,
    user_id,
    lang
):

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


    loading = await update.message.reply_text(
        t["refreshing"],
        parse_mode="HTML"
    )


    try:

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
                t["no_mail"],
                reply_markup=main_keyboard(lang),
                parse_mode="HTML"
            )

            return


        await loading.edit_text(
            f"📨 <b>{len(messages)}</b> "
            f"message(s) found.",
            reply_markup=main_keyboard(lang),
            parse_mode="HTML"
        )


    except Exception as e:

        logger.error(
            "Refresh error: %s",
            e
        )

        await loading.edit_text(
            t["api_error"],
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

    lang = (
        get_language(user_id)
        or "en"
    )

    await update.message.reply_text(
        TEXT[lang]["language_select"],
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

    lang = (
        get_language(user_id)
        or "en"
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

    lang = (
        get_language(user_id)
        or "en"
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

    lang = (
        get_language(user_id)
        or "en"
    )

    mailbox = get_mailbox(
        user_id
    )

    mailbox_text = (
        mailbox["email"]
        if mailbox
        else "None"
    )

    await update.message.reply_text(
        TEXT[lang]["stats"].format(
            user_id=user_id,
            mailbox=html.escape(
                mailbox_text
            )
        ),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):

    return user_id in ADMIN_IDS


# =========================================================
# ADMIN-ONLY COMMAND EXAMPLE
# =========================================================

async def admin_command(
    update,
    context
):

    user_id = (
        update.effective_user.id
    )

    lang = (
        get_language(user_id)
        or "en"
    )

    if not is_admin(user_id):

        await update.message.reply_text(
            TEXT[lang]["admin_only"],
            parse_mode="HTML"
        )

        return

    await update.message.reply_text(
        "🔐 <b>Admin Panel</b>\n\n"
        "Admin command accepted.",
        parse_mode="HTML"
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update,
    context
):

    query = (
        update.callback_query
    )

    await query.answer()

    user_id = (
        query.from_user.id
    )

    data = query.data


    # -----------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------

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
            TEXT[lang]["language_success"],
            parse_mode="HTML"
        )

        # Automatically create email

        await generate_email(
            update,
            user_id,
            lang
        )

        return


    # -----------------------------------------------------
    # GENERATE
    # -----------------------------------------------------

    if data == "generate":

        lang = (
            get_language(user_id)
            or "en"
        )

        await generate_email(
            update,
            user_id,
            lang
        )

        return


    # -----------------------------------------------------
    # INBOX
    # -----------------------------------------------------

    if data == "inbox":

        lang = (
            get_language(user_id)
            or "en"
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


        messages = data_result.get(
            "messages",
            []
        )


        if not messages:

            await query.message.reply_text(
                TEXT[lang]["no_mail"],
                reply_markup=main_keyboard(
                    lang
                ),
                parse_mode="HTML"
            )

            return


        for msg in messages[:10]:

            sender = (
                msg.get("from")
                or "Unknown"
            )

            if isinstance(
                sender,
                dict
            ):

                sender = (
                    sender.get("address")
                    or sender.get("name")
                    or "Unknown"
                )


            subject = (
                msg.get("subject")
                or "(No Subject)"
            )

            intro = (
                msg.get("intro")
                or ""
            )

            date = (
                msg.get("createdAt")
                or ""
            )


            code = extract_code(
                intro
            )


            text = TEXT[lang][
                "new_mail"
            ].format(

                sender=html.escape(
                    str(sender)
                ),

                subject=html.escape(
                    str(subject)
                ),

                date=html.escape(
                    str(date)
                ),

                body=html.escape(
                    str(intro)[:500]
                )
            )


            buttons = []


            if code:

                buttons.append([

                    InlineKeyboardButton(
                        TEXT[lang][
                            "copy_code"
                        ].format(
                            code=code
                        ),
                        callback_data=(
                            f"code_{code}"
                        )
                    )

                ])


            await query.message.reply_text(
                text,
                reply_markup=(
                    InlineKeyboardMarkup(
                        buttons
                    )
                    if buttons
                    else None
                ),
                parse_mode="HTML"
            )

        return


    # -----------------------------------------------------
    # REFRESH
    # -----------------------------------------------------

    if data == "refresh":

        lang = (
            get_language(user_id)
            or "en"
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


        messages = data_result.get(
            "messages",
            []
        )


        await query.message.reply_text(

            f"🔄 <b>Refresh Complete</b>\n\n"
            f"📨 Messages found: "
            f"<b>{len(messages)}</b>",

            reply_markup=main_keyboard(
                lang
            ),

            parse_mode="HTML"
        )

        return


    # -----------------------------------------------------
    # COPY CODE
    # -----------------------------------------------------

    if data.startswith("code_"):

        code = data.replace(
            "code_",
            "",
            1
        )

        lang = (
            get_language(user_id)
            or "en"
        )

        await query.answer(
            TEXT[lang]["code_found"].format(
                code=code
            ),
            show_alert=True
        )

        return


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


    # -------------------------
    # Commands
    # -------------------------

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
            lambda u, c: refresh_inbox(
                u,
                u.effective_user.id,
                get_language(
                    u.effective_user.id
                ) or "en"
            )
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


    # Admin command
    application.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )


    # -------------------------
    # Inline Buttons
    # -------------------------

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
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
