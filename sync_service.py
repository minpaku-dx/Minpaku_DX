"""
sync_service.py — Beds24→DB同期サービス
Beds24からメッセージ取得 → DB保存 → AI生成 → LINE通知

ai_reply.py の後継。全自動化の中核。

使い方:
  python sync_service.py                        # ワンショット
  python sync_service.py --poll --interval 300  # 5分間隔で常駐
"""
import argparse
import time
import datetime

from beds24 import (
    get_access_token,
    get_unread_guest_messages,
    get_message_thread,
    get_booking_details,
)
from ai_engine import generate_reply
from line_notify import send_line_message
import db


AI_MODEL = "gemini-2.0-flash-lite"


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


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


def run_once():
    """ワンショット: Beds24同期 → AI生成 → LINE通知"""
    print(f"[{_now()}] === sync_service 開始 ===")

    token = get_access_token()
    if not token:
        print(f"[{_now()}] [ERROR] Beds24トークン取得失敗")
        return

    # Step 1: Beds24 → DB同期
    new_messages = sync_messages(token)

    if not new_messages:
        print(f"[{_now()}] 新着ゲストメッセージなし")
        return

    print(f"[{_now()}] 新着 {len(new_messages)} 件を検出")

    # Step 2: 各メッセージに対してAI生成 → LINE通知
    for msg in new_messages:
        booking_id = msg["booking_id"]
        print(f"[{_now()}] 処理中: 予約ID {booking_id}")

        # AI生成
        draft_text = generate_and_save_draft(msg, token)
        print(f"[{_now()}]   AIドラフト生成完了")

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
            print(f"[{_now()}]   LINE通知送信完了")
        except Exception as e:
            print(f"[{_now()}]   [ERROR] LINE通知失敗: {e}")

    print(f"[{_now()}] === sync_service 完了 ({len(new_messages)} 件処理) ===")


def run_poll(interval: int):
    """定期ポーリング: interval秒ごとにrun_onceを実行"""
    print(f"[{_now()}] ポーリング開始 — {interval}秒間隔")
    print(f"[{_now()}] 終了するには Ctrl+C を押してください\n")

    while True:
        try:
            run_once()
            time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n[{_now()}] ポーリング終了")
            break
        except Exception as e:
            print(f"[{_now()}] [ERROR] {e}")
            time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minpaku DX — Sync Service")
    parser.add_argument("--poll", action="store_true", help="定期ポーリングモード")
    parser.add_argument("--interval", type=int, default=300, help="ポーリング間隔（秒）")
    args = parser.parse_args()

    if args.poll:
        run_poll(args.interval)
    else:
        run_once()
