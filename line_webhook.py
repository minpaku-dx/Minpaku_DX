"""
line_webhook.py — LINE Webhookサーバー
LINEからのpostback（承認/修正）を受け取り、Beds24に返信を送信する。
データソース: DB（sync_service.pyが事前に同期済み）
"""
import os
import re
import subprocess
import threading
import time
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

from dotenv import load_dotenv
load_dotenv()

from beds24 import get_access_token, send_reply
import db

# ===== 設定 =====
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# Flask & LINE SDK
app = Flask(__name__)
handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# 編集中ステートを管理（user_id → message_id）
editing_state = {}


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


def _send_to_beds24(booking_id: int, message: str) -> bool:
    """Beds24にメッセージを送信する"""
    token = get_access_token()
    if not token:
        print("[ERROR] Beds24トークン取得失敗")
        return False
    return send_reply(token, booking_id, message)


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

    # pending_id = DB上のmessage_id
    message_id = int(pending_id)
    message = db.get_message_by_id(message_id)

    if not message:
        reply_text(event.reply_token, "このメッセージは期限切れか、既に処理済みです。")
        return

    if message["status"] != "draft_ready":
        reply_text(event.reply_token, "このメッセージは既に処理済みです。")
        return

    booking_id = message["booking_id"]
    draft = db.get_draft(message_id)

    # ── 承認 ──
    if action == "approve":
        if not draft:
            reply_text(event.reply_token, "AIドラフトが見つかりませんでした。")
            return

        draft_text = draft["draft_text"]
        success = _send_to_beds24(booking_id, draft_text)

        if success:
            db.update_message_status(message_id, "sent")
            db.log_action(message_id, draft["id"], "sent", draft_text, "line")
            reply_text(
                event.reply_token,
                f"送信完了\n予約ID: {booking_id}\n\nBeds24にメッセージを送信しました。",
            )
            print(f"[OK] 承認・送信完了 — 予約ID: {booking_id}")
        else:
            reply_text(
                event.reply_token,
                f"送信失敗\n予約ID: {booking_id}\n\nBeds24への送信でエラーが発生しました。再度お試しください。",
            )

    # ── 修正 ──
    elif action == "edit":
        editing_state[user_id] = message_id
        guest_msg = message.get("message", "")[:100]
        reply_text(
            event.reply_token,
            f"修正モード\n予約ID: {booking_id}\n\n"
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
        reply_text(event.reply_token, "sync_service.py が稼働中であれば、未読メッセージの返信案が自動で届きます。")
        return

    message_id = editing_state.pop(user_id)
    message = db.get_message_by_id(message_id)

    if not message:
        reply_text(event.reply_token, "対象のメッセージが見つかりませんでした。")
        return

    booking_id = message["booking_id"]
    draft = db.get_draft(message_id)

    # 修正文をBeds24に送信
    success = _send_to_beds24(booking_id, text)

    if success:
        db.update_message_status(message_id, "sent")
        db.log_action(message_id, draft["id"] if draft else None, "edited", text, "line")
        reply_text(
            event.reply_token,
            f"修正版を送信完了\n予約ID: {booking_id}\n\n"
            f"【送信内容】\n{text[:200]}",
        )
        print(f"[OK] 修正・送信完了 — 予約ID: {booking_id}")
    else:
        # 失敗した場合は編集ステートを戻す
        editing_state[user_id] = message_id
        reply_text(
            event.reply_token,
            f"送信失敗\n予約ID: {booking_id}\n\nBeds24への送信でエラーが発生しました。もう一度送信文を入力してください。",
        )


# ===== サーバー起動 =====
if __name__ == "__main__":
    PORT = 5000

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
                print(f"\n  このWebhook URLを LINE Developers Console に設定してください。")
                print(f"  設定場所: Messaging API → Webhook URL\n")

    tunnel_thread = threading.Thread(target=start_cloudflared, daemon=True)
    tunnel_thread.start()
    time.sleep(3)

    app.run(port=PORT, debug=False)
