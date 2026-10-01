"""
get_ai_response with the cache, retrieval and the OpenRouter call replaced by fakes, so nothing leaves the machine.
The Langfuse variables are unset (tests/conftest.py clears them), so these also show the bot runs without tracing.
"""

from types import SimpleNamespace

import pytest
import requests

PRODUCT = {
    "id": "LUX-104",
    "name": "Chesterfield Leather Sofa Set",
    "description": "5-seater Chesterfield sofa set in full-grain leather.",
    "pricing_tier": "Ultra-Luxury",
    "source": "keyword",
}
LLM_REPLY = "The Chesterfield set comes with a solid oak or walnut frame. Which leather colour do you prefer?"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


@pytest.fixture
def bot(load_module, monkeypatch):
    """bot.py with fakes in place. calls.llm holds each OpenRouter request body, calls.cached each cache write."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    module = load_module("whatsapp_bot", "agents/whatsapp-sales/bot.py")
    calls = SimpleNamespace(llm=[], cached=[])

    def fake_post(url, headers, json, timeout):
        calls.llm.append(json)
        return FakeResponse({"choices": [{"message": {"content": LLM_REPLY}}], "usage": {"total_tokens": 42}})

    monkeypatch.setattr(module, "get_cached_answer", lambda question: (None, None))
    monkeypatch.setattr(module, "cache_answer", lambda question, answer: calls.cached.append((question, answer)))
    monkeypatch.setattr(module, "retrieve", lambda question: [PRODUCT])
    monkeypatch.setattr(requests, "post", fake_post)
    return SimpleNamespace(module=module, calls=calls)


def test_answers_with_retrieved_products_and_caches_the_reply(bot):
    history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Welcome."}]

    reply = bot.module.get_ai_response("Tell me about LUX-104", history)

    assert reply == LLM_REPLY
    request = bot.calls.llm[0]
    assert request["model"] == "anthropic/claude-3.5-haiku"
    system_prompt = request["messages"][0]["content"]
    assert "- [LUX-104] Chesterfield Leather Sofa Set:" in system_prompt
    assert request["messages"][1:] == [*history, {"role": "user", "content": "Tell me about LUX-104"}]
    assert bot.calls.cached == [("Tell me about LUX-104", LLM_REPLY)]


def test_cache_hit_skips_retrieval_and_the_llm(bot, monkeypatch):
    def no_retrieval(question):
        raise AssertionError("retrieval should not run on a cache hit")

    monkeypatch.setattr(bot.module, "get_cached_answer", lambda question: ("Cached answer", 0.97))
    monkeypatch.setattr(bot.module, "retrieve", no_retrieval)

    assert bot.module.get_ai_response("Tell me about LUX-104") == "Cached answer"
    assert bot.calls.llm == []


def test_cache_errors_do_not_block_the_reply(bot, monkeypatch):
    def broken_cache(*args):
        raise OSError("No space left on device")

    monkeypatch.setattr(bot.module, "get_cached_answer", broken_cache)
    monkeypatch.setattr(bot.module, "cache_answer", broken_cache)

    assert bot.module.get_ai_response("Tell me about LUX-104") == LLM_REPLY


def test_llm_failure_returns_the_fallback_and_caches_nothing(bot, monkeypatch):
    def unreachable(*args, **kwargs):
        raise requests.ConnectionError("OpenRouter unreachable")

    monkeypatch.setattr(requests, "post", unreachable)

    reply = bot.module.get_ai_response("Tell me about LUX-104")

    assert reply.startswith("I'm sorry, I'm unable to respond right now.")
    assert bot.calls.cached == []

