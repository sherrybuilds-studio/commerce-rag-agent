import logging
import sys
import types

import pytest

from shared import observability

LANGFUSE_ENV = {
    "LANGFUSE_PUBLIC_KEY": "pk-test",
    "LANGFUSE_SECRET_KEY": "sk-test",
    "LANGFUSE_BASE_URL": "https://langfuse.invalid",
}


@pytest.fixture
def langfuse_calls(monkeypatch):
    """Replace the langfuse package with a fake that records calls instead of sending them."""
    calls = []

    class FakeObservation:
        def __init__(self, kind, kwargs):
            calls.append((kind, kwargs))

        def span(self, **kwargs):
            return FakeObservation("span", kwargs)

        def generation(self, **kwargs):
            return FakeObservation("generation", kwargs)

        def update(self, **kwargs):
            calls.append(("update", kwargs))

        def end(self, **kwargs):
            calls.append(("end", kwargs))

    class FakeLangfuse:
        def __init__(self, **kwargs):
            calls.append(("client", kwargs))

        def trace(self, **kwargs):
            return FakeObservation("trace", kwargs)

        def flush(self):
            calls.append(("flush", {}))

    fake_module = types.ModuleType("langfuse")
    fake_module.Langfuse = FakeLangfuse
    monkeypatch.setitem(sys.modules, "langfuse", fake_module)
    monkeypatch.setattr(observability, "_client", None)
    monkeypatch.setattr(observability, "_warned_partial_config", False)
    return calls


def run_one_traced_message():
    with observability.trace_conversation("user-1", "Tell me about LUX-104") as trace:
        observability.log_cache_hit(trace, "q", "cached answer", 0.97)
        observability.log_retrieval(trace, "q", [{"id": "LUX-104", "name": "Sofa", "source": "keyword"}])
        observability.log_llm_call(
            trace, "anthropic/claude-3.5-haiku", [], "reply",
            {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
        )
        trace.update(output="reply")


def test_tracing_is_a_no_op_without_langfuse_env(langfuse_calls):
    assert not observability.tracing_enabled()
    run_one_traced_message()
    assert langfuse_calls == []  # no client was created, nothing was sent


def test_partial_langfuse_env_keeps_tracing_off_and_names_the_gap(monkeypatch, langfuse_calls, caplog):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    with caplog.at_level(logging.WARNING, logger="shared.observability"):
        run_one_traced_message()

    assert langfuse_calls == []
    assert "LANGFUSE_BASE_URL" in caplog.text


def test_tracing_reaches_langfuse_when_configured(monkeypatch, langfuse_calls):
    for name, value in LANGFUSE_ENV.items():
        monkeypatch.setenv(name, value)

    run_one_traced_message()

    kinds = [kind for kind, _ in langfuse_calls]
    assert kinds[0] == "client"
    assert langfuse_calls[0][1] == {
        "public_key": "pk-test",
        "secret_key": "sk-test",
        "host": "https://langfuse.invalid",
    }
    assert ("trace", {"name": "whatsapp_conversation", "user_id": "user-1", "input": "Tell me about LUX-104"}) in (
        langfuse_calls
    )
    span_names = [kwargs["name"] for kind, kwargs in langfuse_calls if kind == "span"]
    assert span_names == ["cache_hit", "rag_retrieval"]
    generation = next(kwargs for kind, kwargs in langfuse_calls if kind == "generation")
    assert generation["usage"] == {"input": 12, "output": 5, "total": 17}
    assert kinds[-1] == "flush"
