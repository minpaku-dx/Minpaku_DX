import requests
import json
import uuid
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from google import genai
from line_notify import send_line_message

load_dotenv()

# ===== 設定 =====
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PENDING_FILE = os.path.join(os.path.dirname(__file__), "pending.json")
JST = timezone(timedelta(hours=9))

# Gemini を初期化
client = genai.Client(api_key=GEMINI_API_KEY)


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
def get_access_token():
    """Beds24のアクセストークンを取得"""
    url = "https://beds24.com/api/v2/authentication/token"
    headers = {"accept": "application/json", "refreshToken": REFRESH_TOKEN}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("token")
    return None


def get_unread_guest_messages(token):
    """未読のゲストメッセージのみを抽出して返す"""
    url = "https://beds24.com/api/v2/bookings/messages"
    headers = {"accept": "application/json", "token": token}
    params = {"limit": 20}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"メッセージ取得エラー: {response.json()}")
        return []

    messages = response.json().get("data", [])
    unread_guest = [
        m for m in messages
        if m.get("source") == "guest" and not m.get("read")
    ]
    return unread_guest


def get_message_thread(token, booking_id):
    """指定bookingIdの会話スレッドを時系列順（古い→新しい）で返す"""
    url = "https://beds24.com/api/v2/bookings/messages"
    headers = {"accept": "application/json", "token": token}
    params = {"bookingId": booking_id, "limit": 200}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return []

    messages = response.json().get("data", [])
    thread = [
        {
            "message": m.get("message", ""),
            "time": m.get("time", ""),
            "source": m.get("source", ""),
        }
        for m in messages
    ]
    thread.sort(key=lambda m: m.get("time", ""))
    return thread


# ===== 会話履歴フォーマット =====
def format_time_label(iso_time: str) -> str:
    """ISO時刻を '3/7 15:00' のような読みやすい形式に変換"""
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00")).astimezone(JST)
        now = datetime.now(JST)
        if dt.date() == now.date():
            return f"今日 {dt.strftime('%H:%M')}"
        elif dt.date() == (now - timedelta(days=1)).date():
            return f"昨日 {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%-m/%-d %H:%M")
    except Exception:
        return iso_time[:16]


def build_conversation_history(thread: list, max_items: int = 5) -> str:
    """
    メッセージスレッドから直近max_items件を
    '[時刻] ゲスト/ホスト: メッセージ' 形式のテキストに変換する
    """
    recent = thread[-max_items:] if len(thread) > max_items else thread
    lines = []
    for i, m in enumerate(recent):
        time_label = format_time_label(m["time"])
        sender = "ゲスト" if m["source"] == "guest" else "ホスト"
        text = m["message"][:120].replace("\n", " ")
        # 最後のメッセージに「←今回の未読」マークを付加
        suffix = "（←今回の未読メッセージ）" if i == len(recent) - 1 and m["source"] == "guest" else ""
        lines.append(f"[{time_label}] {sender}: {text}{suffix}")
    return "\n".join(lines)


# ===== AI返信生成 =====
def generate_reply(guest_message: str, conversation_history: str) -> str:
    """過去の会話文脈を踏まえてGeminiにプロの返信案を生成させる"""
    prompt = f"""
あなたは日本の高級ホテルの経験豊富なコンシェルジュです。
以下の会話履歴を踏まえた上で、最新のゲストメッセージに対して、
プロとして丁寧かつ簡潔な日本語の返信案を1つ作成してください。

【直近の会話履歴】
{conversation_history}

【返信のルール】
- 敬語・丁寧語を使う
- 温かみのある表現にする
- 過去の文脈を踏まえた自然な返信にする
- 必要な情報は明確に答える
- 署名は「民泊スタッフ一同」とする
- 返信案のみを出力する（前置き・説明文は不要）
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


# ===== メイン処理 =====
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
        print("✅ 未読のゲストメッセージはありません。")
        exit()

    print(f"📬 未読ゲストメッセージが {len(messages)} 件あります。\n")

    # 承認待ちデータを読み込み
    pending = load_pending()

    # 予約IDごとにスレッドをキャッシュ（同じ予約IDで何度もAPIを叩かない）
    thread_cache = {}

    # Step3: 各メッセージに対して履歴取得 → AI返信案生成 → LINE通知
    for i, msg in enumerate(messages, 1):
        booking_id = msg.get("bookingId", "不明")
        guest_text = msg.get("message", "（本文なし）")

        print(f"{'='*60}")
        print(f"【 {i}件目 】予約ID: {booking_id}")

        # Step3a: メッセージスレッド（履歴）を取得
        if booking_id not in thread_cache:
            thread_cache[booking_id] = get_message_thread(token, booking_id)
        thread = thread_cache[booking_id]
        conversation_history = build_conversation_history(thread, max_items=5)

        print(f"\n▼ 会話履歴")
        print(conversation_history)
        print(f"\n▼ AI返信案（Gemini生成）")

        # Step3b: 文脈を踏まえたAI返信を生成
        reply = generate_reply(guest_text, conversation_history)
        print(reply)

        # Step4: pending.json に承認待ちデータを保存
        pending_id = str(uuid.uuid4())[:8]
        pending[pending_id] = {
            "booking_id": booking_id,
            "guest_message": guest_text,
            "ai_reply": reply,
            "conversation_history": conversation_history,
            "status": "pending",
        }

        # Step5: LINEにボタン付きFlex Message（履歴付き）を送信
        send_line_message(pending_id, str(booking_id), guest_text, reply, conversation_history)
        print("  → LINE通知を送信しました ✅\n")

    # 承認待ちデータを保存
    save_pending(pending)
    print(f"📋 {len(messages)} 件の承認待ちデータを pending.json に保存しました。")
