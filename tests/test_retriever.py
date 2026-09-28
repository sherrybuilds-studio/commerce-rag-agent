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


def test_sku_inside_a_sentence_is_a_keyword_hit(semantic_returns):
    semantic_returns("Royal Oak Dining Set", "Heritage Sleigh Bed", "Milan Oval Dining Table")

    results = retriever.retrieve("Tell me about LUX-104.")

    assert results[0]["id"] == "LUX-104"
    assert results[0]["source"] == "keyword"


def test_product_name_inside_a_sentence_is_a_keyword_hit(semantic_returns):
    semantic_returns("Royal Oak Dining Set")

    results = retriever.retrieve("Is the Heritage Sleigh Bed available in oak?")

    assert results[0]["id"] == "LUX-108"
    assert results[0]["source"] == "keyword"


def test_the_named_product_ranks_before_products_that_mention_it():
    # LUX-108's description says it "pairs naturally with LUX-109".
    assert [r["id"] for r in retriever.keyword_search("LUX-109")] == ["LUX-109", "LUX-108"]


def test_keyword_matches_are_whole_words():
    assert retriever.keyword_search("Hi") == []  # not a match for "white" or "hand-stitched"
    assert retriever.keyword_search("LUX-10") == []  # not a prefix match for LUX-101 to LUX-109


def test_keyword_hits_survive_a_semantic_search_failure(monkeypatch):
    def broken_semantic_search(query, n_results=3):
        raise RuntimeError("Collection [products] does not exist")  # index not built yet

    monkeypatch.setattr(retriever, "semantic_search", broken_semantic_search)

    results = retriever.retrieve("Tell me about LUX-104.")

    assert [r["id"] for r in results] == ["LUX-104"]
