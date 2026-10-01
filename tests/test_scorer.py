"""
Lead scorer (agents/lead-generation/scorer.py). Price 40 + location 40 + freshness 20 + property type 10 = 110.
Tiers: ULTRA LUXURY 80+, LUXURY 60+, STANDARD 40+, LOW below that. run_scorer keeps 40+ by default.
"""

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture(scope="module")
def scorer(load_module):
    return load_module("lead_scorer", "agents/lead-generation/scorer.py")


def listing(title, location, price, age):
    """A listing scraped `age` ago, timestamped the way the scraper writes it (UTC with an offset)."""
    return {
        "title": title,
        "location": location,
        "price_value": price,
        "scraped_at": (datetime.now(UTC) - age).isoformat(),
    }


VILLA = listing("Villa with garden", "Prime district", 2_500_000, timedelta(hours=1))  # 40 + 40 + 20 + 10 = 110
APARTMENT = listing("Apartment with balcony", "North quarter", 900_000, timedelta(days=2))  # 30 + 25 + 15 + 5 = 75
FLAT = listing("Flat near the station", "Suburbs", 500_000, timedelta(days=5))  # 20 + 15 + 10 + 5 = 50
STUDIO = listing("Studio", "Unlisted area", 100_000, timedelta(days=30))  # 5 + 10 + 5 + 5 = 25


def test_tiers_follow_the_total_score(scorer):
    expected = {"ULTRA LUXURY": (VILLA, 110), "LUXURY": (APARTMENT, 75), "STANDARD": (FLAT, 50), "LOW": (STUDIO, 25)}
    for tier, (lead, score) in expected.items():
        scored = scorer.score_lead(lead)
        assert (scored["tier"], scored["score"]) == (tier, score)

    # 40 + 15 + 20 + 5 = 80 is exactly the ULTRA LUXURY threshold.
    boundary = scorer.score_lead(listing("Apartment", "Suburbs", 2_000_000, timedelta(hours=1)))
    assert (boundary["tier"], boundary["score"]) == ("ULTRA LUXURY", 80)


def test_run_scorer_keeps_leads_at_or_above_the_minimum_best_first(scorer):
    leads = [STUDIO, FLAT, VILLA, APARTMENT]

    assert [lead["score"] for lead in scorer.run_scorer(leads)] == [110, 75, 50]
    assert [lead["score"] for lead in scorer.run_scorer(leads, min_score=50)] == [110, 75, 50]
    assert [lead["score"] for lead in scorer.run_scorer(leads, min_score=51)] == [110, 75]


def test_freshness_reads_utc_and_older_offset_less_timestamps(scorer):
    now = datetime.now(UTC)
    assert scorer.score_freshness((now - timedelta(hours=2)).isoformat()) == 20
    assert scorer.score_freshness((now - timedelta(days=2)).isoformat()) == 15
    assert scorer.score_freshness((now - timedelta(days=5)).isoformat()) == 10
    assert scorer.score_freshness((now - timedelta(days=9)).isoformat()) == 5

    # Earlier scraper runs wrote local time without an offset.
    local_naive = datetime.now().astimezone().replace(tzinfo=None) - timedelta(hours=2)
    assert scorer.score_freshness(local_naive.isoformat()) == 20


def test_unreadable_timestamp_scores_the_minimum_freshness(scorer):
    for bad in ["", "yesterday", "2026-13-45T25:61:00", None]:
        assert scorer.score_freshness(bad) == 5

    lead = {**VILLA, "scraped_at": "garbled"}
    assert scorer.score_lead(lead)["score_breakdown"]["freshness"] == 5
