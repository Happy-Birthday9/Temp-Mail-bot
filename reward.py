# ============================================================
# reward.py
# TEMP MAIL BOT - REWARD SYSTEM
# ============================================================

from decimal import Decimal

from database import (
    add_email_reward_once,
    add_referral_once,
    get_balance,
    get_referrer,
)

# ============================================================
# REWARD AMOUNTS
# ============================================================

EMAIL_CODE_REWARD = Decimal("0.00130")
REFERRAL_REWARD = Decimal("0.00158")

# Backward-compatible name
EMAIL_REWARD = EMAIL_CODE_REWARD


# ============================================================
# FORMAT REWARD
# ============================================================

def format_reward(amount):
    """
    Reward amount সুন্দরভাবে format করবে।
    Example:
        0.00130 -> $0.00130
        0.00158 -> $0.00158
    """

    try:
        value = Decimal(str(amount))
        return f"${value:.5f}"
    except Exception:
        return "$0.00000"


# ============================================================
# EMAIL / CODE REWARD
# ============================================================

def reward_email_code(user_id, reward_key):
    """
    একটি unique email/code-এর জন্য user-কে reward দেবে।

    একই user + একই reward_key আবার এলে
    দ্বিতীয়বার balance add হবে না।
    """

    user_id = int(user_id)

    if not reward_key:
        return {
            "success": False,
            "added": False,
            "amount": 0.0,
            "balance": get_balance(user_id),
        }

    reward_key = str(reward_key).strip()

    if not reward_key:
        return {
            "success": False,
            "added": False,
            "amount": 0.0,
            "balance": get_balance(user_id),
        }

    try:
        added, balance = add_email_reward_once(
            user_id=user_id,
            reward_key=reward_key,
            amount=float(EMAIL_CODE_REWARD),
        )

        return {
            "success": True,
            "added": added,
            "amount": (
                float(EMAIL_CODE_REWARD)
                if added else 0.0
            ),
            "balance": balance,
        }

    except Exception:
        return {
            "success": False,
            "added": False,
            "amount": 0.0,
            "balance": get_balance(user_id),
        }


# ============================================================
# REFERRAL REWARD
# ============================================================

def reward_referral(referrer_id, referred_id):
    """
    নতুন referred user-এর জন্য referrer-কে
    $0.00158 reward দেবে।

    একই referred user-এর জন্য
    দ্বিতীয়বার reward দেওয়া যাবে না।
    """

    referrer_id = int(referrer_id)
    referred_id = int(referred_id)

    if referrer_id == referred_id:
        return {
            "success": False,
            "added": False,
            "amount": 0.0,
            "balance": get_balance(referrer_id),
        }

    try:
        added, balance = add_referral_once(
            referrer_id=referrer_id,
            referred_id=referred_id,
            amount=float(REFERRAL_REWARD),
        )

        return {
            "success": True,
            "added": added,
            "amount": (
                float(REFERRAL_REWARD)
                if added else 0.0
            ),
            "balance": balance,
        }

    except Exception:
        return {
            "success": False,
            "added": False,
            "amount": 0.0,
            "balance": get_balance(referrer_id),
        }


# ============================================================
# AUTO REFERRAL REWARD
# ============================================================

def process_referral(user_id):
    """
    User-এর database-এ referrer থাকলে
    referrer-কে একবার referral reward দেওয়ার চেষ্টা করবে।
    """

    user_id = int(user_id)

    referrer_id = get_referrer(user_id)

    if not referrer_id:
        return None

    return reward_referral(
        referrer_id=referrer_id,
        referred_id=user_id,
    )


# ============================================================
# BALANCE INFO
# ============================================================

def get_user_balance(user_id):
    """
    User-এর current balance return করবে।
    """

    return get_balance(int(user_id))


# ============================================================
# FORMAT BALANCE
# ============================================================

def format_balance(user_id):
    """
    Telegram message-এর জন্য balance সুন্দরভাবে format করবে।
    """

    balance = Decimal(
        str(get_balance(int(user_id)))
    )

    return f"${balance:.5f}"


# ============================================================
# EMAIL REWARD MESSAGE
# ============================================================

def email_reward_message(user_id, reward_key):
    """
    Email/code receive করার পর Telegram-এ
    reward message তৈরি করবে।
    """

    result = reward_email_code(
        user_id=user_id,
        reward_key=reward_key,
    )

    if result["added"]:
        return (
            f"💰 <b>You earned:</b> "
            f"{format_reward(result['amount'])}"
        )

    return (
        "ℹ️ <b>Reward already received for this code.</b>"
    )


# ============================================================
# REFERRAL REWARD MESSAGE
# ============================================================

def referral_reward_message(
    referrer_id,
    referred_id,
):
    """
    Referral successful হলে message return করবে।
    """

    result = reward_referral(
        referrer_id=referrer_id,
        referred_id=referred_id,
    )

    if result["added"]:
        return (
            "🎉 <b>Referral Successful!</b>\n\n"
            f"💰 You earned: "
            f"{format_reward(result['amount'])}\n"
            f"💳 Balance: "
            f"${Decimal(str(result['balance'])):.5f}"
        )

    return None


# ============================================================
# CONSTANTS
# ============================================================

EMAIL_REWARD_AMOUNT = float(EMAIL_CODE_REWARD)
REFERRAL_REWARD_AMOUNT = float(REFERRAL_REWARD)
