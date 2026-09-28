import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify
from scorer import run_scorer
from scraper import run_scraper
from storage import save_leads

app = Flask(__name__)

def run_pipeline():
    print("=" * 50)
    print("LEAD GENERATION PIPELINE STARTING")
    print("=" * 50)
    # Step 1 — Scrape
    raw_listings = run_scraper()
    if not raw_listings:
        print("No listings found. Exiting.")
        return [], 0
    # Step 2 — Score
    qualified_leads = run_scorer(raw_listings)
    if not qualified_leads:
        print("No qualified leads found. Exiting.")
        return [], 0
    # Step 3 — Save locally
    with open("agents/lead-generation/qualified_leads.json", "w") as f:
        json.dump(qualified_leads, f, indent=2)
    # Step 4 — Save to Google Sheets
    new_leads = save_leads(qualified_leads)
    print("\nPipeline complete.")
    print(f"Total qualified leads: {len(qualified_leads)}")
    print(f"New leads added to Google Sheets: {new_leads}")
    print("=" * 50)
    return qualified_leads, new_leads

# HTTP endpoint for n8n
@app.route('/run-leads', methods=['POST'])
def trigger_leads():
    qualified_leads, new_leads = run_pipeline()
    return jsonify({
        "status": "success",
        "total_qualified": len(qualified_leads),
        "new_to_sheets": new_leads,
        "leads": qualified_leads
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "lead-generation"})

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        print("Starting lead generation API server on port 5000...")
        app.run(host='127.0.0.1', port=5000)
    else:
        run_pipeline()
