"""
Semantic cache: threshold, 7-day TTL, least-recently-used cap.
Embeddings are small hand-made vectors, so no model is loaded.
"""

import json

import pytest

from rag import cache

DAY = 24 * 60 * 60

# Cosine similarity with "base": close = 24/25 = 0.96, near miss = 35/37 = 0.946, other = 0.
VECTORS = {
    "base":      [1.0, 0.0],
    "close":     [24.0, 7.0],
    "near miss": [35.0, 12.0],
    "other":     [0.0, 1.0],
}


class FakeClock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def cache_path(tmp_path):
    return tmp_path / "cache.json"


@pytest.fixture
def make_cache(cache_path, clock):
    def make(vectors=VECTORS, **settings):
        return cache.SemanticCache(path=cache_path, embed_fn=vectors.__getitem__, clock=clock, **settings)

    return make


def test_defaults():
    assert cache.THRESHOLD == 0.95
    assert cache.TTL_SECONDS == 7 * DAY
    assert cache.MAX_ENTRIES == 500


def test_hit_above_threshold(make_cache):
    semantic_cache = make_cache()
    semantic_cache.put("base", "Answer A")

    answer, similarity = semantic_cache.get("close")

    assert answer == "Answer A"
    assert similarity == pytest.approx(0.96)


def test_similarity_exactly_at_threshold_is_a_hit(make_cache):
    # 3/5 is exact in floating point, so this checks >= rather than >.
    semantic_cache = make_cache({"a": [1.0, 0.0], "b": [3.0, 4.0]}, threshold=0.6)
    semantic_cache.put("a", "Answer A")

    assert semantic_cache.get("b") == ("Answer A", 0.6)


def test_miss_below_threshold(make_cache):
    semantic_cache = make_cache()
    semantic_cache.put("base", "Answer A")

    assert semantic_cache.get("near miss") == (None, None)
    assert semantic_cache.get("other") == (None, None)


def test_similar_question_is_stored_once(make_cache):
    semantic_cache = make_cache()
    semantic_cache.put("base", "Answer A")
    semantic_cache.put("close", "Answer B")

    assert semantic_cache.stats()["questions"] == ["base"]


def test_entries_expire_after_seven_days(make_cache, clock):
    semantic_cache = make_cache()
    semantic_cache.put("base", "Answer A")

    clock.advance(7 * DAY - 1)
    assert semantic_cache.get("base")[0] == "Answer A"

    clock.advance(2)
    assert semantic_cache.get("base") == (None, None)


def test_expired_entries_are_dropped_from_the_file(make_cache, clock, cache_path):
    semantic_cache = make_cache()
    semantic_cache.put("base", "old answer")

    clock.advance(8 * DAY)
    semantic_cache.put("other", "new answer")

    assert [e["question"] for e in json.loads(cache_path.read_text())] == ["other"]


def test_least_recently_used_entry_is_evicted_at_the_cap(make_cache, clock):
    one_hot = {f"q{i}": [1.0 if j == i else 0.0 for j in range(4)] for i in range(4)}
    semantic_cache = make_cache(one_hot, max_entries=3)
    for question in ("q0", "q1", "q2"):
        semantic_cache.put(question, f"answer {question}")
        clock.advance(1)

    semantic_cache.get("q0")  # q0 becomes the most recently used, so q1 is now the oldest
    clock.advance(1)
    semantic_cache.put("q3", "answer q3")

    assert sorted(semantic_cache.stats()["questions"]) == ["q0", "q2", "q3"]


def test_unreadable_or_old_format_file_counts_as_empty(make_cache, cache_path):
    semantic_cache = make_cache()

    cache_path.write_text("{not json")
    assert semantic_cache.get("base") == (None, None)

    # The previous format had an ISO "cached_at" and no numeric timestamps.
    old_entry = {"question": "base", "answer": "stale", "embedding": [1.0, 0.0], "cached_at": "2026-05-05T10:00:00"}
    cache_path.write_text(json.dumps([old_entry]))
    assert semantic_cache.get("base") == (None, None)

    semantic_cache.put("base", "fresh")
    assert semantic_cache.get("base")[0] == "fresh"
