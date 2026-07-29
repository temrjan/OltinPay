"""Telegram notification service."""

import httpx

from src.config import settings

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_notification(
    telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
) -> bool:
    """Send notification via Telegram bot.

    Returns True if sent successfully.
    """
    if not settings.telegram_bot_token:
        return False

    token = settings.telegram_bot_token.get_secret_value()
    url = TELEGRAM_API_URL.format(token=token)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": telegram_id,
                    "text": message,
                    "parse_mode": parse_mode,
                },
                timeout=10.0,
            )
            return response.status_code == 200
    except Exception:
        return False


async def notify_transfer_received(
    recipient_telegram_id: int,
    sender_oltin_id: str,
    amount: str,
    language: str = "en",
) -> bool:
    """Notify user about received transfer."""
    messages = {
        "uz": f"💰 <b>Sizga OLTIN keldi!</b>\n\n@{sender_oltin_id} sizga <b>{amount} OLTIN</b> yubordi.",
        "ru": f"💰 <b>Вам пришёл OLTIN!</b>\n\n@{sender_oltin_id} отправил вам <b>{amount} OLTIN</b>.",
        "en": f"💰 <b>You received OLTIN!</b>\n\n@{sender_oltin_id} sent you <b>{amount} OLTIN</b>.",
    }

    message = messages.get(language, messages["en"])
    return await send_telegram_notification(recipient_telegram_id, message)


async def notify_staking_reward(
    telegram_id: int,
    amount: str,
    language: str = "en",
) -> bool:
    """Notify user about staking reward."""
    messages = {
        "uz": f"🎁 <b>Steyking mukofoti!</b>\n\nSizga <b>+{amount} OLTIN</b> hisoblandi.",
        "ru": f"🎁 <b>Награда за стейкинг!</b>\n\nВам начислено <b>+{amount} OLTIN</b>.",
        "en": f"🎁 <b>Staking reward!</b>\n\nYou earned <b>+{amount} OLTIN</b>.",
    }

    message = messages.get(language, messages["en"])
    return await send_telegram_notification(telegram_id, message)
