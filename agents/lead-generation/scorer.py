"""
agents/lead-generation/scorer.py
Scores raw listings from scraper.
Higher score = better lead = contact first.
Max score: 110 points
"""

from datetime import UTC, datetime, timedelta

# Premium tier — highest score
TIER_1_AREAS = ["prime", "central", "old town", "harbour", "garden district", "embassy"]

# Good tier — solid leads
TIER_2_AREAS = ["north", "west end", "riverside", "heights", "park"]

# Standard tier — still worth contacting if price is high
TIER_3_AREAS = ["suburbs", "outskirts", "new town", "east side"]

HOUSE_KEYWORDS     = ["house", "villa", "farmhouse", "bungalow", "detached"]
APARTMENT_KEYWORDS = ["apartment", "flat", "studio", "penthouse"]


def score_price(price_value: int) -> int:
    """Score based on property value. Max 40 points."""
    if price_value >= 2_000_000:
        return 40
    elif price_value >= 800_000:
        return 30
    elif price_value >= 400_000:
        return 20
    else:
        return 5


def score_location(listing: dict) -> int:
    """Score based on area prestige. Max 40 points."""
    combined = listing.get("location", "").lower() + " " + listing.get("title", "").lower()
    if any(area in combined for area in TIER_1_AREAS):
        return 40
    elif any(area in combined for area in TIER_2_AREAS):
        return 25
    elif any(area in combined for area in TIER_3_AREAS):
        return 15
    else:
        return 10


def score_freshness(scraped_at: str) -> int:
    """Score based on how recently listed. Max 20 points. An unreadable timestamp scores the minimum."""
    try:
        scraped = datetime.fromisoformat(scraped_at)
        if scraped.tzinfo is None:
            scraped = scraped.astimezone()  # no offset: written in local time by older scraper runs
        age = datetime.now(UTC) - scraped
    except (TypeError, ValueError, OverflowError, OSError):
        return 5

    if age < timedelta(hours=24):
        return 20
    elif age < timedelta(days=3):
        return 15
    elif age < timedelta(days=7):
        return 10
    else:
        return 5


def score_property_type(title: str) -> int:
    """Bonus for house/villa over apartment. Max 10 points."""
    title_lower = title.lower()
    if any(kw in title_lower for kw in HOUSE_KEYWORDS):
        return 10
    elif any(kw in title_lower for kw in APARTMENT_KEYWORDS):
        return 5
    return 7


def score_lead(listing: dict) -> dict:
    """Score a single listing and return enriched lead dict."""
    price_score    = score_price(listing.get("price_value", 0))
    location_score = score_location(listing)
    freshness_score = score_freshness(listing["scraped_at"])
    type_score     = score_property_type(listing["title"])

    total_score = price_score + location_score + freshness_score + type_score

    if total_score >= 80:
        tier = "ULTRA LUXURY"
    elif total_score >= 60:
        tier = "LUXURY"
    elif total_score >= 40:
        tier = "STANDARD"
    else:
        tier = "LOW"

    return {
        **listing,
        "score":          total_score,
        "tier":           tier,
        "score_breakdown": {
            "price":     price_score,
            "location":  location_score,
            "freshness": freshness_score,
            "type":      type_score,
        },
        "outreach_status": "pending",
    }


def run_scorer(listings: list, min_score: int = 40) -> list:
    """Score all listings, filter low quality, sort by score."""
    print(f"\nScoring {len(listings)} listings...")

    scored    = [score_lead(listing) for listing in listings]
    qualified = [lead for lead in scored if lead["score"] >= min_score]
    qualified.sort(key=lambda lead: lead["score"], reverse=True)

    print(f"Qualified leads: {len(qualified)} (score >= {min_score})")
    print(f"Ultra Luxury: {sum(1 for lead in qualified if lead['tier'] == 'ULTRA LUXURY')}")
    print(f"Luxury:       {sum(1 for lead in qualified if lead['tier'] == 'LUXURY')}")
    print(f"Standard:     {sum(1 for lead in qualified if lead['tier'] == 'STANDARD')}")

    return qualified


if __name__ == "__main__":
    import json
    with open("agents/lead-generation/raw_leads.json") as f:
        raw = json.load(f)
    scored = run_scorer(raw)
    print("\nTop lead:")
    if scored:
        print(json.dumps(scored[0], indent=2))
