"""
web_app.py — Agent 1 (Frontend)
Minpaku DX Web Dashboard — localhost UI for Human-in-the-Loop message approval.
Run: python web_app.py
Open: http://localhost:5000
"""

import threading
from flask import Flask, render_template, request, jsonify

from beds24 import (
    get_access_token,
    get_unread_guest_messages,
    get_message_thread,
    get_booking_details,
    send_reply,
)
from ai_engine import generate_reply

app = Flask(__name__)

# ── token cache (refresh once per session) ──────────────────────────────────
_token_cache = {"token": None}
_token_lock = threading.Lock()

def get_token():
    with _token_lock:
        if not _token_cache["token"]:
            _token_cache["token"] = get_access_token()
        return _token_cache["token"]

def invalidate_token():
    with _token_lock:
        _token_cache["token"] = None


# ── helpers ─────────────────────────────────────────────────────────────────

def build_message_card(msg, token):
    """Fetch full context for one message and generate AI draft."""
    booking_id  = msg["bookingId"]
    property_id = msg.get("propertyId") or 0
    thread      = get_message_thread(token, booking_id)
    booking     = get_booking_details(token, booking_id)
    draft       = generate_reply(
        guest_message=msg["message"],
        property_id=property_id,
        thread=thread,
        booking_info=booking,
    )
    return {
        "id":          msg["id"],
        "bookingId":   booking_id,
        "propertyId":  property_id,
        "guestText":   msg["message"],
        "time":        msg.get("time", "")[:16].replace("T", " "),
        "guestName":   booking.get("guestName", "不明"),
        "checkIn":     booking.get("checkIn", ""),
        "checkOut":    booking.get("checkOut", ""),
        "propertyName":booking.get("propertyName", ""),
        "draft":       draft,
        "thread":      thread,
    }


# ── routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/messages")
def api_messages():
    """Fetch unread messages + generate AI drafts. Called by JS on load/refresh."""
    token = get_token()
    if not token:
        return jsonify({"error": "Beds24認証失敗"}), 500

    raw = get_unread_guest_messages(token)
    cards = []
    for msg in raw:
        try:
            cards.append(build_message_card(msg, token))
        except Exception as e:
            cards.append({
                "id": msg.get("id"),
                "bookingId": msg.get("bookingId"),
                "error": str(e),
                "guestText": msg.get("message", ""),
            })
    return jsonify({"messages": cards})


@app.route("/api/send", methods=["POST"])
def api_send():
    """Send a reply to Beds24."""
    body      = request.json
    booking_id = body.get("bookingId")
    message    = body.get("message", "").strip()

    if not booking_id or not message:
        return jsonify({"ok": False, "error": "bookingIdとmessageは必須です"}), 400

    token = get_token()
    if not token:
        return jsonify({"ok": False, "error": "認証失敗"}), 500

    success = send_reply(token, int(booking_id), message)
    if not success:
        # Token might be stale — invalidate and retry once
        invalidate_token()
        token = get_token()
        success = send_reply(token, int(booking_id), message)

    return jsonify({"ok": success})


@app.route("/api/skip", methods=["POST"])
def api_skip():
    """Client-side skip — nothing to do server-side, just ack."""
    return jsonify({"ok": True})


# ── entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Minpaku DX Dashboard")
    print("  http://localhost:8080\n")
    app.run(debug=True, port=8080)
