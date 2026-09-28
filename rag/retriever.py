"""
rag/retriever.py — Hybrid Search (Semantic + Keyword)
Semantic search finds meaning, keyword search finds exact matches.
Both combined = more accurate product retrieval.
"""

import json
import logging
import os

import chromadb
from sentence_transformers import SentenceTransformer

_base         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH       = os.path.join(_base, "rag/chroma_db")
PRODUCTS_PATH = os.path.join(_base, "rag/knowledge_base/products.json")

logger = logging.getLogger(__name__)

model      = SentenceTransformer("all-MiniLM-L6-v2")
client     = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_collection("products")

with open(PRODUCTS_PATH, "r") as f:
    ALL_PRODUCTS = json.load(f)


def keyword_search(query: str) -> list:
    """
    Exact keyword match against product fields.
    Catches SKU codes (LUX-101), material names (Velvet),
    and specific words semantic search might miss.
    """
    query_lower = query.lower()
    matches     = []

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

        if query_lower in searchable:
            matches.append({
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

    return matches


def semantic_search(query: str, n_results: int = 3) -> list:
    """
    Vector similarity search using ChromaDB.
    Finds products by meaning even if exact words do not match.
    """
    embedding = model.encode([query]).tolist()
    results   = collection.query(
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
    Semantic search fills remaining slots.
    """
    try:
        keyword_results  = keyword_search(query)
        semantic_results = semantic_search(query, n_results)
    except Exception:
        logger.exception("Retrieval failed")
        return []

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
