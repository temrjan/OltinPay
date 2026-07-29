"""Bot keyboard/copy must not surface the AI assistant (hidden in the demo scope)."""

import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("WEBAPP_URL", "https://app.oltinpay.com")

import bot  # noqa: E402

_ASSISTANT_WORDS = ("assistant", "ассистент", "yordamchi", "aylin", "помощник")


def _buttons(markup):
    return [b for row in markup.inline_keyboard for b in row]


def test_webapp_keyboard_has_no_assistant_button():
    bot.user_languages[1] = "ru"
    buttons = _buttons(bot.webapp_keyboard(1))
    texts = [b.text.lower() for b in buttons]
    urls = [b.web_app.url.lower() for b in buttons if b.web_app]

    assert not any(w in t for t in texts for w in _ASSISTANT_WORDS), texts
    assert not any("aylin" in u for u in urls), urls
    # The wallet launch button is still present.
    assert any("app.oltinpay.com" in u for u in urls), urls


def test_welcome_copy_has_no_ai_line():
    for lang in ("uz", "ru", "en"):
        welcome = bot.MESSAGES[lang]["welcome"].lower()
        assert not any(w in welcome for w in _ASSISTANT_WORDS), lang


# OLTIN is a gold-INDEXED obligation, not tokenized/gold-backed gold; the copy
# must never imply the token is gold (see positioning rule).
_GOLD_BACKING_WORDS = ("tokenized", "токенизированн", "tokenizatsiya", "обеспечен")


def test_welcome_copy_avoids_gold_backing_claim():
    for lang in ("uz", "ru", "en"):
        welcome = bot.MESSAGES[lang]["welcome"].lower()
        assert not any(w in welcome for w in _GOLD_BACKING_WORDS), lang
