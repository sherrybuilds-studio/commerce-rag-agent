import os
import requests
from dotenv import load_dotenv
from rag.retriever import retrieve
from rag.cache import get_cached_answer, cache_answer
from shared.observability import (
    trace_conversation,
    log_cache_hit,
    log_retrieval,
    log_llm_call,
)

GERMAN_WORDS = {
    "ich", "das", "die", "der", "ein", "eine", "ist", "bin", "haben",
    "suche", "brauche", "möchte", "kaufen", "preis", "farbe", "größe",
    "bitte", "danke", "ja", "nein", "und", "oder", "für", "mit", "wie",
    "was", "wann", "wo", "kann", "kein", "keine", "mein", "meine",
    "sie", "wir", "ihr", "dieser", "diese", "welche", "welcher",
}


def detect_language(text: str) -> str:
    if any(c in text for c in "äöüÄÖÜß"):
        return "German"
    words = set(text.lower().split())
    if words & GERMAN_WORDS:
        return "German"
    return "English"


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "Missing required env var OPENROUTER_API_KEY. Please set it before starting the bot."
    )

_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_dir, "system_prompt.md"), "r") as f:
    SYSTEM_PROMPT = f.read()


def get_ai_response(customer_message, conversation_history=None, user_id="anonymous"):
    if conversation_history is None:
        conversation_history = []

    with trace_conversation(user_id, customer_message) as trace:
        # Step 1 — Check cache first (saves API costs)
        cached, similarity = get_cached_answer(customer_message)
        if cached is not None:
            log_cache_hit(trace, customer_message, cached, similarity)
            trace.update(output=cached)
            return cached

        # Step 2 — RAG retrieval
        try:
            relevant = retrieve(customer_message)
        except Exception as e:
            print(f"Retrieval error: {e}")
            relevant = []

        log_retrieval(trace, customer_message, relevant)

        product_info = "\n".join([
            f"- [{p.get('id', '')}] {p['name']}: {p['description']} | Tier: {p.get('pricing_tier', 'Luxury')}"
            for p in relevant
        ])

        lang = detect_language(customer_message)
        if lang == "German":
            lang_instruction = (
                "## LANGUAGE INSTRUCTION — MANDATORY\n"
                "The customer wrote in GERMAN. Your entire reply must be in German.\n"
                "Do NOT use any English words. Respond as a professional German-speaking "
                "sales consultant."
            )
        else:
            lang_instruction = (
                "## LANGUAGE INSTRUCTION — MANDATORY\n"
                "The customer wrote in ENGLISH. Your entire reply must be in English.\n"
                "Respond as a professional English-speaking sales consultant."
            )

        full_prompt = f"{lang_instruction}\n\n{SYSTEM_PROMPT}\n\n## Relevant Products\n{product_info}"

        messages = [{"role": "system", "content": full_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": customer_message})

        # Step 3 — Call OpenRouter
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "anthropic/claude-3.5-haiku",
                    "messages": messages,
                    "max_tokens": 300
                },
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            reply = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {})
        except Exception as e:
            print(f"AI request failed: {e}")
            return (
                "I'm sorry, I'm unable to respond right now. "
                "Please try again in a moment."
            )

        log_llm_call(trace, "anthropic/claude-3.5-haiku", messages, reply, tokens)

        # Step 4 — Cache the answer for future use
        cache_answer(customer_message, reply)

        trace.update(output=reply)
        return reply


if __name__ == "__main__":
    print("Interior Brand AI Bot — Test Mode")
    print("Type 'quit' to exit\n")
    history = []
    while True:
        user_input = input("Customer: ")
        if user_input.lower() == "quit":
            break
        reply = get_ai_response(user_input, history)
        print(f"\nBot: {reply}\n")
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
