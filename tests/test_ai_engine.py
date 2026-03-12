"""
Tests for ai_engine.py — AI reply generation with mocked Gemini client.
"""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import ai_engine


# ---------------------------------------------------------------------------
# _is_japanese
# ---------------------------------------------------------------------------

class TestIsJapanese:
    def test_hiragana(self):
        assert ai_engine._is_japanese("こんにちは") is True

    def test_katakana(self):
        assert ai_engine._is_japanese("カタカナ") is True

    def test_kanji(self):
        assert ai_engine._is_japanese("漢字") is True

    def test_english_only(self):
        assert ai_engine._is_japanese("Hello world") is False

    def test_mixed_returns_true(self):
        assert ai_engine._is_japanese("Hello こんにちは") is True

    def test_empty_string(self):
        assert ai_engine._is_japanese("") is False

    def test_numbers_and_symbols(self):
        assert ai_engine._is_japanese("123 !@#") is False

    def test_chinese_detected_as_japanese(self):
        # CJK characters overlap; this is expected behavior
        assert ai_engine._is_japanese("你好") is True

    def test_korean_not_detected(self):
        assert ai_engine._is_japanese("안녕하세요") is False


# ---------------------------------------------------------------------------
# _load_property_rules
# ---------------------------------------------------------------------------

class TestLoadPropertyRules:
    def test_file_exists(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        rules_file = rules_dir / "property_10.md"
        rules_file.write_text("Check-in at 3pm", encoding="utf-8")

        with patch.object(ai_engine, "RULES_DIR", rules_dir):
            result = ai_engine._load_property_rules(10)
        assert result == "Check-in at 3pm"

    def test_file_missing(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        with patch.object(ai_engine, "RULES_DIR", rules_dir):
            result = ai_engine._load_property_rules(999)
        assert result == ""


# ---------------------------------------------------------------------------
# _format_thread
# ---------------------------------------------------------------------------

class TestFormatThread:
    def test_empty_thread(self):
        assert ai_engine._format_thread([]) == "（会話履歴なし）"

    def test_basic_formatting(self):
        thread = [
            {"source": "guest", "message": "Hello"},
            {"source": "host", "message": "Welcome!"},
        ]
        result = ai_engine._format_thread(thread)
        assert "ゲスト: Hello" in result
        assert "ホスト: Welcome!" in result


# ---------------------------------------------------------------------------
# generate_reply
# ---------------------------------------------------------------------------

class TestGenerateReply:
    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="Check-in at 3pm")
    def test_returns_ai_text(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Dear Guest, check-in is at 3pm."
        mock_client.return_value.models.generate_content.return_value = mock_response

        result = ai_engine.generate_reply(
            guest_message="What time is check-in?",
            property_id=10,
            thread=[{"source": "guest", "message": "What time is check-in?"}],
            booking_info={"guestName": "Taro", "checkIn": "2026-03-13", "checkOut": "2026-03-15"},
        )
        assert result == "Dear Guest, check-in is at 3pm."
        mock_client.return_value.models.generate_content.assert_called_once()

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_prompt_includes_guest_details(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Reply"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="Hello",
            property_id=10,
            thread=[],
            booking_info={
                "guestName": "John",
                "checkIn": "2026-03-13",
                "checkOut": "2026-03-15",
                "numAdult": 3,
                "numChild": 2,
                "guestCountry": "US",
                "guestArrivalTime": "16:00",
                "guestComments": "Wheelchair access needed",
            },
        )
        # Verify the prompt was passed to the AI
        call_args = mock_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents") or call_args[1].get("contents") or call_args[0][0] if call_args[0] else ""
        # The prompt is the contents kwarg
        actual_prompt = call_args.kwargs.get("contents", "")
        assert "John" in actual_prompt
        assert "大人3名" in actual_prompt
        assert "子供2名" in actual_prompt
        assert "US" in actual_prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_non_japanese_message_triggers_language_instruction(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Reply in English"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="What time is check-in?",
            property_id=10,
            thread=[],
            booking_info={"guestName": "John"},
        )
        call_args = mock_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", "")
        assert "日本語以外" in prompt or "同じ言語" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_guest_language_override(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Respuesta"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_reply(
            guest_message="Hola",
            property_id=10,
            thread=[],
            booking_info={"guestName": "Carlos", "guestLanguage": "Spanish"},
        )
        call_args = mock_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", "")
        assert "Spanish" in prompt


# ---------------------------------------------------------------------------
# generate_proactive_message
# ---------------------------------------------------------------------------

class TestGenerateProactiveMessage:
    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_pre_checkin(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Welcome to Sakura House!"
        mock_client.return_value.models.generate_content.return_value = mock_response

        result = ai_engine.generate_proactive_message(
            trigger_type="pre_checkin",
            booking_info={"guestName": "Taro", "checkIn": "2026-03-13", "checkOut": "2026-03-15"},
            property_id=10,
        )
        assert result == "Welcome to Sakura House!"
        call_args = mock_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", "")
        assert "ウェルカム" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_post_checkout(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Thank you for staying!"
        mock_client.return_value.models.generate_content.return_value = mock_response

        result = ai_engine.generate_proactive_message(
            trigger_type="post_checkout",
            booking_info={"guestName": "Taro"},
            property_id=10,
        )
        assert result == "Thank you for staying!"
        call_args = mock_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", "")
        assert "サンキュー" in prompt

    @patch.object(ai_engine, "_get_client")
    @patch.object(ai_engine, "_load_property_rules", return_value="")
    def test_foreign_guest_gets_language_instruction(self, mock_rules, mock_client):
        mock_response = MagicMock()
        mock_response.text = "Welcome!"
        mock_client.return_value.models.generate_content.return_value = mock_response

        ai_engine.generate_proactive_message(
            trigger_type="pre_checkin",
            booking_info={"guestName": "John", "guestCountry": "US", "guestLanguage": "English"},
            property_id=10,
        )
        call_args = mock_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", "")
        assert "English" in prompt
