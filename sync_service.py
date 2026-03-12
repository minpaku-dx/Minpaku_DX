"""
sync_service.py — Beds24→DB同期サービス
Beds24からメッセージ取得 → DB保存 → AI生成 → LINE通知

ai_reply.py の後継。全自動化の中核。

使い方:
  python sync_service.py                        # ワンショット
  python sync_service.py --poll --interval 300  # 5分間隔で常駐
"""
import argparse
import logging
import time
from datetime import datetime, timedelta, timezone

from beds24 import (
    get_access_token,
    get_unread_guest_messages,
    get_message_thread,
    get_booking_details,
    get_bookings_by_date_range,
    get_bookings_by_checkout_range,
)
from ai_engine import generate_reply, generate_proactive_message, AI_MODEL
from line_notify import send_line_message, send_proactive_line_message
import db

# Push notification (graceful import — works even if Firebase not configured)
try:
    from push_notify import send_push_notification
    _push_available = True
except Exception:
    _push_available = False

# プロアクティブメッセージの設定
PROACTIVE_CHECKIN_DAYS_BEFORE = 2  # チェックインの何日前にウェルカム送信
JST = timezone(timedelta(hours=9))

logger = logging.getLogger("minpaku-dx.sync")


def sync_messages(token: str) -> list[dict]:
    """
    Beds24から未読ゲストメッセージを取得し、DBに新着のみ保存する。
    Returns: 新着メッセージのリスト（DB上のdict）
    """
    raw_messages = get_unread_guest_messages(token)
    new_messages = []

    for msg in raw_messages:
        beds24_id = msg.get("id")
        if not beds24_id:
            continue

        msg_id, is_new = db.upsert_message(
            beds24_message_id=beds24_id,
            booking_id=msg["bookingId"],
            property_id=msg.get("propertyId"),
            source=msg.get("source", "guest"),
            message=msg.get("message", ""),
            sent_at=msg.get("time", ""),
            is_read=msg.get("read", False),
        )

        if is_new:
            new_messages.append(db.get_message_by_id(msg_id))

    return new_messages


def sync_thread_to_db(token: str, booking_id: int) -> None:
    """予約IDの会話スレッド全件をDBに同期する。"""
    thread = get_message_thread(token, booking_id)
    for msg in thread:
        beds24_id = msg.get("id")
        if not beds24_id:
            continue
        db.upsert_message(
            beds24_message_id=beds24_id,
            booking_id=msg["bookingId"],
            property_id=msg.get("propertyId"),
            source=msg.get("source", ""),
            message=msg.get("message", ""),
            sent_at=msg.get("time", ""),
            is_read=msg.get("read", False),
        )


def sync_booking_to_db(token: str, booking_id: int) -> dict:
    """予約情報をBeds24から取得してDBに保存する。返り値はbooking dict。"""
    info = get_booking_details(token, booking_id)
    if info:
        db.upsert_booking(
            beds24_booking_id=booking_id,
            property_id=info.get("propertyId"),
            guest_name=info.get("guestName", "不明"),
            check_in=info.get("checkIn", ""),
            check_out=info.get("checkOut", ""),
            property_name=info.get("propertyName", ""),
            num_adult=info.get("numAdult", 0),
            num_child=info.get("numChild", 0),
            guest_country=info.get("guestCountry", ""),
            guest_language=info.get("guestLanguage", ""),
            guest_arrival_time=info.get("guestArrivalTime", ""),
            guest_comments=info.get("guestComments", ""),
        )
    return info


def generate_and_save_draft(message: dict, token: str) -> str:
    """
    1件のゲストメッセージに対してAIドラフトを生成し、DBに保存する。
    message.status を 'draft_ready' に更新する。
    Returns: ドラフトテキスト
    """
    msg_id = message["id"]
    booking_id = message["booking_id"]
    property_id = message.get("property_id")

    # 会話スレッドをDBに同期してからDBから取得
    sync_thread_to_db(token, booking_id)
    thread = db.get_thread(booking_id)

    # 予約情報をDBに同期してからDBから取得
    booking_info = sync_booking_to_db(token, booking_id)

    # beds24.pyのスキーマに合わせてthread形式を変換
    thread_for_ai = [
        {
            "id": m["beds24_message_id"],
            "bookingId": m["booking_id"],
            "propertyId": m["property_id"],
            "message": m["message"],
            "time": m["sent_at"],
            "source": m["source"],
            "read": bool(m["is_read"]),
        }
        for m in thread
    ]

    # AI返信案を生成
    draft_text = generate_reply(
        guest_message=message["message"],
        property_id=property_id,
        thread=thread_for_ai,
        booking_info=booking_info,
    )

    # DB保存
    db.save_draft(msg_id, booking_id, draft_text, AI_MODEL)
    db.update_message_status(msg_id, "draft_ready")

    return draft_text


def build_conversation_summary(thread: list[dict], max_items: int = 5) -> str:
    """会話履歴をLINE通知用のサマリーテキストに変換する。"""
    recent = thread[-max_items:] if len(thread) > max_items else thread
    lines = []
    for m in recent:
        sender = "ゲスト" if m.get("source") == "guest" else "ホスト"
        text = m.get("message", "")[:120].replace("\n", " ")
        lines.append(f"{sender}: {text}")
    return "\n".join(lines)


def _upsert_booking_from_api(booking: dict) -> None:
    """Beds24 API応答の予約データを直接DBにupsertする（追加APIコール不要）。"""
    booking_id = booking.get("bookingId")
    if not booking_id:
        return
    db.upsert_booking(
        beds24_booking_id=booking_id,
        property_id=booking.get("propertyId"),
        guest_name=booking.get("guestName", "不明"),
        check_in=booking.get("checkIn", ""),
        check_out=booking.get("checkOut", ""),
        property_name=booking.get("propertyName", ""),
        num_adult=booking.get("numAdult", 0),
        num_child=booking.get("numChild", 0),
        guest_country=booking.get("guestCountry", ""),
        guest_language=booking.get("guestLanguage", ""),
        guest_arrival_time=booking.get("guestArrivalTime", ""),
        guest_comments=booking.get("guestComments", ""),
    )


def _process_proactive_booking(
    booking: dict, trigger_type: str, metrics: dict
) -> None:
    """1件のプロアクティブメッセージを生成→DB保存→LINE通知する。"""
    booking_id = booking.get("bookingId")
    property_id = booking.get("propertyId")

    # 予約情報をDBに保存（既取得データを使い、追加API呼び出しなし）
    _upsert_booking_from_api(booking)

    # AI生成
    try:
        draft_text = generate_proactive_message(trigger_type, booking, property_id)
        pro_id = db.save_proactive_draft(booking_id, property_id, trigger_type, draft_text, AI_MODEL)
        metrics["proactive_generated"] += 1
        logger.info("プロアクティブ生成完了: 予約 %d (%s)", booking_id, trigger_type)
    except Exception as e:
        logger.error("プロアクティブAI生成失敗 (予約 %d): %s", booking_id, e)
        metrics["proactive_errors"] += 1
        return

    # LINE通知
    try:
        send_proactive_line_message(
            proactive_id=str(pro_id),
            booking_id=str(booking_id),
            trigger_type=trigger_type,
            ai_message=draft_text,
            guest_name=booking.get("guestName", ""),
            property_name=booking.get("propertyName", ""),
            check_in=booking.get("checkIn", ""),
            check_out=booking.get("checkOut", ""),
        )
        logger.info("プロアクティブLINE通知送信完了: 予約 %d", booking_id)
    except Exception as e:
        logger.error("プロアクティブLINE通知失敗: %s", e)

    # Push notification (mobile app)
    if _push_available and property_id:
        try:
            trigger_label = "ウェルカム" if trigger_type == "pre_checkin" else "サンキュー"
            send_push_notification(
                property_id=property_id,
                message_type="proactive",
                data={
                    "title": f"{trigger_label}: {booking.get('guestName', '')}",
                    "body": draft_text[:200],
                    "extra": {
                        "booking_id": str(booking_id),
                        "trigger_type": trigger_type,
                    },
                },
            )
        except Exception as e:
            logger.error("プロアクティブプッシュ通知失敗: %s", e)


def check_proactive_triggers(token: str) -> dict:
    """プロアクティブメッセージのトリガーをチェックし、該当予約にAI生成→LINE通知。"""
    metrics = {"proactive_generated": 0, "proactive_errors": 0}
    today_jst = datetime.now(JST).date()

    # --- Pre-check-in: チェックインN日前の予約を検出 ---
    target_date = today_jst + timedelta(days=PROACTIVE_CHECKIN_DAYS_BEFORE)
    target_str = target_date.isoformat()
    logger.info("プロアクティブ: チェックイン %s の予約を検索", target_str)

    for booking in get_bookings_by_date_range(token, target_str, target_str):
        booking_id = booking.get("bookingId")
        if not booking_id:
            continue
        if db.has_proactive(booking_id, "pre_checkin"):
            continue
        if db.has_recent_conversation(booking_id, hours=48):
            logger.info("プロアクティブスキップ: 予約 %d（最近の会話あり）", booking_id)
            continue
        _process_proactive_booking(booking, "pre_checkin", metrics)

    # --- Post-checkout: チェックアウト翌日の予約を検出 ---
    yesterday = today_jst - timedelta(days=1)
    yesterday_str = yesterday.isoformat()
    logger.info("プロアクティブ: チェックアウト %s の予約を検索", yesterday_str)

    for booking in get_bookings_by_checkout_range(token, yesterday_str, yesterday_str):
        booking_id = booking.get("bookingId")
        if not booking_id:
            continue
        if db.has_proactive(booking_id, "post_checkout"):
            continue
        if db.has_recent_conversation(booking_id, hours=48):
            logger.info("プロアクティブスキップ: 予約 %d（最近の会話あり）", booking_id)
            continue
        _process_proactive_booking(booking, "post_checkout", metrics)

    return metrics


def run_once() -> dict:
    """ワンショット: Beds24同期 → AI生成 → LINE通知 → プロアクティブ。Returns metrics dict."""
    logger.info("=== sync_service 開始 ===")
    metrics = {"messages_processed": 0, "drafts_generated": 0, "line_notifications_sent": 0, "errors": 0,
               "proactive_generated": 0, "proactive_errors": 0}

    token = get_access_token()
    if not token:
        logger.error("Beds24トークン取得失敗")
        return metrics

    # Step 1: Beds24 → DB同期
    new_messages = sync_messages(token)

    # Step 1.5: unprocessedのまま残っているメッセージを再取得（AI生成失敗リトライ）
    stuck_messages = db.get_unprocessed_guest_messages()

    # 新着 + リトライ対象を統合（重複排除）
    seen_ids = set()
    all_messages = []
    for msg in new_messages + stuck_messages:
        if msg["id"] not in seen_ids:
            seen_ids.add(msg["id"])
            all_messages.append(msg)

    if not all_messages:
        logger.info("新着ゲストメッセージなし")
        # メッセージがなくてもプロアクティブチェックは実行
        try:
            pro_metrics = check_proactive_triggers(token)
            metrics["proactive_generated"] += pro_metrics.get("proactive_generated", 0)
            metrics["proactive_errors"] += pro_metrics.get("proactive_errors", 0)
        except Exception as e:
            logger.error("プロアクティブチェック失敗: %s", e)
        return metrics

    retry_count = len(all_messages) - len(new_messages)
    if retry_count > 0:
        logger.info("新着 %d 件 + リトライ %d 件を検出", len(new_messages), retry_count)
    else:
        logger.info("新着 %d 件を検出", len(new_messages))

    # Step 1.7: 同一booking_idのメッセージをグルーピングし、最新のみ処理
    # AIは全スレッドを参照するので、最新メッセージ1件でゲストの意図を網羅できる
    latest_by_booking: dict[int, dict] = {}
    grouped_older: dict[int, list[dict]] = {}
    for msg in all_messages:
        bid = msg["booking_id"]
        if bid not in latest_by_booking or msg.get("sent_at", "") > latest_by_booking[bid].get("sent_at", ""):
            if bid in latest_by_booking:
                grouped_older.setdefault(bid, []).append(latest_by_booking[bid])
            latest_by_booking[bid] = msg
        else:
            grouped_older.setdefault(bid, []).append(msg)

    skipped_count = sum(len(v) for v in grouped_older.values())
    all_messages = list(latest_by_booking.values())
    if skipped_count > 0:
        logger.info("同一予約の重複 %d 件をスキップ（最新のみ処理）", skipped_count)

    # Step 2: 各メッセージに対してAI生成 → LINE通知
    for msg in all_messages:
        booking_id = msg["booking_id"]
        logger.info("処理中: 予約ID %d", booking_id)

        # AI生成
        try:
            draft_text = generate_and_save_draft(msg, token)
        except Exception as e:
            logger.error("AI生成失敗 (予約ID %d): %s", booking_id, e)
            logger.info("→ 次回サイクルでリトライされます")
            metrics["errors"] += 1
            continue
        metrics["drafts_generated"] += 1
        logger.info("AIドラフト生成完了")

        # 同一予約の古いメッセージもdraft_readyに更新（リトライループ防止）
        for older_msg in grouped_older.get(booking_id, []):
            db.update_message_status(older_msg["id"], "draft_ready")

        # LINE通知用のデータ準備
        draft = db.get_draft(msg["id"])
        booking = db.get_booking(booking_id)
        thread = db.get_thread(booking_id)
        thread_for_summary = [
            {"source": m["source"], "message": m["message"]}
            for m in thread
        ]
        conversation_summary = build_conversation_summary(thread_for_summary)

        pending_id = str(msg["id"])
        guest_name = booking.get("guest_name", "") if booking else ""
        property_name = booking.get("property_name", "") if booking else ""

        # LINE通知
        try:
            send_line_message(
                pending_id=pending_id,
                booking_id=str(booking_id),
                guest_message=msg["message"],
                ai_reply=draft_text,
                conversation_history=conversation_summary,
                guest_name=guest_name,
                property_name=property_name,
            )
            logger.info("LINE通知送信完了")
            metrics["line_notifications_sent"] += 1
        except Exception as e:
            logger.error("LINE通知失敗: %s", e)
            metrics["errors"] += 1

        # Push notification (mobile app)
        if _push_available and msg.get("property_id"):
            try:
                send_push_notification(
                    property_id=msg["property_id"],
                    message_type="new_message",
                    data={
                        "title": f"新着メッセージ: {guest_name}" if guest_name else "新着ゲストメッセージ",
                        "body": msg["message"][:200],
                        "extra": {
                            "message_id": str(msg["id"]),
                            "booking_id": str(booking_id),
                        },
                    },
                )
            except Exception as e:
                logger.error("プッシュ通知失敗: %s", e)

    metrics["messages_processed"] = len(all_messages)

    # Step 3: プロアクティブメッセージのトリガーチェック
    try:
        pro_metrics = check_proactive_triggers(token)
        metrics["proactive_generated"] += pro_metrics.get("proactive_generated", 0)
        metrics["proactive_errors"] += pro_metrics.get("proactive_errors", 0)
    except Exception as e:
        logger.error("プロアクティブチェック失敗: %s", e)
        metrics["proactive_errors"] += 1

    logger.info("=== sync_service 完了 (%d 件処理, %d プロアクティブ生成) ===",
                len(all_messages), metrics["proactive_generated"])
    return metrics


def run_poll(interval: int):
    """定期ポーリング: interval秒ごとにrun_onceを実行"""
    logger.info("ポーリング開始 — %d秒間隔", interval)
    logger.info("終了するには Ctrl+C を押してください")

    while True:
        try:
            run_once()
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("ポーリング終了")
            break
        except Exception as e:
            logger.error("予期しないエラー: %s", e)
            time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Minpaku DX — Sync Service")
    parser.add_argument("--poll", action="store_true", help="定期ポーリングモード")
    parser.add_argument("--interval", type=int, default=300, help="ポーリング間隔（秒）")
    args = parser.parse_args()

    if args.poll:
        run_poll(args.interval)
    else:
        run_once()
