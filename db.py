"""
db.py — DB接続・CRUD関数
全エントリーポイント（LINE/Web/CLI/sync_service）が共通利用する。

DATABASE_URL 環境変数で切り替え:
  - 未設定 or sqlite:// → SQLite（ローカル開発）
  - postgresql://       → PostgreSQL（Supabase本番）
"""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
_USE_PG = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

if _USE_PG:
    import psycopg2
    import psycopg2.extras

# SQLite fallback path
_SQLITE_PATH = os.getenv("MINPAKU_DB_PATH", str(Path(__file__).parent / "minpaku.db"))

# Placeholder: SQLite uses ?, PostgreSQL uses %s
_PH = "%s" if _USE_PG else "?"


@contextmanager
def _get_conn():
    """DB接続のコンテキストマネージャー。with文で使う。"""
    if _USE_PG:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _fetchall(conn, sql, params=()):
    """SELECT結果をlist[dict]で返す。"""
    if _USE_PG:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    else:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _fetchone(conn, sql, params=()):
    """SELECT結果を1件dictで返す。なければNone。"""
    if _USE_PG:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
    else:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def _execute(conn, sql, params=()):
    """INSERT/UPDATE実行。lastrowidを返す。"""
    if _USE_PG:
        cur = conn.cursor()
        # PostgreSQL: RETURNING id でlastrowidを取得
        if "INSERT" in sql.upper() and "RETURNING" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        cur.execute(sql, params)
        try:
            row = cur.fetchone()
            return row[0] if row else None
        except psycopg2.ProgrammingError:
            return None
    else:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def init_db():
    """テーブルが存在しなければ作成する。"""
    if _USE_PG:
        ddl = """
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                beds24_message_id INTEGER UNIQUE,
                booking_id INTEGER NOT NULL,
                property_id INTEGER,
                source TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                status TEXT DEFAULT 'unprocessed',
                synced_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_messages_booking ON messages(booking_id);
            CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
            CREATE INDEX IF NOT EXISTS idx_messages_beds24_id ON messages(beds24_message_id);

            CREATE TABLE IF NOT EXISTS ai_drafts (
                id SERIAL PRIMARY KEY,
                message_id INTEGER REFERENCES messages(id),
                booking_id INTEGER NOT NULL,
                draft_text TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_drafts_message ON ai_drafts(message_id);

            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                beds24_booking_id INTEGER UNIQUE NOT NULL,
                property_id INTEGER,
                guest_name TEXT,
                check_in TEXT,
                check_out TEXT,
                property_name TEXT,
                synced_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS action_logs (
                id SERIAL PRIMARY KEY,
                message_id INTEGER REFERENCES messages(id),
                draft_id INTEGER REFERENCES ai_drafts(id),
                action TEXT NOT NULL,
                final_text TEXT,
                channel TEXT NOT NULL,
                acted_at TIMESTAMPTZ DEFAULT NOW()
            );
        """
    else:
        ddl = """
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
        """
    with _get_conn() as conn:
        if _USE_PG:
            conn.cursor().execute(ddl)
        else:
            conn.executescript(ddl)


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
    Returns: (message_id, is_new)
    """
    ph = _PH
    with _get_conn() as conn:
        row = _fetchone(conn, f"SELECT id FROM messages WHERE beds24_message_id = {ph}", (beds24_message_id,))

        if row:
            msg_id = row["id"]
            _execute(conn, f"UPDATE messages SET is_read = {ph} WHERE id = {ph}", (int(is_read), msg_id))
            return msg_id, False

        msg_id = _execute(
            conn,
            f"""INSERT INTO messages
               (beds24_message_id, booking_id, property_id, source, message, sent_at, is_read)
               VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})""",
            (beds24_message_id, booking_id, property_id, source, message, sent_at, int(is_read)),
        )
        return msg_id, True


def get_unprocessed_guest_messages() -> list[dict]:
    with _get_conn() as conn:
        return _fetchall(conn, "SELECT * FROM messages WHERE status = 'unprocessed' AND source = 'guest' ORDER BY sent_at")


def get_draft_ready_messages() -> list[dict]:
    with _get_conn() as conn:
        return _fetchall(conn,
            """SELECT m.*, d.id AS draft_id, d.draft_text, d.model AS draft_model
               FROM messages m
               LEFT JOIN ai_drafts d ON d.message_id = m.id
               WHERE m.status = 'draft_ready'
               ORDER BY m.sent_at""")


def get_thread(booking_id: int) -> list[dict]:
    ph = _PH
    with _get_conn() as conn:
        return _fetchall(conn, f"SELECT * FROM messages WHERE booking_id = {ph} ORDER BY sent_at", (booking_id,))


def update_message_status(message_id: int, status: str) -> None:
    ph = _PH
    with _get_conn() as conn:
        _execute(conn, f"UPDATE messages SET status = {ph} WHERE id = {ph}", (status, message_id))


def get_message_by_id(message_id: int) -> dict | None:
    ph = _PH
    with _get_conn() as conn:
        return _fetchone(conn, f"SELECT * FROM messages WHERE id = {ph}", (message_id,))


# ── AIドラフト ──

def save_draft(message_id: int, booking_id: int, draft_text: str, model: str) -> int:
    ph = _PH
    with _get_conn() as conn:
        return _execute(conn,
            f"INSERT INTO ai_drafts (message_id, booking_id, draft_text, model) VALUES ({ph}, {ph}, {ph}, {ph})",
            (message_id, booking_id, draft_text, model))


def get_draft(message_id: int) -> dict | None:
    ph = _PH
    with _get_conn() as conn:
        return _fetchone(conn,
            f"SELECT * FROM ai_drafts WHERE message_id = {ph} ORDER BY created_at DESC LIMIT 1",
            (message_id,))


# ── 予約情報 ──

def upsert_booking(
    beds24_booking_id: int,
    property_id: int | None,
    guest_name: str,
    check_in: str,
    check_out: str,
    property_name: str,
) -> None:
    ph = _PH
    with _get_conn() as conn:
        _execute(conn,
            f"""INSERT INTO bookings (beds24_booking_id, property_id, guest_name, check_in, check_out, property_name)
               VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
               ON CONFLICT(beds24_booking_id) DO UPDATE SET
                 property_id = EXCLUDED.property_id,
                 guest_name = EXCLUDED.guest_name,
                 check_in = EXCLUDED.check_in,
                 check_out = EXCLUDED.check_out,
                 property_name = EXCLUDED.property_name""",
            (beds24_booking_id, property_id, guest_name, check_in, check_out, property_name))


def get_booking(beds24_booking_id: int) -> dict | None:
    ph = _PH
    with _get_conn() as conn:
        return _fetchone(conn, f"SELECT * FROM bookings WHERE beds24_booking_id = {ph}", (beds24_booking_id,))


# ── アクションログ ──

def log_action(
    message_id: int,
    draft_id: int | None,
    action: str,
    final_text: str | None,
    channel: str,
) -> None:
    ph = _PH
    with _get_conn() as conn:
        _execute(conn,
            f"INSERT INTO action_logs (message_id, draft_id, action, final_text, channel) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
            (message_id, draft_id, action, final_text, channel))


# 起動時に自動でテーブル作成
init_db()
