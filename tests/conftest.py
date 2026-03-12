"""
Shared fixtures for the Minpaku DX test suite.

Key design decisions:
- Each test gets its own temporary SQLite database via tmp_path
- The db module is reloaded per-test to pick up the new MINPAKU_DB_PATH
- External services (Beds24, Gemini, LINE) are never called
"""
import os
import importlib
import pytest


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """
    Provide a fresh SQLite database for each test.
    Returns the reloaded db module bound to the temp database.
    """
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("MINPAKU_DB_PATH", db_path)
    # Ensure SQLite mode — set to empty string (not delete) so load_dotenv
    # won't re-populate from .env file (override=False is the default)
    monkeypatch.setenv("DATABASE_URL", "")

    import db as db_module
    # Reload to pick up new env vars and re-run init_db()
    importlib.reload(db_module)
    return db_module


@pytest.fixture()
def sample_message():
    """A typical Beds24-style raw message dict."""
    return {
        "id": 1001,
        "bookingId": 500,
        "propertyId": 10,
        "source": "guest",
        "message": "What time is check-in?",
        "time": "2026-03-10T14:00:00",
        "read": False,
    }


@pytest.fixture()
def sample_booking():
    """A typical normalized booking dict."""
    return {
        "bookingId": 500,
        "propertyId": 10,
        "guestName": "Taro Yamada",
        "checkIn": "2026-03-13",
        "checkOut": "2026-03-15",
        "propertyName": "Sakura House",
        "numAdult": 2,
        "numChild": 1,
        "guestCountry": "JP",
        "guestLanguage": "ja",
        "guestArrivalTime": "15:00",
        "guestComments": "Late arrival",
    }
