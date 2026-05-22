# Interior Brand AI — Change Log

## May 5, 2026 — Session 6
- Installed n8n on VPS via PM2 (port 5678)
- Added Flask API endpoint to lead pipeline — /run-leads and /health routes
- Built first n8n workflow: Interior Brand — Lead Pipeline
- Schedule trigger: every 6 hours automatic execution
- HTTP Request node calls Python scraper via 127.0.0.1:5000
- Telegram node sends formatted lead alert to personal chat
- Created dedicated Telegram bot for n8n lead notifications
- First automated lead delivered from luxury residential market — Score 110
- All PM2 services stable: bot-leads, bot-n8n, bot-openclaw
- Total RAM usage: 615mb of 6.7GB
- Lead pipeline running autonomously every 6 hours

## May 5, 2026
- Add semantic caching — rag/cache.py with 95% similarity threshold
- Connect cache to bot.py — checks cache before every API call
- Remove sensitive files from GitHub tracking
- Add lead generation README

## May 3, 2026
- Add lead generation pipeline — scraper, scorer, storage, runner
- Add Google Sheets integration — leads saved automatically
- Add tier-based location scoring system
- Add furnished property filter
- Add luxury residential market price range filter
- Connect Google Cloud — Sheets API + Drive API enabled
- Add google_credentials.json to gitignore

## April 29, 2026 — Session 4
- Add Flask webhook server for Meta WhatsApp Cloud API
- Update products.json with lead time, wood options, finish options fields
- Re-index ChromaDB with updated product data
- Fix system prompt pricing objection handling
- Add chroma_db to gitignore
- Add .env.example and requirements.txt
- Improve README accuracy

## April 27, 2026 — Session 3
- Built RAG pipeline with ChromaDB and sentence-transformers
- Built rag/indexer.py — converts products to vector embeddings
- Built rag/retriever.py — searches ChromaDB, returns top 3 matches
- Connected RAG to bot.py — replaced JSON dumping with smart retrieval
- Token cost reduced from 1,118 to 695 per message (38% cheaper)
- Fixed language detection in system prompt
- Added price hallucination guard
- Fixed model to anthropic/claude-3.5-haiku

## April 25, 2026 — Session 2
- Built bot.py with Claude 3.5 Haiku via OpenRouter
- Bot responds in English and German (auto-detected)
- Updated system prompt with language rules
- Pushed to GitHub, no secrets leaked

## April 21, 2026 — Session 1
- Created Facebook Business Manager
- Linked WhatsApp Business (approved)
- Created GitHub repo
- Set up folder structure
- Wrote system_prompt.md and products.json
