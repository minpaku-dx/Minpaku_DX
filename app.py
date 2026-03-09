"""
app.py — Minpaku DX 統合サーバー（FastAPI）
LINE Webhook + Web Dashboard + Background Sync を1プロセスで実行。

ローカル:  uvicorn app:app --reload --port 8000
本番:      uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import os
import logging
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from dotenv import load_dotenv
load_dotenv()

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

from beds24 import get_access_token, send_reply
from sync_service import run_once as sync_run_once
import db

# ===== 設定 =====
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))

line_handler = WebhookHandler(CHANNEL_SECRET or "dummy-secret-for-init")
line_config = Configuration(access_token=CHANNEL_ACCESS_TOKEN or "dummy-token-for-init")
templates = Jinja2Templates(directory="templates")

logger = logging.getLogger("minpaku-dx")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 編集中ステート（user_id → message_id）
editing_state: dict[str, int] = {}


# ===== Background Scheduler =====
scheduler = BackgroundScheduler()

def _sync_job():
    """APSchedulerから呼ばれる定期同期ジョブ。"""
    try:
        sync_run_once()
    except Exception as e:
        logger.error(f"sync job error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時: スケジューラー開始
    scheduler.add_job(_sync_job, "interval", seconds=SYNC_INTERVAL, id="sync_beds24", replace_existing=True)
    scheduler.start()
    logger.info(f"Background sync started ({SYNC_INTERVAL}s interval)")
    yield
    # 終了時: スケジューラー停止
    scheduler.shutdown()

app = FastAPI(title="Minpaku DX", lifespan=lifespan)


# ===== LINE Reply ヘルパー =====
def reply_text(reply_token: str, text: str):
    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=text)])
        )


def _send_to_beds24(booking_id: int, message: str) -> bool:
    token = get_access_token()
    if not token:
        logger.error("Beds24 token failed")
        return False
    return send_reply(token, booking_id, message)


# ===== LINE Webhook =====
@app.post("/callback")
async def line_callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = (await request.body()).decode("utf-8")
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"


@line_handler.add(PostbackEvent)
def handle_postback(event):
    data = parse_qs(event.postback.data)
    action = data.get("action", [None])[0]
    pending_id = data.get("pending_id", [None])[0]
    user_id = event.source.user_id

    if not action or not pending_id:
        return

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

    if action == "approve":
        if not draft:
            reply_text(event.reply_token, "AIドラフトが見つかりませんでした。")
            return
        draft_text = draft["draft_text"]
        success = _send_to_beds24(booking_id, draft_text)
        if success:
            db.update_message_status(message_id, "sent")
            db.log_action(message_id, draft["id"], "sent", draft_text, "line")
            reply_text(event.reply_token, f"送信完了\n予約ID: {booking_id}\n\nBeds24にメッセージを送信しました。")
            logger.info(f"Approved: booking {booking_id}")
        else:
            reply_text(event.reply_token, f"送信失敗\n予約ID: {booking_id}\n\n再度お試しください。")

    elif action == "edit":
        editing_state[user_id] = message_id
        guest_msg = message.get("message", "")[:100]
        reply_text(event.reply_token,
            f"修正モード\n予約ID: {booking_id}\n\n【ゲスト】\n{guest_msg}\n\n修正した返信文をこのチャットに入力してください。")


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text
    print(f"[LINE] Message from user_id: {user_id}")

    if user_id not in editing_state:
        reply_text(event.reply_token, "未読メッセージの返信案は自動で届きます。")
        return

    message_id = editing_state.pop(user_id)
    message = db.get_message_by_id(message_id)

    if not message:
        reply_text(event.reply_token, "対象のメッセージが見つかりませんでした。")
        return

    booking_id = message["booking_id"]
    draft = db.get_draft(message_id)
    success = _send_to_beds24(booking_id, text)

    if success:
        db.update_message_status(message_id, "sent")
        db.log_action(message_id, draft["id"] if draft else None, "edited", text, "line")
        reply_text(event.reply_token, f"修正版を送信完了\n予約ID: {booking_id}\n\n【送信内容】\n{text[:200]}")
        logger.info(f"Edited & sent: booking {booking_id}")
    else:
        editing_state[user_id] = message_id
        reply_text(event.reply_token, f"送信失敗\n予約ID: {booking_id}\n\nもう一度送信文を入力してください。")


# ===== Web Dashboard =====
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


class SendRequest(BaseModel):
    messageId: int | None = None
    bookingId: int
    message: str

class SkipRequest(BaseModel):
    messageId: int | None = None


@app.get("/api/messages")
async def api_messages():
    messages = db.get_draft_ready_messages()
    cards = []
    for msg in messages:
        booking = db.get_booking(msg["booking_id"])
        thread = db.get_thread(msg["booking_id"])
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
    return {"messages": cards}


@app.post("/api/send")
async def api_send(body: SendRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="messageは必須です")

    token = get_access_token()
    if not token:
        raise HTTPException(status_code=500, detail="Beds24認証失敗")

    success = send_reply(token, body.bookingId, body.message.strip())
    if not success:
        token = get_access_token()
        success = send_reply(token, body.bookingId, body.message.strip())

    if success and body.messageId:
        draft = db.get_draft(body.messageId)
        original_draft = draft["draft_text"] if draft else ""
        action = "sent" if body.message.strip() == original_draft else "edited"
        db.update_message_status(body.messageId, "sent")
        db.log_action(body.messageId, draft["id"] if draft else None, action, body.message.strip(), "web")

    return {"ok": success}


@app.post("/api/skip")
async def api_skip(body: SkipRequest):
    if body.messageId:
        draft = db.get_draft(body.messageId)
        db.update_message_status(body.messageId, "skipped")
        db.log_action(body.messageId, draft["id"] if draft else None, "skipped", None, "web")
    return {"ok": True}


# ===== Health Check =====
@app.get("/health")
async def health():
    return {"status": "ok", "sync_interval": SYNC_INTERVAL}
