"""
Tests for line_notify.py — LINE Flex Message construction with mocked API.

We mock at the SDK level to prevent Pydantic validation of PushMessageRequest/FlexMessage,
and instead capture the flex JSON dict that would be sent.
"""
from unittest.mock import patch, MagicMock
import json

import pytest

import line_notify


@pytest.fixture()
def captured_flex():
    """
    Mock the entire LINE SDK call chain and capture the flex_json dict
    that is passed to FlexContainer.from_dict().
    Returns a dict with 'flex' key that gets populated after a send call.
    """
    capture = {"flex": None, "push_args": None}

    mock_messaging = MagicMock()

    def fake_push(req):
        capture["push_args"] = req

    mock_messaging.push_message = fake_push

    mock_api_ctx = MagicMock()
    mock_api_ctx.__enter__ = MagicMock(return_value=mock_api_ctx)
    mock_api_ctx.__exit__ = MagicMock(return_value=False)

    with patch("line_notify.ApiClient", return_value=mock_api_ctx), \
         patch("line_notify.MessagingApi", return_value=mock_messaging), \
         patch("line_notify.PushMessageRequest", side_effect=lambda **kw: kw) as mock_push_cls, \
         patch("line_notify.FlexMessage", side_effect=lambda **kw: kw) as mock_flex_msg, \
         patch("line_notify.FlexContainer") as mock_flex_container:

        def from_dict_capture(d):
            capture["flex"] = d
            return d

        mock_flex_container.from_dict = from_dict_capture

        yield capture


# ---------------------------------------------------------------------------
# send_line_message
# ---------------------------------------------------------------------------

class TestSendLineMessage:
    def test_calls_push_message(self, captured_flex):
        line_notify.send_line_message(
            pending_id="42",
            booking_id="500",
            guest_message="When is check-in?",
            ai_reply="Check-in is at 3pm.",
            guest_name="Taro",
            property_name="Sakura House",
        )
        assert captured_flex["push_args"] is not None

    def test_flex_message_contains_postback_actions(self, captured_flex):
        line_notify.send_line_message(
            pending_id="42",
            booking_id="500",
            guest_message="Q",
            ai_reply="A",
        )
        flex = captured_flex["flex"]
        footer = flex["footer"]
        buttons = []
        for item in footer["contents"]:
            if item.get("type") == "button":
                buttons.append(item)
            elif item.get("type") == "box":
                buttons.extend(item.get("contents", []))

        actions_data = [b["action"]["data"] for b in buttons if b.get("type") == "button"]
        assert any("action=approve" in d and "pending_id=42" in d for d in actions_data)
        assert any("action=edit" in d and "pending_id=42" in d for d in actions_data)
        assert any("action=skip" in d and "pending_id=42" in d for d in actions_data)

    def test_header_shows_guest_and_property(self, captured_flex):
        line_notify.send_line_message(
            pending_id="42",
            booking_id="500",
            guest_message="Q",
            ai_reply="A",
            guest_name="Taro",
            property_name="Sakura",
        )
        flex = captured_flex["flex"]
        header_texts = [c["text"] for c in flex["header"]["contents"]]
        assert any("Taro" in t and "Sakura" in t for t in header_texts)

    def test_conversation_history_included_when_provided(self, captured_flex):
        line_notify.send_line_message(
            pending_id="42",
            booking_id="500",
            guest_message="Q",
            ai_reply="A",
            conversation_history="Guest: Hello\nHost: Welcome",
        )
        flex = captured_flex["flex"]
        body_texts = [c.get("text", "") for c in flex["body"]["contents"]]
        assert any("直近のやり取り" in t for t in body_texts)

    def test_no_history_section_when_empty(self, captured_flex):
        line_notify.send_line_message(
            pending_id="42",
            booking_id="500",
            guest_message="Q",
            ai_reply="A",
            conversation_history="",
        )
        flex = captured_flex["flex"]
        body_texts = [c.get("text", "") for c in flex["body"]["contents"]]
        assert not any("直近のやり取り" in t for t in body_texts)

    def test_guest_message_truncated(self, captured_flex):
        long_msg = "X" * 300
        line_notify.send_line_message(
            pending_id="42",
            booking_id="500",
            guest_message=long_msg,
            ai_reply="A",
        )
        flex = captured_flex["flex"]
        body_texts = [c.get("text", "") for c in flex["body"]["contents"]]
        guest_texts = [t for t in body_texts if "X" in t]
        for t in guest_texts:
            assert len(t) <= 150


# ---------------------------------------------------------------------------
# send_proactive_line_message
# ---------------------------------------------------------------------------

class TestSendProactiveLineMessage:
    def test_calls_push_message(self, captured_flex):
        line_notify.send_proactive_line_message(
            proactive_id="7",
            booking_id="500",
            trigger_type="pre_checkin",
            ai_message="Welcome!",
            guest_name="Taro",
            property_name="Sakura",
        )
        assert captured_flex["push_args"] is not None

    def test_pre_checkin_color_theme(self, captured_flex):
        line_notify.send_proactive_line_message(
            proactive_id="7",
            booking_id="500",
            trigger_type="pre_checkin",
            ai_message="Welcome!",
        )
        flex = captured_flex["flex"]
        header = flex["header"]
        assert header["backgroundColor"] == "#f0fff4"
        title = header["contents"][0]
        assert title["color"] == "#06d6a0"
        assert "ウェルカム" in title["text"]

    def test_post_checkout_color_theme(self, captured_flex):
        line_notify.send_proactive_line_message(
            proactive_id="7",
            booking_id="500",
            trigger_type="post_checkout",
            ai_message="Thank you!",
        )
        flex = captured_flex["flex"]
        header = flex["header"]
        assert header["backgroundColor"] == "#f8f0ff"
        title = header["contents"][0]
        assert title["color"] == "#7209b7"
        assert "サンキュー" in title["text"]

    def test_pro_prefix_in_postback_data(self, captured_flex):
        line_notify.send_proactive_line_message(
            proactive_id="7",
            booking_id="500",
            trigger_type="pre_checkin",
            ai_message="Welcome!",
        )
        flex = captured_flex["flex"]
        footer = flex["footer"]
        buttons = []
        for item in footer["contents"]:
            if item.get("type") == "button":
                buttons.append(item)
            elif item.get("type") == "box":
                buttons.extend(item.get("contents", []))
        actions_data = [b["action"]["data"] for b in buttons if b.get("type") == "button"]
        assert all("pro_7" in d for d in actions_data)

    def test_checkin_checkout_dates_in_body(self, captured_flex):
        line_notify.send_proactive_line_message(
            proactive_id="7",
            booking_id="500",
            trigger_type="pre_checkin",
            ai_message="Welcome!",
            check_in="2026-03-13",
            check_out="2026-03-15",
        )
        flex = captured_flex["flex"]
        body_texts = [c.get("text", "") for c in flex["body"]["contents"]]
        assert any("2026-03-13" in t and "2026-03-15" in t for t in body_texts)

    def test_header_shows_guest_and_property(self, captured_flex):
        line_notify.send_proactive_line_message(
            proactive_id="7",
            booking_id="500",
            trigger_type="pre_checkin",
            ai_message="Welcome!",
            guest_name="Taro",
            property_name="Sakura",
        )
        flex = captured_flex["flex"]
        header_texts = [c["text"] for c in flex["header"]["contents"]]
        assert any("Taro" in t and "Sakura" in t for t in header_texts)
