"""
rag/cache.py — Semantic Caching
Saves answers to repeat questions so they skip retrieval and the LLM call.

A question whose embedding has cosine similarity THRESHOLD or more with a cached question gets the
cached answer. Entries expire TTL_SECONDS after they were written. When the cache holds more than
MAX_ENTRIES, the least recently used entries are evicted. The cache is one JSON file next to this
module, replaced atomically on every write.
"""

import contextlib
import json
import logging
import os
import tempfile
import threading
import time

import numpy as np

from rag.embeddings import embed

CACHE_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.json")
THRESHOLD   = 0.95              # cosine similarity required to reuse an answer
TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
MAX_ENTRIES = 500

logger = logging.getLogger(__name__)


def cosine_similarity(a, b) -> float:
    """Similarity between two vectors. 1.0 = same direction. 0.0 for zero or mismatched vectors."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return 0.0
    norms = np.linalg.norm(a) * np.linalg.norm(b)
    if norms == 0:
        return 0.0
    return float(np.dot(a, b) / norms)


class SemanticCache:
    """File-backed semantic cache with a TTL and a least-recently-used size cap."""

    def __init__(self, path=CACHE_FILE, embed_fn=embed, threshold=THRESHOLD,
                 ttl_seconds=TTL_SECONDS, max_entries=MAX_ENTRIES, clock=time.time):
        self.path        = path
        self.embed_fn    = embed_fn
        self.threshold   = threshold
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock       = clock
        self._lock       = threading.Lock()

    def get(self, question: str) -> tuple:
        """(answer, similarity) of the most similar fresh entry at or above the threshold, else (None, None)."""
        embedding = self.embed_fn(question)
        with self._lock:
            now     = self.clock()
            entries = self._load_fresh(now)
            entry, similarity = self._closest(entries, embedding)
            if entry is None:
                return None, None
            entry["last_used"] = now
            entry["hits"]      = entry.get("hits", 0) + 1
            self._save(entries)
        logger.info("Cache hit (%.0f%% similar): %s", similarity * 100, entry["question"][:50])
        return entry["answer"], similarity

    def put(self, question: str, answer: str) -> None:
        """Store an answer unless a similar question is already cached. Evicts least recently used entries."""
        embedding = self.embed_fn(question)
        with self._lock:
            now     = self.clock()
            entries = self._load_fresh(now)
            if self._closest(entries, embedding)[0] is not None:
                return
            entries.append({
                "question":   question,
                "answer":     answer,
                "embedding":  embedding,
                "created_at": now,
                "last_used":  now,
                "hits":       0,
            })
            if len(entries) > self.max_entries:
                entries.sort(key=lambda e: e.get("last_used", e["created_at"]))
                entries = entries[-self.max_entries:]
            self._save(entries)
        logger.info("Cached: %s", question[:50])

    def stats(self) -> dict:
        with self._lock:
            entries = self._load_fresh(self.clock())
        return {
            "total_entries": len(entries),
            "questions":     [e["question"] for e in entries],
        }

    def _closest(self, entries, embedding):
        best, best_similarity = None, None
        for entry in entries:
            similarity = cosine_similarity(embedding, entry["embedding"])
            if similarity >= self.threshold and (best_similarity is None or similarity > best_similarity):
                best, best_similarity = entry, similarity
        return best, best_similarity

    def _load_fresh(self, now) -> list:
        """Entries younger than the TTL. A missing or unreadable file counts as an empty cache."""
        try:
            with open(self.path) as f:
                entries = json.load(f)
        except FileNotFoundError:
            return []
        except (OSError, ValueError):
            logger.warning("Ignoring unreadable cache file %s", self.path)
            return []
        if not isinstance(entries, list):
            return []
        return [e for e in entries if self._is_fresh(e, now)]

    def _is_fresh(self, entry, now) -> bool:
        # Entries without numeric timestamps (the older cache format) count as expired.
        if not isinstance(entry, dict) or not {"question", "answer", "embedding"} <= entry.keys():
            return False
        created_at = entry.get("created_at")
        if not isinstance(created_at, int | float):
            return False
        return now - created_at < self.ttl_seconds

    def _save(self, entries) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=os.path.basename(self.path) + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(entries, f)
            os.replace(tmp_path, self.path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_path)
            raise


_default_cache = SemanticCache()


def get_cached_answer(question: str) -> tuple:
    """
    Check if a similar question exists in cache.
    Returns (answer, similarity) if similarity >= THRESHOLD, else (None, None).
    """
    return _default_cache.get(question)


def cache_answer(question: str, answer: str) -> None:
    """Save a new question-answer pair to cache."""
    _default_cache.put(question, answer)


def get_cache_stats() -> dict:
    """Return cache statistics."""
    return _default_cache.stats()
