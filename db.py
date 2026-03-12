"""
db.py — DB接続・CRUD関数
全エントリーポイント（LINE/Web/CLI/sync_service）が共通利用する。

DATABASE_URL 環境変数で切り替え:
  - 未設定 or sqlite:// → SQLite（ローカル開発）
  - postgresql://       → PostgreSQL（Supabase本番）
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
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
                num_adult INTEGER DEFAULT 0,
                num_child INTEGER DEFAULT 0,
                guest_country TEXT,
                guest_language TEXT,
                guest_arrival_time TEXT,
                guest_comments TEXT,
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

            CREATE TABLE IF NOT EXISTS proactive_messages (
                id SERIAL PRIMARY KEY,
                beds24_booking_id INTEGER NOT NULL,
                property_id INTEGER,
                trigger_type TEXT NOT NULL,
                status TEXT DEFAULT 'draft_ready',
                draft_text TEXT,
                model TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(beds24_booking_id, trigger_type)
            );
            CREATE INDEX IF NOT EXISTS idx_proactive_booking ON proactive_messages(beds24_booking_id);
            CREATE INDEX IF NOT EXISTS idx_proactive_status ON proactive_messages(status);

            CREATE TABLE IF NOT EXISTS editing_state (
                user_id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS devices (
                id SERIAL PRIMARY KEY,
                supabase_user_id TEXT NOT NULL,
                fcm_token TEXT UNIQUE NOT NULL,
                platform TEXT NOT NULL,
                app_version TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_active_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(supabase_user_id);

            CREATE TABLE IF NOT EXISTS user_settings (
                supabase_user_id TEXT PRIMARY KEY,
                notify_new_message BOOLEAN DEFAULT TRUE,
                notify_proactive BOOLEAN DEFAULT TRUE,
                notify_reminder BOOLEAN DEFAULT TRUE,
                line_fallback BOOLEAN DEFAULT TRUE,
                ai_tone TEXT DEFAULT 'friendly',
                ai_signature TEXT DEFAULT '民泊スタッフ一同',
                theme TEXT DEFAULT 'system',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS user_properties (
                supabase_user_id TEXT NOT NULL,
                property_id INTEGER NOT NULL,
                permission TEXT DEFAULT 'manage',
                PRIMARY KEY (supabase_user_id, property_id)
            );
            CREATE INDEX IF NOT EXISTS idx_user_properties_user ON user_properties(supabase_user_id);
            CREATE INDEX IF NOT EXISTS idx_user_properties_property ON user_properties(property_id);
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
                num_adult INTEGER DEFAULT 0,
                num_child INTEGER DEFAULT 0,
                guest_country TEXT,
                guest_language TEXT,
                guest_arrival_time TEXT,
                guest_comments TEXT,
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

            CREATE TABLE IF NOT EXISTS proactive_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                beds24_booking_id INTEGER NOT NULL,
                property_id INTEGER,
                trigger_type TEXT NOT NULL,
                status TEXT DEFAULT 'draft_ready',
                draft_text TEXT,
                model TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(beds24_booking_id, trigger_type)
            );
            CREATE INDEX IF NOT EXISTS idx_proactive_booking ON proactive_messages(beds24_booking_id);
            CREATE INDEX IF NOT EXISTS idx_proactive_status ON proactive_messages(status);

            CREATE TABLE IF NOT EXISTS editing_state (
                user_id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supabase_user_id TEXT NOT NULL,
                fcm_token TEXT UNIQUE NOT NULL,
                platform TEXT NOT NULL,
                app_version TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(supabase_user_id);

            CREATE TABLE IF NOT EXISTS user_settings (
                supabase_user_id TEXT PRIMARY KEY,
                notify_new_message INTEGER DEFAULT 1,
                notify_proactive INTEGER DEFAULT 1,
                notify_reminder INTEGER DEFAULT 1,
                line_fallback INTEGER DEFAULT 1,
                ai_tone TEXT DEFAULT 'friendly',
                ai_signature TEXT DEFAULT '民泊スタッフ一同',
                theme TEXT DEFAULT 'system',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_properties (
                supabase_user_id TEXT NOT NULL,
                property_id INTEGER NOT NULL,
                permission TEXT DEFAULT 'manage',
                PRIMARY KEY (supabase_user_id, property_id)
            );
            CREATE INDEX IF NOT EXISTS idx_user_properties_user ON user_properties(supabase_user_id);
            CREATE INDEX IF NOT EXISTS idx_user_properties_property ON user_properties(property_id);
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
               LEFT JOIN ai_drafts d ON d.id = (
                   SELECT d2.id FROM ai_drafts d2
                   WHERE d2.message_id = m.id
                   ORDER BY d2.created_at DESC, d2.id DESC
                   LIMIT 1
               )
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
    num_adult: int = 0,
    num_child: int = 0,
    guest_country: str = "",
    guest_language: str = "",
    guest_arrival_time: str = "",
    guest_comments: str = "",
) -> None:
    ph = _PH
    with _get_conn() as conn:
        _execute(conn,
            f"""INSERT INTO bookings (beds24_booking_id, property_id, guest_name, check_in, check_out, property_name,
                   num_adult, num_child, guest_country, guest_language, guest_arrival_time, guest_comments)
               VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
               ON CONFLICT(beds24_booking_id) DO UPDATE SET
                 property_id = EXCLUDED.property_id,
                 guest_name = EXCLUDED.guest_name,
                 check_in = EXCLUDED.check_in,
                 check_out = EXCLUDED.check_out,
                 property_name = EXCLUDED.property_name,
                 num_adult = EXCLUDED.num_adult,
                 num_child = EXCLUDED.num_child,
                 guest_country = EXCLUDED.guest_country,
                 guest_language = EXCLUDED.guest_language,
                 guest_arrival_time = EXCLUDED.guest_arrival_time,
                 guest_comments = EXCLUDED.guest_comments""",
            (beds24_booking_id, property_id, guest_name, check_in, check_out, property_name,
             num_adult, num_child, guest_country, guest_language, guest_arrival_time, guest_comments))


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


# ── プロアクティブメッセージ ──

def has_proactive(beds24_booking_id: int, trigger_type: str) -> bool:
    """指定予約・トリガーのプロアクティブメッセージが既に存在するか。"""
    ph = _PH
    with _get_conn() as conn:
        row = _fetchone(conn,
            f"SELECT id FROM proactive_messages WHERE beds24_booking_id = {ph} AND trigger_type = {ph}",
            (beds24_booking_id, trigger_type))
        return row is not None


def save_proactive_draft(
    beds24_booking_id: int,
    property_id: int | None,
    trigger_type: str,
    draft_text: str,
    model: str,
) -> int | None:
    ph = _PH
    with _get_conn() as conn:
        return _execute(conn,
            f"""INSERT INTO proactive_messages (beds24_booking_id, property_id, trigger_type, draft_text, model)
               VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
               ON CONFLICT(beds24_booking_id, trigger_type) DO UPDATE SET
                 draft_text = EXCLUDED.draft_text,
                 model = EXCLUDED.model,
                 status = 'draft_ready'""",
            (beds24_booking_id, property_id, trigger_type, draft_text, model))


def get_proactive_by_id(proactive_id: int) -> dict | None:
    ph = _PH
    with _get_conn() as conn:
        return _fetchone(conn, f"SELECT * FROM proactive_messages WHERE id = {ph}", (proactive_id,))


def get_draft_ready_proactive() -> list[dict]:
    with _get_conn() as conn:
        return _fetchall(conn,
            "SELECT * FROM proactive_messages WHERE status = 'draft_ready' ORDER BY created_at")


def update_proactive_status(proactive_id: int, status: str) -> None:
    ph = _PH
    with _get_conn() as conn:
        _execute(conn, f"UPDATE proactive_messages SET status = {ph} WHERE id = {ph}", (status, proactive_id))


def has_recent_conversation(beds24_booking_id: int, hours: int = 48) -> bool:
    """指定予約に最近のメッセージがあるか（プロアクティブ送信スキップ判定用）。"""
    ph = _PH
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with _get_conn() as conn:
        row = _fetchone(conn,
            f"SELECT id FROM messages WHERE booking_id = {ph} AND sent_at > {ph} LIMIT 1",
            (beds24_booking_id, cutoff))
        return row is not None


# ── 編集ステート（LINE） ──

def save_editing_state(user_id: str, message_id: str) -> None:
    """LINE編集ステートを保存（user_id → message_id）。既存なら上書き。"""
    ph = _PH
    with _get_conn() as conn:
        _execute(conn,
            f"""INSERT INTO editing_state (user_id, message_id)
               VALUES ({ph}, {ph})
               ON CONFLICT(user_id) DO UPDATE SET message_id = EXCLUDED.message_id""",
            (user_id, str(message_id)))


def get_editing_state(user_id: str) -> str | None:
    """LINE編集ステートを取得。なければNone。"""
    ph = _PH
    with _get_conn() as conn:
        row = _fetchone(conn, f"SELECT message_id FROM editing_state WHERE user_id = {ph}", (user_id,))
        return row["message_id"] if row else None


def delete_editing_state(user_id: str) -> None:
    """LINE編集ステートを削除。"""
    ph = _PH
    with _get_conn() as conn:
        _execute(conn, f"DELETE FROM editing_state WHERE user_id = {ph}", (user_id,))


# ── デバイス管理（モバイルアプリ） ──

def upsert_device(user_id: str, fcm_token: str, platform: str, app_version: str | None = None) -> None:
    """デバイスを登録/更新（fcm_tokenの重複時は上書き）。"""
    ph = _PH
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        _execute(conn,
            f"""INSERT INTO devices (supabase_user_id, fcm_token, platform, app_version, last_active_at)
               VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
               ON CONFLICT(fcm_token) DO UPDATE SET
                 supabase_user_id = EXCLUDED.supabase_user_id,
                 platform = EXCLUDED.platform,
                 app_version = EXCLUDED.app_version,
                 last_active_at = EXCLUDED.last_active_at""",
            (user_id, fcm_token, platform, app_version, now))


def get_devices_for_property(property_id: int) -> list[dict]:
    """プロパティに関連するユーザーのデバイス一覧を取得。"""
    ph = _PH
    with _get_conn() as conn:
        return _fetchall(conn,
            f"""SELECT d.* FROM devices d
               INNER JOIN user_properties up ON d.supabase_user_id = up.supabase_user_id
               WHERE up.property_id = {ph}""",
            (property_id,))


def delete_device(fcm_token: str, user_id: str | None = None) -> None:
    """デバイスを削除。user_id指定時はオーナーシップチェック付き。"""
    ph = _PH
    with _get_conn() as conn:
        if user_id:
            _execute(conn,
                     f"DELETE FROM devices WHERE fcm_token = {ph} AND supabase_user_id = {ph}",
                     (fcm_token, user_id))
        else:
            _execute(conn, f"DELETE FROM devices WHERE fcm_token = {ph}", (fcm_token,))


# ── ユーザー設定（モバイルアプリ） ──

def get_user_settings(user_id: str) -> dict:
    """ユーザー設定を取得。なければデフォルトで作成して返す。"""
    ph = _PH
    with _get_conn() as conn:
        row = _fetchone(conn, f"SELECT * FROM user_settings WHERE supabase_user_id = {ph}", (user_id,))
        if row:
            return row
        # デフォルト設定を作成
        _execute(conn,
            f"INSERT INTO user_settings (supabase_user_id) VALUES ({ph})",
            (user_id,))
        row = _fetchone(conn, f"SELECT * FROM user_settings WHERE supabase_user_id = {ph}", (user_id,))
        return row or {
            "supabase_user_id": user_id,
            "notify_new_message": True,
            "notify_proactive": True,
            "notify_reminder": True,
            "line_fallback": True,
            "ai_tone": "friendly",
            "ai_signature": "民泊スタッフ一同",
            "theme": "system",
        }


def upsert_user_settings(user_id: str, **kwargs) -> None:
    """ユーザー設定を更新。存在しなければ作成。"""
    ph = _PH
    allowed_keys = {
        "notify_new_message", "notify_proactive", "notify_reminder",
        "line_fallback", "ai_tone", "ai_signature", "theme",
    }
    filtered = {k: v for k, v in kwargs.items() if k in allowed_keys and v is not None}
    if not filtered:
        return

    with _get_conn() as conn:
        # Ensure row exists
        existing = _fetchone(conn, f"SELECT supabase_user_id FROM user_settings WHERE supabase_user_id = {ph}", (user_id,))
        if not existing:
            _execute(conn, f"INSERT INTO user_settings (supabase_user_id) VALUES ({ph})", (user_id,))

        # Build UPDATE
        set_clauses = [f"{k} = {ph}" for k in filtered]
        values = list(filtered.values()) + [user_id]
        _execute(conn,
            f"UPDATE user_settings SET {', '.join(set_clauses)} WHERE supabase_user_id = {ph}",
            tuple(values))


# ── ユーザー⇔プロパティ関連（モバイルアプリ） ──

def get_user_properties(user_id: str) -> list[dict]:
    """ユーザーに関連するプロパティIDリストを取得。"""
    ph = _PH
    with _get_conn() as conn:
        return _fetchall(conn,
            f"SELECT * FROM user_properties WHERE supabase_user_id = {ph}",
            (user_id,))


def add_user_property(user_id: str, property_id: int, permission: str = "manage") -> None:
    """ユーザーにプロパティを関連付ける。"""
    ph = _PH
    with _get_conn() as conn:
        _execute(conn,
            f"""INSERT INTO user_properties (supabase_user_id, property_id, permission)
               VALUES ({ph}, {ph}, {ph})
               ON CONFLICT(supabase_user_id, property_id) DO UPDATE SET
                 permission = EXCLUDED.permission""",
            (user_id, property_id, permission))


# ── メッセージ履歴（モバイルアプリ） ──

def get_messages_history(
    property_ids: list[int],
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """指定プロパティの処理済みメッセージ履歴を取得。"""
    if not property_ids:
        return []
    ph = _PH
    placeholders = ", ".join([ph] * len(property_ids))

    where_clauses = [f"m.property_id IN ({placeholders})"]
    params = list(property_ids)

    if status_filter and status_filter != "all":
        where_clauses.append(f"m.status = {ph}")
        params.append(status_filter)
    else:
        # Exclude unprocessed messages — only show sent/skipped/draft_ready
        where_clauses.append("m.status != 'unprocessed'")

    where_sql = " AND ".join(where_clauses)
    params.extend([limit, offset])

    with _get_conn() as conn:
        return _fetchall(conn,
            f"""SELECT m.*, d.draft_text, d.model AS draft_model
               FROM messages m
               LEFT JOIN ai_drafts d ON d.id = (
                   SELECT d2.id FROM ai_drafts d2
                   WHERE d2.message_id = m.id
                   ORDER BY d2.created_at DESC, d2.id DESC
                   LIMIT 1
               )
               WHERE {where_sql}
               ORDER BY m.sent_at DESC
               LIMIT {ph} OFFSET {ph}""",
            tuple(params))


def get_message_detail(message_id: int) -> dict | None:
    """メッセージの詳細を取得（予約情報・スレッド・ドラフト付き）。"""
    ph = _PH
    with _get_conn() as conn:
        msg = _fetchone(conn,
            f"""SELECT m.*, d.draft_text, d.model AS draft_model, d.id AS draft_id
               FROM messages m
               LEFT JOIN ai_drafts d ON d.id = (
                   SELECT d2.id FROM ai_drafts d2
                   WHERE d2.message_id = m.id
                   ORDER BY d2.created_at DESC, d2.id DESC
                   LIMIT 1
               )
               WHERE m.id = {ph}""",
            (message_id,))
        if not msg:
            return None

        booking = _fetchone(conn,
            f"SELECT * FROM bookings WHERE beds24_booking_id = {ph}",
            (msg["booking_id"],))

        thread = _fetchall(conn,
            f"SELECT * FROM messages WHERE booking_id = {ph} ORDER BY sent_at",
            (msg["booking_id"],))

        return {
            "message": msg,
            "booking": booking,
            "thread": thread,
        }


def _migrate_bookings_add_guest_fields():
    """既存のbookingsテーブルに新カラムを追加するマイグレーション。
    カラムが既に存在する場合は何もしない（安全に再実行可能）。"""
    new_columns = [
        ("num_adult", "INTEGER DEFAULT 0"),
        ("num_child", "INTEGER DEFAULT 0"),
        ("guest_country", "TEXT DEFAULT ''"),
        ("guest_language", "TEXT DEFAULT ''"),
        ("guest_arrival_time", "TEXT DEFAULT ''"),
        ("guest_comments", "TEXT DEFAULT ''"),
    ]
    if _USE_PG:
        import psycopg2
        for col_name, col_type in new_columns:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            try:
                conn.cursor().execute(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_type}")
            except psycopg2.errors.DuplicateColumn:
                pass
            finally:
                conn.close()
    else:
        with _get_conn() as conn:
            for col_name, col_type in new_columns:
                try:
                    conn.execute(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass


def check_health() -> tuple[bool, str]:
    """DB接続テスト。(ok, message)を返す。"""
    try:
        with _get_conn() as conn:
            _fetchone(conn, "SELECT 1")
        return True, "connected"
    except Exception as e:
        return False, str(e)


# 起動時に自動でテーブル作成＋マイグレーション
init_db()
_migrate_bookings_add_guest_fields()
