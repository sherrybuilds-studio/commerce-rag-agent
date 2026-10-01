"""
FastAPI webhook (agents/whatsapp-sales/api.py) with the bot and the outbound WhatsApp call replaced by fakes.
Each test loads a fresh copy of the module, so settings and rate-limit counters start clean.
"""

import sys
import types
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

VERIFY_TOKEN = "verify-token-for-tests"


@pytest.fixture
def webhook(load_module, monkeypatch):
    """Load api.py with the given environment. None unsets a variable."""

    def load(**env):
        for name, value in {"WEBHOOK_VERIFY_TOKEN": VERIFY_TOKEN, **env}.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)

        asked = []

        def fake_get_ai_response(message, history=None, user_id="anonymous"):
            asked.append(message)
            return f"reply to: {message}"

        fake_bot = types.ModuleType("bot")
        fake_bot.get_ai_response = fake_get_ai_response
        monkeypatch.setitem(sys.modules, "bot", fake_bot)

        module = load_module("whatsapp_api", "agents/whatsapp-sales/api.py")
        sent = []
        monkeypatch.setattr(module, "send_message", lambda to, text: sent.append((to, text)))
        return SimpleNamespace(module=module, client=TestClient(module.app), asked=asked, sent=sent)

    return load


def handshake(client, token, challenge="1158201444"):
    params = {"hub.mode": "subscribe", "hub.verify_token": token, "hub.challenge": challenge}
    return client.get("/webhook", params=params)


def test_handshake_returns_the_challenge_as_plain_text(webhook):
    api = webhook()

    response = handshake(api.client, VERIFY_TOKEN)

    assert response.status_code == 200
    assert response.text == "1158201444"  # Meta compares the body with the challenge it sent


def test_handshake_rejects_a_wrong_token(webhook):
    api = webhook()

    assert handshake(api.client, "wrong-token").status_code == 403


def test_handshake_fails_closed_when_no_token_is_configured(webhook):
    api = webhook(WEBHOOK_VERIFY_TOKEN="")

    assert handshake(api.client, "").status_code == 403
