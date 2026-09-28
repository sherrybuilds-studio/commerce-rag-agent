"""
rag/retriever.py — Hybrid Search (Semantic + Keyword)
Semantic search finds meaning, keyword search finds exact matches.
Both combined = more accurate product retrieval.

The embedding model and the ChromaDB collection load on first use, so importing this module is cheap.
"""

import json
import logging
import os
import re
import string
from functools import lru_cache

from rag.embeddings import get_model

_base         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH       = os.path.join(_base, "rag/chroma_db")
PRODUCTS_PATH = os.path.join(_base, "rag/knowledge_base/products.json")

logger = logging.getLogger(__name__)

with open(PRODUCTS_PATH, "r") as f:
    ALL_PRODUCTS = json.load(f)


@lru_cache(maxsize=1)
def get_collection():
    """The collection built by rag/indexer.py. Raises until the index exists."""
    import chromadb

    return chromadb.PersistentClient(path=DB_PATH).get_collection("products")


def _contains_words(text: str, phrase: str) -> bool:
    """True when phrase occurs in text as whole words: "velvet" is in "velvet-lined", "hi" is not in "white"."""
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def keyword_search(query: str) -> list:
    """
    Exact keyword match against product fields.
    A product matches when the message names its SKU code (LUX-101) or its full product name anywhere,
    or when the whole message is a word or phrase from its fields, such as a material name (Velvet).
    Matching is on whole words and ignores case. Products the message names come first.
    """
    query_lower = " ".join(query.lower().split())
    phrase      = query_lower.strip(string.punctuation + " ")
    named       = []
    mentioned   = []

    for p in ALL_PRODUCTS:
        searchable = " ".join([
            p.get("id", ""),
            p.get("name", ""),
            p.get("category", ""),
            p.get("wood", ""),
            p.get("description", ""),
            " ".join(p.get("wood_options", [])),
            " ".join(p.get("finish_options", [])),
        ]).lower()

        labels = (p.get("id", "").lower(), p.get("name", "").lower())
        if any(label and _contains_words(query_lower, label) for label in labels):
            bucket = named
        elif len(phrase) >= 3 and _contains_words(searchable, phrase):
            bucket = mentioned
        else:
            continue

        bucket.append({
            "id":             p["id"],
            "name":           p["name"],
            "pricing_tier":   p.get("pricing_tier", "Luxury"),
            "description":    p["description"],
            "lead_time":      p.get("lead_time_weeks", "6-8"),
            "wood_options":   p.get("wood_options", []),
            "finish_options": p.get("finish_options", []),
            "customizable":   p.get("customizable", False),
            "source":         "keyword"
        })

    return named + mentioned


def semantic_search(query: str, n_results: int = 3) -> list:
    """
    Vector similarity search using ChromaDB.
    Finds products by meaning even if exact words do not match.
    """
    embedding = get_model().encode([query]).tolist()
    results   = get_collection().query(
        query_embeddings=embedding,
        n_results=n_results
    )

    products = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i]
        full = next((p for p in ALL_PRODUCTS if p["name"] == meta["name"]), {})
        products.append({
            "id":             full.get("id", ""),
            "name":           meta["name"],
            "pricing_tier":   meta.get("pricing_tier", "Luxury"),
            "description":    doc,
            "lead_time":      full.get("lead_time_weeks", "6-8"),
            "wood_options":   full.get("wood_options", []),
            "finish_options": full.get("finish_options", []),
            "customizable":   full.get("customizable", False),
            "source":         "semantic"
        })

    return products


def retrieve(query: str, n_results: int = 3) -> list:
    """
    Hybrid search — keyword first, semantic fills the rest.
    If keyword finds exact matches, they go to the top.
    Semantic search fills remaining slots. If it fails (index not built, model not
    downloadable), the keyword matches are still returned.
    """
    keyword_results = keyword_search(query)
    try:
        semantic_results = semantic_search(query, n_results)
    except Exception:
        logger.exception("Semantic search failed, returning keyword matches only")
        semantic_results = []

    seen  = set()
    final = []

    for r in keyword_results:
        if r["name"] not in seen:
            seen.add(r["name"])
            final.append(r)

    for r in semantic_results:
        if r["name"] not in seen:
            seen.add(r["name"])
            final.append(r)

    return final[:n_results]
