"""Telegram webhook: /start welcome + inline Mini App button, secret-gated."""

import json
from typing import Any

import httpx
import pytest
import respx
from httpx import AsyncClient
from pydantic import SecretStr

from src.config import settings

TOKEN = "123456:TESTTOKEN"
SECRET = "test-webhook-secret"
WEBHOOK = "/telegram/webhook"
SEND_URL = f"/bot{TOKEN}/sendMessage"
TELEGRAM_BASE = "https://api.telegram.org"

# Every test needs the bot token + webhook secret on the settings singleton;
# tests that need a different state (e.g. no secret) re-patch it themselves.
pytestmark = pytest.mark.usefixtures("bot_configured")


@pytest.fixture
def bot_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure bot token + webhook secret on the shared settings singleton."""
    monkeypatch.setattr(settings, "telegram_bot_token", SecretStr(TOKEN))
    monkeypatch.setattr(settings, "telegram_webhook_secret", SecretStr(SECRET))


def _update(
    text: str, language_code: str | None = "ru", chat_id: int = 555
) -> dict[str, Any]:
    """Build a minimal Telegram message update."""
    message: dict[str, Any] = {"chat": {"id": chat_id}, "text": text}
    if language_code is not None:
        message["from"] = {"id": chat_id, "language_code": language_code}
    return {"update_id": 1, "message": message}


async def test_start_replies_with_launch_button(client: AsyncClient) -> None:
    with respx.mock(base_url=TELEGRAM_BASE, assert_all_called=False) as mock:
        route = mock.post(SEND_URL).mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {}})
        )
        resp = await client.post(
            WEBHOOK,
            json=_update("/start", chat_id=555),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert resp.status_code == 200
    assert route.called
    sent = json.loads(route.calls.last.request.content)
    assert sent["chat_id"] == 555
    button = sent["reply_markup"]["inline_keyboard"][0][0]
    assert button["web_app"]["url"] == settings.telegram_webapp_url


async def test_wrong_secret_is_rejected_and_sends_nothing(client: AsyncClient) -> None:
    with respx.mock(base_url=TELEGRAM_BASE, assert_all_called=False) as mock:
        route = mock.post(SEND_URL).mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        resp = await client.post(
            WEBHOOK,
            json=_update("/start"),
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        )

    assert resp.status_code == 403
    assert not route.called


async def test_missing_secret_header_is_rejected(client: AsyncClient) -> None:
    with respx.mock(base_url=TELEGRAM_BASE, assert_all_called=False) as mock:
        route = mock.post(SEND_URL).mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        resp = await client.post(WEBHOOK, json=_update("/start"))

    assert resp.status_code == 403
    assert not route.called


async def test_unconfigured_webhook_fails_closed(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "telegram_webhook_secret", None)
    resp = await client.post(
        WEBHOOK,
        json=_update("/start"),
        headers={"X-Telegram-Bot-Api-Secret-Token": "anything"},
    )
    assert resp.status_code == 503


async def test_non_command_is_ignored(client: AsyncClient) -> None:
    with respx.mock(base_url=TELEGRAM_BASE, assert_all_called=False) as mock:
        route = mock.post(SEND_URL).mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        resp = await client.post(
            WEBHOOK,
            json=_update("привет, как дела"),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert resp.status_code == 200
    assert not route.called


async def test_start_with_bot_mention_triggers(client: AsyncClient) -> None:
    with respx.mock(base_url=TELEGRAM_BASE, assert_all_called=False) as mock:
        route = mock.post(SEND_URL).mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {}})
        )
        resp = await client.post(
            WEBHOOK,
            json=_update("/start@Oltin_Paybot"),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert resp.status_code == 200
    assert route.called


@pytest.mark.parametrize(
    ("language_code", "expected_button"),
    [
        ("ru", "🥇 Открыть приложение"),
        ("uz", "🥇 Ilovani ochish"),
        ("en-US", "🥇 Open the app"),
        ("fr", "🥇 Open the app"),
        (None, "🥇 Open the app"),
    ],
)
async def test_button_label_follows_language(
    client: AsyncClient,
    language_code: str | None,
    expected_button: str,
) -> None:
    with respx.mock(base_url=TELEGRAM_BASE, assert_all_called=False) as mock:
        route = mock.post(SEND_URL).mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {}})
        )
        resp = await client.post(
            WEBHOOK,
            json=_update("/start", language_code=language_code),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert resp.status_code == 200
    sent = json.loads(route.calls.last.request.content)
    assert sent["reply_markup"]["inline_keyboard"][0][0]["text"] == expected_button
