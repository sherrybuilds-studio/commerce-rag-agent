import os
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

_REQUIRED_KEYS = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"]
_missing = [k for k in _REQUIRED_KEYS if not os.getenv(k)]
if _missing:
    raise RuntimeError(
        f"Missing Langfuse env vars: {', '.join(_missing)}. "
        "Set them in .env before starting the bot."
    )

from langfuse import Langfuse

_client = None


def get_langfuse_client():
    global _client
    if _client is None:
        _client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_BASE_URL"),
        )
    return _client


@contextmanager
def trace_conversation(user_id, message):
    """Root trace for one WhatsApp message. Yields the trace for child logging."""
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
