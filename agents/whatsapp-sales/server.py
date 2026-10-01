"""
Interior Brand — WhatsApp Webhook Server
Receives messages from Meta Cloud API and passes to bot.
Run: python3 agents/whatsapp-sales/server.py
"""

import logging
import os

import requests
from bot import get_ai_response
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

META_TOKEN        = os.getenv("META_ACCESS_TOKEN")
META_PHONE_ID     = os.getenv("META_PHONE_NUMBER_ID")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")

app = Flask(__name__)

conversations = {}


def mask_number(number: str) -> str:
    """Last four digits only, so the logs hold no full customer phone numbers."""
    return "..." + number[-4:]


@app.route("/webhook", methods=["GET"])
def verify():
    """Meta calls this once to verify your webhook URL is real."""
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        logger.info("Webhook verified by Meta")
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    """Meta sends every incoming WhatsApp message here."""
    data = request.get_json()

    try:
        entry   = data["entry"][0]
        changes = entry["changes"][0]["value"]

        if "messages" not in changes:
            return jsonify({"status": "ok"}), 200

        message     = changes["messages"][0]
        from_number = message["from"]
        msg_type    = message["type"]

        if msg_type == "text":
            user_text = message["text"]["body"]
            logger.info("Text message from %s (%d characters)", mask_number(from_number), len(user_text))

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

    return jsonify({"status": "ok"}), 200


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


if __name__ == "__main__":
    print("Interior Brand Webhook Server running on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
