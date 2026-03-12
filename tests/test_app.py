"""
Tests for app.py — FastAPI endpoints using TestClient.

The background scheduler is disabled by mocking the lifespan.
External APIs (Beds24, LINE SDK) are mocked.
"""
import importlib
import os
import base64
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_client(test_db, monkeypatch):
    """
    Create a TestClient with a fresh DB and mocked scheduler.
    Dashboard auth is configured with test/test credentials.
    """
    monkeypatch.setenv("DASHBOARD_USER", "test")
    monkeypatch.setenv("DASHBOARD_PASS", "test")
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test-secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("LINE_OWNER_USER_ID", "U1234")
    monkeypatch.setenv("REFRESH_TOKEN", "fake-refresh")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    # Reload app with mocked lifespan (no scheduler)
    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    import app as app_module
    importlib.reload(app_module)
    app_module.app.router.lifespan_context = noop_lifespan
    # Update auth credentials
    app_module.DASHBOARD_USER = "test"
    app_module.DASHBOARD_PASS = "test"
    # Clear auth failures from previous tests
    app_module._auth_failures.clear()

    client = TestClient(app_module.app)
    return client, app_module, test_db


def _basic_auth(user="test", password="test"):
    """Helper to create Basic Auth header."""
    cred = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {cred}"}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self, app_client):
        client, _, _ = app_client
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "db" in data
        assert data["db"]["ok"] is True

    def test_health_contains_sync_info(self, app_client):
        client, _, _ = app_client
        data = client.get("/health").json()
        assert "sync" in data
        assert "server_start_time" in data


# ---------------------------------------------------------------------------
# LINE callback
# ---------------------------------------------------------------------------

class TestLineCallback:
    def test_invalid_signature_returns_400(self, app_client):
        client, app_module, _ = app_client
        resp = client.post(
            "/callback",
            content=b'{"events":[]}',
            headers={"X-Line-Signature": "bad-signature", "Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_missing_signature_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/callback", content=b'{}')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Dashboard (auth required)
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_dashboard_requires_auth(self, app_client):
        client, _, _ = app_client
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 401

    def test_dashboard_with_bad_credentials(self, app_client):
        client, _, _ = app_client
        resp = client.get("/", headers=_basic_auth("wrong", "wrong"))
        assert resp.status_code == 401

    def test_dashboard_with_valid_credentials(self, app_client):
        client, _, _ = app_client
        # Need templates directory to exist
        resp = client.get("/", headers=_basic_auth())
        # Either 200 (template found) or 500 (template not found) — but not 401
        assert resp.status_code != 401


# ---------------------------------------------------------------------------
# GET /api/messages
# ---------------------------------------------------------------------------

class TestApiMessages:
    def test_requires_auth(self, app_client):
        client, _, _ = app_client
        resp = client.get("/api/messages")
        assert resp.status_code == 401

    def test_returns_empty_list(self, app_client):
        client, _, _ = app_client
        resp = client.get("/api/messages", headers=_basic_auth())
        assert resp.status_code == 200
        assert resp.json()["messages"] == []

    def test_returns_draft_ready_messages_with_type(self, app_client):
        client, _, db = app_client
        msg_id, _ = db.upsert_message(1, 500, 10, "guest", "Hello", "2026-03-10T14:00:00", False)
        db.save_draft(msg_id, 500, "AI reply", "gemini-2.5-flash")
        db.update_message_status(msg_id, "draft_ready")

        resp = client.get("/api/messages", headers=_basic_auth())
        data = resp.json()
        assert len(data["messages"]) == 1
        card = data["messages"][0]
        assert card["type"] == "reply"
        assert card["guestText"] == "Hello"
        assert card["draft"] == "AI reply"

    def test_includes_proactive_messages(self, app_client):
        client, _, db = app_client
        db.upsert_booking(500, 10, "Taro", "2026-03-13", "2026-03-15", "Sakura")
        db.save_proactive_draft(500, 10, "pre_checkin", "Welcome!", "gemini-2.5-flash")

        resp = client.get("/api/messages", headers=_basic_auth())
        data = resp.json()
        pro_cards = [c for c in data["messages"] if c["type"] == "proactive"]
        assert len(pro_cards) == 1
        assert pro_cards[0]["triggerType"] == "pre_checkin"
        assert str(pro_cards[0]["id"]).startswith("pro_")


# ---------------------------------------------------------------------------
# POST /api/send
# ---------------------------------------------------------------------------

class TestApiSend:
    def test_requires_auth(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/send", json={"bookingId": 500, "message": "Hi"})
        assert resp.status_code == 401

    def test_empty_message_rejected(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/send",
                           json={"bookingId": 500, "message": "  "},
                           headers=_basic_auth())
        assert resp.status_code == 400

    def test_send_regular_message(self, app_client):
        client, app_module, db = app_client
        msg_id, _ = db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T14:00:00", False)
        db.save_draft(msg_id, 500, "Draft", "model")
        db.update_message_status(msg_id, "draft_ready")

        with patch.object(app_module, "get_access_token", return_value="token"), \
             patch.object(app_module, "send_reply", return_value=True):
            resp = client.post("/api/send",
                               json={"messageId": msg_id, "bookingId": 500, "message": "Custom reply"},
                               headers=_basic_auth())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        updated = db.get_message_by_id(msg_id)
        assert updated["status"] == "sent"

    def test_send_proactive_message(self, app_client):
        client, app_module, db = app_client
        pro_id = db.save_proactive_draft(500, 10, "pre_checkin", "Welcome", "model")

        with patch.object(app_module, "get_access_token", return_value="token"), \
             patch.object(app_module, "send_reply", return_value=True):
            resp = client.post("/api/send",
                               json={"messageId": f"pro_{pro_id}", "bookingId": 500, "message": "Welcome!"},
                               headers=_basic_auth())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        pro = db.get_proactive_by_id(pro_id)
        assert pro["status"] == "sent"

    def test_send_retry_on_first_failure(self, app_client):
        client, app_module, db = app_client

        call_count = [0]
        def mock_send_reply(token, bid, msg):
            call_count[0] += 1
            return call_count[0] >= 2  # Fail first, succeed second

        with patch.object(app_module, "get_access_token", return_value="token"), \
             patch.object(app_module, "send_reply", side_effect=mock_send_reply), \
             patch.object(app_module, "invalidate_token_cache"):
            resp = client.post("/api/send",
                               json={"bookingId": 500, "message": "Hi"},
                               headers=_basic_auth())
        assert resp.json()["ok"] is True

    def test_no_beds24_token(self, app_client):
        client, app_module, _ = app_client
        with patch.object(app_module, "get_access_token", return_value=None):
            resp = client.post("/api/send",
                               json={"bookingId": 500, "message": "Hi"},
                               headers=_basic_auth())
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/skip
# ---------------------------------------------------------------------------

class TestApiSkip:
    def test_requires_auth(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/skip", json={"messageId": 1})
        assert resp.status_code == 401

    def test_skip_regular_message(self, app_client):
        client, _, db = app_client
        msg_id, _ = db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T14:00:00", False)
        db.update_message_status(msg_id, "draft_ready")

        resp = client.post("/api/skip",
                           json={"messageId": msg_id},
                           headers=_basic_auth())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        updated = db.get_message_by_id(msg_id)
        assert updated["status"] == "skipped"

    def test_skip_proactive_message(self, app_client):
        client, _, db = app_client
        pro_id = db.save_proactive_draft(500, 10, "pre_checkin", "Welcome", "model")

        resp = client.post("/api/skip",
                           json={"messageId": f"pro_{pro_id}"},
                           headers=_basic_auth())
        assert resp.status_code == 200
        pro = db.get_proactive_by_id(pro_id)
        assert pro["status"] == "skipped"

    def test_invalid_message_id_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/skip",
                           json={"messageId": "not_a_number"},
                           headers=_basic_auth())
        assert resp.status_code == 400
