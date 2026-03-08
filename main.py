"""
main.py — Agent 1 (Frontend) — Entry Point
Minpaku DX: AI-assisted reply system for minpaku operators.

Wires backend (beds24.py, ai_engine.py) to frontend (cli.py).
Runs in two modes:
  - Single run:  python main.py
  - Poll mode:   python main.py --poll
"""

import sys
import time
import os
import argparse

# ─────────────────────────────────────────────
#  BACKEND IMPORT — with mock fallback
#  Remove mock stubs once Agent 2 delivers beds24.py / ai_engine.py
# ─────────────────────────────────────────────

MOCK_MODE = False

try:
    from beds24 import (
        get_access_token,
        get_unread_guest_messages,
        get_message_thread,
        get_booking_details,
        send_reply,
    )
    from ai_engine import generate_reply
    print("  [OK] Backend modules loaded.")
except ImportError:
    MOCK_MODE = True
    print("  [MOCK] Backend not ready. Running with sample data.")

    # ── MOCK DATA ──────────────────────────────────────────────────────────────
    _MOCK_TOKEN = "mock-token"

    _MOCK_MESSAGES = [
        {
            "id": 1001,
            "bookingId": 73705556,
            "propertyId": 206100,
            "message": "What is the alarm device near the TV for? It keeps going off when we sneeze.",
            "time": "2026-03-07T10:22:00Z",
            "source": "guest",
            "read": False,
        },
        {
            "id": 1002,
            "bookingId": 79900935,
            "propertyId": 206100,
            "message": "はい。できます。",
            "time": "2026-03-07T11:05:00Z",
            "source": "guest",
            "read": False,
        },
    ]

    _MOCK_THREAD = {
        73705556: [
            {"id": 990, "bookingId": 73705556, "propertyId": 206100,
             "message": "※This is an automated message.※ Please check in guide: https://axsp.me/xxx",
             "time": "2026-03-06T09:00:00Z", "source": "host", "read": True},
            {"id": 1001, "bookingId": 73705556, "propertyId": 206100,
             "message": "What is the alarm device near the TV for? It keeps going off when we sneeze.",
             "time": "2026-03-07T10:22:00Z", "source": "guest", "read": False},
        ],
        79900935: [
            {"id": 1002, "bookingId": 79900935, "propertyId": 206100,
             "message": "はい。できます。",
             "time": "2026-03-07T11:05:00Z", "source": "guest", "read": False},
        ],
    }

    _MOCK_BOOKING = {
        73705556: {
            "guestName": "Jeanne Yao",
            "checkIn": "2026-03-07",
            "checkOut": "2026-03-09",
            "propertyId": 206100,
            "propertyName": "平井戸建",
        },
        79900935: {
            "guestName": "Seki Haruka",
            "checkIn": "2026-03-07",
            "checkOut": "2026-03-08",
            "propertyId": 206100,
            "propertyName": "平井戸建",
        },
    }

    def get_access_token():
        return _MOCK_TOKEN

    def get_unread_guest_messages(token):
        return _MOCK_MESSAGES

    def get_message_thread(token, booking_id):
        return _MOCK_THREAD.get(booking_id, [])

    def get_booking_details(token, booking_id):
        return _MOCK_BOOKING.get(booking_id, {
            "guestName": "不明", "checkIn": "不明", "checkOut": "不明",
            "propertyId": 0, "propertyName": "不明",
        })

    def send_reply(token, booking_id, message):
        print(f"  [MOCK] send_reply called — booking {booking_id}")
        print(f"  [MOCK] message: {message[:80]}")
        return True  # Simulate success

    def generate_reply(guest_message, property_id, thread, booking_info):
        return (
            f"（モック返信）\n"
            f"この返信はモックデータです。AI Engineが接続されると本物の返信が生成されます。\n\n"
            f"ゲストのメッセージ「{guest_message[:40]}...」を受け取りました。\n\n"
            f"民泊スタッフ一同"
        )
    # ────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────
#  macOS NOTIFICATION
# ─────────────────────────────────────────────

def notify_macos(title, message):
    """Show a macOS notification center popup."""
    safe_title = title.replace("'", "\\'")
    safe_message = message.replace("'", "\\'")
    os.system(
        f"osascript -e 'display notification \"{safe_message}\" with title \"{safe_title}\"'"
    )


# ─────────────────────────────────────────────
#  CORE LOGIC
# ─────────────────────────────────────────────

def run_once():
    """Single pass: fetch unread messages and run CLI session."""
    from cli import run_session

    token = get_access_token()
    if not token:
        print("\n  [ERROR] Beds24認証失敗。.env の REFRESH_TOKEN を確認してください。")
        sys.exit(1)

    run_session(
        token=token,
        get_unread_fn=get_unread_guest_messages,
        get_thread_fn=get_message_thread,
        get_booking_fn=get_booking_details,
        generate_fn=generate_reply,
        send_fn=send_reply,
    )


def run_poll(interval_seconds=300):
    """
    Poll mode: check for new messages every N seconds.
    Sends macOS notification when new messages are found.
    Tracks seen message IDs to avoid duplicate alerts.
    """
    seen_ids = set()

    print(f"\n  ポーリング開始 — {interval_seconds // 60}分ごとに未読チェックします。")
    print("  終了するには Ctrl+C を押してください。\n")

    while True:
        try:
            token = get_access_token()
            if not token:
                print("  [WARNING] トークン取得失敗。再試行します...")
                time.sleep(30)
                continue

            messages = get_unread_guest_messages(token)

            # Find truly new messages (not seen in this session)
            new_messages = [m for m in messages if m.get("id") not in seen_ids]

            if new_messages:
                count = len(new_messages)
                print(f"\n  {count} 件の新着メッセージを検出しました。")
                notify_macos(
                    "Minpaku DX — 新着メッセージ",
                    f"未読ゲストメッセージが {count} 件あります。"
                )
                # Mark all current unread IDs as seen (they'll be handled in session)
                for m in messages:
                    seen_ids.add(m.get("id"))

                # Drop into interactive session
                from cli import run_session
                run_session(
                    token=token,
                    get_unread_fn=lambda t: messages,  # reuse already-fetched list
                    get_thread_fn=get_message_thread,
                    get_booking_fn=get_booking_details,
                    generate_fn=generate_reply,
                    send_fn=send_reply,
                )
            else:
                # Update seen_ids silently
                for m in messages:
                    seen_ids.add(m.get("id"))
                print(f"  [{_now()}] 未読なし。{interval_seconds // 60}分後に再チェックします。", end="\r")

            time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\n  ポーリング終了。")
            break


def _now():
    import datetime
    return datetime.datetime.now().strftime("%H:%M:%S")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Minpaku DX — AI返信アシスタント"
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="ポーリングモードで起動（バックグラウンドで定期チェック）"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="ポーリング間隔（秒）。デフォルト: 300秒（5分）"
    )
    args = parser.parse_args()

    if MOCK_MODE:
        print("  ※ モックモードで動作中 — beds24.py / ai_engine.py を作成すると本番モードになります。\n")

    if args.poll:
        run_poll(interval_seconds=args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
