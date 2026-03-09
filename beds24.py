import os
import requests
from dotenv import load_dotenv

load_dotenv()

BEDS24_API_BASE = "https://beds24.com/api/v2"
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# ページネーション上限（無限ループ防止）
MAX_PAGES = 20


def get_access_token() -> str | None:
    """Beds24のアクセストークンを返す。失敗時はNone。"""
    url = f"{BEDS24_API_BASE}/authentication/token"
    headers = {"accept": "application/json", "refreshToken": REFRESH_TOKEN}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("token")
        print(f"[beds24] 認証エラー: {response.status_code} {response.text}")
    except requests.RequestException as e:
        print(f"[beds24] 接続エラー: {e}")
    return None


def _fetch_messages_paginated(token: str, params: dict) -> list[dict]:
    """メッセージAPIを全ページ取得して結合する。"""
    url = f"{BEDS24_API_BASE}/bookings/messages"
    headers = {"accept": "application/json", "token": token}
    all_messages = []

    page = 1
    while page <= MAX_PAGES:
        params["page"] = page
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                print(f"[beds24] メッセージ取得エラー (page {page}): {response.status_code} {response.text}")
                break

            body = response.json()
            data = body.get("data", [])
            all_messages.extend(data)

            # ページネーション情報を確認
            pages_info = body.get("pages", {})
            total_pages = pages_info.get("total", 1)

            if page >= total_pages:
                break
            page += 1

        except requests.RequestException as e:
            print(f"[beds24] 接続エラー (page {page}): {e}")
            break

    return all_messages


def _normalize_message(m: dict) -> dict:
    """APIレスポンスのメッセージを統一スキーマに変換する。"""
    return {
        "id": m.get("id"),
        "bookingId": m.get("bookingId"),
        "propertyId": m.get("propId") or m.get("propertyId"),
        "message": m.get("message", ""),
        "time": m.get("time", ""),
        "source": m.get("source", ""),
        "read": bool(m.get("read")),
    }


def get_unread_guest_messages(token: str) -> list[dict]:
    """未読かつsource=='guest'のメッセージリストを全ページから返す。"""
    messages = _fetch_messages_paginated(token, {})
    return [
        _normalize_message(m)
        for m in messages
        if m.get("source") == "guest" and not m.get("read")
    ]


def get_message_thread(token: str, booking_id: int) -> list[dict]:
    """指定bookingIdの会話スレッド全件を時系列順で返す。"""
    messages = _fetch_messages_paginated(token, {"bookingId": booking_id})
    thread = [_normalize_message(m) for m in messages]
    thread.sort(key=lambda m: m.get("time", ""))
    return thread


def get_booking_details(token: str, booking_id: int) -> dict:
    """予約詳細を返す。"""
    url = f"{BEDS24_API_BASE}/bookings"
    headers = {"accept": "application/json", "token": token}
    params = {"bookingId": booking_id}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"[beds24] 予約詳細取得エラー: {response.status_code} {response.text}")
            return {}
        data = response.json().get("data", [])
        if not data:
            return {}
        b = data[0]
        import json
        print(f"[beds24] === FULL BOOKING RESPONSE (id={booking_id}) ===")
        print(json.dumps(b, indent=2, ensure_ascii=False, default=str))
        print(f"[beds24] === END FULL BOOKING RESPONSE ===")
        first_name = b.get("guestFirstName", "")
        last_name = b.get("guestLastName", "")
        guest_name = f"{first_name} {last_name}".strip() or b.get("guestName", "不明")
        return {
            "guestName": guest_name,
            "checkIn": b.get("firstNight") or b.get("checkIn", ""),
            "checkOut": b.get("lastNight") or b.get("checkOut", ""),
            "propertyId": b.get("propId") or b.get("propertyId"),
            "propertyName": b.get("propName") or b.get("propertyName", ""),
        }
    except requests.RequestException as e:
        print(f"[beds24] 接続エラー: {e}")
        return {}


def send_reply(token: str, booking_id: int, message: str) -> bool:
    """Beds24にメッセージを送信。成功時True、失敗時False。"""
    url = f"{BEDS24_API_BASE}/bookings/messages"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "token": token,
    }
    payload = {
        "bookingId": booking_id,
        "message": message,
        "source": "host",
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code in (200, 201):
            return True
        print(f"[beds24] 送信エラー: {response.status_code} {response.text}")
        return False
    except requests.RequestException as e:
        print(f"[beds24] 接続エラー: {e}")
        return False
