# Lead Generation Agent

Automated pipeline that scrapes luxury property listings from property listing platforms,
scores them by quality, and saves qualified leads to Google Sheets.

## Pipeline

```
property listing platforms → scraper.py → scorer.py → storage.py → Google Sheets
```

## Run

```bash
# Run pipeline once
python3 agents/lead-generation/run.py

# Start as API server (for n8n or cron trigger)
python3 agents/lead-generation/run.py serve
# POST /run-leads  — triggers pipeline
# GET  /health     — health check
```

## Scoring

| Component | Max Points |
|---|---|
| Price tier | 40 |
| Location tier | 40 |
| Freshness (recency) | 20 |
| Property type | 10 |
| **Total** | **110** |

Minimum score to qualify: **40 points**

Tiers: `ULTRA LUXURY` (80+) · `LUXURY` (60+) · `STANDARD` (40+)

## Configuration

Update `TARGET_AREAS_PLATFORM_1` and `TARGET_AREAS_PLATFORM_2` in `scraper.py` with
the area slugs for your target market. Replace platform URLs with your actual
property listing platforms.

Set `GOOGLE_SHEET_ID` in your `.env` file, and place `google_credentials.json`
(Google service account) at `agents/lead-generation/google_credentials.json`.
