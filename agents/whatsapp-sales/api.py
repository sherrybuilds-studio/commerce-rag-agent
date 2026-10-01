"""
Interior Brand — WhatsApp Webhook API (FastAPI)
Receives WhatsApp messages from Meta's Cloud API, answers through bot.py and replies via the Graph API.

Run from this folder: uvicorn api:app --port 5000
"""

import logging
import os

import requests
from bot import get_ai_response
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

META_TOKEN        = os.getenv("META_ACCESS_TOKEN")
META_PHONE_ID     = os.getenv("META_PHONE_NUMBER_ID")
META_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Interior Brand WhatsApp API",
    description="Webhook server for WhatsApp messages using FastAPI",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

BLOCKED_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "forget your instructions",
    "you are now",
    "system prompt",
    "reveal your prompt",
]


def sanitize_input(text: str) -> str:
    text  = text[:500]
    lower = text.lower()
    if any(pattern in lower for pattern in BLOCKED_PATTERNS):
        return "[blocked]"
    return text


def mask_number(number: str) -> str:
    """Last four digits only, so the logs hold no full customer phone numbers."""
    return "..." + number[-4:]


conversations = {}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge")
):
    """Meta calls this once to verify your webhook URL is real. The body must be the bare challenge."""
    if META_VERIFY_TOKEN and hub_mode == "subscribe" and hub_verify_token == META_VERIFY_TOKEN:
        logger.info("Webhook verified by Meta")
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/webhook")
@limiter.limit("10/minute")
def receive_message(request: Request, data: dict):
    """Meta sends every incoming WhatsApp message here."""
    try:
        entry   = data["entry"][0]
        changes = entry["changes"][0]["value"]

        if "messages" not in changes:
            return {"status": "ok"}

        message     = changes["messages"][0]
        from_number = message["from"]
        msg_type    = message["type"]

        if msg_type == "text":
            user_text = sanitize_input(message["text"]["body"])
            logger.info("Text message from %s (%d characters)", mask_number(from_number), len(user_text))

            if user_text == "[blocked]":
                logger.warning("Blocked a prompt-injection attempt from %s", mask_number(from_number))
                return {"status": "ok"}

            history = conversations.get(from_number, [])
            reply   = get_ai_response(user_text, history)

            if from_number not in conversations:
                conversations[from_number] = []
            conversations[from_number].append({"role": "user",      "content": user_text})
            conversations[from_number].append({"role": "assistant",  "content": reply})
            conversations[from_number] = conversations[from_number][-10:]

            send_message(from_number, reply)

        elif msg_type == "image":
            send_message(from_number,
                "Thank you for sharing! I've received your room photo. "
                "Could you tell me which style you're drawn to — modern, classic, or contemporary?")

    except (KeyError, IndexError) as e:
        logger.warning("Ignoring a webhook payload without the expected field %s", e)

    return {"status": "ok"}


def send_message(to: str, text: str):
    """Send a WhatsApp message via Meta Cloud API."""
    url = f"https://graph.facebook.com/v19.0/{META_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type":  "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to":   to,
        "type": "text",
        "text": {"body": text},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.ok:
        logger.info("Reply sent to %s", mask_number(to))
    else:
        logger.error("Sending to %s failed with HTTP %s: %s", mask_number(to), resp.status_code, resp.text[:300])
