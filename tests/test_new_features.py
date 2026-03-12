"""
Tests for new features:
- AI cultural context & language handling (ai_engine.py)
- Settings & onboarding API endpoints (app.py)
- User settings integration in sync_service.py
"""
import importlib
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

import ai_engine


# ===========================================================================
# AI Engine — Cultural Context
# ===========================================================================

class TestBuildCulturalContext:
    def test_western_guest(self):
        result = ai_engine._build_cultural_context("US", 0, 2)
        assert "欧米圏" in result
        assert "フレンドリー" in result

    def test_western_guest_uk(self):
        result = ai_engine._build_cultural_context("GB", 0, 1)
        assert "欧米圏" in result

    def test_non_western_foreign_guest(self):
        result = ai_engine._build_cultural_context("TH", 0, 1)
        assert "海外からのゲスト" in result
        assert "丁寧" in result

    def test_family_with_children(self):
        result = ai_engine._build_cultural_context("US", 2, 2)
        assert "お子様連れ" in result
        assert "2名" in result

    def test_large_group(self):
        result = ai_engine._build_cultural_context("JP", 0, 4)
        assert "大人4名" in result
        assert "騒音" in result

    def test_japanese_guest_no_context(self):
        result = ai_engine._build_cultural_context("JP", 0, 1)
        assert result == ""

    def test_empty_country_no_context(self):
        result = ai_engine._build_cultural_context("", 0, 1)
        assert result == ""

    def test_combined_western_family_group(self):
        result = ai_engine._build_cultural_context("US", 1, 4)
        assert "欧米圏" in result
        assert "お子様連れ" in result
        assert "大人4名" in result


# ===========================================================================
# AI Engine — Language Instruction
# ===========================================================================

class TestBuildLanguageInstruction:
    def test_explicit_guest_language(self):
        result = ai_engine._build_language_instruction("French", "FR")
        assert "French" in result
        assert "返信全体を必ず" in result

    def test_japanese_language_no_instruction(self):
        result = ai_engine._build_language_instruction("ja", "JP")
        assert result == ""

    def test_country_fallback_french(self):
        result = ai_engine._build_language_instruction("", "FR")
        assert "French" in result

    def test_country_fallback_german(self):
        result = ai_engine._build_language_instruction("", "DE")
        assert "German" in result

    def test_country_fallback_chinese(self):
        result = ai_engine._build_language_instruction("", "CN")
        assert "Chinese" in result

    def test_country_fallback_korean(self):
        result = ai_engine._build_language_instruction("", "KR")
        assert "Korean" in result

    def test_unknown_country_defaults_to_english(self):
        result = ai_engine._build_language_instruction("", "ZZ")
        assert "English" in result or "英語" in result

    def test_non_japanese_message_detection(self):
        result = ai_engine._build_language_instruction("", "", "Hello, what time is check-in?")
        assert "日本語以外" in result

    def test_japanese_message_no_instruction(self):
        result = ai_engine._build_language_instruction("", "", "チェックインは何時ですか？")
        assert result == ""

    def test_empty_everything_no_instruction(self):
        result = ai_engine._build_language_instruction("", "", "")
        assert result == ""


# ===========================================================================
# AI Engine — User Settings in Prompt
# ===========================================================================

class TestUserSettingsInPrompt:
    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_custom_signature(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Reply"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="Hello",
            property_id=10,
            thread=[],
            booking_info={"guestName": "Taro"},
            user_settings={"ai_signature": "オーナー太郎", "ai_tone": "friendly"},
        )
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
        assert "オーナー太郎" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_formal_tone(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Reply"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="Hello",
            property_id=10,
            thread=[],
            booking_info={"guestName": "Taro"},
            user_settings={"ai_tone": "formal"},
        )
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
        assert "フォーマル" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_casual_tone(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Reply"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="Hello",
            property_id=10,
            thread=[],
            booking_info={"guestName": "Taro"},
            user_settings={"ai_tone": "casual"},
        )
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
        assert "カジュアル" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_no_settings_uses_default_signature(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Reply"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="Hello",
            property_id=10,
            thread=[],
            booking_info={"guestName": "Taro"},
        )
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
        assert "民泊スタッフ一同" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_proactive_uses_settings(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Welcome"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_proactive_message(
            trigger_type="pre_checkin",
            booking_info={"guestName": "Taro"},
            property_id=10,
            user_settings={"ai_signature": "カスタム署名", "ai_tone": "casual"},
        )
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
        assert "カスタム署名" in prompt
        assert "カジュアル" in prompt


# ===========================================================================
# AI Engine — Cultural Context in Prompt
# ===========================================================================

class TestCulturalContextInPrompt:
    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_western_guest_context_in_reply(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Reply"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="Hello",
            property_id=10,
            thread=[],
            booking_info={"guestName": "John", "guestCountry": "US", "numChild": 1, "numAdult": 2},
        )
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
        assert "欧米圏" in prompt
        assert "お子様連れ" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_proactive_includes_cultural_context(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Welcome"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_proactive_message(
            trigger_type="pre_checkin",
            booking_info={"guestName": "Hans", "guestCountry": "DE", "numAdult": 4},
            property_id=10,
        )
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
        assert "欧米圏" in prompt
        assert "大人4名" in prompt


# ===========================================================================
# Backend — Settings & Onboarding Endpoints
# ===========================================================================

@pytest.fixture()
def api_client(test_db, monkeypatch):
    """TestClient with mocked Supabase auth for mobile API endpoints."""
    monkeypatch.setenv("DASHBOARD_USER", "test")
    monkeypatch.setenv("DASHBOARD_PASS", "test")
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test-secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("LINE_OWNER_USER_ID", "U1234")
    monkeypatch.setenv("REFRESH_TOKEN", "fake-refresh")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    import app as app_module
    importlib.reload(app_module)
    app_module.app.router.lifespan_context = noop_lifespan
    app_module.DASHBOARD_USER = "test"
    app_module.DASHBOARD_PASS = "test"
    app_module._auth_failures.clear()

    client = TestClient(app_module.app)
    return client, app_module, test_db


def _mock_auth(user_id="user-123", email="test@example.com"):
    """Override get_current_user to return a fake user."""
    async def fake_user():
        return {"id": user_id, "email": email}
    return fake_user


class TestSettingsEndpoints:
    def test_get_settings_unauthenticated(self, api_client):
        client, _, _ = api_client
        resp = client.get("/api/settings")
        assert resp.status_code == 401

    def test_get_settings_returns_defaults(self, api_client):
        client, app_module, db = api_client
        from auth import get_current_user
        app_module.app.dependency_overrides[get_current_user] = _mock_auth()

        resp = client.get("/api/settings")
        assert resp.status_code == 200
        settings = resp.json()["settings"]
        assert settings["ai_tone"] == "friendly"
        assert settings["ai_signature"] == "民泊スタッフ一同"

        app_module.app.dependency_overrides.clear()

    def test_update_settings(self, api_client):
        client, app_module, db = api_client
        from auth import get_current_user
        app_module.app.dependency_overrides[get_current_user] = _mock_auth()

        resp = client.put("/api/settings", json={
            "ai_tone": "formal",
            "ai_signature": "テスト署名",
            "notify_new_message": False,
        })
        assert resp.status_code == 200
        settings = resp.json()["settings"]
        assert settings["ai_tone"] == "formal"
        assert settings["ai_signature"] == "テスト署名"

        # Verify persistence
        resp2 = client.get("/api/settings")
        assert resp2.json()["settings"]["ai_tone"] == "formal"

        app_module.app.dependency_overrides.clear()

    def test_update_settings_empty_body(self, api_client):
        client, app_module, _ = api_client
        from auth import get_current_user
        app_module.app.dependency_overrides[get_current_user] = _mock_auth()

        resp = client.put("/api/settings", json={})
        assert resp.status_code == 400

        app_module.app.dependency_overrides.clear()

    def test_update_ignores_unknown_fields(self, api_client):
        client, app_module, _ = api_client
        from auth import get_current_user
        app_module.app.dependency_overrides[get_current_user] = _mock_auth()

        # SettingsUpdateRequest will silently ignore unknown fields
        resp = client.put("/api/settings", json={"ai_tone": "casual", "unknown_field": "ignored"})
        assert resp.status_code == 200
        assert resp.json()["settings"]["ai_tone"] == "casual"

        app_module.app.dependency_overrides.clear()


class TestOnboardingEndpoint:
    def test_onboarding_unauthenticated(self, api_client):
        client, _, _ = api_client
        resp = client.post("/api/onboarding", json={"beds24_refresh_token": "fake"})
        assert resp.status_code == 401

    @patch("requests.get")
    def test_onboarding_valid_token(self, mock_get, api_client):
        client, app_module, db = api_client
        from auth import get_current_user
        app_module.app.dependency_overrides[get_current_user] = _mock_auth()

        # Mock Beds24 token validation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "access-token-123"}
        mock_get.return_value = mock_response

        # Seed a booking so property detection works
        db.upsert_booking(500, 206100, "Test Guest", "2026-03-13", "2026-03-15", "平井戸建")

        resp = client.post("/api/onboarding", json={"beds24_refresh_token": "valid-token"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert len(data["properties"]) == 1
        assert data["properties"][0]["property_id"] == 206100

        # Verify user-property association
        props = db.get_user_properties("user-123")
        assert len(props) == 1
        assert props[0]["property_id"] == 206100

        app_module.app.dependency_overrides.clear()

    @patch("requests.get")
    def test_onboarding_invalid_token(self, mock_get, api_client):
        client, app_module, _ = api_client
        from auth import get_current_user
        app_module.app.dependency_overrides[get_current_user] = _mock_auth()

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        resp = client.post("/api/onboarding", json={"beds24_refresh_token": "bad-token"})
        assert resp.status_code == 400
        assert "検証に失敗" in resp.json()["detail"]

        app_module.app.dependency_overrides.clear()

    @patch("requests.get")
    def test_onboarding_no_properties(self, mock_get, api_client):
        client, app_module, db = api_client
        from auth import get_current_user
        app_module.app.dependency_overrides[get_current_user] = _mock_auth()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "access-token"}
        mock_get.return_value = mock_response

        # No bookings → no properties detected
        resp = client.post("/api/onboarding", json={"beds24_refresh_token": "valid"})
        assert resp.status_code == 200
        assert resp.json()["properties"] == []

        app_module.app.dependency_overrides.clear()


# ===========================================================================
# Sync Service — Owner Settings Lookup
# ===========================================================================

class TestGetOwnerSettings:
    def test_returns_settings_for_property_owner(self, test_db):
        import sync_service as ss
        importlib.reload(ss)

        # Set up user, property association, and settings
        test_db.add_user_property("owner-1", 206100)
        test_db.upsert_user_settings("owner-1", ai_tone="formal", ai_signature="オーナー")

        settings = ss._get_owner_settings(206100)
        assert settings is not None
        assert settings["ai_tone"] == "formal"
        assert settings["ai_signature"] == "オーナー"

    def test_returns_none_for_unknown_property(self, test_db):
        import sync_service as ss
        importlib.reload(ss)

        result = ss._get_owner_settings(999999)
        assert result is None

    def test_returns_none_for_none_property(self, test_db):
        import sync_service as ss
        importlib.reload(ss)

        result = ss._get_owner_settings(None)
        assert result is None
