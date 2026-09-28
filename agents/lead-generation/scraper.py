"""
agents/lead-generation/scraper.py
Scrapes property listing platforms for luxury residential listings.
Filters: unfurnished only, target luxury residential market areas.
"""

import json
import random
import time
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup

# Configure target areas and platform slugs for your market
TARGET_AREAS_PLATFORM_1 = [
    "luxury-residential-area-1",
    "luxury-residential-area-2",
    "luxury-residential-area-3",
    "luxury-residential-area-4",
    "luxury-residential-area-5",
]

TARGET_AREAS_PLATFORM_2 = [
    "luxury-area-north-1",
    "luxury-area-north-2",
    "luxury-area-south-1",
    "luxury-area-south-2",
    "luxury-area-central",
]

# Tier labels for property value ranges
PRICE_TIER_HIGH   = "Ultra-Luxury"
PRICE_TIER_MID    = "Luxury"
PRICE_TIER_ENTRY  = "Premium"

FURNISHED_KEYWORDS = [
    "furnished", "fully furnished", "semi furnished",
    "furnishd", "frnished"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def parse_price(price_text: str) -> int:
    """Convert price text to integer for comparison."""
    try:
        price_text = price_text.lower().strip()
        price_text = price_text.replace(",", "").replace("€", "").replace("$", "").strip()
        # Handle abbreviated formats (e.g. 1.5M, 500K)
        if "m" in price_text:
            return int(float(price_text.replace("m", "").strip()) * 1_000_000)
        elif "k" in price_text:
            return int(float(price_text.replace("k", "").strip()) * 1_000)
        else:
            return int(float(price_text))
    except (AttributeError, ValueError):
        return 0


def get_price_tier(price: int) -> str:
    """Map numeric price to luxury tier label."""
    if price >= 2_000_000:
        return PRICE_TIER_HIGH
    elif price >= 800_000:
        return PRICE_TIER_MID
    else:
        return PRICE_TIER_ENTRY


def is_furnished(title: str) -> bool:
    """Return True if listing appears to be furnished — skip these."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in FURNISHED_KEYWORDS)


def scrape_platform_1_area(area_slug: str) -> list:
    """Scrape one area from property listing platform 1."""
    # Replace with the actual platform URL for your target market
    url = f"https://listing-platform-1.example.com/homes/{area_slug}-1-1.html"
    listings = []

    try:
        print(f"  [Platform 1] Scraping: {area_slug}")
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code != 200:
            print(f"  Failed: {resp.status_code}")
            return []

        soup  = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("li", attrs={"aria-label": "Listing"})
        if not cards:
            cards = soup.find_all("article")

        for card in cards:
            try:
                title_el = card.find("h2") or card.find("h3")
                title    = title_el.get_text(strip=True) if title_el else "Unknown"

                if is_furnished(title):
                    continue

                price_el   = card.find(attrs={"aria-label": "Price"})
                if not price_el:
                    price_el = card.find(class_=lambda x: x and "price" in x.lower())
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price_val  = parse_price(price_text)
                price_tier = get_price_tier(price_val)

                loc_el   = card.find(attrs={"aria-label": "Location"})
                if not loc_el:
                    loc_el = card.find(class_=lambda x: x and "location" in x.lower())
                location = loc_el.get_text(strip=True) if loc_el else area_slug

                link_el = card.find("a", href=True)
                link    = "https://listing-platform-1.example.com" + link_el["href"] \
                          if link_el and link_el["href"].startswith("/") else ""

                listings.append({
                    "title":      title,
                    "price_value": price_val,
                    "price_text": price_text,
                    "price_tier": price_tier,
                    "location":   location,
                    "area":       area_slug,
                    "source":     "platform_1",
                    "url":        link,
                    "scraped_at": datetime.now(UTC).isoformat(),
                    "status":     "new",
                })
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                print(f"  Skipped a listing card: {e}")
                continue

        print(f"  Found {len(listings)} unfurnished listings in luxury residential market")

    except requests.exceptions.RequestException as e:
        print(f"  Network error: {e}")

    time.sleep(random.uniform(2, 4))
    return listings


def scrape_platform_2_area(area_slug: str) -> list:
    """Scrape one area from property listing platform 2."""
    url = f"https://listing-platform-2.example.com/sale/{area_slug}/"
    listings = []

    try:
        print(f"  [Platform 2] Scraping: {area_slug}")
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code != 200:
            print(f"  Failed: {resp.status_code}")
            return []

        soup  = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("div", class_=lambda x: x and "property" in x.lower())
        if not cards:
            cards = soup.find_all("article")

        for card in cards:
            try:
                title_el = card.find("h2") or card.find("h3") or card.find("h4")
                title    = title_el.get_text(strip=True) if title_el else "Unknown"

                if is_furnished(title):
                    continue

                price_el   = card.find(class_=lambda x: x and "price" in x.lower())
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price_val  = parse_price(price_text)
                price_tier = get_price_tier(price_val)

                link_el = card.find("a", href=True)
                link    = "https://listing-platform-2.example.com" + link_el["href"] \
                          if link_el and link_el["href"].startswith("/") else ""

                listings.append({
                    "title":      title,
                    "price_value": price_val,
                    "price_text": price_text,
                    "price_tier": price_tier,
                    "location":   area_slug,
                    "area":       area_slug,
                    "source":     "platform_2",
                    "url":        link,
                    "scraped_at": datetime.now(UTC).isoformat(),
                    "status":     "new",
                })
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                print(f"  Skipped a listing card: {e}")
                continue

        print(f"  Found {len(listings)} unfurnished listings in luxury residential market")

    except requests.exceptions.RequestException as e:
        print(f"  Network error: {e}")

    time.sleep(random.uniform(2, 4))
    return listings


def run_scraper() -> list:
    """Run scraper across property listing platforms, return combined unique results."""
    print(f"\nLead Scraper starting — {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')}")
    print("Sources: property listing platforms")
    print("Target market: luxury residential")
    print("Furnished properties: EXCLUDED\n")

    all_listings = []

    for area in TARGET_AREAS_PLATFORM_1:
        listings = scrape_platform_1_area(area)
        all_listings.extend(listings)

    for area in TARGET_AREAS_PLATFORM_2:
        listings = scrape_platform_2_area(area)
        all_listings.extend(listings)

    # Remove duplicates by URL
    seen_urls = set()
    unique    = []
    for listing in all_listings:
        if listing["url"] not in seen_urls:
            seen_urls.add(listing["url"])
            unique.append(listing)

    platform_1_count = sum(1 for listing in unique if listing["source"] == "platform_1")
    platform_2_count = sum(1 for listing in unique if listing["source"] == "platform_2")

    print(f"\nTotal unique listings: {len(unique)}")
    print(f"  Platform 1: {platform_1_count}")
    print(f"  Platform 2: {platform_2_count}")

    with open("agents/lead-generation/raw_leads.json", "w") as f:
        json.dump(unique, f, indent=2)
    print("Saved to agents/lead-generation/raw_leads.json")

    return unique


if __name__ == "__main__":
    results = run_scraper()
    if results:
        print(json.dumps(results[0], indent=2))
