"""
Tests for sync_service.py — sync logic with mocked external dependencies.
"""
import importlib
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def sync_db(test_db):
    """Reload sync_service after db is re-initialized with temp path."""
    import sync_service as ss
    importlib.reload(ss)
    return test_db, ss


# ---------------------------------------------------------------------------
# sync_messages
# ---------------------------------------------------------------------------

class TestSyncMessages:
    def test_new_messages_saved(self, sync_db):
        db, ss = sync_db
        raw = [
            {"id": 1, "bookingId": 500, "propertyId": 10, "source": "guest",
             "message": "Hello", "time": "2026-03-10T14:00:00", "read": False},
            {"id": 2, "bookingId": 501, "propertyId": 11, "source": "guest",
             "message": "Hi", "time": "2026-03-10T15:00:00", "read": False},
        ]
        with patch.object(ss, "get_unread_guest_messages", return_value=raw):
            result = ss.sync_messages("fake-token")
        assert len(result) == 2

    def test_duplicates_skipped(self, sync_db):
        db, ss = sync_db
        raw = [{"id": 1, "bookingId": 500, "propertyId": 10, "source": "guest",
                "message": "Hello", "time": "2026-03-10T14:00:00", "read": False}]
        with patch.object(ss, "get_unread_guest_messages", return_value=raw):
            first = ss.sync_messages("fake-token")
            second = ss.sync_messages("fake-token")
        assert len(first) == 1
        assert len(second) == 0

    def test_skips_messages_without_id(self, sync_db):
        db, ss = sync_db
        raw = [{"bookingId": 500, "source": "guest", "message": "No ID"}]
        with patch.object(ss, "get_unread_guest_messages", return_value=raw):
            result = ss.sync_messages("fake-token")
        assert len(result) == 0

    def test_empty_api_response(self, sync_db):
        db, ss = sync_db
        with patch.object(ss, "get_unread_guest_messages", return_value=[]):
            result = ss.sync_messages("fake-token")
        assert result == []


# ---------------------------------------------------------------------------
# generate_and_save_draft
# ---------------------------------------------------------------------------

class TestGenerateAndSaveDraft:
    def test_happy_path(self, sync_db):
        db, ss = sync_db
        msg_id, _ = db.upsert_message(1, 500, 10, "guest", "When is check-in?",
                                       "2026-03-10T14:00:00", False)
        message = db.get_message_by_id(msg_id)

        with patch.object(ss, "sync_thread_to_db"), \
             patch.object(ss, "sync_booking_to_db", return_value={"guestName": "Taro"}), \
             patch.object(ss, "generate_reply", return_value="Check-in is at 3pm"):
            result = ss.generate_and_save_draft(message, "fake-token")

        assert result == "Check-in is at 3pm"
        draft = db.get_draft(msg_id)
        assert draft is not None
        assert draft["draft_text"] == "Check-in is at 3pm"
        updated = db.get_message_by_id(msg_id)
        assert updated["status"] == "draft_ready"


# ---------------------------------------------------------------------------
# build_conversation_summary
# ---------------------------------------------------------------------------

class TestBuildConversationSummary:
    def test_basic_summary(self, sync_db):
        _, ss = sync_db
        thread = [
            {"source": "guest", "message": "Hello"},
            {"source": "host", "message": "Welcome!"},
        ]
        result = ss.build_conversation_summary(thread)
        assert "ゲスト: Hello" in result
        assert "ホスト: Welcome!" in result

    def test_truncation_at_max_items(self, sync_db):
        _, ss = sync_db
        thread = [{"source": "guest", "message": f"Msg {i}"} for i in range(10)]
        result = ss.build_conversation_summary(thread, max_items=3)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        # Should keep the last 3
        assert "Msg 7" in result
        assert "Msg 9" in result

    def test_long_message_truncated_at_120(self, sync_db):
        _, ss = sync_db
        long_msg = "A" * 200
        thread = [{"source": "guest", "message": long_msg}]
        result = ss.build_conversation_summary(thread)
        # The message portion should be at most 120 chars
        text_part = result.split(": ", 1)[1]
        assert len(text_part) <= 120

    def test_newlines_replaced_with_space(self, sync_db):
        _, ss = sync_db
        thread = [{"source": "guest", "message": "Line1\nLine2\nLine3"}]
        result = ss.build_conversation_summary(thread)
        assert "\n" not in result.split(": ", 1)[1]

    def test_empty_thread(self, sync_db):
        _, ss = sync_db
        assert ss.build_conversation_summary([]) == ""


# ---------------------------------------------------------------------------
# _upsert_booking_from_api
# ---------------------------------------------------------------------------

class TestUpsertBookingFromApi:
    def test_field_mapping(self, sync_db, sample_booking):
        db, ss = sync_db
        ss._upsert_booking_from_api(sample_booking)
        b = db.get_booking(500)
        assert b is not None
        assert b["guest_name"] == "Taro Yamada"
        assert b["check_in"] == "2026-03-13"
        assert b["check_out"] == "2026-03-15"
        assert b["property_name"] == "Sakura House"
        assert b["num_adult"] == 2
        assert b["num_child"] == 1

    def test_missing_booking_id_does_nothing(self, sync_db):
        db, ss = sync_db
        ss._upsert_booking_from_api({"guestName": "Nobody"})
        # No booking should exist
        assert db.get_booking(0) is None


# ---------------------------------------------------------------------------
# _process_proactive_booking
# ---------------------------------------------------------------------------

class TestProcessProactiveBooking:
    def test_happy_path(self, sync_db, sample_booking):
        db, ss = sync_db
        metrics = {"proactive_generated": 0, "proactive_errors": 0}

        with patch.object(ss, "generate_proactive_message", return_value="Welcome!"), \
             patch.object(ss, "send_proactive_line_message") as mock_line:
            ss._process_proactive_booking(sample_booking, "pre_checkin", metrics)

        assert metrics["proactive_generated"] == 1
        assert metrics["proactive_errors"] == 0
        mock_line.assert_called_once()
        assert db.has_proactive(500, "pre_checkin")

    def test_ai_failure(self, sync_db, sample_booking):
        db, ss = sync_db
        metrics = {"proactive_generated": 0, "proactive_errors": 0}

        with patch.object(ss, "generate_proactive_message", side_effect=Exception("AI down")):
            ss._process_proactive_booking(sample_booking, "pre_checkin", metrics)

        assert metrics["proactive_generated"] == 0
        assert metrics["proactive_errors"] == 1
        assert not db.has_proactive(500, "pre_checkin")

    def test_line_failure_still_saves_draft(self, sync_db, sample_booking):
        db, ss = sync_db
        metrics = {"proactive_generated": 0, "proactive_errors": 0}

        with patch.object(ss, "generate_proactive_message", return_value="Welcome!"), \
             patch.object(ss, "send_proactive_line_message", side_effect=Exception("LINE down")):
            ss._process_proactive_booking(sample_booking, "pre_checkin", metrics)

        # AI generation succeeded even though LINE failed
        assert metrics["proactive_generated"] == 1
        assert db.has_proactive(500, "pre_checkin")


# ---------------------------------------------------------------------------
# check_proactive_triggers
# ---------------------------------------------------------------------------

class TestCheckProactiveTriggers:
    def test_pre_checkin_detected(self, sync_db, sample_booking):
        db, ss = sync_db
        checkin_booking = {**sample_booking, "bookingId": 600}

        with patch.object(ss, "get_bookings_by_date_range", return_value=[checkin_booking]), \
             patch.object(ss, "get_bookings_by_checkout_range", return_value=[]), \
             patch.object(ss, "generate_proactive_message", return_value="Welcome!"), \
             patch.object(ss, "send_proactive_line_message"):
            metrics = ss.check_proactive_triggers("fake-token")

        assert metrics["proactive_generated"] == 1

    def test_post_checkout_detected(self, sync_db, sample_booking):
        db, ss = sync_db
        checkout_booking = {**sample_booking, "bookingId": 700}

        with patch.object(ss, "get_bookings_by_date_range", return_value=[]), \
             patch.object(ss, "get_bookings_by_checkout_range", return_value=[checkout_booking]), \
             patch.object(ss, "generate_proactive_message", return_value="Thank you!"), \
             patch.object(ss, "send_proactive_line_message"):
            metrics = ss.check_proactive_triggers("fake-token")

        assert metrics["proactive_generated"] == 1

    def test_skip_if_already_has_proactive(self, sync_db, sample_booking):
        db, ss = sync_db
        db.save_proactive_draft(500, 10, "pre_checkin", "Already sent", "model")

        with patch.object(ss, "get_bookings_by_date_range", return_value=[sample_booking]), \
             patch.object(ss, "get_bookings_by_checkout_range", return_value=[]), \
             patch.object(ss, "generate_proactive_message") as mock_ai:
            metrics = ss.check_proactive_triggers("fake-token")

        mock_ai.assert_not_called()
        assert metrics["proactive_generated"] == 0

    def test_skip_if_recent_conversation(self, sync_db, sample_booking):
        db, ss = sync_db
        recent_time = datetime.now(timezone.utc).isoformat()
        db.upsert_message(1, 500, 10, "guest", "Hi", recent_time, False)

        with patch.object(ss, "get_bookings_by_date_range", return_value=[sample_booking]), \
             patch.object(ss, "get_bookings_by_checkout_range", return_value=[]), \
             patch.object(ss, "generate_proactive_message") as mock_ai:
            metrics = ss.check_proactive_triggers("fake-token")

        mock_ai.assert_not_called()
        assert metrics["proactive_generated"] == 0

    def test_skip_booking_without_id(self, sync_db):
        db, ss = sync_db
        no_id = {"guestName": "Ghost"}

        with patch.object(ss, "get_bookings_by_date_range", return_value=[no_id]), \
             patch.object(ss, "get_bookings_by_checkout_range", return_value=[]), \
             patch.object(ss, "generate_proactive_message") as mock_ai:
            metrics = ss.check_proactive_triggers("fake-token")

        mock_ai.assert_not_called()


# ---------------------------------------------------------------------------
# run_once
# ---------------------------------------------------------------------------

class TestRunOnce:
    def test_no_token_returns_empty_metrics(self, sync_db):
        _, ss = sync_db
        with patch.object(ss, "get_access_token", return_value=None):
            metrics = ss.run_once()
        assert metrics["messages_processed"] == 0
        assert metrics["drafts_generated"] == 0

    def test_no_messages_still_checks_proactive(self, sync_db):
        _, ss = sync_db
        with patch.object(ss, "get_access_token", return_value="token"), \
             patch.object(ss, "sync_messages", return_value=[]), \
             patch.object(ss, "check_proactive_triggers", return_value={"proactive_generated": 2, "proactive_errors": 0}) as mock_pro:
            # Also need to mock get_unprocessed_guest_messages to return empty
            with patch("db.get_unprocessed_guest_messages", return_value=[]):
                metrics = ss.run_once()
        mock_pro.assert_called_once()
        assert metrics["proactive_generated"] == 2

    def test_full_flow_with_messages(self, sync_db):
        db, ss = sync_db
        msg_id, _ = db.upsert_message(1, 500, 10, "guest", "When is check-in?",
                                       "2026-03-10T14:00:00", False)
        msg = db.get_message_by_id(msg_id)

        with patch.object(ss, "get_access_token", return_value="token"), \
             patch.object(ss, "sync_messages", return_value=[msg]), \
             patch.object(ss, "generate_and_save_draft", return_value="3pm"), \
             patch.object(ss, "send_line_message"), \
             patch.object(ss, "check_proactive_triggers", return_value={"proactive_generated": 0, "proactive_errors": 0}):
            # Mock stuck messages to empty
            with patch("db.get_unprocessed_guest_messages", return_value=[]):
                metrics = ss.run_once()
        assert metrics["messages_processed"] == 1
        assert metrics["drafts_generated"] == 1

    def test_ai_error_counted(self, sync_db):
        db, ss = sync_db
        msg_id, _ = db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T14:00:00", False)
        msg = db.get_message_by_id(msg_id)

        with patch.object(ss, "get_access_token", return_value="token"), \
             patch.object(ss, "sync_messages", return_value=[msg]), \
             patch.object(ss, "generate_and_save_draft", side_effect=Exception("AI error")), \
             patch.object(ss, "check_proactive_triggers", return_value={"proactive_generated": 0, "proactive_errors": 0}):
            with patch("db.get_unprocessed_guest_messages", return_value=[]):
                metrics = ss.run_once()
        assert metrics["errors"] == 1
        assert metrics["drafts_generated"] == 0


# ---------------------------------------------------------------------------
# Booking grouping logic
# ---------------------------------------------------------------------------

class TestBookingGrouping:
    def test_same_booking_grouped_latest_only(self, sync_db):
        db, ss = sync_db
        id1, _ = db.upsert_message(1, 500, 10, "guest", "First", "2026-03-10T10:00:00", False)
        id2, _ = db.upsert_message(2, 500, 10, "guest", "Second", "2026-03-10T11:00:00", False)
        id3, _ = db.upsert_message(3, 501, 10, "guest", "Other booking", "2026-03-10T10:30:00", False)

        msg1 = db.get_message_by_id(id1)
        msg2 = db.get_message_by_id(id2)
        msg3 = db.get_message_by_id(id3)

        draft_calls = []

        def mock_generate(msg, token):
            draft_calls.append(msg["id"])
            return "Reply"

        with patch.object(ss, "get_access_token", return_value="token"), \
             patch.object(ss, "sync_messages", return_value=[msg1, msg2, msg3]), \
             patch.object(ss, "generate_and_save_draft", side_effect=mock_generate), \
             patch.object(ss, "send_line_message"), \
             patch.object(ss, "check_proactive_triggers", return_value={"proactive_generated": 0, "proactive_errors": 0}):
            with patch("db.get_unprocessed_guest_messages", return_value=[]):
                metrics = ss.run_once()

        # Should process 2 messages (1 per booking), not 3
        assert metrics["messages_processed"] == 2
        # For booking 500, only the latest (id2) should be processed
        assert id2 in draft_calls
        assert id1 not in draft_calls
