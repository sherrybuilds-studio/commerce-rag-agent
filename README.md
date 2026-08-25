# Commerce RAG Agent — WhatsApp sales assistant for a furniture brand

> **Status (2026-08-25):** public snapshot (May 2026) of a client pilot. The
> production version runs in a private repo with Langfuse cost tracing per agent;
> the **38% token-cost cut (1,118 → 695 tokens/message)** below is the measured,
> dated figure. Live products + dated evidence: [sherrybuilds.com](https://sherrybuilds.com).

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude_Haiku-via_OpenRouter-blueviolet?logo=anthropic)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5-orange)
![WhatsApp](https://img.shields.io/badge/WhatsApp_Cloud_API-Meta-25D366?logo=whatsapp&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

A production-grade AI sales agent for a luxury interior design brand, delivered over
WhatsApp. Handles English and German customer conversations, retrieves the right
products using a hybrid RAG pipeline, and autonomously generates qualified sales leads.

---

## Features

- **Conversational AI** — Claude Haiku (3.5 in this snapshot, 4.5 now) answers product questions in English and German with strict tone and format rules
- **Hybrid RAG** — keyword + semantic (ChromaDB) retrieval finds the right products even for vague queries
- **Semantic caching** — 95% similarity threshold avoids redundant API calls; 38% reduction in token costs measured in production
- **Lead generation** — automated scraper targets luxury residential market listings, scores and qualifies leads, and writes results to Google Sheets
- **n8n automation** — lead pipeline runs every 6 hours without human intervention
- **Prompt injection guard** — FastAPI layer sanitizes input before it reaches the model
- **Observability** — full Langfuse tracing (cache hits, RAG retrievals, LLM calls, token usage)

---

## Architecture

```
Customer (WhatsApp)
        │
        ▼
Meta Cloud API  ──POST──▶  /webhook  (api.py — FastAPI + rate limiting)
                                │
                                ▼
                          bot.py — get_ai_response()
                           │
                ┌──────────┼──────────────────────┐
                │          │                      │
                ▼          ▼                      ▼
          cache.py    retriever.py         OpenRouter API
          (semantic   (keyword +           claude-3.5-haiku
           cache,     semantic,            + system_prompt.md
           95% sim.)  ChromaDB)            + product context
                │          │                      │
                └──────────┴──────────────────────┘
                                │
                                ▼
                     Reply → Meta Graph API v19.0
                                │
                                ▼
                         Customer (WhatsApp)

Lead Generation Pipeline (n8n triggers every 6 hours)
─────────────────────────────────────────────────────
property listing platforms → scraper.py → scorer.py → storage.py → Google Sheets
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Messaging** | Meta WhatsApp Cloud API (Graph v19.0) | Webhook + outbound messages |
| **Web server** | FastAPI + Uvicorn | ASGI webhook server with rate limiting |
| **AI model** | Claude Haiku via OpenRouter (3.5 in this snapshot; retired 2026-07, now 4.5) | Conversational response generation |
| **Vector DB** | ChromaDB (persistent) | Semantic product search |
| **Embeddings** | `all-MiniLM-L6-v2` (sentence-transformers) | Encoding queries and products |
| **Caching** | Custom semantic cache (cosine similarity) | 38% API cost reduction |
| **Lead scraping** | BeautifulSoup + Requests | Luxury property listing aggregation |
| **Lead storage** | Google Sheets API (gspread) | CRM-style outreach pipeline |
| **Automation** | n8n (self-hosted) | Scheduled lead pipeline execution |
| **Observability** | Langfuse | End-to-end conversation tracing |
| **Database** | Supabase | Persistent lead storage |

---

## Results

| Metric | Value |
|---|---|
| Token cost reduction (post-RAG) | **38%** (1,118 → 695 tokens/message) |
| Cache similarity threshold | **95%** cosine similarity |
| Leads pipeline cadence | **Every 6 hours** (fully automated) |
| Max reply length | **4 lines** (WhatsApp UX constraint) |
| Eval pass threshold | **≥ 80%** keyword match across 10 gold questions |
| Languages supported | **English, German** (auto-detected) |

---

## Project Structure

```
commerce-rag-agent/
├── agents/
│   ├── whatsapp-sales/
│   │   ├── bot.py              # Core AI logic: cache → RAG → LLM
│   │   ├── server.py           # Flask webhook (stable baseline)
│   │   ├── api.py              # FastAPI webhook (production)
│   │   └── system_prompt.md    # System instructions loaded at runtime
│   └── lead-generation/
│       ├── run.py              # Pipeline orchestrator + Flask API for n8n
│       ├── scraper.py          # Property listing scraper
│       ├── scorer.py           # Lead quality scoring (price, location, freshness)
│       └── storage.py          # Google Sheets integration
├── rag/
│   ├── indexer.py              # Builds ChromaDB from products.json
│   ├── retriever.py            # Hybrid search (keyword + semantic)
│   ├── cache.py                # Semantic response cache
│   └── knowledge_base/
│       └── products.json       # 12 luxury furniture products (source of truth)
├── shared/
│   ├── database.py             # Supabase client
│   └── observability.py        # Langfuse tracing helpers
├── tests/
│   └── eval.py                 # 10-question keyword-based eval framework
├── .env.example                # Required environment variables
└── requirements.txt
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/sherrybuilds-studio/commerce-rag-agent.git
cd commerce-rag-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your keys — see .env.example for all required variables
```

### 3. Build the vector index

```bash
python3 rag/indexer.py
```

### 4. Run the webhook server

```bash
# FastAPI (recommended for production)
cd agents/whatsapp-sales && uvicorn api:app --reload --port 5000

# Flask (stable baseline)
python3 agents/whatsapp-sales/server.py
```

### 5. Test in terminal (no webhook needed)

```bash
python3 agents/whatsapp-sales/bot.py
```

### 6. Run the evaluation suite

```bash
python3 tests/eval.py
# Must score >= 80% before deploying
```

### 7. Run the lead pipeline

```bash
python3 agents/lead-generation/run.py
```

---

## Environment Variables

See [.env.example](.env.example) for the full list. Key variables:

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | LLM access via OpenRouter |
| `META_ACCESS_TOKEN` | Yes | Meta WhatsApp Cloud API |
| `META_PHONE_NUMBER_ID` | Yes | Your WhatsApp Business phone |
| `META_VERIFY_TOKEN` | Yes | Webhook verification secret |
| `SUPABASE_URL` | Optional | Lead database |
| `SUPABASE_KEY` | Optional | Lead database |
| `LANGFUSE_PUBLIC_KEY` | Optional | Observability tracing |

---

## Evaluation (May 2026 run)

The eval suite in `tests/eval.py` runs 10 gold-standard questions (English + German)
and checks that the bot's responses contain expected keywords.

```
INTERIOR BRAND BOT — EVALUATION FRAMEWORK
============================================================
Test 1: Dining table inquiry in English          PASS
Test 2: Sofa inquiry in English                  PASS
Test 3: Top product inquiry                      PASS
...
Test 10: German language dining table inquiry    PASS
============================================================
FINAL SCORE: 90.0%
PASSED: 9/10
RESULT: PRODUCTION READY
```

---

## License

MIT
