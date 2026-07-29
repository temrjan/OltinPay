"""Telegram bot webhook — replies to /start etc. with a Mini App launch button."""

import hmac

from fastapi import APIRouter, Header, HTTPException, Request, status

from src.config import settings
from src.notifications import send_telegram_notification
from src.telegram.messages import welcome
from src.telegram.schemas import TgUpdate

router = APIRouter()

# Advertised bot commands. All reply with the welcome + Mini App entry: the app
# owns language selection, so /lang shows the same welcome rather than a dead
# command, and /help needs nothing beyond the launch button.
_WELCOME_COMMANDS = frozenset({"/start", "/help", "/lang"})


def _command(text: str) -> str:
    """Leading bot command in ``text``, else "".

    ``"/start@Oltin_Paybot arg"`` -> ``"/start"``; non-commands -> ``""``.
    """
    stripped = text.strip()
    if not stripped:
        return ""
    first = stripped.split(maxsplit=1)[0]
    if not first.startswith("/"):
        return ""
    return first.split("@", 1)[0].lower()


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    """Handle a Telegram update.

    The secret-token header is checked first (constant-time); the webhook fails
    closed when the secret is unset and returns 403 on any mismatch, so only
    Telegram (which echoes the secret set via setWebhook) is ever served.
    """
    secret = settings.telegram_webhook_secret
    if secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="webhook not configured",
        )
    if not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "", secret.get_secret_value()
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    # Only authenticated requests reach here. A malformed body is ignored (200)
    # rather than retried — Telegram always sends well-formed JSON.
    try:
        update = TgUpdate.model_validate(await request.json())
    except Exception:
        return {"ok": True}

    message = update.message
    if (
        message is not None
        and message.text is not None
        and _command(message.text) in _WELCOME_COMMANDS
    ):
        language = message.from_user.language_code if message.from_user else None
        text, markup = welcome(language)
        await send_telegram_notification(message.chat.id, text, reply_markup=markup)

    return {"ok": True}
