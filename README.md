# commerce-rag-agent

A WhatsApp product assistant I built for a furniture brand. It answers product questions in English and German from a 12-item catalogue.
It retrieves the relevant products (keyword match first, then vector search) and sends only those to the model, rather than the whole catalogue.
That change cut the prompt from 1,118 to 695 tokens per message, 38% smaller, measured on 2026-04-27 ([CHANGELOG.md](./CHANGELOG.md)).

Status: pilot. Author: Shehryar Irfan · [sherrybuilds.com](https://sherrybuilds.com) · [sherry.aiops@gmail.com](mailto:sherry.aiops@gmail.com)

---

## Architecture

```
WhatsApp user
   │
   ▼
Meta Cloud API ──POST /webhook──▶ agents/whatsapp-sales/api.py (FastAPI)
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
   answers repeats          fills the rest (top 3)    + retrieved products only
          └────────────────────────┴─────────────────────────┘
                                   ▼
                        reply via Meta Graph API

Separate: agents/lead-generation/  scraper.py → scorer.py → storage.py (Google Sheets)
          run.py exposes POST /run-leads on 127.0.0.1:5000 for an external scheduler
```

| Path | Role |
|---|---|
| `agents/whatsapp-sales/api.py` | FastAPI webhook: verification handshake, rate limiting, injection filter |
| `agents/whatsapp-sales/server.py` | Older Flask webhook, kept as a baseline |
| `agents/whatsapp-sales/bot.py` | Cache check, retrieval, LLM call, cache write. You can also run it on its own as a terminal chat |
| `rag/indexer.py` | Builds the ChromaDB index from `rag/knowledge_base/products.json` |
| `rag/retriever.py` | Hybrid retrieval: exact keyword hits first, semantic results fill up to 3 |
| `rag/cache.py` | File-backed semantic cache (`rag/cache.json`), 0.95 cosine threshold |
| `shared/database.py` | Supabase client for leads |
| `shared/observability.py` | Tracing hooks (see Limits) |
| `tests/eval.py` | 10 questions (English and German) with keyword checks. Passes at 80% or more |

## What's verified

| Claim | Evidence | Date |
|---|---|---|
| Prompt cut from 1,118 to 695 tokens per message (38%) once retrieval replaced the full catalogue in the prompt | [CHANGELOG.md](./CHANGELOG.md), "Session 3" | 2026-04-27 |
| Semantic cache threshold 0.95 cosine | [`rag/cache.py`](./rag/cache.py) `THRESHOLD` | in code |

`tests/eval.py` calls the live model through OpenRouter, so its score changes from run to run. No dated result file is committed. Treat it as a smoke test, not a benchmark.

## Run it

Needs Python 3.11 and an OpenRouter key.

```bash
git clone https://github.com/sherrybuilds-studio/commerce-rag-agent.git
cd commerce-rag-agent
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn slowapi requests python-dotenv chromadb sentence-transformers numpy supabase langfuse flask beautifulsoup4 gspread
cp .env.example .env            # fill in values; names listed below
python3 rag/indexer.py          # build the ChromaDB index
python3 agents/whatsapp-sales/bot.py            # terminal chat, no WhatsApp needed
cd agents/whatsapp-sales && uvicorn api:app --port 5000   # webhook
python3 tests/eval.py           # from the repo root
```

Environment variables (names only):

| Variable | Needed by |
|---|---|
| `OPENROUTER_API_KEY` | `bot.py` |
| `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID` | webhook replies |
| `WEBHOOK_VERIFY_TOKEN` (FastAPI) / `META_VERIFY_TOKEN` (Flask) | Meta webhook handshake |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | required at import by `shared/observability.py` |
| `SUPABASE_URL`, `SUPABASE_KEY` | lead storage |
| `GOOGLE_SHEET_ID` | lead pipeline output |

`.env.example` also lists `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. The Python code does not read them. They were used by an external n8n workflow.

## Limits

- `requirements.txt` is a full system freeze and will not install cleanly. Use the `pip install` line above until it is replaced.
- `shared/observability.py` stops the bot at startup if the three tracing variables are unset. Tracing is not running in the current deployment. Making it optional is an open fix.
- The scraper URLs in `agents/lead-generation/scraper.py` are placeholders (`listing-platform-*.example.com`), so the public lead pipeline does not fetch anything as shipped.
- The catalogue in `products.json` has 12 items. Retrieval quality on a larger catalogue is untested.
- The cache is a JSON file scanned linearly, with no expiry or size cap in this version.

## License

MIT
