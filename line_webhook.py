"""
line_webhook.py — LINE Webhookサーバー
LINEからのpostback（承認/修正）を受け取り、Beds24に返信を送信する。
起動すると ngrok トンネルが自動的に開き、外部URLが発行される。
"""
import json
import os
import requests
from urllib.parse import parse_qs

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

# ===== 設定 =====
from dotenv import load_dotenv
load_dotenv()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
BEDS24_REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

PENDING_FILE = os.path.join(os.path.dirname(__file__), "pending.json")

# Flask & LINE SDK
app = Flask(__name__)
handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# 編集中ステートを管理（user_id → pending_id）
editing_state = {}


# ===== pending.json 管理 =====
def load_pending():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_pending(data):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===== Beds24 API =====
def get_beds24_token():
    """Beds24 アクセストークンを取得する"""
    url = "https://beds24.com/api/v2/authentication/token"
    headers = {"accept": "application/json", "refreshToken": BEDS24_REFRESH_TOKEN}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("token")
    return None


def send_to_beds24(booking_id: int, message: str) -> bool:
    """Beds24にメッセージを送信する"""
    token = get_beds24_token()
    if not token:
        print("[ERROR] Beds24トークン取得失敗")
        return False

    url = "https://beds24.com/api/v2/bookings/messages"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "token": token,
    }
    payload = {
        "bookingId": booking_id,
        "message": message,
        "source": "host",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code in (200, 201):
        return True
    print(f"[ERROR] Beds24送信エラー: {resp.status_code} {resp.text}")
    return False


# ===== LINE Reply ヘルパー =====
def reply_text(reply_token: str, text: str):
    """LINEにテキスト返信する"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


# ===== Webhook エンドポイント =====
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# ===== Postback イベント（承認 / 修正ボタン） =====
@handler.add(PostbackEvent)
def handle_postback(event):
    data = parse_qs(event.postback.data)
    action = data.get("action", [None])[0]
    pending_id = data.get("pending_id", [None])[0]
    user_id = event.source.user_id

    if not action or not pending_id:
        return

    pending = load_pending()
    item = pending.get(pending_id)

    if not item:
        reply_text(event.reply_token, "⚠️ このメッセージは期限切れか、既に処理済みです。")
        return

    if item.get("status") != "pending":
        reply_text(event.reply_token, "✅ このメッセージは既に処理済みです。")
        return

    booking_id = item["booking_id"]

    # ── 承認 ──
    if action == "approve":
        ai_reply = item["ai_reply"]
        success = send_to_beds24(int(booking_id), ai_reply)

        if success:
            item["status"] = "sent"
            save_pending(pending)
            reply_text(
                event.reply_token,
                f"✅ 送信完了！\n予約ID: {booking_id}\n\nBeds24にメッセージを送信しました。",
            )
            print(f"[OK] 承認・送信完了 — 予約ID: {booking_id}")
        else:
            reply_text(
                event.reply_token,
                f"❌ 送信失敗\n予約ID: {booking_id}\n\nBeds24への送信でエラーが発生しました。再度お試しください。",
            )

    # ── 修正 ──
    elif action == "edit":
        editing_state[user_id] = pending_id
        guest_msg = item.get("guest_message", "")[:100]
        reply_text(
            event.reply_token,
            f"✏️ 修正モード\n予約ID: {booking_id}\n\n"
            f"【ゲスト】\n{guest_msg}\n\n"
            f"修正した返信文をこのチャットに入力してください。",
        )


# ===== テキストメッセージ（修正文の受信） =====
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text

    # 編集中ステートがある場合のみ処理
    if user_id not in editing_state:
        reply_text(event.reply_token, "💡 ai_reply.py を実行すると、未読メッセージの返信案が届きます。")
        return

    pending_id = editing_state.pop(user_id)
    pending = load_pending()
    item = pending.get(pending_id)

    if not item:
        reply_text(event.reply_token, "⚠️ 対象のメッセージが見つかりませんでした。")
        return

    booking_id = item["booking_id"]

    # 修正文をBeds24に送信
    success = send_to_beds24(int(booking_id), text)

    if success:
        item["status"] = "sent_edited"
        item["edited_reply"] = text
        save_pending(pending)
        reply_text(
            event.reply_token,
            f"✅ 修正版を送信完了！\n予約ID: {booking_id}\n\n"
            f"【送信内容】\n{text[:200]}",
        )
        print(f"[OK] 修正・送信完了 — 予約ID: {booking_id}")
    else:
        # 失敗した場合は編集ステートを戻す
        editing_state[user_id] = pending_id
        reply_text(
            event.reply_token,
            f"❌ 送信失敗\n予約ID: {booking_id}\n\nBeds24への送信でエラーが発生しました。もう一度送信文を入力してください。",
        )


# ===== サーバー起動 =====
if __name__ == "__main__":
    PORT = 5000

    # cloudflared トンネルを開く
    import subprocess
    import threading
    import re
    import time

    def start_cloudflared():
        """cloudflared を起動し、公開URLを取得して表示する"""
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            match = re.search(r"(https://[a-z0-9\-]+\.trycloudflare\.com)", line)
            if match:
                public_url = match.group(1)
                print(f"\n{'='*60}")
                print(f"  LINE Webhook サーバー起動")
                print(f"  Tunnel URL: {public_url}")
                print(f"  Webhook URL: {public_url}/callback")
                print(f"{'='*60}")
                print(f"\n  ↑ このWebhook URLを LINE Developers Console に設定してください。")
                print(f"  設定場所: Messaging API → Webhook URL\n")

    tunnel_thread = threading.Thread(target=start_cloudflared, daemon=True)
    tunnel_thread.start()
    time.sleep(3)

    app.run(port=PORT, debug=False)
