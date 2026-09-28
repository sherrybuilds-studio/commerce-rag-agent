"""
Hybrid retrieval: keyword matches first, semantic results fill the remaining slots.
semantic_search is replaced with canned results, so no model or ChromaDB index is needed.
"""

import pytest

from rag import retriever


@pytest.fixture
def semantic_returns(monkeypatch):
    """Make semantic_search return products with the given names, in that order."""

    def install(*names):
        def fake_semantic_search(query, n_results=3):
            return [{"id": "", "name": name, "source": "semantic"} for name in names][:n_results]

        monkeypatch.setattr(retriever, "semantic_search", fake_semantic_search)

    return install


def test_keyword_hits_rank_before_semantic_results(semantic_returns):
    semantic_returns("Royal Oak Dining Set", "Modular Sectional Sofa", "Heritage Sleigh Bed")

    results = retriever.retrieve("velvet", n_results=5)

    assert [r["source"] for r in results] == ["keyword", "keyword", "keyword", "semantic", "semantic"]
    assert [r["name"] for r in results] == [
        "Modular Sectional Sofa",  # velvet upholstery options
        "Grand Walk-In Wardrobe System",  # velvet-lined drawers
        "Classic 4-Door Wardrobe",  # velvet-lined drawers
        "Royal Oak Dining Set",
        "Heritage Sleigh Bed",  # the semantic copy of the sofa is dropped as a duplicate
    ]


def test_semantic_results_fill_up_to_n_results(semantic_returns):
    semantic_returns("Royal Oak Dining Set", "Heritage Sleigh Bed", "Milan Oval Dining Table")

    results = retriever.retrieve("LUX-104")

    assert [r["name"] for r in results] == [
        "Chesterfield Leather Sofa Set",
        "Royal Oak Dining Set",
        "Heritage Sleigh Bed",
    ]
    assert results[0]["id"] == "LUX-104"
    assert results[0]["source"] == "keyword"
