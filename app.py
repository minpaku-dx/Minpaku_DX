"""
app.py — Minpaku DX 統合サーバー（FastAPI）
LINE Webhook + Web Dashboard + Background Sync を1プロセスで実行。

ローカル:  uvicorn app:app --reload --port 8000
本番:      uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import os
import logging
import secrets
import time
from datetime import datetime
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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

from beds24 import get_access_token, send_reply, invalidate_token_cache
from sync_service import run_once as sync_run_once
from auth import get_current_user
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

# ===== 環境変数バリデーション =====
REQUIRED_ENV_VARS = [
    "REFRESH_TOKEN",
    "GEMINI_API_KEY",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_CHANNEL_SECRET",
    "LINE_OWNER_USER_ID",
]
_missing_env_vars = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
if _missing_env_vars:
    for var_name in _missing_env_vars:
        logger.error("必須環境変数 %s が未設定です", var_name)
    logger.error("主要機能が正常に動作しない可能性があります: %s", ", ".join(_missing_env_vars))

# 編集中ステート — DB永続化（サーバー再起動でも維持）

# ===== Dashboard Basic Auth =====
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "")

security = HTTPBasic()

# Rate limiting: IP → (failure_count, last_failure_time)
_auth_failures: dict[str, tuple[int, float]] = {}
AUTH_MAX_FAILURES = 5
AUTH_LOCKOUT_SECONDS = 60


def verify_credentials(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    """Basic Auth認証。環境変数未設定時は503、ロックアウト中は429、認証失敗は401。"""
    client_ip = request.client.host if request.client else "unknown"

    # Rate limit check
    if client_ip in _auth_failures:
        count, last_time = _auth_failures[client_ip]
        if count >= AUTH_MAX_FAILURES:
            if time.time() - last_time < AUTH_LOCKOUT_SECONDS:
                logger.warning(f"Auth lockout: {client_ip} ({count} failures)")
                raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
            else:
                del _auth_failures[client_ip]

    # Dashboard disabled if credentials not configured
    if not DASHBOARD_USER or not DASHBOARD_PASS:
        raise HTTPException(status_code=503, detail="Dashboard is disabled (credentials not configured)")

    correct_user = secrets.compare_digest(credentials.username, DASHBOARD_USER)
    correct_pass = secrets.compare_digest(credentials.password, DASHBOARD_PASS)

    if not correct_user or not correct_pass:
        # Record failure
        count, _ = _auth_failures.get(client_ip, (0, 0))
        _auth_failures[client_ip] = (count + 1, time.time())
        logger.warning(f"Auth failed: {client_ip} (attempt {count + 1})")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Clear failures on success
    _auth_failures.pop(client_ip, None)
    return credentials.username


# ===== Background Scheduler =====
scheduler = BackgroundScheduler()

# 同期ステータス追跡
_server_start_time = datetime.now().isoformat()
_sync_status: dict[str, object] = {
    "last_sync_at": None,
    "last_sync_success": None,
    "last_sync_error": None,
    "total_runs": 0,
    "total_messages_processed": 0,
    "total_drafts_generated": 0,
    "total_line_notifications_sent": 0,
    "total_errors": 0,
    "total_proactive_generated": 0,
    "total_proactive_errors": 0,
}

def _sync_job():
    """APSchedulerから呼ばれる定期同期ジョブ。"""
    try:
        metrics = sync_run_once()
        _sync_status["last_sync_at"] = datetime.now().isoformat()
        _sync_status["last_sync_success"] = True
        _sync_status["last_sync_error"] = None
        _sync_status["total_runs"] += 1
        _sync_status["total_messages_processed"] += metrics.get("messages_processed", 0)
        _sync_status["total_drafts_generated"] += metrics.get("drafts_generated", 0)
        _sync_status["total_line_notifications_sent"] += metrics.get("line_notifications_sent", 0)
        _sync_status["total_errors"] += metrics.get("errors", 0)
        _sync_status["total_proactive_generated"] += metrics.get("proactive_generated", 0)
        _sync_status["total_proactive_errors"] += metrics.get("proactive_errors", 0)
    except Exception as e:
        _sync_status["last_sync_at"] = datetime.now().isoformat()
        _sync_status["last_sync_success"] = False
        _sync_status["last_sync_error"] = str(e)
        _sync_status["total_runs"] += 1
        _sync_status["total_errors"] += 1
        logger.error("sync job error: %s", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時: スケジューラー開始
    scheduler.add_job(_sync_job, "interval", seconds=SYNC_INTERVAL, id="sync_beds24", replace_existing=True, next_run_time=datetime.now())
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

    # プロアクティブメッセージの場合（pro_プレフィックス）
    if pending_id.startswith("pro_"):
        _handle_proactive_postback(event, action, pending_id, user_id)
        return

    try:
        message_id = int(pending_id)
    except ValueError:
        reply_text(event.reply_token, "無効なメッセージIDです。")
        return
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
        db.save_editing_state(user_id, str(message_id))
        guest_msg = message.get("message", "")[:100]
        reply_text(event.reply_token,
            f"修正モード\n予約ID: {booking_id}\n\n【ゲスト】\n{guest_msg}\n\n修正した返信文をこのチャットに入力してください。")

    elif action == "skip":
        db.update_message_status(message_id, "skipped")
        db.log_action(message_id, draft["id"] if draft else None, "skipped", None, "line")
        reply_text(event.reply_token, f"スキップしました\n予約ID: {booking_id}")
        logger.info(f"Skipped: booking {booking_id}")


def _handle_proactive_postback(event, action: str, pending_id: str, user_id: str):
    """プロアクティブメッセージのpostback処理。"""
    try:
        proactive_id = int(pending_id.replace("pro_", ""))
    except ValueError:
        reply_text(event.reply_token, "無効なメッセージIDです。")
        return
    proactive = db.get_proactive_by_id(proactive_id)

    if not proactive:
        reply_text(event.reply_token, "このメッセージは期限切れか、既に処理済みです。")
        return

    if proactive["status"] != "draft_ready":
        reply_text(event.reply_token, "このメッセージは既に処理済みです。")
        return

    booking_id = proactive["beds24_booking_id"]

    if action == "approve":
        draft_text = proactive["draft_text"]
        success = _send_to_beds24(booking_id, draft_text)
        if success:
            db.update_proactive_status(proactive_id, "sent")
            trigger_label = "ウェルカム" if proactive["trigger_type"] == "pre_checkin" else "サンキュー"
            reply_text(event.reply_token, f"{trigger_label}送信完了\n予約ID: {booking_id}\n\nBeds24にメッセージを送信しました。")
            logger.info(f"Proactive approved: booking {booking_id} ({proactive['trigger_type']})")
        else:
            reply_text(event.reply_token, f"送信失敗\n予約ID: {booking_id}\n\n再度お試しください。")

    elif action == "edit":
        # editing_stateに"pro_"プレフィックス付きで保存
        db.save_editing_state(user_id, pending_id)
        reply_text(event.reply_token,
            f"修正モード（プロアクティブ）\n予約ID: {booking_id}\n\n修正したメッセージをこのチャットに入力してください。")

    elif action == "skip":
        db.update_proactive_status(proactive_id, "skipped")
        reply_text(event.reply_token, f"スキップしました\n予約ID: {booking_id}")
        logger.info(f"Proactive skipped: booking {booking_id}")


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text
    edit_target = db.get_editing_state(user_id)
    if not edit_target:
        reply_text(event.reply_token, "未読メッセージの返信案は自動で届きます。")
        return

    db.delete_editing_state(user_id)

    # プロアクティブメッセージの編集
    if isinstance(edit_target, str) and edit_target.startswith("pro_"):
        try:
            proactive_id = int(edit_target.replace("pro_", ""))
        except ValueError:
            reply_text(event.reply_token, "無効なメッセージIDです。")
            return
        proactive = db.get_proactive_by_id(proactive_id)
        if not proactive:
            reply_text(event.reply_token, "対象のメッセージが見つかりませんでした。")
            return
        booking_id = proactive["beds24_booking_id"]
        success = _send_to_beds24(booking_id, text)
        if success:
            db.update_proactive_status(proactive_id, "sent")
            reply_text(event.reply_token, f"修正版を送信完了\n予約ID: {booking_id}\n\n【送信内容】\n{text[:200]}")
            logger.info(f"Proactive edited & sent: booking {booking_id}")
        else:
            db.save_editing_state(user_id, edit_target)
            reply_text(event.reply_token, f"送信失敗\n予約ID: {booking_id}\n\nもう一度送信文を入力してください。")
        return

    # 通常メッセージの編集（edit_targetは数字文字列）
    try:
        message_id = int(edit_target)
    except ValueError:
        reply_text(event.reply_token, "無効なメッセージIDです。")
        return
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
        db.save_editing_state(user_id, str(message_id))
        reply_text(event.reply_token, f"送信失敗\n予約ID: {booking_id}\n\nもう一度送信文を入力してください。")


# ===== Web Dashboard =====
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = Depends(verify_credentials)):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/messages")
async def api_messages(user: str = Depends(verify_credentials)):
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
            "type": "reply",
        })
    # プロアクティブメッセージも含める
    proactive_msgs = db.get_draft_ready_proactive()
    for pro in proactive_msgs:
        booking = db.get_booking(pro["beds24_booking_id"])
        trigger_label = "チェックイン前ウェルカム" if pro["trigger_type"] == "pre_checkin" else "チェックアウト後サンキュー"
        cards.append({
            "id": f"pro_{pro['id']}",
            "bookingId": pro["beds24_booking_id"],
            "propertyId": pro.get("property_id") or 0,
            "guestText": "",
            "time": pro.get("created_at", "")[:16].replace("T", " "),
            "guestName": booking.get("guest_name", "不明") if booking else "不明",
            "checkIn": booking.get("check_in", "") if booking else "",
            "checkOut": booking.get("check_out", "") if booking else "",
            "propertyName": booking.get("property_name", "") if booking else "",
            "draft": pro.get("draft_text", ""),
            "thread": [],
            "type": "proactive",
            "triggerType": pro["trigger_type"],
            "triggerLabel": trigger_label,
        })

    return {"messages": cards}


class SendRequest(BaseModel):
    messageId: str | int | None = None
    bookingId: int
    message: str

class SkipRequest(BaseModel):
    messageId: str | int | None = None


@app.post("/api/send")
async def api_send(body: SendRequest, user: str = Depends(verify_credentials)):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="messageは必須です")

    token = get_access_token()
    if not token:
        raise HTTPException(status_code=500, detail="Beds24認証失敗")

    success = send_reply(token, body.bookingId, body.message.strip())
    if not success:
        invalidate_token_cache()
        token = get_access_token()
        if token:
            success = send_reply(token, body.bookingId, body.message.strip())

    msg_id = str(body.messageId) if body.messageId else ""

    if success:
        # プロアクティブメッセージの場合
        if msg_id.startswith("pro_"):
            try:
                proactive_id = int(msg_id.replace("pro_", ""))
                db.update_proactive_status(proactive_id, "sent")
            except (ValueError, Exception) as e:
                logger.error("プロアクティブステータス更新失敗: %s", e)
        elif body.messageId:
            try:
                int_id = int(body.messageId)
                draft = db.get_draft(int_id)
                original_draft = draft["draft_text"] if draft else ""
                action = "sent" if body.message.strip() == original_draft else "edited"
                db.update_message_status(int_id, "sent")
                db.log_action(int_id, draft["id"] if draft else None, action, body.message.strip(), "web")
            except (ValueError, Exception) as e:
                logger.error("メッセージステータス更新失敗: %s", e)

    return {"ok": success}


@app.post("/api/skip")
async def api_skip(body: SkipRequest, user: str = Depends(verify_credentials)):
    msg_id = str(body.messageId) if body.messageId else ""

    try:
        if msg_id.startswith("pro_"):
            proactive_id = int(msg_id.replace("pro_", ""))
            db.update_proactive_status(proactive_id, "skipped")
        elif body.messageId:
            int_id = int(body.messageId)
            draft = db.get_draft(int_id)
            db.update_message_status(int_id, "skipped")
            db.log_action(int_id, draft["id"] if draft else None, "skipped", None, "web")
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なメッセージIDです")
    return {"ok": True}


# ===== Mobile App API (Supabase Auth) =====

class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    platform: str
    app_version: str | None = None

class AppSendRequest(BaseModel):
    messageId: str | int | None = None
    bookingId: int
    message: str

class AppSkipRequest(BaseModel):
    messageId: str | int | None = None


@app.get("/api/me")
async def api_me(user: dict = Depends(get_current_user)):
    """Returns user info + their properties."""
    user_id = user["id"]
    properties = db.get_user_properties(user_id)
    settings = db.get_user_settings(user_id)
    return {
        "user": user,
        "properties": properties,
        "settings": settings,
    }


@app.get("/api/messages/history")
async def api_messages_history(
    status: str = "all",
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    """Returns processed messages for user's properties."""
    user_id = user["id"]
    properties = db.get_user_properties(user_id)
    property_ids = [p["property_id"] for p in properties]
    if not property_ids:
        return {"messages": [], "total": 0}

    status_filter = status if status in ("sent", "skipped", "draft_ready") else None
    messages = db.get_messages_history(property_ids, status_filter=status_filter, limit=limit, offset=offset)
    return {"messages": messages}


@app.get("/api/messages/{message_id}")
async def api_message_detail(message_id: int, user: dict = Depends(get_current_user)):
    """Returns full message with booking, thread, draft."""
    user_id = user["id"]
    detail = db.get_message_detail(message_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Message not found")

    # Verify user has access to this property
    msg_property_id = detail["message"].get("property_id")
    if msg_property_id:
        properties = db.get_user_properties(user_id)
        property_ids = [p["property_id"] for p in properties]
        if msg_property_id not in property_ids:
            raise HTTPException(status_code=403, detail="Access denied")

    return detail


@app.get("/api/bookings")
async def api_bookings(user: dict = Depends(get_current_user)):
    """Returns bookings for user's properties."""
    user_id = user["id"]
    properties = db.get_user_properties(user_id)
    property_ids = [p["property_id"] for p in properties]
    if not property_ids:
        return {"bookings": []}

    ph = db._PH
    placeholders = ", ".join([ph] * len(property_ids))
    with db._get_conn() as conn:
        bookings = db._fetchall(conn,
            f"SELECT * FROM bookings WHERE property_id IN ({placeholders}) ORDER BY check_in DESC",
            tuple(property_ids))
    return {"bookings": bookings}


@app.get("/api/bookings/{booking_id}")
async def api_booking_detail(booking_id: int, user: dict = Depends(get_current_user)):
    """Returns booking detail with messages."""
    user_id = user["id"]
    booking = db.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Verify user has access to this property
    if booking.get("property_id"):
        properties = db.get_user_properties(user_id)
        property_ids = [p["property_id"] for p in properties]
        if booking["property_id"] not in property_ids:
            raise HTTPException(status_code=403, detail="Access denied")

    thread = db.get_thread(booking_id)
    return {"booking": booking, "messages": thread}


@app.get("/api/properties")
async def api_properties(user: dict = Depends(get_current_user)):
    """Returns user's properties with pending message counts."""
    user_id = user["id"]
    properties = db.get_user_properties(user_id)
    property_ids = [p["property_id"] for p in properties]
    if not property_ids:
        return {"properties": []}

    result = []
    ph = db._PH
    with db._get_conn() as conn:
        for prop in properties:
            pid = prop["property_id"]
            # Get pending count
            count_row = db._fetchone(conn,
                f"SELECT COUNT(*) as cnt FROM messages WHERE property_id = {ph} AND status = 'draft_ready'",
                (pid,))
            pending_count = count_row["cnt"] if count_row else 0

            # Get property name from a recent booking
            name_row = db._fetchone(conn,
                f"SELECT property_name FROM bookings WHERE property_id = {ph} LIMIT 1",
                (pid,))
            property_name = name_row["property_name"] if name_row else ""

            result.append({
                "property_id": pid,
                "permission": prop["permission"],
                "property_name": property_name,
                "pending_count": pending_count,
            })

    return {"properties": result}


@app.post("/api/devices")
async def api_register_device(body: DeviceRegisterRequest, user: dict = Depends(get_current_user)):
    """Register a device for push notifications."""
    db.upsert_device(user["id"], body.fcm_token, body.platform, body.app_version)
    return {"ok": True}


@app.delete("/api/devices/{fcm_token}")
async def api_unregister_device(fcm_token: str, user: dict = Depends(get_current_user)):
    """Remove a device from push notifications (only own devices)."""
    db.delete_device(fcm_token, user_id=user["sub"])
    return {"ok": True}


@app.post("/api/app/send")
async def api_app_send(body: AppSendRequest, user: dict = Depends(get_current_user)):
    """Send message via Beds24 (Supabase auth version). Same logic as /api/send."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="messageは必須です")

    token = get_access_token()
    if not token:
        raise HTTPException(status_code=500, detail="Beds24認証失敗")

    success = send_reply(token, body.bookingId, body.message.strip())
    if not success:
        invalidate_token_cache()
        token = get_access_token()
        if token:
            success = send_reply(token, body.bookingId, body.message.strip())

    msg_id = str(body.messageId) if body.messageId else ""

    if success:
        if msg_id.startswith("pro_"):
            try:
                proactive_id = int(msg_id.replace("pro_", ""))
                db.update_proactive_status(proactive_id, "sent")
            except (ValueError, Exception) as e:
                logger.error("プロアクティブステータス更新失敗: %s", e)
        elif body.messageId:
            try:
                int_id = int(body.messageId)
                draft = db.get_draft(int_id)
                original_draft = draft["draft_text"] if draft else ""
                action = "sent" if body.message.strip() == original_draft else "edited"
                db.update_message_status(int_id, "sent")
                db.log_action(int_id, draft["id"] if draft else None, action, body.message.strip(), "app")
            except (ValueError, Exception) as e:
                logger.error("メッセージステータス更新失敗: %s", e)

    return {"ok": success}


@app.post("/api/app/skip")
async def api_app_skip(body: AppSkipRequest, user: dict = Depends(get_current_user)):
    """Skip message (Supabase auth version). Same logic as /api/skip."""
    msg_id = str(body.messageId) if body.messageId else ""

    try:
        if msg_id.startswith("pro_"):
            proactive_id = int(msg_id.replace("pro_", ""))
            db.update_proactive_status(proactive_id, "skipped")
        elif body.messageId:
            int_id = int(body.messageId)
            draft = db.get_draft(int_id)
            db.update_message_status(int_id, "skipped")
            db.log_action(int_id, draft["id"] if draft else None, "skipped", None, "app")
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なメッセージIDです")
    return {"ok": True}


# ===== Health Check =====
@app.get("/health")
async def health():
    try:
        db_ok, db_msg = db.check_health()
    except Exception as e:
        db_ok, db_msg = False, str(e)

    is_healthy = db_ok and not _missing_env_vars
    return {
        "status": "ok" if is_healthy else "degraded",
        "server_start_time": _server_start_time,
        "sync_interval": SYNC_INTERVAL,
        "db": {"ok": db_ok, "message": db_msg},
        "missing_env_vars": _missing_env_vars,
        "sync": _sync_status,
    }

