"""
cli.py — Agent 1 (Frontend)
Human-in-the-Loop CLI for Minpaku DX
Handles display, user input, approval flow, and edit mode.
Does NOT call Beds24 or Gemini directly — those come from beds24.py / ai_engine.py.
"""

import os
import sys
import textwrap


# ─────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────

WIDTH = 62

def _line(char="─"):
    print(char * WIDTH)

def _header(text):
    print(f"\n{'═' * WIDTH}")
    print(f"  {text}")
    print(f"{'═' * WIDTH}")

def _section(label):
    print(f"\n  \033[1m{label}\033[0m")
    print("  " + "─" * (WIDTH - 2))

def _wrap(text, indent=4):
    """Word-wrap long text with indentation."""
    lines = text.strip().split("\n")
    for line in lines:
        if line.strip() == "":
            print()
            continue
        for wrapped in textwrap.wrap(line, WIDTH - indent) or [""]:
            print(" " * indent + wrapped)

def _badge(label, value, color_code=""):
    reset = "\033[0m" if color_code else ""
    print(f"  {color_code}{label}:\033[0m  {value}{reset}" if color_code else f"  {label}:  {value}")


# ─────────────────────────────────────────────
#  BOOKING INFO DISPLAY
# ─────────────────────────────────────────────

def display_booking_header(index, total, booking_info, msg):
    """Print the top section: booking + guest info."""
    _header(f"メッセージ {index}/{total}")
    _badge("予約ID", msg.get("bookingId", "不明"))
    _badge("物件", booking_info.get("propertyName", "不明"))
    _badge("ゲスト", booking_info.get("guestName", "不明"), "\033[96m")
    _badge("チェックイン", booking_info.get("checkIn", "不明"))
    _badge("チェックアウト", booking_info.get("checkOut", "不明"))
    _badge("受信時刻", msg.get("time", "")[:16].replace("T", " "))


def display_thread(thread):
    """Print the conversation history above the latest message."""
    if not thread:
        return
    _section("会話履歴")
    # Show up to last 6 messages for context (excluding the unread one)
    history = [m for m in thread if not (m.get("source") == "guest" and not m.get("read"))]
    for m in history[-6:]:
        sender_label = "\033[93mゲスト\033[0m" if m.get("source") == "guest" else "\033[90mホスト\033[0m"
        time_str = m.get("time", "")[:16].replace("T", " ")
        print(f"\n  [{time_str}] {sender_label}")
        _wrap(m.get("message", ""), indent=4)


def display_guest_message(msg):
    """Print the unread guest message (highlighted)."""
    _section("ゲストの最新メッセージ \033[91m[未読]\033[0m")
    _wrap(msg.get("message", "（メッセージなし）"), indent=4)


def display_ai_draft(draft):
    """Print the AI-generated reply draft."""
    _section("AI返信案")
    _wrap(draft, indent=4)


# ─────────────────────────────────────────────
#  APPROVAL FLOW
# ─────────────────────────────────────────────

def prompt_action():
    """Ask user what to do with the AI draft. Returns 's', 'e', or 'n'."""
    print()
    _line()
    print("  [s] 送信  [e] 編集  [n] スキップ")
    _line()
    while True:
        choice = input("  選択 > ").strip().lower()
        if choice in ("s", "e", "n"):
            return choice
        print("  's', 'e', 'n' のいずれかを入力してください。")


def edit_mode(original_draft):
    """
    Let the user rewrite the reply.
    Shows the original, clears it, lets user type freely.
    Returns the edited text.
    """
    print()
    print("  \033[93m編集モード\033[0m — 新しい返信を入力してください。")
    print("  （複数行入力可。空行を2回連続で入力すると確定します）")
    print()

    lines = []
    blank_count = 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            blank_count += 1
            if blank_count >= 2:
                break
            lines.append("")
        else:
            blank_count = 0
            lines.append(line)

    edited = "\n".join(lines).strip()
    if not edited:
        print("  \033[91m入力が空です。元の返信案を使用します。\033[0m")
        return original_draft
    return edited


def confirm_send(message_text):
    """Final confirmation before actually sending. Returns True to send."""
    print()
    _section("送信内容の最終確認")
    _wrap(message_text, indent=4)
    print()
    _line()
    print("  [y] 送信する  [n] キャンセル")
    _line()
    while True:
        choice = input("  選択 > ").strip().lower()
        if choice == "y":
            return True
        if choice == "n":
            return False
        print("  'y' か 'n' を入力してください。")


# ─────────────────────────────────────────────
#  SEND RESULT FEEDBACK
# ─────────────────────────────────────────────

def display_send_success(booking_id):
    print(f"\n  \033[92m送信完了\033[0m — 予約ID {booking_id} に返信しました。\n")

def display_send_failure(booking_id):
    print(f"\n  \033[91m送信失敗\033[0m — 予約ID {booking_id}。後で再試行してください。\n")

def display_skipped(booking_id):
    print(f"\n  \033[90mスキップ\033[0m — 予約ID {booking_id} は保留中です。\n")


# ─────────────────────────────────────────────
#  MAIN SESSION — runs through all unread messages
# ─────────────────────────────────────────────

def run_session(token, get_unread_fn, get_thread_fn, get_booking_fn, generate_fn, send_fn):
    """
    Process all unread guest messages one by one.

    Args:
        token:          Beds24 access token (str)
        get_unread_fn:  beds24.get_unread_guest_messages
        get_thread_fn:  beds24.get_message_thread
        get_booking_fn: beds24.get_booking_details
        generate_fn:    ai_engine.generate_reply
        send_fn:        beds24.send_reply
    """
    messages = get_unread_fn(token)

    if not messages:
        print("\n  未読のゲストメッセージはありません。\n")
        return

    total = len(messages)
    print(f"\n  未読ゲストメッセージ: {total} 件\n")

    for index, msg in enumerate(messages, start=1):
        booking_id = msg.get("bookingId")
        property_id = msg.get("propertyId")

        # Fetch context from backend
        thread = get_thread_fn(token, booking_id)
        booking_info = get_booking_fn(token, booking_id)

        # Generate AI draft
        guest_text = msg.get("message", "")
        print("\n  AI返信案を生成中...")
        draft = generate_fn(
            guest_message=guest_text,
            property_id=property_id,
            thread=thread,
            booking_info=booking_info,
        )

        # Display everything
        display_booking_header(index, total, booking_info, msg)
        display_thread(thread)
        display_guest_message(msg)
        display_ai_draft(draft)

        # Approval loop
        final_reply = draft
        while True:
            action = prompt_action()

            if action == "n":
                display_skipped(booking_id)
                break

            if action == "e":
                final_reply = edit_mode(draft)
                display_ai_draft(final_reply)
                # Go back to s/e/n after editing
                continue

            if action == "s":
                if confirm_send(final_reply):
                    success = send_fn(token, booking_id, final_reply)
                    if success:
                        display_send_success(booking_id)
                    else:
                        display_send_failure(booking_id)
                else:
                    print("  キャンセルしました。")
                break

    _header("セッション完了")
    print()
