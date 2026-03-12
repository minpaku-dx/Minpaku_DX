"""
Tests for beds24.py — API client with mocked HTTP requests.
"""
import time
from unittest.mock import patch, MagicMock

import pytest
import requests

import beds24


@pytest.fixture(autouse=True)
def reset_token_cache():
    """Reset token cache before each test."""
    beds24._token_cache["token"] = None
    beds24._token_cache["expires_at"] = 0.0
    yield
    beds24._token_cache["token"] = None
    beds24._token_cache["expires_at"] = 0.0


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data)
    return resp


# ---------------------------------------------------------------------------
# get_access_token
# ---------------------------------------------------------------------------

class TestGetAccessToken:
    @patch("beds24.requests.get")
    def test_fetches_new_token(self, mock_get):
        mock_get.return_value = _mock_response(200, {"token": "abc123"})
        token = beds24.get_access_token()
        assert token == "abc123"
        mock_get.assert_called_once()

    @patch("beds24.requests.get")
    def test_caches_token(self, mock_get):
        mock_get.return_value = _mock_response(200, {"token": "abc123"})
        beds24.get_access_token()
        beds24.get_access_token()
        # Second call should use cache, not make another HTTP call
        assert mock_get.call_count == 1

    @patch("beds24.requests.get")
    def test_expired_cache_refetches(self, mock_get):
        mock_get.return_value = _mock_response(200, {"token": "abc123"})
        beds24.get_access_token()
        # Force expiry
        beds24._token_cache["expires_at"] = time.time() - 1
        mock_get.return_value = _mock_response(200, {"token": "new_token"})
        token = beds24.get_access_token()
        assert token == "new_token"
        assert mock_get.call_count == 2

    @patch("beds24.requests.get")
    def test_auth_error_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(401, {"error": "unauthorized"})
        token = beds24.get_access_token()
        assert token is None

    @patch("beds24.requests.get")
    def test_network_error_returns_none(self, mock_get):
        mock_get.side_effect = requests.RequestException("connection refused")
        token = beds24.get_access_token()
        assert token is None

    def test_invalidate_token_cache(self):
        beds24._token_cache["token"] = "cached"
        beds24._token_cache["expires_at"] = time.time() + 9999
        beds24.invalidate_token_cache()
        assert beds24._token_cache["token"] is None
        assert beds24._token_cache["expires_at"] == 0.0


# ---------------------------------------------------------------------------
# _normalize_booking
# ---------------------------------------------------------------------------

class TestNormalizeBooking:
    def test_standard_fields(self):
        raw = {
            "id": 500,
            "guestFirstName": "Taro",
            "guestLastName": "Yamada",
            "firstNight": "2026-03-13",
            "lastNight": "2026-03-15",
            "propId": 10,
            "propName": "Sakura House",
            "numAdult": 2,
            "numChild": 1,
            "guestCountry": "JP",
            "guestLanguage": "ja",
            "guestArrivalTime": "15:00",
            "guestComments": "Late arrival",
        }
        result = beds24._normalize_booking(raw)
        assert result["bookingId"] == 500
        assert result["guestName"] == "Taro Yamada"
        assert result["checkIn"] == "2026-03-13"
        assert result["checkOut"] == "2026-03-15"
        assert result["propertyId"] == 10
        assert result["propertyName"] == "Sakura House"
        assert result["numAdult"] == 2

    def test_fallback_to_alternative_fields(self):
        raw = {
            "bookingId": 600,
            "guestName": "Hanako",
            "checkIn": "2026-04-01",
            "checkOut": "2026-04-03",
            "propertyId": 20,
            "propertyName": "Maple Inn",
        }
        result = beds24._normalize_booking(raw)
        assert result["bookingId"] == 600
        assert result["guestName"] == "Hanako"
        assert result["checkIn"] == "2026-04-01"

    def test_missing_guest_name_defaults(self):
        raw = {"id": 500}
        result = beds24._normalize_booking(raw)
        assert result["guestName"] == "不明"

    def test_first_last_name_concatenation(self):
        raw = {"id": 1, "guestFirstName": "John", "guestLastName": "Doe"}
        result = beds24._normalize_booking(raw)
        assert result["guestName"] == "John Doe"

    def test_only_first_name(self):
        raw = {"id": 1, "guestFirstName": "John"}
        result = beds24._normalize_booking(raw)
        assert result["guestName"] == "John"

    def test_empty_names_fall_back_to_guestName(self):
        raw = {"id": 1, "guestFirstName": "", "guestLastName": "", "guestName": "Fallback"}
        result = beds24._normalize_booking(raw)
        assert result["guestName"] == "Fallback"


# ---------------------------------------------------------------------------
# _normalize_message
# ---------------------------------------------------------------------------

class TestNormalizeMessage:
    def test_standard_fields(self):
        raw = {
            "id": 100,
            "bookingId": 500,
            "propId": 10,
            "message": "Hello",
            "time": "2026-03-10T14:00:00",
            "source": "guest",
            "read": False,
        }
        result = beds24._normalize_message(raw)
        assert result["id"] == 100
        assert result["propertyId"] == 10
        assert result["read"] is False

    def test_read_truthy(self):
        raw = {"id": 1, "bookingId": 1, "read": 1}
        result = beds24._normalize_message(raw)
        assert result["read"] is True

    def test_propertyId_fallback(self):
        raw = {"id": 1, "bookingId": 1, "propertyId": 20}
        result = beds24._normalize_message(raw)
        assert result["propertyId"] == 20


# ---------------------------------------------------------------------------
# get_unread_guest_messages (pagination)
# ---------------------------------------------------------------------------

class TestGetUnreadGuestMessages:
    @patch("beds24.requests.get")
    def test_single_page(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "data": [
                {"id": 1, "bookingId": 500, "source": "guest", "read": False, "message": "Q"},
                {"id": 2, "bookingId": 500, "source": "host", "read": False, "message": "A"},
            ],
            "pages": {"total": 1},
        })
        result = beds24.get_unread_guest_messages("token")
        # Only guest messages with read=False
        assert len(result) == 1
        assert result[0]["id"] == 1

    @patch("beds24.requests.get")
    def test_multiple_pages(self, mock_get):
        page1 = _mock_response(200, {
            "data": [{"id": 1, "bookingId": 500, "source": "guest", "read": False, "message": "Page1"}],
            "pages": {"total": 2},
        })
        page2 = _mock_response(200, {
            "data": [{"id": 2, "bookingId": 501, "source": "guest", "read": False, "message": "Page2"}],
            "pages": {"total": 2},
        })
        mock_get.side_effect = [page1, page2]
        result = beds24.get_unread_guest_messages("token")
        assert len(result) == 2

    @patch("beds24.requests.get")
    def test_api_error_returns_partial(self, mock_get):
        mock_get.return_value = _mock_response(500, {"error": "server error"})
        result = beds24.get_unread_guest_messages("token")
        assert result == []


# ---------------------------------------------------------------------------
# get_bookings_by_date_range / get_bookings_by_checkout_range (pagination)
# ---------------------------------------------------------------------------

class TestGetBookingsByRange:
    @patch("beds24.requests.get")
    def test_date_range_single_page(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "data": [{"id": 500, "guestFirstName": "Taro", "guestLastName": "Y",
                       "firstNight": "2026-03-13", "lastNight": "2026-03-15"}],
            "pages": {"total": 1},
        })
        result = beds24.get_bookings_by_date_range("token", "2026-03-13", "2026-03-13")
        assert len(result) == 1
        assert result[0]["bookingId"] == 500

    @patch("beds24.requests.get")
    def test_checkout_range_pagination(self, mock_get):
        page1 = _mock_response(200, {
            "data": [{"id": 500, "firstNight": "2026-03-10", "lastNight": "2026-03-12"}],
            "pages": {"total": 2},
        })
        page2 = _mock_response(200, {
            "data": [{"id": 501, "firstNight": "2026-03-11", "lastNight": "2026-03-12"}],
            "pages": {"total": 2},
        })
        mock_get.side_effect = [page1, page2]
        result = beds24.get_bookings_by_checkout_range("token", "2026-03-12", "2026-03-12")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# send_reply
# ---------------------------------------------------------------------------

class TestSendReply:
    @patch("beds24.requests.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(200, {"ok": True})
        assert beds24.send_reply("token", 500, "Thank you!") is True

    @patch("beds24.requests.post")
    def test_201_also_success(self, mock_post):
        mock_post.return_value = _mock_response(201, {"ok": True})
        assert beds24.send_reply("token", 500, "Hi") is True

    @patch("beds24.requests.post")
    def test_failure(self, mock_post):
        mock_post.return_value = _mock_response(400, {"error": "bad request"})
        assert beds24.send_reply("token", 500, "Hi") is False

    @patch("beds24.requests.post")
    def test_network_error(self, mock_post):
        mock_post.side_effect = requests.RequestException("timeout")
        assert beds24.send_reply("token", 500, "Hi") is False


# ---------------------------------------------------------------------------
# get_booking_details
# ---------------------------------------------------------------------------

class TestGetBookingDetails:
    @patch("beds24.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "data": [{"id": 500, "guestFirstName": "Taro", "guestLastName": "Y",
                       "firstNight": "2026-03-13", "lastNight": "2026-03-15",
                       "propId": 10, "propName": "Sakura"}],
        })
        result = beds24.get_booking_details("token", 500)
        assert result["bookingId"] == 500
        assert result["guestName"] == "Taro Y"

    @patch("beds24.requests.get")
    def test_empty_data(self, mock_get):
        mock_get.return_value = _mock_response(200, {"data": []})
        result = beds24.get_booking_details("token", 999)
        assert result == {}

    @patch("beds24.requests.get")
    def test_api_error(self, mock_get):
        mock_get.return_value = _mock_response(500, {})
        result = beds24.get_booking_details("token", 500)
        assert result == {}
