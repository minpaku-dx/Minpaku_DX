"""
ai_reply.py — LINE通知フロー（オーケストレーター）
未読メッセージ取得→AI返信生成→LINE通知→承認待ち保存

全てのAPI呼び出し・AI生成は beds24.py / ai_engine.py に委譲する。
"""
import uuid
from beds24 import (
    get_access_token,
    get_unread_guest_messages,
    get_message_thread,
    get_booking_details,
)
from ai_engine import generate_reply
from line_notify import send_line_message
from pending_store import load_pending, save_pending


def build_conversation_summary(thread: list[dict], max_items: int = 5) -> str:
    """
    メッセージスレッドから直近max_items件を
    'ゲスト/ホスト: メッセージ' 形式のテキストに変換する。
    LINE通知の表示用（ai_engine.pyの_format_threadとは別の用途）。
    """
    recent = thread[-max_items:] if len(thread) > max_items else thread
    lines = []
    for m in recent:
        sender = "ゲスト" if m.get("source") == "guest" else "ホスト"
        text = m.get("message", "")[:120].replace("\n", " ")
        lines.append(f"{sender}: {text}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("=== AI返信アシスタント 起動 ===\n")

    # Step1: Beds24 アクセストークン取得
    token = get_access_token()
    if not token:
        print("認証エラー: Beds24トークンを取得できませんでした。")
        exit()

    # Step2: 未読ゲストメッセージを取得
    messages = get_unread_guest_messages(token)

    if not messages:
        print("未読のゲストメッセージはありません。")
        exit()

    print(f"未読ゲストメッセージが {len(messages)} 件あります。\n")

    # 承認待ちデータを読み込み
    pending = load_pending()

    # 予約IDごとにスレッドをキャッシュ
    thread_cache = {}

    # Step3: 各メッセージに対して履歴取得 → AI返信案生成 → LINE通知
    for i, msg in enumerate(messages, 1):
        booking_id = msg.get("bookingId", "不明")
        guest_text = msg.get("message", "（本文なし）")
        property_id = msg.get("propertyId")

        print(f"{'='*60}")
        print(f"【 {i}件目 】予約ID: {booking_id}")

        # Step3a: メッセージスレッド（履歴）を取得
        if booking_id not in thread_cache:
            thread_cache[booking_id] = get_message_thread(token, booking_id)
        thread = thread_cache[booking_id]

        # Step3b: 予約詳細を取得
        booking_info = get_booking_details(token, booking_id)

        # 表示用の会話サマリー
        conversation_summary = build_conversation_summary(thread, max_items=5)
        print(f"\n▼ 会話履歴")
        print(conversation_summary)

        # Step3c: AI返信を生成（beds24.pyと同じスキーマのthread + booking_infoを渡す）
        print(f"\n▼ AI返信案（Gemini生成）")
        reply = generate_reply(guest_text, property_id, thread, booking_info)
        print(reply)

        # Step4: pending に承認待ちデータを保存
        pending_id = str(uuid.uuid4())[:8]
        pending[pending_id] = {
            "booking_id": booking_id,
            "guest_message": guest_text,
            "ai_reply": reply,
            "conversation_history": conversation_summary,
            "status": "pending",
        }

        # Step5: LINEにFlex Messageを送信
        send_line_message(pending_id, str(booking_id), guest_text, reply, conversation_summary)
        print("  → LINE通知を送信しました\n")

    # 承認待ちデータを保存
    save_pending(pending)
    print(f"{len(messages)} 件の承認待ちデータを pending.json に保存しました。")
