"""
Tests for db.py — all CRUD functions against a temporary SQLite database.
"""
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# upsert_message
# ---------------------------------------------------------------------------

class TestUpsertMessage:
    def test_insert_new_message(self, test_db):
        msg_id, is_new = test_db.upsert_message(
            beds24_message_id=1001,
            booking_id=500,
            property_id=10,
            source="guest",
            message="Hello",
            sent_at="2026-03-10T14:00:00",
            is_read=False,
        )
        assert is_new is True
        assert isinstance(msg_id, int)

    def test_insert_returns_valid_id(self, test_db):
        msg_id, _ = test_db.upsert_message(
            beds24_message_id=1001, booking_id=500, property_id=10,
            source="guest", message="Hello", sent_at="2026-03-10T14:00:00", is_read=False,
        )
        row = test_db.get_message_by_id(msg_id)
        assert row is not None
        assert row["message"] == "Hello"

    def test_update_existing_message(self, test_db):
        msg_id1, is_new1 = test_db.upsert_message(
            beds24_message_id=1001, booking_id=500, property_id=10,
            source="guest", message="Hello", sent_at="2026-03-10T14:00:00", is_read=False,
        )
        msg_id2, is_new2 = test_db.upsert_message(
            beds24_message_id=1001, booking_id=500, property_id=10,
            source="guest", message="Hello", sent_at="2026-03-10T14:00:00", is_read=True,
        )
        assert is_new1 is True
        assert is_new2 is False
        assert msg_id1 == msg_id2

    def test_update_sets_is_read(self, test_db):
        msg_id, _ = test_db.upsert_message(
            beds24_message_id=1001, booking_id=500, property_id=10,
            source="guest", message="Hello", sent_at="2026-03-10T14:00:00", is_read=False,
        )
        test_db.upsert_message(
            beds24_message_id=1001, booking_id=500, property_id=10,
            source="guest", message="Hello", sent_at="2026-03-10T14:00:00", is_read=True,
        )
        row = test_db.get_message_by_id(msg_id)
        assert row["is_read"] == 1

    def test_different_beds24_ids_create_separate_rows(self, test_db):
        id1, new1 = test_db.upsert_message(
            beds24_message_id=1001, booking_id=500, property_id=10,
            source="guest", message="A", sent_at="2026-03-10T14:00:00", is_read=False,
        )
        id2, new2 = test_db.upsert_message(
            beds24_message_id=1002, booking_id=500, property_id=10,
            source="guest", message="B", sent_at="2026-03-10T14:01:00", is_read=False,
        )
        assert new1 is True and new2 is True
        assert id1 != id2


# ---------------------------------------------------------------------------
# get_unprocessed_guest_messages
# ---------------------------------------------------------------------------

class TestGetUnprocessedGuestMessages:
    def test_returns_only_unprocessed_guest(self, test_db):
        test_db.upsert_message(1, 500, 10, "guest", "Q1", "2026-03-10T10:00:00", False)
        test_db.upsert_message(2, 500, 10, "host", "A1", "2026-03-10T10:01:00", False)
        test_db.upsert_message(3, 501, 10, "guest", "Q2", "2026-03-10T10:02:00", False)

        msgs = test_db.get_unprocessed_guest_messages()
        assert len(msgs) == 2
        assert all(m["source"] == "guest" for m in msgs)

    def test_excludes_processed_messages(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        test_db.update_message_status(msg_id, "draft_ready")

        msgs = test_db.get_unprocessed_guest_messages()
        assert len(msgs) == 0

    def test_empty_when_no_messages(self, test_db):
        assert test_db.get_unprocessed_guest_messages() == []

    def test_ordered_by_sent_at(self, test_db):
        test_db.upsert_message(2, 500, 10, "guest", "Later", "2026-03-10T12:00:00", False)
        test_db.upsert_message(1, 500, 10, "guest", "Earlier", "2026-03-10T10:00:00", False)
        msgs = test_db.get_unprocessed_guest_messages()
        assert msgs[0]["message"] == "Earlier"
        assert msgs[1]["message"] == "Later"


# ---------------------------------------------------------------------------
# get_draft_ready_messages
# ---------------------------------------------------------------------------

class TestGetDraftReadyMessages:
    def test_returns_draft_ready_with_latest_draft(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        test_db.save_draft(msg_id, 500, "Draft v1", "gemini-2.5-flash")
        test_db.save_draft(msg_id, 500, "Draft v2", "gemini-2.5-flash")
        test_db.update_message_status(msg_id, "draft_ready")

        results = test_db.get_draft_ready_messages()
        assert len(results) == 1
        assert results[0]["draft_text"] == "Draft v2"

    def test_excludes_non_draft_ready(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        # status is still 'unprocessed'
        assert test_db.get_draft_ready_messages() == []

    def test_message_without_draft_still_returned(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        test_db.update_message_status(msg_id, "draft_ready")
        results = test_db.get_draft_ready_messages()
        assert len(results) == 1
        assert results[0]["draft_text"] is None


# ---------------------------------------------------------------------------
# get_thread
# ---------------------------------------------------------------------------

class TestGetThread:
    def test_returns_messages_for_booking(self, test_db):
        test_db.upsert_message(1, 500, 10, "guest", "Q1", "2026-03-10T10:00:00", False)
        test_db.upsert_message(2, 500, 10, "host", "A1", "2026-03-10T10:01:00", False)
        test_db.upsert_message(3, 999, 10, "guest", "Other", "2026-03-10T10:02:00", False)

        thread = test_db.get_thread(500)
        assert len(thread) == 2

    def test_ordered_by_sent_at(self, test_db):
        test_db.upsert_message(2, 500, 10, "host", "Reply", "2026-03-10T10:01:00", False)
        test_db.upsert_message(1, 500, 10, "guest", "Question", "2026-03-10T10:00:00", False)
        thread = test_db.get_thread(500)
        assert thread[0]["source"] == "guest"
        assert thread[1]["source"] == "host"

    def test_empty_thread(self, test_db):
        assert test_db.get_thread(999) == []


# ---------------------------------------------------------------------------
# update_message_status / get_message_by_id
# ---------------------------------------------------------------------------

class TestMessageStatus:
    def test_update_status(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        test_db.update_message_status(msg_id, "sent")
        row = test_db.get_message_by_id(msg_id)
        assert row["status"] == "sent"

    def test_get_nonexistent_message(self, test_db):
        assert test_db.get_message_by_id(99999) is None


# ---------------------------------------------------------------------------
# save_draft / get_draft
# ---------------------------------------------------------------------------

class TestDraft:
    def test_save_and_get_draft(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        draft_id = test_db.save_draft(msg_id, 500, "Hello reply", "gemini-2.5-flash")
        assert isinstance(draft_id, int)

        draft = test_db.get_draft(msg_id)
        assert draft is not None
        assert draft["draft_text"] == "Hello reply"
        assert draft["model"] == "gemini-2.5-flash"

    def test_multiple_drafts_returns_one(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        test_db.save_draft(msg_id, 500, "Old draft", "gemini-2.5-flash")
        test_db.save_draft(msg_id, 500, "New draft", "gemini-2.5-flash")
        draft = test_db.get_draft(msg_id)
        # get_draft returns one of the drafts (ordered by created_at DESC);
        # both share the same second-precision timestamp so either is acceptable
        assert draft["draft_text"] in ("Old draft", "New draft")

    def test_get_draft_nonexistent(self, test_db):
        assert test_db.get_draft(99999) is None


# ---------------------------------------------------------------------------
# upsert_booking / get_booking
# ---------------------------------------------------------------------------

class TestBooking:
    def test_insert_booking(self, test_db):
        test_db.upsert_booking(
            beds24_booking_id=500, property_id=10, guest_name="Taro",
            check_in="2026-03-13", check_out="2026-03-15", property_name="Sakura",
        )
        b = test_db.get_booking(500)
        assert b is not None
        assert b["guest_name"] == "Taro"
        assert b["property_name"] == "Sakura"

    def test_update_booking_on_conflict(self, test_db):
        test_db.upsert_booking(
            beds24_booking_id=500, property_id=10, guest_name="Taro",
            check_in="2026-03-13", check_out="2026-03-15", property_name="Sakura",
        )
        test_db.upsert_booking(
            beds24_booking_id=500, property_id=10, guest_name="Hanako",
            check_in="2026-03-13", check_out="2026-03-16", property_name="Sakura Updated",
        )
        b = test_db.get_booking(500)
        assert b["guest_name"] == "Hanako"
        assert b["check_out"] == "2026-03-16"
        assert b["property_name"] == "Sakura Updated"

    def test_booking_with_guest_fields(self, test_db):
        test_db.upsert_booking(
            beds24_booking_id=500, property_id=10, guest_name="Taro",
            check_in="2026-03-13", check_out="2026-03-15", property_name="Sakura",
            num_adult=2, num_child=1, guest_country="JP",
            guest_language="ja", guest_arrival_time="15:00",
            guest_comments="Late check-in",
        )
        b = test_db.get_booking(500)
        assert b["num_adult"] == 2
        assert b["num_child"] == 1
        assert b["guest_country"] == "JP"
        assert b["guest_language"] == "ja"
        assert b["guest_arrival_time"] == "15:00"
        assert b["guest_comments"] == "Late check-in"

    def test_get_nonexistent_booking(self, test_db):
        assert test_db.get_booking(99999) is None


# ---------------------------------------------------------------------------
# log_action
# ---------------------------------------------------------------------------

class TestLogAction:
    def test_log_action_inserts(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        draft_id = test_db.save_draft(msg_id, 500, "Draft", "model")
        # Should not raise
        test_db.log_action(msg_id, draft_id, "sent", "Final text", "line")

    def test_log_action_with_none_draft(self, test_db):
        msg_id, _ = test_db.upsert_message(1, 500, 10, "guest", "Q", "2026-03-10T10:00:00", False)
        test_db.log_action(msg_id, None, "skipped", None, "web")


# ---------------------------------------------------------------------------
# Proactive messages
# ---------------------------------------------------------------------------

class TestProactiveMessages:
    def test_has_proactive_false_initially(self, test_db):
        assert test_db.has_proactive(500, "pre_checkin") is False

    def test_save_and_has_proactive(self, test_db):
        test_db.save_proactive_draft(500, 10, "pre_checkin", "Welcome!", "gemini-2.5-flash")
        assert test_db.has_proactive(500, "pre_checkin") is True
        assert test_db.has_proactive(500, "post_checkout") is False

    def test_get_proactive_by_id(self, test_db):
        pro_id = test_db.save_proactive_draft(500, 10, "pre_checkin", "Welcome!", "gemini-2.5-flash")
        row = test_db.get_proactive_by_id(pro_id)
        assert row is not None
        assert row["draft_text"] == "Welcome!"
        assert row["trigger_type"] == "pre_checkin"
        assert row["status"] == "draft_ready"

    def test_get_proactive_by_id_nonexistent(self, test_db):
        assert test_db.get_proactive_by_id(99999) is None

    def test_get_draft_ready_proactive(self, test_db):
        test_db.save_proactive_draft(500, 10, "pre_checkin", "Welcome!", "gemini-2.5-flash")
        test_db.save_proactive_draft(501, 10, "post_checkout", "Thanks!", "gemini-2.5-flash")
        results = test_db.get_draft_ready_proactive()
        assert len(results) == 2

    def test_update_proactive_status(self, test_db):
        pro_id = test_db.save_proactive_draft(500, 10, "pre_checkin", "Welcome!", "gemini-2.5-flash")
        test_db.update_proactive_status(pro_id, "sent")
        row = test_db.get_proactive_by_id(pro_id)
        assert row["status"] == "sent"

    def test_update_proactive_excludes_from_draft_ready(self, test_db):
        pro_id = test_db.save_proactive_draft(500, 10, "pre_checkin", "Welcome!", "gemini-2.5-flash")
        test_db.update_proactive_status(pro_id, "sent")
        assert test_db.get_draft_ready_proactive() == []

    def test_upsert_proactive_on_conflict(self, test_db):
        id1 = test_db.save_proactive_draft(500, 10, "pre_checkin", "Version 1", "model1")
        id2 = test_db.save_proactive_draft(500, 10, "pre_checkin", "Version 2", "model2")
        # Same booking + trigger should upsert, so only one row
        results = test_db.get_draft_ready_proactive()
        assert len(results) == 1
        assert results[0]["draft_text"] == "Version 2"

    def test_upsert_proactive_resets_status(self, test_db):
        pro_id = test_db.save_proactive_draft(500, 10, "pre_checkin", "V1", "model")
        test_db.update_proactive_status(pro_id, "sent")
        # Re-insert should reset status to draft_ready
        test_db.save_proactive_draft(500, 10, "pre_checkin", "V2", "model")
        results = test_db.get_draft_ready_proactive()
        assert len(results) == 1
        assert results[0]["status"] == "draft_ready"


# ---------------------------------------------------------------------------
# has_recent_conversation
# ---------------------------------------------------------------------------

class TestHasRecentConversation:
    def test_no_messages_returns_false(self, test_db):
        assert test_db.has_recent_conversation(500) is False

    def test_recent_message_returns_true(self, test_db):
        recent_time = datetime.now(timezone.utc).isoformat()
        test_db.upsert_message(1, 500, 10, "guest", "Hi", recent_time, False)
        assert test_db.has_recent_conversation(500) is True

    def test_old_message_returns_false(self, test_db):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        test_db.upsert_message(1, 500, 10, "guest", "Hi", old_time, False)
        assert test_db.has_recent_conversation(500, hours=48) is False

    def test_custom_hours_window(self, test_db):
        # Message from 5 hours ago
        msg_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        test_db.upsert_message(1, 500, 10, "guest", "Hi", msg_time, False)
        assert test_db.has_recent_conversation(500, hours=6) is True
        assert test_db.has_recent_conversation(500, hours=4) is False


# ---------------------------------------------------------------------------
# Editing state
# ---------------------------------------------------------------------------

class TestEditingState:
    def test_save_and_get(self, test_db):
        test_db.save_editing_state("user_abc", "42")
        assert test_db.get_editing_state("user_abc") == "42"

    def test_get_nonexistent(self, test_db):
        assert test_db.get_editing_state("nobody") is None

    def test_upsert_overwrites(self, test_db):
        test_db.save_editing_state("user_abc", "42")
        test_db.save_editing_state("user_abc", "99")
        assert test_db.get_editing_state("user_abc") == "99"

    def test_delete(self, test_db):
        test_db.save_editing_state("user_abc", "42")
        test_db.delete_editing_state("user_abc")
        assert test_db.get_editing_state("user_abc") is None

    def test_delete_nonexistent_no_error(self, test_db):
        test_db.delete_editing_state("nobody")  # Should not raise

    def test_proactive_message_id_prefix(self, test_db):
        test_db.save_editing_state("user_abc", "pro_7")
        assert test_db.get_editing_state("user_abc") == "pro_7"


# ---------------------------------------------------------------------------
# check_health
# ---------------------------------------------------------------------------

class TestCheckHealth:
    def test_health_ok(self, test_db):
        ok, msg = test_db.check_health()
        assert ok is True
        assert msg == "connected"
