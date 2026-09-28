"""
shared/observability.py: optional Langfuse tracing.

Tracing is on only when LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_BASE_URL are all set.
Otherwise every function here is a no-op, so the bot starts and answers without a Langfuse account.
"""

import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

LANGFUSE_ENV_VARS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")

_client = None
_warned_partial_config = False


class _NoOpObservation:
    """Stands in for a Langfuse trace, span or generation while tracing is off."""

    def span(self, **kwargs):
        return self

    def generation(self, **kwargs):
        return self

    def update(self, **kwargs):
        return self

    def end(self, **kwargs):
        return self


_NOOP = _NoOpObservation()


def tracing_enabled() -> bool:
    """True when all three Langfuse variables are set. Warns once when only some of them are."""
    global _warned_partial_config
    missing = [name for name in LANGFUSE_ENV_VARS if not os.getenv(name)]
    if not missing:
        return True
    if len(missing) < len(LANGFUSE_ENV_VARS) and not _warned_partial_config:
        logger.warning("Langfuse tracing is off. Missing: %s", ", ".join(missing))
        _warned_partial_config = True
    return False


def get_langfuse_client():
    global _client
    if _client is None:
        from langfuse import Langfuse  # imported only when tracing is on

        _client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_BASE_URL"),
        )
    return _client


@contextmanager
def trace_conversation(user_id, message):
    """Root trace for one WhatsApp message. Yields the trace, or a no-op stand-in when tracing is off."""
    if not tracing_enabled():
        yield _NOOP
        return

    client = get_langfuse_client()
    trace = client.trace(
        name="whatsapp_conversation",
        user_id=str(user_id),
        input=message,
    )
    try:
        yield trace
    finally:
        client.flush()


def log_cache_hit(trace, query, response, similarity):
    span = trace.span(
        name="cache_hit",
        input={"query": query, "similarity": round(float(similarity), 4)},
        output={"response": response},
    )
    span.end()


def log_retrieval(trace, query, docs, scores=None):
    span = trace.span(
        name="rag_retrieval",
        input={"query": query},
        output={
            "docs": [
                {"id": d.get("id"), "name": d.get("name"), "source": d.get("source")}
                for d in docs
            ],
            "count": len(docs),
        },
    )
    span.end()


def log_llm_call(trace, model, prompt, response, tokens=None):
    usage = None
    if tokens:
        usage = {
            "input": tokens.get("prompt_tokens", 0),
            "output": tokens.get("completion_tokens", 0),
            "total": tokens.get("total_tokens", 0),
        }
    gen = trace.generation(
        name="llm_call",
        model=model,
        input=prompt,
        output=response,
        usage=usage,
    )
    gen.end()
