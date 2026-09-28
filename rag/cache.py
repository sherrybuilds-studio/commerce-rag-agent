"""
rag/cache.py — Semantic Caching
Saves common questions and answers to avoid repeat API calls.
Similarity threshold: 95% — if question is this similar, return cached answer.
"""

import json
import os
from datetime import UTC, datetime

import numpy as np
from sentence_transformers import SentenceTransformer

CACHE_FILE = "rag/cache.json"
THRESHOLD  = 0.95  # 95% similarity required to use cache

model = SentenceTransformer("all-MiniLM-L6-v2")


def load_cache() -> list:
    """Load existing cache from disk."""
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save_cache(cache: list):
    """Save cache to disk."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def cosine_similarity(a: list, b: list) -> float:
    """Calculate similarity between two vectors. 1.0 = identical."""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_cached_answer(question: str) -> tuple:
    """
    Check if a similar question exists in cache.
    Returns (answer, similarity) if similarity >= 95%, else (None, None).
    """
    cache = load_cache()
    if not cache:
        return None, None

    question_embedding = model.encode([question])[0].tolist()

    for entry in cache:
        similarity = cosine_similarity(question_embedding, entry["embedding"])
        if similarity >= THRESHOLD:
            print(f"Cache hit ({similarity:.0%} similar): {entry['question'][:50]}")
            return entry["answer"], similarity

    return None, None


def cache_answer(question: str, answer: str):
    """Save a new question-answer pair to cache."""
    cache = load_cache()

    # Check if already cached to avoid duplicates
    question_embedding = model.encode([question])[0].tolist()
    for entry in cache:
        similarity = cosine_similarity(question_embedding, entry["embedding"])
        if similarity >= THRESHOLD:
            return  # Already cached

    cache.append({
        "question":  question,
        "answer":    answer,
        "embedding": question_embedding,
        "cached_at": datetime.now(UTC).isoformat(),
        "hits":      0,
    })

    save_cache(cache)
    print(f"Cached: {question[:50]}")


def get_cache_stats() -> dict:
    """Return cache statistics."""
    cache = load_cache()
    return {
        "total_entries": len(cache),
        "questions":     [e["question"] for e in cache],
    }
