import os
import logging
import threading
import time
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("minpaku-dx.beds24")

BEDS24_API_BASE = "https://beds24.com/api/v2"
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# ページネーション上限（無限ループ防止）
MAX_PAGES = 20

# Token cache with TTL (20分、Beds24トークンは約1時間有効)
_token_cache: dict[str, object] = {"token": None, "expires_at": 0.0}
_token_lock = threading.Lock()
_TOKEN_TTL = 20 * 60


def get_access_token() -> str | None:
    """Beds24のアクセストークンを返す。キャッシュがあれば再利用、期限切れなら再取得。"""
    with _token_lock:
        if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
            return _token_cache["token"]

    url = f"{BEDS24_API_BASE}/authentication/token"
    headers = {"accept": "application/json", "refreshToken": REFRESH_TOKEN}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            token = response.json().get("token")
            if token:
                with _token_lock:
                    _token_cache["token"] = token
                    _token_cache["expires_at"] = time.time() + _TOKEN_TTL
            return token
        logger.error("認証エラー: %d %s", response.status_code, response.text)
    except requests.RequestException as e:
        logger.error("接続エラー: %s", e)
    return None


def invalidate_token_cache() -> None:
    """トークンキャッシュを無効化する（認証エラー時に使用）。"""
    with _token_lock:
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0.0


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
                logger.error("メッセージ取得エラー (page %d): %d %s", page, response.status_code, response.text)
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
            logger.error("接続エラー (page %d): %s", page, e)
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
    # APIフィルタでレスポンス量を削減（Python側フィルタは安全ネットとして残す）
    params = {"source": "guest", "read": "false"}
    messages = _fetch_messages_paginated(token, params)
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


def _normalize_booking(b: dict) -> dict:
    """APIレスポンスの予約データを統一スキーマに変換する。"""
    first_name = b.get("guestFirstName", "")
    last_name = b.get("guestLastName", "")
    guest_name = f"{first_name} {last_name}".strip() or b.get("guestName", "不明")
    return {
        "bookingId": b.get("id") or b.get("bookingId"),
        "guestName": guest_name,
        "checkIn": b.get("firstNight") or b.get("checkIn", ""),
        "checkOut": b.get("lastNight") or b.get("checkOut", ""),
        "propertyId": b.get("propId") or b.get("propertyId"),
        "propertyName": b.get("propName") or b.get("propertyName", ""),
        "numAdult": b.get("numAdult", 0),
        "numChild": b.get("numChild", 0),
        "guestCountry": b.get("guestCountry", ""),
        "guestLanguage": b.get("guestLanguage", ""),
        "guestArrivalTime": b.get("guestArrivalTime", ""),
        "guestComments": b.get("guestComments", ""),
    }


def get_booking_details(token: str, booking_id: int) -> dict:
    """予約詳細を返す。"""
    url = f"{BEDS24_API_BASE}/bookings"
    headers = {"accept": "application/json", "token": token}
    params = {"bookingId": booking_id}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            logger.error("予約詳細取得エラー: %d %s", response.status_code, response.text)
            return {}
        data = response.json().get("data", [])
        if not data:
            return {}
        return _normalize_booking(data[0])
    except requests.RequestException as e:
        logger.error("接続エラー: %s", e)
        return {}


def get_bookings_by_date_range(token: str, arrival_from: str, arrival_to: str) -> list[dict]:
    """指定期間にチェックインする予約一覧を返す。日付はYYYY-MM-DD形式。"""
    url = f"{BEDS24_API_BASE}/bookings"
    headers = {"accept": "application/json", "token": token}
    params = {"arrivalFrom": arrival_from, "arrivalTo": arrival_to}
    all_bookings = []
    page = 1

    while page <= MAX_PAGES:
        params["page"] = page
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                logger.error("予約一覧取得エラー (page %d): %d %s", page, response.status_code, response.text)
                break
            body = response.json()
            data = body.get("data", [])
            for b in data:
                all_bookings.append(_normalize_booking(b))
            pages_info = body.get("pages", {})
            if page >= pages_info.get("total", 1):
                break
            page += 1
        except requests.RequestException as e:
            logger.error("接続エラー (page %d): %s", page, e)
            break

    return all_bookings


def get_bookings_by_checkout_range(token: str, departure_from: str, departure_to: str) -> list[dict]:
    """指定期間にチェックアウトする予約一覧を返す。日付はYYYY-MM-DD形式。"""
    url = f"{BEDS24_API_BASE}/bookings"
    headers = {"accept": "application/json", "token": token}
    params = {"departureFrom": departure_from, "departureTo": departure_to}
    all_bookings = []
    page = 1

    while page <= MAX_PAGES:
        params["page"] = page
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                logger.error("予約一覧取得エラー (page %d): %d %s", page, response.status_code, response.text)
                break
            body = response.json()
            data = body.get("data", [])
            for b in data:
                all_bookings.append(_normalize_booking(b))
            pages_info = body.get("pages", {})
            if page >= pages_info.get("total", 1):
                break
            page += 1
        except requests.RequestException as e:
            logger.error("接続エラー (page %d): %s", page, e)
            break

    return all_bookings


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
        logger.error("送信エラー: %d %s", response.status_code, response.text)
        return False
    except requests.RequestException as e:
        logger.error("接続エラー: %s", e)
        return False
