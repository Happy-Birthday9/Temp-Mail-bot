# ============================================================
# reward.py
# TEMP MAIL TELEGRAM BOT - REWARD SYSTEM
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

EMAIL_REWARD = Decimal("0.00130")
REFERRAL_REWARD = Decimal("0.00158")

# Names used directly by bot.py
EMAIL_CODE_REWARD = EMAIL_REWARD
EMAIL_REWARD_AMOUNT = float(EMAIL_REWARD)
REFERRAL_REWARD_AMOUNT = float(REFERRAL_REWARD)


# ============================================================
# FORMAT
# ============================================================

def format_reward(amount):
    """
    Format reward amount for Telegram messages.

    Example:
        0.00130 -> $0.00130
    """
    try:
        return f"${Decimal(str(amount)):.5f}"
    except Exception:
        return "$0.00000"


def format_balance(user_id):
    balance = Decimal(str(get_balance(int(user_id))))
    return f"${balance:.5f}"


# ============================================================
# EMAIL / CODE REWARD
# ============================================================

def reward_email_code(user_id, reward_key):
    """
    Give reward only once for the same user + reward_key.
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

    added, balance = add_email_reward_once(
        user_id=user_id,
        reward_key=reward_key,
        amount=EMAIL_REWARD,
    )

    return {
        "success": True,
        "added": added,
        "amount": float(EMAIL_REWARD) if added else 0.0,
        "balance": balance,
    }


# ============================================================
# REFERRAL REWARD
# ============================================================

def reward_referral(referrer_id, referred_id):
    """
    Give referral reward only once for a referred user.
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

    added, balance = add_referral_once(
        referrer_id=referrer_id,
        referred_id=referred_id,
        amount=REFERRAL_REWARD,
    )

    return {
        "success": True,
        "added": added,
        "amount": float(REFERRAL_REWARD) if added else 0.0,
        "balance": balance,
    }


# ============================================================
# AUTO REFERRAL REWARD
# ============================================================

def process_referral(user_id):
    """
    If the user has a referrer, give the referrer
    the referral reward once.
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
# BALANCE
# ============================================================

def get_user_balance(user_id):
    return get_balance(int(user_id))


# ============================================================
# EMAIL REWARD MESSAGE
# ============================================================

def email_reward_message(user_id, reward_key):
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

def referral_reward_message(referrer_id, referred_id):
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
            f"{format_reward(result['balance'])}"
        )

    return None
