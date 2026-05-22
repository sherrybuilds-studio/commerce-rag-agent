"""
tests/eval.py — Bot Evaluation Framework
Runs 10 gold standard questions and scores the bot.
Run: python3 tests/eval.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "bot", "agents/whatsapp-sales/bot.py"
)
bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_module)
get_ai_response = bot_module.get_ai_response

TEST_CASES = [
    {
        "question": "Hello, I'm looking for a dining table for 10 people.",
        "expected_keywords": ["dining", "table", ["walnut", "oak"], "customize"],
        "description": "Dining table inquiry in English"
    },
    {
        "question": "What sofa options do you have for a large living room?",
        "expected_keywords": ["sofa", ["modular", "sectional"], ["fabric", "leather"]],
        "description": "Sofa inquiry in English"
    },
    {
        "question": "What is your most expensive or most premium product?",
        "expected_keywords": [["kitchen", "LUX-111", "artisan"], ["ultra-luxury", "luxury", "flagship"]],
        "description": "Top product inquiry"
    },
    {
        "question": "Tell me about LUX-104.",
        "expected_keywords": ["chesterfield", ["leather", "sofa"], ["oak", "walnut"]],
        "description": "SKU code lookup"
    },
    {
        "question": "How long does delivery take for custom furniture?",
        "expected_keywords": ["week", ["delivery", "lead time", "ready"], "custom"],
        "description": "Delivery time question"
    },
    {
        "question": "Can I get a discount on a full bedroom suite?",
        "expected_keywords": [["quality", "craft", "premium", "handcraft"], ["consultation", "invest"]],
        "description": "Discount objection"
    },
    {
        "question": "I need a walk-in wardrobe system for a large master bedroom.",
        "expected_keywords": ["wardrobe", ["walk-in", "LUX-109"], ["oak", "walnut"]],
        "description": "Walk-in wardrobe inquiry"
    },
    {
        "question": "Can the dimensions be customized to fit my space?",
        "expected_keywords": ["custom", ["size", "dimension", "bespoke"], ["adjust", "configur", "width"]],
        "description": "Customization question"
    },
    {
        "question": "I need a complete master bedroom suite — bed, wardrobe, everything.",
        "expected_keywords": ["bedroom", ["suite", "collection", "LUX-107"], ["wardrobe", "bed"]],
        "description": "Full bedroom suite inquiry"
    },
    {
        "question": "Ich suche einen Esstisch für 8 Personen.",
        "expected_keywords": [["esstisch", "tisch", "dining", "table"], ["holz", "wood", "walnut", "eiche"]],
        "description": "German language dining table inquiry"
    },
]


def score_response(response: str, keywords: list) -> float:
    """Check how many expected keywords appear in the response.
    A keyword entry can be a string or a list of strings (OR alternatives).
    """
    response_lower = response.lower()

    def matches(entry):
        if isinstance(entry, list):
            return any(alt.lower() in response_lower for alt in entry)
        return entry.lower() in response_lower

    matched = sum(1 for kw in keywords if matches(kw))
    return matched / len(keywords)


def run_evaluation():
    print("=" * 60)
    print("INTERIOR BRAND BOT — EVALUATION FRAMEWORK")
    print("=" * 60)

    total_score = 0
    results = []

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"Question: {test['question']}")

        response = get_ai_response(test["question"], [])
        score    = score_response(response, test["expected_keywords"])
        total_score += score

        status = "PASS" if score >= 0.5 else "FAIL"
        print(f"Response: {response[:120]}...")
        print(f"Score: {score:.0%} — {status}")
        results.append({"test": test["description"], "score": score, "status": status})

    final_score = (total_score / len(TEST_CASES)) * 100
    passed      = sum(1 for r in results if r["status"] == "PASS")

    print("\n" + "=" * 60)
    print(f"FINAL SCORE: {final_score:.1f}%")
    print(f"PASSED: {passed}/{len(TEST_CASES)}")
    print("=" * 60)

    if final_score >= 80:
        print("RESULT: PRODUCTION READY")
    elif final_score >= 60:
        print("RESULT: NEEDS IMPROVEMENT")
    else:
        print("RESULT: NOT READY — review system prompt and product catalog")


if __name__ == "__main__":
    run_evaluation()
