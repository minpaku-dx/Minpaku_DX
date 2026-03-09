"""
db.py — DB接続・CRUD関数
全エントリーポイント（LINE/Web/CLI/sync_service）が共通利用する。
開発段階: SQLite / サービス化: Supabase(PostgreSQL)に切り替え
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("MINPAKU_DB_PATH", str(Path(__file__).parent / "minpaku.db"))

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """テーブルが存在しなければ作成する。"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beds24_message_id INTEGER UNIQUE,
            booking_id INTEGER NOT NULL,
            property_id INTEGER,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            status TEXT DEFAULT 'unprocessed',
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_messages_booking ON messages(booking_id);
        CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
        CREATE INDEX IF NOT EXISTS idx_messages_beds24_id ON messages(beds24_message_id);

        CREATE TABLE IF NOT EXISTS ai_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER REFERENCES messages(id),
            booking_id INTEGER NOT NULL,
            draft_text TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_drafts_message ON ai_drafts(message_id);

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beds24_booking_id INTEGER UNIQUE NOT NULL,
            property_id INTEGER,
            guest_name TEXT,
            check_in TEXT,
            check_out TEXT,
            property_name TEXT,
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER REFERENCES messages(id),
            draft_id INTEGER REFERENCES ai_drafts(id),
            action TEXT NOT NULL,
            final_text TEXT,
            channel TEXT NOT NULL,
            acted_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# ── メッセージ ──

def upsert_message(
    beds24_message_id: int,
    booking_id: int,
    property_id: int | None,
    source: str,
    message: str,
    sent_at: str,
    is_read: bool,
) -> tuple[int, bool]:
    """
    beds24_message_idで重複チェック。新規ならINSERT、既存ならUPDATE。
    Returns: (message_id, is_new) — is_new=True なら新規挿入
    """
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM messages WHERE beds24_message_id = ?",
        (beds24_message_id,),
    )
    row = cur.fetchone()

    if row:
        msg_id = row["id"]
        cur.execute(
            "UPDATE messages SET is_read = ?, synced_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(is_read), msg_id),
        )
        conn.commit()
        conn.close()
        return msg_id, False

    cur.execute(
        """INSERT INTO messages
           (beds24_message_id, booking_id, property_id, source, message, sent_at, is_read)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (beds24_message_id, booking_id, property_id, source, message, sent_at, int(is_read)),
    )
    msg_id = cur.lastrowid
    conn.commit()
    conn.close()
    return msg_id, True


def get_unprocessed_guest_messages() -> list[dict]:
    """status='unprocessed' かつ source='guest' のメッセージを返す。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE status = 'unprocessed' AND source = 'guest' ORDER BY sent_at",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_draft_ready_messages() -> list[dict]:
    """status='draft_ready' のメッセージ + ai_drafts を結合して返す。"""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT m.*, d.id AS draft_id, d.draft_text, d.model AS draft_model
           FROM messages m
           LEFT JOIN ai_drafts d ON d.message_id = m.id
           WHERE m.status = 'draft_ready'
           ORDER BY m.sent_at""",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_thread(booking_id: int) -> list[dict]:
    """指定booking_idの全メッセージを時系列順で返す。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE booking_id = ? ORDER BY sent_at",
        (booking_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_message_status(message_id: int, status: str) -> None:
    """メッセージのstatusを更新する。"""
    conn = _get_conn()
    conn.execute("UPDATE messages SET status = ? WHERE id = ?", (status, message_id))
    conn.commit()
    conn.close()


def get_message_by_id(message_id: int) -> dict | None:
    """message_idでメッセージを1件取得する。"""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── AIドラフト ──

def save_draft(message_id: int, booking_id: int, draft_text: str, model: str) -> int:
    """ai_draftsにINSERT。draft_idを返す。"""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO ai_drafts (message_id, booking_id, draft_text, model) VALUES (?, ?, ?, ?)",
        (message_id, booking_id, draft_text, model),
    )
    draft_id = cur.lastrowid
    conn.commit()
    conn.close()
    return draft_id


def get_draft(message_id: int) -> dict | None:
    """message_idに紐づく最新のドラフトを返す。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM ai_drafts WHERE message_id = ? ORDER BY created_at DESC LIMIT 1",
        (message_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── 予約情報 ──

def upsert_booking(
    beds24_booking_id: int,
    property_id: int | None,
    guest_name: str,
    check_in: str,
    check_out: str,
    property_name: str,
) -> None:
    """予約情報を保存/更新する。"""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO bookings (beds24_booking_id, property_id, guest_name, check_in, check_out, property_name)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(beds24_booking_id) DO UPDATE SET
             property_id = excluded.property_id,
             guest_name = excluded.guest_name,
             check_in = excluded.check_in,
             check_out = excluded.check_out,
             property_name = excluded.property_name,
             synced_at = CURRENT_TIMESTAMP""",
        (beds24_booking_id, property_id, guest_name, check_in, check_out, property_name),
    )
    conn.commit()
    conn.close()


def get_booking(beds24_booking_id: int) -> dict | None:
    """予約情報を返す。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM bookings WHERE beds24_booking_id = ?",
        (beds24_booking_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── アクションログ ──

def log_action(
    message_id: int,
    draft_id: int | None,
    action: str,
    final_text: str | None,
    channel: str,
) -> None:
    """送信/編集/スキップの記録をINSERT。"""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO action_logs (message_id, draft_id, action, final_text, channel) VALUES (?, ?, ?, ?, ?)",
        (message_id, draft_id, action, final_text, channel),
    )
    conn.commit()
    conn.close()


# 起動時に自動でテーブル作成
init_db()
