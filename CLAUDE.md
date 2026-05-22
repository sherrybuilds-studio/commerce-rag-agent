NEVER run rm, chmod 777, git push, DROP, DELETE without showing the command and waiting for explicit confirmation first.

# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

WhatsApp AI sales agent for a luxury interior design brand. The bot handles
English and German customer conversations, retrieves products via hybrid RAG
(ChromaDB + keyword search), and runs an automated lead generation pipeline.

## Current Status

- WhatsApp bot with RAG + semantic cache: WORKING in terminal
- Lead pipeline + Google Sheets integration: WORKING
- n8n automation (every 6 hours): CONFIGURED
- Meta WhatsApp Cloud API webhook: code ready, connect via Meta dashboard
- Real product data: configured in `rag/knowledge_base/products.json`

## Running the Project

**Test the bot in terminal (no webhook needed):**
```bash
python3 agents/whatsapp-sales/bot.py
```

**Start the webhook server (Flask, stable):**
```bash
python3 agents/whatsapp-sales/server.py
```

**Start the webhook server (FastAPI, production — auto-docs at /docs):**
```bash
cd agents/whatsapp-sales && uvicorn api:app --reload --port 5000
```

**Rebuild ChromaDB index (run after editing products.json):**
```bash
python3 rag/indexer.py
```

**Run the evaluation suite:**
```bash
python3 tests/eval.py
# Must score >= 80% before deploying
```

**Run lead generation once:**
```bash
python3 agents/lead-generation/run.py
```

**Start lead gen API server (for n8n to trigger):**
```bash
python3 agents/lead-generation/run.py serve
```

## Architecture

### Request flow (WhatsApp bot)

```
Customer WhatsApp → Meta Cloud API → /webhook (server.py or api.py)
  → bot.py: get_ai_response()
    1. Check semantic cache (rag/cache.py, 95% similarity threshold)
    2. If miss: hybrid search via rag/retriever.py
       - keyword_search() — exact matches (SKUs, material names)
       - semantic_search() — ChromaDB vector similarity
       - Keyword results rank first; semantic fills remaining slots
    3. Call OpenRouter (claude-3.5-haiku) with system_prompt.md + product context
    4. Cache the answer
  → Send reply via Meta Graph API v19.0
```

### Lead generation pipeline

```
n8n POST /run-leads (every 6 hours) → run.py
  → scraper.py: property listing platforms (luxury residential, unfurnished only)
  → scorer.py: qualifies and scores leads
  → storage.py: saves to Google Sheets + agents/lead-generation/qualified_leads.json
```

### Key files

| Path | Purpose |
|---|---|
| `agents/whatsapp-sales/bot.py` | Core AI logic: cache → RAG → OpenRouter |
| `agents/whatsapp-sales/server.py` | Flask webhook server |
| `agents/whatsapp-sales/api.py` | FastAPI webhook server (production) |
| `agents/whatsapp-sales/system_prompt.md` | System prompt loaded at startup |
| `rag/indexer.py` | Builds ChromaDB from products.json |
| `rag/retriever.py` | Hybrid search (keyword + semantic) |
| `rag/cache.py` | Semantic cache (reads/writes rag/cache.json) |
| `rag/knowledge_base/products.json` | Product catalogue — primary data source |
| `shared/database.py` | Supabase client (save_lead, get_leads) |
| `tests/eval.py` | 10-question keyword-based eval framework |

## Tech Stack

- AI: `anthropic/claude-3.5-haiku` via OpenRouter
- Vector DB: ChromaDB (`all-MiniLM-L6-v2` embeddings)
- Webhooks: Flask (server.py) or FastAPI (api.py)
- Messaging: Meta WhatsApp Cloud API (Graph API v19.0)
- Leads: Google Sheets API
- Automation: n8n
- Database: Supabase (leads table)
- Observability: Langfuse

## Required env vars

See `.env.example`. Key vars:
- `OPENROUTER_API_KEY` — bot will raise RuntimeError on startup if missing
- `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, `META_VERIFY_TOKEN` — Meta webhook
- `SUPABASE_URL`, `SUPABASE_KEY` — shared/database.py
- `GOOGLE_SHEET_ID` — lead generation pipeline

## Critical rules

- NEVER touch `.env` or push it to GitHub
- Always use `os.getenv()` for secrets
- Check cache BEFORE calling OpenRouter API
- Max 4 lines per WhatsApp reply
- Never hallucinate prices — only use ChromaDB data (products.json is the source of truth)

## Code style

- Python 3, no type hints needed
- Use f-strings
- Keep functions small and single-purpose
- Comments in English only
