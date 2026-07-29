"""Welcome copy and the inline Mini App launch button (uz / ru / en)."""

from typing import Any

from src.config import settings

# Supported bot languages. Anything else falls back to English.
_SUPPORTED = ("uz", "ru", "en")
_DEFAULT = "en"

_WELCOME = {
    "uz": (
        "👋 <b>OltinPay'ga xush kelibsiz!</b>\n\n"
        "OLTIN — oltinga bog'langan aktiv uchun nokustodial hamyon: so'm bilan "
        "ayirboshlash, steyking bilan jamg'arish va o'tkazmalar. Kalit faqat "
        "sizning qurilmangizda saqlanadi.\n\n"
        "Ilovani ochish uchun quyidagi tugmani bosing."
    ),
    "ru": (
        "👋 <b>Добро пожаловать в OltinPay!</b>\n\n"
        "Некастодиальный кошелёк золото-индексированного актива OLTIN: обмен с "
        "сумом, накопление со стейкингом и переводы. Ключ хранится только на "
        "вашем устройстве.\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение."
    ),
    "en": (
        "👋 <b>Welcome to OltinPay!</b>\n\n"
        "A non-custodial wallet for OLTIN, a gold-indexed asset: swap with the "
        "som, save with staking, and send transfers. Your key stays on your "
        "device only.\n\n"
        "Tap the button below to open the app."
    ),
}

_BUTTON = {
    "uz": "🥇 Ilovani ochish",
    "ru": "🥇 Открыть приложение",
    "en": "🥇 Open the app",
}


def resolve_language(language_code: str | None) -> str:
    """Map a Telegram ``language_code`` (e.g. ``ru``, ``en-US``) to uz/ru/en."""
    if not language_code:
        return _DEFAULT
    prefix = language_code.split("-", 1)[0].lower()
    return prefix if prefix in _SUPPORTED else _DEFAULT


def welcome(language_code: str | None) -> tuple[str, dict[str, Any]]:
    """Return (HTML text, inline_keyboard markup) for the /start welcome.

    The button is a web_app button whose URL is the configured Mini App —
    a constant, never user input.
    """
    lang = resolve_language(language_code)
    markup: dict[str, Any] = {
        "inline_keyboard": [
            [{"text": _BUTTON[lang], "web_app": {"url": settings.telegram_webapp_url}}]
        ]
    }
    return _WELCOME[lang], markup
