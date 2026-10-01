# commerce-rag-agent

[![CI](https://github.com/sherrybuilds-studio/commerce-rag-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/sherrybuilds-studio/commerce-rag-agent/actions/workflows/ci.yml)

A WhatsApp product assistant I built for a furniture brand. It answers product questions in English and German from a 12-item catalogue.
It retrieves the relevant products (keyword match first, then vector search) and sends only those to the model, rather than the whole catalogue.
That change cut the prompt from 1,118 to 695 tokens per message, 38% smaller, measured on 2026-04-27 ([CHANGELOG.md](./CHANGELOG.md)).

Status: pilot. Author: Shehryar Irfan · [sherrybuilds.com](https://sherrybuilds.com) · [sherry.aiops@gmail.com](mailto:sherry.aiops@gmail.com)

---

## Architecture

```text
WhatsApp user
   │
   ▼
Meta Cloud API ──POST /webhook──▶ agents/whatsapp-sales/api.py (FastAPI)
                                   · Meta signature check (X-Hub-Signature-256)
                                   · slowapi rate limit (10/min per IP)
                                   · prompt-injection filter (sanitize_input)
                                   ▼
                          agents/whatsapp-sales/bot.py  get_ai_response()
                                   │
          ┌────────────────────────┼─────────────────────────┐
          ▼                        ▼                         ▼
   rag/cache.py             rag/retriever.py          OpenRouter
   semantic cache,          keyword match first,      anthropic/claude-3.5-haiku
   cosine >= 0.95,          ChromaDB + MiniLM         + system_prompt.md
   7-day expiry,            fills the rest (top 3)    + retrieved products only
   500 entries (LRU)
          └────────────────────────┴─────────────────────────┘
                                   ▼
                        reply via Meta Graph API

Separate: agents/lead-generation/  scraper.py → scorer.py → storage.py (Google Sheets)
          run.py exposes POST /run-leads on 127.0.0.1:5000 for an external scheduler
```

| Path | Role |
| --- | --- |
| `agents/whatsapp-sales/api.py` | FastAPI webhook: verification handshake, Meta signature check, rate limiting, injection filter |
| `agents/whatsapp-sales/meta_signature.py` | Checks `X-Hub-Signature-256`: HMAC-SHA256 of the raw body with `META_APP_SECRET`, compared in constant time |
| `agents/whatsapp-sales/server.py` | Older Flask webhook, kept as a baseline. Same signature check, no rate limit, no injection filter |
| `agents/whatsapp-sales/bot.py` | Cache check, retrieval, LLM call, cache write. You can also run it on its own as a terminal chat |
| `rag/indexer.py` | Builds the ChromaDB index from `rag/knowledge_base/products.json` |
| `rag/retriever.py` | Hybrid retrieval: keyword hits first (a SKU code or product name in the message, or the whole message as a phrase), semantic results fill up to 3 |
| `rag/embeddings.py` | The MiniLM model shared by retrieval and the cache, loaded on first use |
| `rag/cache.py` | File-backed semantic cache (`rag/cache.json`): 0.95 cosine threshold, 7-day expiry, at most 500 entries with least-recently-used eviction |
| `shared/database.py` | Supabase helpers (`save_lead`, `get_leads`). The lead pipeline does not call them |
| `shared/observability.py` | Langfuse tracing. A no-op unless all three `LANGFUSE_*` variables are set |
| `tests/` | Offline pytest suite, see [Tests](#tests) |
| `tests/eval.py` | 10 questions (English and German) with keyword checks against the live model. Passes at 80% or more |

## What's verified

| Claim | Evidence | Date |
| --- | --- | --- |
| Prompt cut from 1,118 to 695 tokens per message (38%) once retrieval replaced the full catalogue in the prompt | [CHANGELOG.md](./CHANGELOG.md), "Session 3" | 2026-04-27 |
| Semantic cache: 0.95 cosine threshold, 7-day expiry, 500-entry cap | [`rag/cache.py`](./rag/cache.py) `THRESHOLD`, `TTL_SECONDS`, `MAX_ENTRIES` | in code |

`tests/eval.py` calls the live model through OpenRouter, so its score changes from run to run. No dated result file is committed. Treat it as a smoke test, not a benchmark.

## Run it

Needs Python 3.11 or newer (CI uses 3.12) and an OpenRouter key.

```bash
git clone https://github.com/sherrybuilds-studio/commerce-rag-agent.git
cd commerce-rag-agent
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # optional: CPU build, skips the CUDA download
pip install -r requirements.txt
cp .env.example .env            # fill in values; names listed below
python3 rag/indexer.py          # build the ChromaDB index
python3 agents/whatsapp-sales/bot.py                       # terminal chat, no WhatsApp needed
cd agents/whatsapp-sales && uvicorn api:app --port 5000    # webhook
```

Environment variables (names only):

| Variable | Needed by |
| --- | --- |
| `OPENROUTER_API_KEY` | `bot.py` |
| `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID` | webhook replies |
| `META_APP_SECRET` | signature check on `POST /webhook`. Without it the webhook answers 503 and logs why |
| `WEBHOOK_VERIFY_TOKEN` (`api.py`), `META_VERIFY_TOKEN` (`server.py`) | Meta webhook handshake |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | optional tracing, on only when all three are set |
| `SUPABASE_URL`, `SUPABASE_KEY` | `shared/database.py` |
| `GOOGLE_SHEET_ID` | lead pipeline output |

`.env.example` also lists `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. The Python code does not read them. They were used by an external n8n workflow.

## Tests

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

The pytest suite runs offline and needs no `.env`, no model download and no ChromaDB index. Fakes stand in for the embedding model, vector search, OpenRouter and the WhatsApp send call. It covers:

- retrieval: keyword hits (a SKU code or product name inside a message) rank before semantic results, and survive a vector-search failure
- the semantic cache: a hit at or above the 0.95 threshold, a miss below it, expiry after 7 days, least-recently-used eviction at the cap
- the lead scorer: tiers, the minimum score filter, and the minimum freshness score for an unreadable timestamp
- the webhooks: the verification handshake, the signature check (valid, wrong, missing, no secret configured), the injection filter, the rate limit, and logs without full phone numbers
- the bot's reply path with tracing off, and the documented run commands starting without `PYTHONPATH`

`tests/eval.py` is not part of the suite. It needs a key and a built index, and pytest does not collect it. Run it by hand with `python3 tests/eval.py`.

CI ([`.github/workflows/ci.yml`](./.github/workflows/ci.yml)) runs `ruff check .` and `pytest -q` on Python 3.12 for every push and pull request. It installs CPU-only torch first, then `requirements-dev.txt`.

## Limits

- The scraper URLs in `agents/lead-generation/scraper.py` are placeholders (`listing-platform-*.example.com`), so the public lead pipeline does not fetch anything as shipped.
- The catalogue in `products.json` has 12 items. Retrieval quality on a larger catalogue is untested.
- The rate limit counts requests per connecting IP address. Behind a proxy or tunnel, every request arrives from the same address, so the limit then applies to all senders together.
- Conversation history and rate-limit counters live in process memory. They reset on restart and are not shared between worker processes.
- `server.py` checks Meta's signature but has no rate limit and no injection filter. Expose `api.py`, not `server.py`.

## License

MIT
