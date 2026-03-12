"""
cli.py — CLI承認フロー
DBからdraft_readyメッセージを表示し、承認/編集/スキップの操作を行う。
"""
import textwrap

from beds24 import get_access_token, send_reply
import db


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
#  DISPLAY FUNCTIONS
# ─────────────────────────────────────────────

def display_booking_header(index, total, booking, msg):
    _header(f"メッセージ {index}/{total}")
    _badge("予約ID", msg.get("booking_id", "不明"))
    _badge("物件", booking.get("property_name", "不明") if booking else "不明")
    _badge("ゲスト", booking.get("guest_name", "不明") if booking else "不明", "\033[96m")
    _badge("チェックイン", booking.get("check_in", "不明") if booking else "不明")
    _badge("チェックアウト", booking.get("check_out", "不明") if booking else "不明")
    if booking:
        num_adult = booking.get("num_adult", 0)
        num_child = booking.get("num_child", 0)
        if num_adult or num_child:
            people = f"大人{num_adult}名" + (f"、子供{num_child}名" if num_child else "")
            _badge("人数", people)
        if booking.get("guest_country"):
            _badge("国籍", booking["guest_country"])
        if booking.get("guest_language"):
            _badge("言語", booking["guest_language"])
        if booking.get("guest_arrival_time"):
            _badge("到着予定", booking["guest_arrival_time"])
        if booking.get("guest_comments"):
            _badge("備考", booking["guest_comments"])
    _badge("受信時刻", msg.get("sent_at", "")[:16].replace("T", " "))


def display_thread(thread):
    if not thread:
        return
    _section("会話履歴")
    history = [m for m in thread if not (m.get("source") == "guest" and not m.get("is_read"))]
    for m in history[-6:]:
        sender_label = "\033[93mゲスト\033[0m" if m.get("source") == "guest" else "\033[90mホスト\033[0m"
        time_str = m.get("sent_at", "")[:16].replace("T", " ")
        print(f"\n  [{time_str}] {sender_label}")
        _wrap(m.get("message", ""), indent=4)


def display_guest_message(msg):
    _section("ゲストの最新メッセージ \033[91m[未読]\033[0m")
    _wrap(msg.get("message", "（メッセージなし）"), indent=4)


def display_ai_draft(draft):
    _section("AI返信案")
    _wrap(draft, indent=4)


# ─────────────────────────────────────────────
#  APPROVAL FLOW
# ─────────────────────────────────────────────

def prompt_action():
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


def display_send_success(booking_id):
    print(f"\n  \033[92m送信完了\033[0m — 予約ID {booking_id} に返信しました。\n")

def display_send_failure(booking_id):
    print(f"\n  \033[91m送信失敗\033[0m — 予約ID {booking_id}。後で再試行してください。\n")

def display_skipped(booking_id):
    print(f"\n  \033[90mスキップ\033[0m — 予約ID {booking_id} は保留中です。\n")


# ─────────────────────────────────────────────
#  MAIN SESSION — DBから読み取り
# ─────────────────────────────────────────────

def run_session():
    """DBからdraft_readyメッセージを取得し、承認フローを実行する。"""
    messages = db.get_draft_ready_messages()

    if not messages:
        print("\n  承認待ちのメッセージはありません。\n")
        return

    total = len(messages)
    print(f"\n  承認待ちメッセージ: {total} 件\n")

    token = get_access_token()
    if not token:
        print("\n  [ERROR] Beds24認証失敗。.env の REFRESH_TOKEN を確認してください。\n")
        return

    for index, msg in enumerate(messages, start=1):
        message_id = msg["id"]
        booking_id = msg["booking_id"]
        draft_text = msg.get("draft_text", "")
        draft_id = msg.get("draft_id")

        booking = db.get_booking(booking_id)
        thread = db.get_thread(booking_id)

        display_booking_header(index, total, booking, msg)
        display_thread(thread)
        display_guest_message(msg)
        display_ai_draft(draft_text)

        final_reply = draft_text
        while True:
            action = prompt_action()

            if action == "n":
                db.update_message_status(message_id, "skipped")
                db.log_action(message_id, draft_id, "skipped", None, "cli")
                display_skipped(booking_id)
                break

            if action == "e":
                final_reply = edit_mode(draft_text)
                display_ai_draft(final_reply)
                continue

            if action == "s":
                if confirm_send(final_reply):
                    success = send_reply(token, booking_id, final_reply)
                    if success:
                        act = "sent" if final_reply == draft_text else "edited"
                        db.update_message_status(message_id, "sent")
                        db.log_action(message_id, draft_id, act, final_reply, "cli")
                        display_send_success(booking_id)
                    else:
                        display_send_failure(booking_id)
                else:
                    print("  キャンセルしました。")
                break

    _header("セッション完了")
    print()
