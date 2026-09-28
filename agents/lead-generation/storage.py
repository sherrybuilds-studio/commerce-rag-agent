"""
agents/lead-generation/storage.py
Saves qualified leads to Google Sheets automatically.
"""

import json
import os
from datetime import datetime

import gspread
from google.auth.exceptions import GoogleAuthError
from google.oauth2.service_account import Credentials

SHEET_ID         = os.getenv("GOOGLE_SHEET_ID", "YOUR_SHEET_ID_HERE")
CREDENTIALS_FILE = "agents/lead-generation/google_credentials.json"
SHEET_NAME       = "Sheet1"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Date Found",
    "Title",
    "Price",
    "Location",
    "Score",
    "Tier",
    "Source",
    "URL",
    "Outreach Status",
    "Notes",
]


def get_sheet():
    """Connect to Google Sheets using service account credentials."""
    creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    return sheet


def setup_headers(sheet):
    """Add headers if sheet is empty."""
    existing = sheet.row_values(1)
    if not existing:
        sheet.append_row(HEADERS)
        print("Headers added to sheet.")


def get_existing_urls(sheet) -> set:
    """Get all URLs already in the sheet to avoid duplicates."""
    try:
        url_col = sheet.col_values(8)  # Column 8 = URL
        return set(url_col[1:])        # Skip header row
    except (gspread.exceptions.GSpreadException, OSError):
        return set()


def save_leads(leads: list) -> int:
    """Save qualified leads to Google Sheets. Returns number of new leads added."""
    print("\nConnecting to Google Sheets...")

    try:
        sheet         = get_sheet()
        setup_headers(sheet)
        existing_urls = get_existing_urls(sheet)

        new_count = 0
        for lead in leads:
            if lead["url"] in existing_urls:
                continue

            row = [
                datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
                lead["title"],
                lead["price_text"],
                lead["location"],
                lead["score"],
                lead["tier"],
                lead["source"],
                lead["url"],
                "Pending",
                "",
            ]

            sheet.append_row(row)
            existing_urls.add(lead["url"])
            new_count += 1
            print(f"  Added: {lead['title'][:50]}...")

        print(f"\nGoogle Sheets updated — {new_count} new leads added.")
        return new_count

    except (gspread.exceptions.GSpreadException, GoogleAuthError, OSError, ValueError) as e:
        # Sheets API, auth, network or credentials-file error. qualified_leads.json is already written.
        print(f"Google Sheets error: {e}")
        return 0


if __name__ == "__main__":
    with open("agents/lead-generation/qualified_leads.json") as f:
        leads = json.load(f)
    save_leads(leads)
