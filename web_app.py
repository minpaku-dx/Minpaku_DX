"""
web_app.py — Minpaku DX Web Dashboard
データソース: DB（sync_service.pyが事前に同期済み）
Run: python web_app.py
Open: http://localhost:8080
"""
import threading
from flask import Flask, render_template, request, jsonify

from beds24 import get_access_token, send_reply
import db

app = Flask(__name__)

# ── token cache (for sending only) ───────────────────────────────────────────
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


# ── routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/messages")
def api_messages():
    """DBからdraft_readyメッセージ + AIドラフトを返す。AI再生成なし。"""
    messages = db.get_draft_ready_messages()
    cards = []
    for msg in messages:
        booking = db.get_booking(msg["booking_id"])
        thread = db.get_thread(msg["booking_id"])
        # threadをフロントエンド用のフォーマットに変換
        thread_formatted = [
            {
                "id": m["beds24_message_id"],
                "bookingId": m["booking_id"],
                "propertyId": m["property_id"],
                "message": m["message"],
                "time": m.get("sent_at", ""),
                "source": m["source"],
                "read": bool(m["is_read"]),
            }
            for m in thread
        ]
        cards.append({
            "id": msg["id"],
            "bookingId": msg["booking_id"],
            "propertyId": msg.get("property_id") or 0,
            "guestText": msg["message"],
            "time": msg.get("sent_at", "")[:16].replace("T", " "),
            "guestName": booking.get("guest_name", "不明") if booking else "不明",
            "checkIn": booking.get("check_in", "") if booking else "",
            "checkOut": booking.get("check_out", "") if booking else "",
            "propertyName": booking.get("property_name", "") if booking else "",
            "draft": msg.get("draft_text", ""),
            "thread": thread_formatted,
        })
    return jsonify({"messages": cards})


@app.route("/api/send", methods=["POST"])
def api_send():
    """Beds24にメッセージ送信 + DB更新。"""
    body = request.json
    message_id = body.get("messageId")
    booking_id = body.get("bookingId")
    message_text = body.get("message", "").strip()

    if not booking_id or not message_text:
        return jsonify({"ok": False, "error": "bookingIdとmessageは必須です"}), 400

    token = get_token()
    if not token:
        return jsonify({"ok": False, "error": "認証失敗"}), 500

    success = send_reply(token, int(booking_id), message_text)
    if not success:
        invalidate_token()
        token = get_token()
        success = send_reply(token, int(booking_id), message_text)

    if success and message_id:
        msg = db.get_message_by_id(int(message_id))
        draft = db.get_draft(int(message_id))
        original_draft = draft["draft_text"] if draft else ""
        action = "sent" if message_text == original_draft else "edited"
        db.update_message_status(int(message_id), "sent")
        db.log_action(int(message_id), draft["id"] if draft else None, action, message_text, "web")

    return jsonify({"ok": success})


@app.route("/api/skip", methods=["POST"])
def api_skip():
    """メッセージをスキップ — DB更新。"""
    body = request.json
    message_id = body.get("messageId")

    if message_id:
        draft = db.get_draft(int(message_id))
        db.update_message_status(int(message_id), "skipped")
        db.log_action(int(message_id), draft["id"] if draft else None, "skipped", None, "web")

    return jsonify({"ok": True})


# ── entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Minpaku DX Dashboard")
    print("  http://localhost:8080\n")
    app.run(debug=True, port=8080)
