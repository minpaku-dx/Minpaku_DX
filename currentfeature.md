# Minpaku DX — 現在の機能詳細レポート

> 最終更新: 2026-03-12（セクション1-2, 5-6, 補足A-G を監査・修正。セクション2を大幅強化：読み込み箇所・未設定時挙動・バリデーション仕様を追記。補足C: proactiveインデックス追加。補足G: max-width修正、showToast修正、ラベル名修正）
> ステータス: 本番稼働中（Railway）

---

## 目次

| # | セクション | 成熟度 | 概要 |
|---|-----------|--------|------|
| 1 | [システム概要](#1-システム概要) | — | アーキテクチャ、技術スタック |
| 2 | [環境変数](#2-環境変数) | — | 必須/任意の設定一覧 |
| 3 | [データベーススキーマ](#3-データベーススキーマ) | — | デュアルバックエンド、4テーブル、リレーション、ステータス遷移 |
| 4 | [ファイル構成と各機能](#4-ファイル構成と各機能) | — | 全ソースファイルの詳細 |
| 4.1 | [app.py](#41-apppy--fastapi統合サーバー本番用) | **強化済** | FastAPI統合サーバー。Basic Auth・レートリミット・即時同期・LINEスキップ |
| 4.2 | [beds24.py](#42-beds24py--beds24-api連携) | **強化済** | Beds24 APIクライアント。ゲスト属性6フィールド追加 |
| 4.3 | [ai_engine.py](#43-ai_enginepy--ai返信生成エンジン) | **強化済** | Gemini AI返信生成。ゲスト属性注入・言語自動検出 |
| 4.4 | [line_notify.py](#44-line_notifypy--line通知送信) | **強化済** | LINE Flex Message送信。承認・修正・スキップ3ボタン完備 |
| 4.5 | [sync_service.py](#45-sync_servicepy--バックグラウンド同期サービス) | **強化済** | 同期・AI生成・通知の中核。booking_idグルーピング・リトライ機構 |
| 4.6 | [db.py](#46-dbpy--データベースレイヤー) | **強化済** | DB抽象化レイヤー。デュアルバックエンド・12フィールドupsert・自動マイグレーション |
| 4.7 | [cli.py](#47-clipy--cliツールターミナルからの承認) | **強化済** | ターミナル承認UI。ゲスト属性表示対応 |
| ~~4.8~~ | ~~web_app.py~~ | 削除済 | app.pyに統合済みのため削除 |
| 4.9 | [dashboard.html](#49-templatesdashboardhtml--webダッシュボード画面) | **強化済** | Web SPA。レスポンシブ対応完了 |
| 4.10 | [物件ルールファイル](#410-rulesproperty_206100md--物件ルールファイル) | — | 物件固有情報 |
| ~~4.11~~ | ~~レガシー・ユーティリティ~~ | 削除済 | web_app.py, line_webhook.py 削除。main.py はCLIランチャーとして残存 |
| 5 | [完全なデータフロー](#5-完全なデータフロー) | — | Beds24→DB→AI→LINE→承認→Beds24 |
| 6 | [デプロイ構成](#6-デプロイ構成) | — | Railway、依存パッケージ |
| 7 | [ファイル一覧](#7-ファイル一覧) | — | 全ファイルのサマリーテーブル |
| A | [補足A: 物件ルールファイル全文](#補足a-物件ルールファイルの全文rulesproperty_206100md) | — | property_206100.md の全文 |
| B | [補足B: LINE Flex Message JSON](#補足b-line-flex-messageの完全なjson構造) | — | Flex Messageの完全JSON |
| C | [補足C: DB関数の全SQL](#補足c-db関数の全sqlクエリ) | — | 全SQLクエリ一覧 |
| D | [補足D: エラーハンドリング](#補足d-エラーハンドリング全パターン) | — | 全ファイルのエラー処理 |
| E | [補足E: ステータス遷移](#補足e-ステータス遷移の全パターンエラー時含む) | — | messages.statusの全遷移図 |
| F | [補足F: APScheduler設定](#補足f-apschedulerの設定詳細) | — | バックグラウンドジョブ設定 |
| G | [補足G: Webダッシュボード詳細](#補足g-webダッシュボードdashboardhtmlのuicssjs詳細) | — | CSS/JS/UIの詳細 |
| 8 | [不完全な部分・既知の問題](#8-不完全な部分既知の問題改善が必要な箇所) | — | バグ、不足機能、改善点 |

---

## 1. システム概要

Minpaku DXは民泊ゲストメッセージの自動応答システム。
Beds24（PMS）から未読ゲストメッセージを検出し、AIが返信案を生成し、LINEでオーナーに承認を求め、承認後にBeds24経由でゲストに送信する。

### アーキテクチャ
```
Beds24 (PMS)
  ↕ API
FastAPI Server (app.py) ← Railway上で稼働
  ├── Background Sync (APScheduler, 5分間隔)
  │     └── Beds24 → DB → AI生成 → LINE通知
  │     └── unprocessed リトライ（AI生成失敗分の自動再処理）
  ├── LINE Webhook
  │     └── POST /callback — オーナーの承認/修正/スキップ → Beds24に送信
  ├── Web Dashboard
  │     ├── GET  /             — ダッシュボードHTML（Basic Auth）
  │     ├── GET  /api/messages — draft_ready + proactiveメッセージ一覧（JSON）
  │     ├── POST /api/send     — メッセージ承認・送信
  │     └── POST /api/skip     — メッセージスキップ
  └── GET /health — ヘルスチェック（同期ステータス含む）

DB: PostgreSQL (Supabase) / SQLite (開発時)
AI: Google Gemini 2.5 Flash
通知: LINE Messaging API
```

---

## 2. 環境変数

### 2.1 起動時バリデーション

`app.py` は起動時に以下5変数の存在を検証する（`REQUIRED_ENV_VARS` リスト）。未設定の変数があればログに `ERROR` を出力するが、**サーバーは停止しない**（部分稼働を許容する設計）。

### 2.2 必須環境変数

| 変数名 | 読み込み箇所 | 用途 | 未設定時の挙動 |
|--------|-------------|------|---------------|
| `REFRESH_TOKEN` | `beds24.py:13` | Beds24 API認証用リフレッシュトークン。アクセストークン取得に使用 | Beds24 API呼び出しが全て失敗（同期不能） |
| `GEMINI_API_KEY` | `ai_engine.py:8` | Google Gemini AI APIキー。`genai.Client(api_key=...)` に渡される | AI返信生成が全て失敗（ドラフト生成不能） |
| `LINE_CHANNEL_ACCESS_TOKEN` | `app.py:47`, `line_notify.py:18` | LINE Messaging APIトークン。Webhook応答とプッシュ通知の両方で使用 | LINE通知送信失敗、Webhook応答不能 |
| `LINE_CHANNEL_SECRET` | `app.py:46` | LINE Webhook署名検証用シークレット。`getenv` のデフォルトは `""`、空文字の場合は `WebhookHandler("dummy-secret-for-init")` で初期化される | Webhook署名検証が常に失敗（LINE経由の承認不能） |
| `LINE_OWNER_USER_ID` | `line_notify.py:19` | LINE通知送信先のオーナーUser ID。`push_message(to=...)` の宛先 | LINE通知の送信先が不明で失敗 |

### 2.3 任意環境変数

| 変数名 | 読み込み箇所 | 用途 | デフォルト値 |
|--------|-------------|------|-------------|
| `DATABASE_URL` | `db.py:18` | DB接続URL。`postgresql://` or `postgres://` で始まる場合はPostgreSQL、それ以外はSQLiteにフォールバック | `""` → SQLite使用 |
| `DASHBOARD_USER` | `app.py:74` | Web Dashboard Basic Auth ユーザー名 | `""` → ダッシュボード無効（503を返す） |
| `DASHBOARD_PASS` | `app.py:75` | Web Dashboard Basic Auth パスワード | `""` → ダッシュボード無効（503を返す） |
| `SYNC_INTERVAL_SECONDS` | `app.py:48` | バックグラウンド同期の間隔（秒）。`int()` でパースされる | `"300"`（5分） |
| `MINPAKU_DB_PATH` | `db.py:26` | SQLiteファイルパス（PostgreSQL使用時は無視される） | `Path(__file__).parent / "minpaku.db"` |

### 2.4 Procfile経由の環境変数

| 変数名 | 用途 | デフォルト値 |
|--------|------|-------------|
| `PORT` | uvicornのリッスンポート。Procfile内で `--port ${PORT:-8000}` として参照される。**Pythonコード内では `os.getenv` で読み取っていない** — Railwayが自動設定し、シェル変数としてuvicornに渡される | `8000`（Procfileのシェルデフォルト） |

> **補足:** `DASHBOARD_USER`/`DASHBOARD_PASS` は任意だが、ダッシュボードを使う場合は実質必須。両方が空文字の場合、`verify_credentials()` が常に `False` を返し、全ダッシュボードエンドポイントが503を返す（安全デフォルト）。

---

## 3. データベーススキーマ

### 3.0 デュアルバックエンド構成

`db.py` はPostgreSQLとSQLiteの両方をサポートする。環境変数 `DATABASE_URL` で自動切替。

| 条件 | バックエンド | 用途 |
|------|-------------|------|
| `DATABASE_URL` が `postgresql://` or `postgres://` で始まる | PostgreSQL (Supabase) | 本番環境 |
| `DATABASE_URL` 未設定 or それ以外 | SQLite (`minpaku.db`) | ローカル開発 |

**内部の違い:**
- プレースホルダー: PG = `%s`, SQLite = `?`（`_PH` 変数で切替）
- ID生成: PG = `SERIAL` + `RETURNING id`, SQLite = `INTEGER PRIMARY KEY AUTOINCREMENT` + `lastrowid`
- タイムスタンプ: PG = `TIMESTAMPTZ DEFAULT NOW()`, SQLite = `TEXT DEFAULT CURRENT_TIMESTAMP`
- 接続: `_get_conn()` コンテキストマネージャーで統一。PGはrollback/commit付き、SQLiteはWALモード+外部キー有効化

**テーブル初期化:** `init_db()` は `db.py` のモジュールインポート時に自動実行される（`app.py` の lifespan 内ではない）。どのファイルが最初に `import db` しても、テーブルが存在しなければ作成される。その直後に `_migrate_bookings_add_guest_fields()` が実行され、既存のbookingsテーブルにゲスト属性カラムが追加される（冪等）。

---

### 3.1 messagesテーブル

全てのBeds24メッセージ（ゲスト・ホスト両方）を格納。

| カラム | 型 (PG / SQLite) | 制約 | 用途 |
|--------|-------------------|------|------|
| `id` | SERIAL / INTEGER AUTOINCREMENT | PRIMARY KEY | 内部ID |
| `beds24_message_id` | INTEGER | UNIQUE | Beds24のメッセージID |
| `booking_id` | INTEGER | NOT NULL | 予約ID |
| `property_id` | INTEGER | （なし = NULLABLE） | 物件ID |
| `source` | TEXT | NOT NULL | Beds24 APIから取得。値は `'guest'` or `'host'`（空文字の可能性あり — `sync_thread_to_db` 経由時） |
| `message` | TEXT | NOT NULL | メッセージ本文 |
| `sent_at` | TEXT | NOT NULL | Beds24上の送信日時 |
| `is_read` | INTEGER | DEFAULT 0 | 既読フラグ（0/1） |
| `status` | TEXT | DEFAULT `'unprocessed'` | ワークフローステータス（下記参照） |
| `synced_at` | TIMESTAMPTZ / TEXT | DEFAULT NOW() / CURRENT_TIMESTAMP | DBに保存された日時 |

**インデックス:**
- `idx_messages_booking` ON `messages(booking_id)`
- `idx_messages_status` ON `messages(status)`
- `idx_messages_beds24_id` ON `messages(beds24_message_id)`

**Upsert動作 (`upsert_message`):**
`beds24_message_id` で重複チェック。新規ならINSERT、既存なら **`is_read` のみUPDATE**（message本文やsourceは更新しない）。返り値は `(message_id, is_new)`。

**ステータス遷移:**

```
                    sync_service.py
                    (AI生成成功)
unprocessed ──────────────────────────→ draft_ready
     │                                      │
     │ AI生成失敗時:                         ├──→ sent     (LINE承認 / LINE修正 / Web送信 / CLI送信)
     │ unprocessedのまま残留                  │
     └─→ 次回サイクルで自動リトライ            └──→ skipped  (LINE / Web / CLI)
```

| 遷移 | トリガー | ファイル:行 |
|------|----------|------------|
| `unprocessed → draft_ready` | AI draft生成成功 | `sync_service.py:133` |
| `draft_ready → sent` | LINE: オーナーが「承認して送信」タップ | `app.py:139` |
| `draft_ready → sent` | LINE: オーナーが修正テキスト送信 | `app.py:173` |
| `draft_ready → sent` | Web: 送信ボタン（原文 or 編集済み） | `app.py:250` |
| `draft_ready → sent` | CLI: 送信確認後 | `cli.py:205` |
| `draft_ready → skipped` | LINE: オーナーが「スキップ」タップ | `app.py:154` |
| `draft_ready → skipped` | Web: スキップボタン | `app.py:265` |
| `draft_ready → skipped` | CLI: スキップ選択 | `cli.py:190` |

**注意:** LINEのFlex Messageには「承認して送信」「修正する」「スキップ」の3ボタン。全チャネル（LINE/Web/CLI）でスキップ可能。

**`action_logs.action` の決定ロジック:**
- LINE承認 → `'sent'`（channel=`'line'`）
- LINE修正 → `'edited'`（channel=`'line'`）
- LINEスキップ → `'skipped'`（channel=`'line'`）
- Web → `final_text == draft_text` なら `'sent'`、異なれば `'edited'`（channel=`'web'`）
- Webスキップ → `'skipped'`（channel=`'web'`）
- CLI → 送信確認後 `'sent'`、編集送信 `'edited'`、スキップ `'skipped'`（channel=`'cli'`）

---

### 3.2 ai_draftsテーブル

AI生成された返信ドラフトを格納。**1つのメッセージに対して複数のドラフトが存在しうる**（AI生成リトライ時、古いドラフトは削除されず新しいものが追加される）。`get_draft(message_id)` は `ORDER BY created_at DESC LIMIT 1` で最新のものを返す。

`get_draft_ready_messages()` は相関サブクエリで最新ドラフトのみをJOINする（`ORDER BY created_at DESC, id DESC LIMIT 1`）。複数ドラフトが存在しても重複行は発生しない。

| カラム | 型 (PG / SQLite) | 制約 | 用途 |
|--------|-------------------|------|------|
| `id` | SERIAL / INTEGER AUTOINCREMENT | PRIMARY KEY | 内部ID |
| `message_id` | INTEGER | REFERENCES messages(id) | 対象メッセージ |
| `booking_id` | INTEGER | NOT NULL | 予約ID |
| `draft_text` | TEXT | NOT NULL | AI生成テキスト |
| `model` | TEXT | NOT NULL | 使用モデル名（現在: `gemini-2.5-flash`） |
| `created_at` | TIMESTAMPTZ / TEXT | DEFAULT NOW() / CURRENT_TIMESTAMP | 生成日時 |

**インデックス:**
- `idx_drafts_message` ON `ai_drafts(message_id)`

---

### 3.3 bookingsテーブル

ゲスト・物件情報を格納。**全予約が自動同期されるわけではない。** `sync_booking_to_db()` はAIドラフト生成時にのみ呼ばれるため、DBに存在するのは一度でもメッセージ処理された予約のみ。

| カラム | 型 (PG / SQLite) | 制約 | 用途 |
|--------|-------------------|------|------|
| `id` | SERIAL / INTEGER AUTOINCREMENT | PRIMARY KEY | 内部ID |
| `beds24_booking_id` | INTEGER | UNIQUE NOT NULL | Beds24の予約ID |
| `property_id` | INTEGER | （なし = NULLABLE） | 物件ID |
| `guest_name` | TEXT | （なし = NULLABLE） | ゲスト氏名（`guestFirstName` + `guestLastName` を結合） |
| `check_in` | TEXT | （なし = NULLABLE） | チェックイン日（Beds24の `firstNight` フィールド） |
| `check_out` | TEXT | （なし = NULLABLE） | チェックアウト日（Beds24の `lastNight` フィールド） |
| `property_name` | TEXT | （なし = NULLABLE） | 物件名（Beds24の `propName` フィールド） |
| `num_adult` | INTEGER | DEFAULT 0 | 大人人数 |
| `num_child` | INTEGER | DEFAULT 0 | 子供人数 |
| `guest_country` | TEXT | DEFAULT '' | ゲスト国籍（Beds24の `guestCountry`） |
| `guest_language` | TEXT | DEFAULT '' | ゲスト言語（Beds24の `guestLanguage`） |
| `guest_arrival_time` | TEXT | DEFAULT '' | 到着予定時間（Beds24の `guestArrivalTime`） |
| `guest_comments` | TEXT | DEFAULT '' | ゲスト備考（Beds24の `guestComments`） |
| `synced_at` | TIMESTAMPTZ / TEXT | DEFAULT NOW() / CURRENT_TIMESTAMP | 同期日時 |

**Upsert動作 (`upsert_booking`):**
`beds24_booking_id` で重複チェック。`ON CONFLICT DO UPDATE SET` で全12フィールドを更新する（`upsert_message` とは異なり、全カラムが上書きされる）。

**マイグレーション:** `_migrate_bookings_add_guest_fields()` が `init_db()` の後に自動実行される。既存のbookingsテーブルに6つの新カラムを `ALTER TABLE ADD COLUMN` で追加する。カラムが既に存在する場合はスキップ（冪等）。PGでは `autocommit=True` で各カラムを個別に追加。

---

### 3.4 action_logsテーブル

全ての操作履歴を記録（監査ログ）。

| カラム | 型 (PG / SQLite) | 制約 | 用途 |
|--------|-------------------|------|------|
| `id` | SERIAL / INTEGER AUTOINCREMENT | PRIMARY KEY | 内部ID |
| `message_id` | INTEGER | REFERENCES messages(id) | 対象メッセージ |
| `draft_id` | INTEGER | REFERENCES ai_drafts(id) | 対象ドラフト（NULLの場合あり — ドラフトなしで編集送信時） |
| `action` | TEXT | NOT NULL | `'sent'`, `'edited'`, `'skipped'` |
| `final_text` | TEXT | （なし = NULLABLE） | 実際に送信されたテキスト（skipped時はNULL） |
| `channel` | TEXT | NOT NULL | `'line'`, `'web'`, `'cli'` |
| `acted_at` | TIMESTAMPTZ / TEXT | DEFAULT NOW() / CURRENT_TIMESTAMP | 操作日時 |

---

### 3.5 proactive_messagesテーブル

プロアクティブメッセージ（チェックイン前ウェルカム、チェックアウト後サンキュー）を管理。

| カラム | 型 (PG / SQLite) | 制約 | 用途 |
|--------|-------------------|------|------|
| `id` | SERIAL / INTEGER AUTOINCREMENT | PRIMARY KEY | 内部ID |
| `beds24_booking_id` | INTEGER | NOT NULL | 対象予約のBeds24 ID |
| `property_id` | INTEGER | （なし = NULLABLE） | 物件ID |
| `trigger_type` | TEXT | NOT NULL | `'pre_checkin'` or `'post_checkout'` |
| `status` | TEXT | DEFAULT 'draft_ready' | `'draft_ready'`, `'sent'`, `'skipped'` |
| `draft_text` | TEXT | （なし = NULLABLE） | AI生成されたメッセージ本文 |
| `model` | TEXT | （なし = NULLABLE） | 使用AIモデル名 |
| `created_at` | TIMESTAMPTZ / TEXT | DEFAULT NOW() / CURRENT_TIMESTAMP | 作成日時 |

**UNIQUE制約:** `(beds24_booking_id, trigger_type)` — 同一予約・同一トリガーの重複送信を防止。
**インデックス:** `idx_proactive_booking` (beds24_booking_id), `idx_proactive_status` (status)

---

### 3.6 editing_stateテーブル

LINE修正モードの状態をDB永続化（サーバー再起動でも維持）。

| カラム | 型 (PG / SQLite) | 制約 | 用途 |
|--------|-------------------|------|------|
| `user_id` | TEXT | PRIMARY KEY | LINEユーザーID |
| `message_id` | TEXT | NOT NULL | 編集対象のメッセージID（通常: `"123"`, プロアクティブ: `"pro_123"`） |
| `created_at` | TIMESTAMPTZ / TEXT | DEFAULT NOW() / CURRENT_TIMESTAMP | 保存日時 |

**Upsert動作:** `ON CONFLICT(user_id) DO UPDATE SET message_id = EXCLUDED.message_id`

---

### 3.7 テーブル間リレーション

```
messages (1) ←──── (N) ai_drafts
    │                      │
    │  message_id (FK)     │
    │                      │
    └──────┬───────────────┘
           │
           ▼
      action_logs
        ├── message_id (FK) → messages.id
        └── draft_id (FK)   → ai_drafts.id

bookings — 他テーブルとFKなし。アプリ層で紐付け。
proactive_messages — beds24_booking_id でbookingsと紐付け（FK制約なし）。
editing_state — 独立テーブル（user_id → message_id のKVストア）。
```

**注意:** `messages.booking_id` / `proactive_messages.beds24_booking_id` と `bookings.beds24_booking_id` の間にFOREIGN KEY制約はない。アプリケーションコード内で `db.get_booking()` を呼んで紐付けている。

---

## 4. ファイル構成と各機能

### 4.1 app.py — FastAPI統合サーバー（本番用）

Railway上で稼働する統合サーバー。LINE Webhook + Web Dashboard + Background Syncを1プロセスで実行。

**起動コマンド:** `uvicorn app:app --host 0.0.0.0 --port ${PORT}`

**起動時の処理（lifespanイベント）:**
- APSchedulerで `_sync_job()` → `sync_service.run_once()` を `SYNC_INTERVAL_SECONDS` 間隔で実行
- `scheduler.start()` で開始、FastAPI終了時に `scheduler.shutdown()` で停止
- 注意: `db.init_db()` はモジュールインポート時に自動実行される（lifespan内ではない）

**ヘルパー関数:**
- `reply_text(reply_token, text)` — LINE `ReplyMessageRequest` のラッパー（`MessagingApi.reply_message` を呼ぶ）
- `_send_to_beds24(booking_id, message) → bool` — `get_access_token()` + `send_reply()` のラッパー。トークンキャッシュあり（beds24.pyのTTL 20分キャッシュを使用）。Web経由と異なりリトライなし

**Pydanticモデル:**
- `SendRequest`: `{messageId: str|int|None, bookingId: int, message: str}` — messageIdは通常 `123` またはプロアクティブ `"pro_123"`
- `SkipRequest`: `{messageId: str|int|None}`

**編集ステート:**
- DB永続化（`editing_state` テーブル）。`db.save_editing_state()` / `db.get_editing_state()` / `db.delete_editing_state()` を使用。サーバー再起動でも維持される。
- プロアクティブメッセージの編集は `"pro_123"` 形式のIDで管理。

**APIエンドポイント:**

| メソッド | パス | 用途 |
|----------|------|------|
| POST | `/callback` | LINE Webhook受信 |
| GET | `/` | Webダッシュボード表示（`templates/dashboard.html`） |
| GET | `/api/messages` | 承認待ちメッセージ一覧（JSON） |
| POST | `/api/send` | メッセージ送信（Web経由） |
| POST | `/api/skip` | メッセージスキップ（Web経由） |
| GET | `/health` | ヘルスチェック — `{status, server_start_time, sync_interval, db, missing_env_vars, sync}` |

**LINE Webhookハンドラー:**

1. **PostbackEvent** (`handle_postback`)
   - パラメータ解析: `parse_qs(event.postback.data)` → `action=approve|edit|skip`, `pending_id={message_id}` or `pro_{proactive_id}`
   - **ルーティング:** `pending_id` が `"pro_"` で始まる場合は `_handle_proactive_postback()` に委譲
   - **ガード条件:** action/pending_id が None → return、メッセージがDBにない → "期限切れか処理済み"、status != 'draft_ready' → "既に処理済み"
   - **approve:**
     1. ドラフト取得（なければエラー返信）
     2. `_send_to_beds24()` でBeds24に送信
     3. 成功: `status='sent'`, `log_action(action='sent', channel='line')`
     4. 失敗: LINE返信: "送信失敗" （statusは `draft_ready` のまま）
   - **edit:**
     1. `db.save_editing_state(user_id, message_id)` でDB永続化
     2. LINE返信: "修正モード\n予約ID: {id}\n\n修正した返信文をこのチャットに入力してください。"
   - **skip:**
     1. `db.update_message_status(id, 'skipped')`, `db.log_action(action='skipped', channel='line')`
     2. LINE返信: "スキップしました"

   **プロアクティブ postback** (`_handle_proactive_postback`):
   - `pending_id` から `"pro_"` を除去してID取得 → `db.get_proactive_by_id()`
   - approve/edit/skip 同様の処理（`db.update_proactive_status()` を使用）

2. **MessageEvent** (`handle_message`)
   - `db.get_editing_state(user_id)` がNoneなら → 「未読メッセージの返信案は自動で届きます。」
   - 編集ステートがある場合:
     1. `db.delete_editing_state(user_id)` でステート消費
     2. `"pro_"` プレフィックスならプロアクティブメッセージの編集処理
     3. それ以外は通常メッセージの編集処理
     4. 送信失敗時: `db.save_editing_state()` でステート復元

**Web API詳細:**

- `POST /api/send` — 送信失敗時に**トークン再取得して1回リトライ**する。`final_text == draft_text` なら `action='sent'`、異なれば `action='edited'`。
- `POST /api/skip` — `log_action(action='skipped', channel='web')`。best-effort（messageId がなくても200を返す）。

---

### 4.2 beds24.py — Beds24 API連携

Beds24 REST API v2 と通信するクライアント。

**定数:**
- `BEDS24_API_BASE` = `"https://beds24.com/api/v2"`
- `REFRESH_TOKEN` = `os.getenv("REFRESH_TOKEN")`
- `MAX_PAGES` = 20（ページネーション上限、無限ループ防止）
- タイムアウト: 全リクエスト 10秒

**関数一覧:**

#### `get_access_token() → str | None`
- エンドポイント: `GET /authentication/token`
- ヘッダー: `refreshToken: {REFRESH_TOKEN}`
- 戻り値: アクセストークン文字列（失敗時 `None`）
- **TTLキャッシュ:** `threading.Lock` ベースの20分キャッシュ。`invalidate_token_cache()` で明示的無効化可能。

#### `_fetch_messages_paginated(token, params) → list[dict]`
- エンドポイント: `GET /bookings/messages`
- ページネーション: レスポンスの `pages.total` で総ページ数を確認し、全ページを巡回
- `MAX_PAGES` に達したら打ち切り
- 戻り値: 全ページのメッセージを結合したリスト（正規化前の生データ）

#### `_normalize_message(m) → dict`
- 入力: Beds24 APIレスポンスの1メッセージ
- 出力: `{id, bookingId, propertyId, message, time, source, read}`
- フォールバック: `propId` → `propertyId`（Beds24 APIのフィールド名揺れを吸収）

#### `get_unread_guest_messages(token) → list[dict]`
- `_fetch_messages_paginated(token, {"source": "guest", "read": "false"})` — APIフィルタでレスポンス量削減
- Python側フィルタも安全ネットとして残存: `source == 'guest'` AND `read == False`

#### `get_message_thread(token, booking_id) → list[dict]`
- `_fetch_messages_paginated(token, {"bookingId": booking_id})`
- `_normalize_message()` 後に `time` で時系列ソート
- 戻り値: 指定予約の全メッセージ

#### `_normalize_booking(b) → dict`
- APIレスポンスの予約データを統一スキーマに変換するヘルパー
- 出力: `{bookingId, guestName, checkIn, checkOut, propertyId, propertyName, numAdult, numChild, guestCountry, guestLanguage, guestArrivalTime, guestComments}`
- フォールバック: `guestFirstName` + `guestLastName` → `guestName`、`firstNight` → `checkIn`、`propId` → `propertyId` 等
- `get_booking_details()`, `get_bookings_by_date_range()`, `get_bookings_by_checkout_range()` の3関数が共通利用

#### `get_booking_details(token, booking_id) → dict`
- エンドポイント: `GET /bookings?bookingId={id}`
- `_normalize_booking()` で正規化して返す（12フィールド）

#### `get_bookings_by_date_range(token, arrival_from, arrival_to) → list[dict]`
- エンドポイント: `GET /bookings?arrivalFrom={date}&arrivalTo={date}`
- ページネーション対応（`MAX_PAGES` まで巡回）
- 戻り値: 指定期間にチェックインする予約リスト（`_normalize_booking()` 済み）
- **用途:** プロアクティブメッセージのpre_checkinトリガー検出

#### `get_bookings_by_checkout_range(token, departure_from, departure_to) → list[dict]`
- エンドポイント: `GET /bookings?departureFrom={date}&departureTo={date}`
- 同上のページネーション対応
- **用途:** プロアクティブメッセージのpost_checkoutトリガー検出

#### `invalidate_token_cache() → None`
- トークンキャッシュを無効化（認証エラー時に使用）

#### `send_reply(token, booking_id, message) → bool`
- エンドポイント: `POST /bookings/messages`
- ペイロード: `{bookingId, message, source: 'host'}`
- 戻り値: 成功時 `True`（HTTP 200/201）、失敗時 `False`

---

### 4.3 ai_engine.py — AI返信生成エンジン

Google Gemini を使ってゲストメッセージへの返信案を生成。

**定数・グローバル:**
- `GEMINI_API_KEY` = `os.getenv("GEMINI_API_KEY")`
- `RULES_DIR` = `Path(__file__).parent / "rules"` — 物件ルールファイルのディレクトリ
- `AI_MODEL` = `"gemini-2.5-flash"` — 使用モデル名。`sync_service.py` が `from ai_engine import AI_MODEL` でインポートし、DB記録に使用
- `_client` — モジュールレベルのグローバル変数（`genai.Client` のシングルトン）

**関数一覧:**

#### `_get_client() → genai.Client`
- 遅延初期化のシングルトン。初回呼び出し時に `genai.Client(api_key=GEMINI_API_KEY)` を生成、以降は再利用

#### `_load_property_rules(property_id) → str`
- 読み込み: `rules/property_{property_id}.md`
- 戻り値: ファイル内容（ファイルが存在しない場合は空文字列 `""`）

#### `_format_thread(thread: list[dict]) → str`
- 変換: `[{source: 'guest', message: 'Hello'}]` → `"ゲスト: Hello"`
- スレッドが空の場合: `"（会話履歴なし）"`
- 戻り値: 改行区切りの会話履歴テキスト

#### `_is_japanese(text) → bool`
- テキストにひらがな（U+3040-309F）、カタカナ（U+30A0-30FF）、CJK漢字（U+4E00-9FFF）のいずれかが含まれるかを判定
- 言語自動検出に使用（`guest_language` が未設定の場合のフォールバック）

#### `generate_reply(guest_message, property_id, thread, booking_info) → str`
- **パラメータ:**
  - `guest_message: str` — ゲストの最新メッセージ
  - `property_id: int` — 物件ID（ルールファイル読み込み用）
  - `thread: list[dict]` — 会話履歴（Beds24スキーマ形式: `{source, message, ...}`）
  - `booking_info: dict` — `{guestName, checkIn, checkOut, propertyName, numAdult, numChild, guestCountry, guestLanguage, guestArrivalTime, guestComments}`
- **プロンプト構造:**
  ```
  あなたはプロの民泊コンシェルジュです。以下の情報をもとに、ゲストへの丁寧な返信案を1つ作成してください。

  # 物件ルール
  {rules/property_{id}.mdの内容 or "（ルールファイルなし）"}

  # 予約情報
  - ゲスト名: {guestName}
  - 物件: {propertyName}
  - チェックイン: {checkIn}
  - チェックアウト: {checkOut}
  - 人数: 大人{numAdult}名、子供{numChild}名  ← 0でない場合のみ表示
  - 国籍: {guestCountry}                      ← 空でない場合のみ表示
  - 到着予定時間: {guestArrivalTime}            ← 空でない場合のみ表示
  - ゲストからの備考: {guestComments}            ← 空でない場合のみ表示

  # これまでの会話
  {会話履歴 or "（会話履歴なし）"}

  # ゲストの最新メッセージ
  {guest_message}

  【返信のルール】
  - 敬語・丁寧語を使う
  - 温かみのある表現にする
  - 物件ルールに基づいた正確な情報を含める
  - 署名は「民泊スタッフ一同」とする
  - 返信案のみを出力する（前置き・説明文は不要）
  - ゲストの言語は「{guestLanguage}」です。返信は{guestLanguage}で作成してください。  ← 言語指示（条件付き）
  ```
- **言語自動検出ロジック:**
  1. `booking_info.guestLanguage` が設定済み（ja/japanese/日本語以外）→ その言語で返信指示
  2. `guestLanguage` 未設定で `_is_japanese(guest_message)` が `False` → 「ゲストと同じ言語で返信」指示
  3. それ以外 → 言語指示なし（日本語デフォルト）
- **API呼び出し:** `client.models.generate_content(model=AI_MODEL, contents=prompt)`
- **戻り値:** `response.text`（生成テキストそのまま。後処理なし）

#### `generate_proactive_message(trigger_type, booking_info, property_id) → str`
- **パラメータ:**
  - `trigger_type: str` — `"pre_checkin"` or `"post_checkout"`
  - `booking_info: dict` — 予約情報（`_normalize_booking()` 形式）
  - `property_id: int` — 物件ID
- **プロンプト構造:**
  - 物件ルール + 予約情報 + ゲスト属性を注入（`generate_reply` と同様）
  - **pre_checkin:** ウェルカム挨拶、チェックイン案内、ゲスト属性に合わせたおすすめスポット提案（200〜400文字）
  - **post_checkout:** 感謝、旅の安全、さりげないレビュー依頼（100〜200文字）
- **言語判定:** `guestLanguage` があればその言語、海外ゲストなら英語、それ以外は日本語

---

### 4.4 line_notify.py — LINE通知送信

オーナーへのLINE通知を送信。Flex Messageで承認カードを構築。

**定数:**
- `CHANNEL_ACCESS_TOKEN` = `os.getenv("LINE_CHANNEL_ACCESS_TOKEN")`
- `OWNER_USER_ID` = `os.getenv("LINE_OWNER_USER_ID")`
- `configuration` — モジュールレベルで `Configuration(access_token=...)` を初期化

**関数一覧:**

#### `send_line_message(pending_id, booking_id, guest_message, ai_reply, conversation_history, guest_name, property_name) → None`
- **送信方式:** `PushMessageRequest`（Webhookの返信ではなく、任意タイミングでの送信）
- **パラメータ:**
  - `pending_id: str` — メッセージID（承認ボタンのpostbackデータに埋め込み）
  - `booking_id: str` — 予約ID
  - `guest_message: str` — ゲストメッセージ（**150文字に切り詰め**）
  - `ai_reply: str` — AI返信案（**300文字に切り詰め**）
  - `conversation_history: str` — 会話履歴サマリー（**500文字に切り詰め**）
  - `guest_name: str` — ゲスト名
  - `property_name: str` — 物件名

- **Flex Message構造:**
  ```
  ┌─ Header（背景: #f0f6ff）
  │  ├─ "新着ゲストメッセージ"（太字、青 #1a73e8）
  │  └─ サブタイトル（優先順位: ①guest_name | property_name → ②guest_name → ③property_name → ④予約ID: {booking_id}）
  │
  ├─ Body
  │  ├─ 予約ID（guest_name or property_name がある場合のみ表示）
  │  ├─ ─── separator ───
  │  ├─ "直近のやり取り"（conversation_history がある場合のみ表示）
  │  │   └─ {conversation_history}（xxsサイズ、灰色 #aaaaaa）
  │  ├─ ─── separator ───
  │  ├─ "ゲスト"
  │  │   └─ {guest_message}
  │  ├─ ─── separator ───
  │  └─ "AI返信案"
  │      └─ {ai_reply}
  │
  └─ Footer（横並び2ボタン）
     ├─ [承認して送信]（primary、青 #1a73e8 → postback: action=approve&pending_id={id}）
     └─ [修正する]（secondary → postback: action=edit&pending_id={id}）
  ```
- **alt_text:** `"新着: {guest_name or '予約'+booking_id} からのメッセージ"`
- **フッターボタン:** 「承認して送信」「修正する」が横並び、「スキップ」がその下（グレー `#aaaaaa`、視覚的に控えめ）

#### `send_proactive_line_message(proactive_id, booking_id, trigger_type, ai_message, guest_name, property_name, check_in, check_out) → None`
- プロアクティブメッセージ用のFlex Message
- **`pending_id`** に `"pro_"` プレフィックスを付与（例: `"pro_123"`）→ postbackでプロアクティブと識別
- **カラーテーマ:**
  - pre_checkin: 緑ヘッダー `#f0fff4` + ボタン `#06d6a0`
  - post_checkout: 紫ヘッダー `#f8f0ff` + ボタン `#7209b7`
- **ボディ:** 予約ID、IN/OUT日程、AIメッセージ案（400文字切り詰め）
- **フッター:** 通常メッセージと同じ3ボタン（承認/修正/スキップ）

---

### 4.5 sync_service.py — バックグラウンド同期サービス

Beds24とDBの同期、AI生成、LINE通知の中核。スタンドアロン実行も可能。

**起動方法:**
- `python sync_service.py` — ワンショット実行
- `python sync_service.py --poll --interval 300` — 5分間隔で常駐ポーリング
- 本番環境では `app.py` の APScheduler から `run_once()` が呼ばれる

**モデル名の管理:**
- `AI_MODEL` は `ai_engine.py` で一元定義（`"gemini-2.5-flash"`）
- `sync_service.py` は `from ai_engine import AI_MODEL` でインポートして `db.save_draft()` に渡す
- これによりDB記録のモデル名と実際の使用モデルが常に一致する

**定数:**
- `PROACTIVE_CHECKIN_DAYS_BEFORE` = 2 — チェックイン何日前にウェルカム送信
- `JST` = `timezone(timedelta(hours=9))` — 日本時間（トリガー日付計算用）

**関数一覧:**

#### `sync_messages(token) → list[dict]`
1. `get_unread_guest_messages(token)` で未読メッセージ取得
2. 各メッセージを `db.upsert_message()` でDB保存
3. `beds24_id` がないメッセージはスキップ（`continue`）
4. **新規メッセージのみリストで返す**（`is_new == True` のもの）

#### `sync_thread_to_db(token, booking_id) → None`
- 指定予約の全会話スレッドをBeds24から取得してDBに同期
- `get_message_thread()` → `db.upsert_message()` をループ

#### `sync_booking_to_db(token, booking_id) → dict`
- 予約詳細をBeds24から取得してDBに保存
- `get_booking_details()` → `db.upsert_booking()` （12フィールド: 基本6 + ゲスト属性6）
- 戻り値: Beds24からの予約情報dict（DBのdictではない）

#### `generate_and_save_draft(message, token) → str`
1. `sync_thread_to_db()` — 会話履歴をDB同期
2. `db.get_thread()` — DBから会話履歴取得
3. `sync_booking_to_db()` — 予約情報をDB同期
4. スレッドをBeds24スキーマに変換（`db.get_thread()` の結果を `{id, bookingId, propertyId, message, time, source, read}` 形式へ）
5. `generate_reply()` — AI返信生成
6. `db.save_draft()` — ドラフトをDB保存（`AI_MODEL` を記録）
7. `db.update_message_status()` → `'draft_ready'`
8. 戻り値: ドラフトテキスト

#### `build_conversation_summary(thread, max_items=5) → str`
- 直近 `max_items` 件の会話を `"ゲスト: {message}"` / `"ホスト: {message}"` 形式で返す
- 各メッセージは **120文字に切り詰め**、改行はスペースに置換

#### `_upsert_booking_from_api(booking) → None`
- Beds24 API応答の予約データを直接DBにupsertする（追加API呼び出し不要）
- `get_bookings_by_date_range()` 等で既に取得済みのデータを使って `db.upsert_booking()` を呼ぶ

#### `_process_proactive_booking(booking, trigger_type, metrics) → None`
- 1件のプロアクティブメッセージを生成→DB保存→LINE通知
- `_upsert_booking_from_api()` → `generate_proactive_message()` → `db.save_proactive_draft()` → `send_proactive_line_message()`

#### `check_proactive_triggers(token) → dict`
- **プロアクティブメッセージのトリガーチェック。** `run_once()` から呼ばれる。
- **Pre-check-in:** JST今日 + 2日後にチェックインする予約を `get_bookings_by_date_range()` で検出
  - スキップ: `db.has_proactive(id, "pre_checkin")` が True、または `db.has_recent_conversation(id, 48)` が True
- **Post-checkout:** JST昨日にチェックアウトした予約を `get_bookings_by_checkout_range()` で検出
  - スキップ: `db.has_proactive(id, "post_checkout")` が True、または `db.has_recent_conversation(id, 48)` が True
- 戻り値: `{"proactive_generated": N, "proactive_errors": N}`

#### `run_once() → dict`
**メイン処理フロー:**
1. `get_access_token()` — トークン取得（失敗時は `return metrics`）
2. `sync_messages(token)` — 新着メッセージ取得
3. `db.get_unprocessed_guest_messages()` — **リトライ対象**を取得
4. 新着 + リトライを統合（`seen_ids` で重複排除）
5. **Booking_idグルーピング:** 同一予約の複数メッセージは最新のみ処理
6. 各メッセージについて:
   - `generate_and_save_draft()` — AI生成（失敗しても次へ `continue`）
   - `send_line_message()` — LINE通知送信（失敗時: ログ出力 + `metrics["errors"]` カウンタ加算）
7. **`check_proactive_triggers(token)`** — プロアクティブメッセージのチェック
8. 戻り値: メトリクス辞書（`messages_processed`, `drafts_generated`, `line_notifications_sent`, `errors`, `proactive_generated`, `proactive_errors`）
- **注意:** メッセージが0件でもプロアクティブチェックは実行される

#### `run_poll(interval) → None`
- `run_once()` を `interval` 秒間隔で無限ループ
- `KeyboardInterrupt` で停止
- 予期しない例外: ログ出力 → **30秒待機** → 次サイクル

---

### 4.6 db.py — データベースレイヤー

SQLiteとPostgreSQLの両方をサポートするDB抽象化レイヤー。詳細はセクション3（デュアルバックエンド構成、テーブル定義、インデックス、upsert動作）を参照。

**内部ヘルパー:**
- `_get_conn()` — コンテキストマネージャー。PGは `autocommit=False` + 明示的 commit/rollback。SQLiteはWALモード + 外部キー有効化。
- `_fetchall(conn, sql, params)` → `list[dict]` — PGは `RealDictCursor`、SQLiteは `sqlite3.Row` → `dict` 変換
- `_fetchone(conn, sql, params)` → `dict | None` — 同上、1行のみ
- `_execute(conn, sql, params)` → `int | None` — INSERT時は `lastrowid` (SQLite) / `RETURNING id` (PG自動付与) を返す

**公開関数一覧（18関数 + 1マイグレーション）:**

| 関数 | 戻り値 | 用途 |
|------|--------|------|
| `init_db()` | None | テーブル作成（6テーブル、IF NOT EXISTS）。モジュールインポート時に自動実行 |
| `upsert_message(...)` | `(int, bool)` | メッセージupsert。既存は `is_read` のみ更新 |
| `get_unprocessed_guest_messages()` | `list[dict]` | `status='unprocessed' AND source='guest'`。リトライ対象の検出にも使用 |
| `get_draft_ready_messages()` | `list[dict]` | `status='draft_ready'`。相関サブクエリで最新ドラフトのみLEFT JOIN |
| `get_thread(booking_id)` | `list[dict]` | 会話スレッド全件（`sent_at` 順） |
| `update_message_status(id, status)` | None | ステータス更新 |
| `get_message_by_id(id)` | `dict\|None` | 1件取得 |
| `save_draft(...)` | `int` | AIドラフト保存。`draft_id` を返す |
| `get_draft(message_id)` | `dict\|None` | 最新ドラフト取得（`ORDER BY created_at DESC LIMIT 1`） |
| `upsert_booking(...)` | None | 予約upsert（12パラメータ）。`ON CONFLICT DO UPDATE SET` で全フィールド上書き |
| `get_booking(beds24_booking_id)` | `dict\|None` | 予約取得 |
| `log_action(...)` | None | 操作ログ記録 |
| `has_proactive(booking_id, trigger_type)` | `bool` | プロアクティブメッセージの存在チェック（重複防止） |
| `save_proactive_draft(booking_id, property_id, trigger_type, draft_text, model)` | `int\|None` | プロアクティブドラフトUPSERT（ON CONFLICT更新） |
| `get_proactive_by_id(id)` | `dict\|None` | プロアクティブメッセージ1件取得 |
| `get_draft_ready_proactive()` | `list[dict]` | 承認待ちプロアクティブ一覧 |
| `update_proactive_status(id, status)` | None | プロアクティブステータス更新 |
| `has_recent_conversation(booking_id, hours)` | `bool` | 最近の会話有無（`sent_at` ベース、パラメータ化クエリ） |
| `save_editing_state(user_id, message_id)` | None | LINE編集ステートをDBに保存（upsert） |
| `get_editing_state(user_id)` | `str\|None` | LINE編集ステート取得 |
| `delete_editing_state(user_id)` | None | LINE編集ステート削除 |
| `check_health()` | `(bool, str)` | DB接続テスト |
| `_migrate_bookings_add_guest_fields()` | None | マイグレーション: bookingsテーブルに6カラム追加（冪等） |

---

### 4.7 cli.py — CLIツール（ターミナルからの承認）

対話型のターミナルインターフェース。**`python main.py`** で起動（`main.py` が `cli.run_session()` を呼ぶ）。

**表示ヘルパー（ANSIカラー対応）:**
- `_line()`, `_header()`, `_section()`, `_wrap()`, `_badge()` — ターミナル装飾用
- `WIDTH = 62` — 表示幅

**操作フロー:**
1. `db.get_draft_ready_messages()` で承認待ち一覧取得
2. `get_access_token()` でBeds24トークン取得（失敗時は終了）
3. 各メッセージについて表示:
   - 予約情報（ゲスト名、物件、チェックイン/アウト、受信時刻）
   - 直近**6件**の会話履歴（未読ゲストメッセージは除外）
   - ゲストの最新メッセージ（ANSIカラーで `[未読]` マーク）
   - AI返信案
4. 操作選択: `[s] 送信` / `[e] 編集` / `[n] スキップ`
5. 編集モード: 複数行入力（**空行2回連続で確定**）。空入力時は元のドラフトを使用
6. 送信確認: `[y] 送信する` / `[n] キャンセル`
7. DB記録: `action='sent'`（原文一致）/ `'edited'`（変更あり）/ `'skipped'`、`channel='cli'`

---

### ~~4.8 web_app.py~~ — 削除済み (2026-03-11)

app.pyに統合済みのため削除。旧Flask版Webダッシュボード。

---

### 4.9 templates/dashboard.html — Webダッシュボード画面

シングルページアプリケーション（SPA）。`app.py` から配信される。

**画面構成:**
```
┌─ ナビバー（sticky、#1a1a2e、56px）
│  ├─ ブランド "Minpaku DX"（"DX" がシアン #4cc9f0）
│  ├─ 未読バッジ（#ef476f、"N 件" 表示）— id="unread-badge"
│  └─ 更新ボタン — id="refresh-btn"
│
├─ メインエリア（max-width: 920px、中央寄せ）
│  ├─ ローディング画面（スピナー + "メッセージを取得中..."）
│  ├─ 空画面（✅ + "未読のゲストメッセージはありません。"）
│  └─ カード一覧 — id="cards-container"
│     └─ 各カード:
│        ├─ ヘッダー部（#f8f9fb）
│        │  ├─ プロアクティブバッジ（type=proactiveの場合: pre_checkin=緑, post_checkout=紫）
│        │  ├─ ゲスト名チップ（青 .guest）
│        │  ├─ 予約IDチップ
│        │  ├─ 物件名チップ
│        │  ├─ IN/OUTチップ
│        │  ├─ タイムスタンプ（灰色 .time）
│        │  └─ ステータスバッジ（pending=#fff3cd / sent=#d1fae5 / skipped=#f0f0f0 / sending=#dbeafe）
│        │
│        ├─ ボディ（2カラムgrid、**640px以下で1カラムに切り替え**）
│        │  ├─ 左パネル:
│        │  │  ├─ 通常カード: 会話履歴（直近5件、未読ゲスト除外）+ ゲスト最新メッセージ（黄色ハイライト #fff8e1）
│        │  │  └─ プロアクティブカード: トリガー種別 + チェックイン/アウト日
│        │  └─ 右パネル: AI返信案（編集可能 textarea）+ AIバッジ / プロアクティブバッジ
│        │
│        └─ アクションバー
│           ├─ [スキップ]（灰色 .btn-skip）
│           └─ [送信]（緑 #06d6a0 .btn-send）
│
└─ トースト通知（右下固定、3500ms表示、✅/❌ プレフィックス付き）
```

**JavaScript状態管理:**
```javascript
let messages = [];           // 全メッセージ配列（サーバーから取得）
const skipped = new Set();   // スキップ済みID（クライアント側のみ）
const sent = new Set();      // 送信済みID（クライアント側のみ）
```

**JavaScript関数:**

| 関数 | 用途 |
|------|------|
| `loadMessages()` | `GET /api/messages` → `renderCards()` |
| `renderCards()` | カード一覧を再描画、未読バッジ更新 |
| `buildCard(m)` | 1枚のカードHTML生成。通常: スレッド未読ゲスト除外+最後5件+120文字切り詰め。プロアクティブ: トリガー種別+日付表示 |
| `sendMessage(id, bookingId)` | `POST /api/send`（IDは文字列化）→ 成功で `sent.add(id)`、失敗でトースト |
| `skipMessage(id)` | `POST /api/skip`（IDは文字列化、best-effort）→ `skipped.add(id)` → ボタン・textarea無効化 |
| `setCardLoading(id, loading)` | 送信中のUI状態管理（ボタン無効化、テキスト変更） |
| `updateCardStatus(id, cls, label)` | ステータスバッジとカードのCSSクラス更新 |
| `showScreen(which)` | 'loading' / 'empty' / 'cards' の表示切り替え |
| `showToast(msg, ok)` | 右下トースト表示（3500ms） |
| `escHtml(s)` | XSS対策。`& < > "` をエスケープ、`\n` を `<br>` に変換 |

**初期化:** ページロード時に `showScreen('loading')` → `loadMessages()` を自動実行

---

### 4.10 rules/property_206100.md — 物件ルールファイル

物件固有の情報をAIプロンプトに注入するためのMarkdownファイル。`ai_engine.py` の `_load_property_rules(property_id)` が `rules/property_{property_id}.md` を読み込む。

**現在の構成:**
```
# 平井戸建 (propertyId: 206100)

## 基本情報
- 住所: 東京都江戸川区平井1-18-7
- Amazon配送先住所
- チェックイン: 16:00〜23:00 / チェックアウト: 10:00

## 設備
- WiFi SSID: Hirai_Guest / パスワード: 要確認
- 騒音モニター（テレビ横、90dB超でアラート、録音なし）

## ハウスルール
- 全館禁煙、ゴミは室内にまとめる、騒音禁止

## アクセス・鍵
- 鍵の場所: 要確認 / チェックイン手順: 要確認

## 緊急連絡先
- オーナー連絡先: 要確認

## よくある質問
- 騒音モニターについて / 早期チェックイン / 駐車場 / 近隣コンビニ
```

**「要確認」が残っている項目:** WiFiパスワード、鍵の場所、チェックイン/アウト手順、緊急連絡先、駐車場、近隣コンビニ

---

### 4.11 レガシー・ユーティリティファイル

#### `main.py` — CLIエントリポイント
- `from cli import run_session` → `run_session()` を呼ぶだけ
- 起動時メッセージ: "Minpaku DX — CLI承認ツール"

#### ~~`web_app.py`~~ — 削除済み (2026-03-11)
#### ~~`line_webhook.py`~~ — 削除済み (2026-03-11)
#### ~~`get_token.py`~~ — 削除済み (2026-03-11)
#### ~~`import requests.py`~~ — 削除済み (2026-03-11)

---

## 5. 完全なデータフロー

### メインフロー: Beds24 → DB → AI → LINE → オーナー承認 → Beds24

```
[5分ごとのサイクル — sync_service.run_once()]

1. BEDS24メッセージ検出
   run_once()
   ├── get_access_token() → Beds24トークン取得（キャッシュ有、TTL 20分）
   │   └── トークン取得失敗 → metrics返却して終了（以降のステップは実行されない）
   └── sync_messages(token) — tokenは引数として受け取る
       ├── get_unread_guest_messages(token) → 未読ゲストメッセージ取得（全ページネーション）
       └── upsert_message() → DBに保存（新規の場合 status: 'unprocessed'）

1.5. リトライ対象の検出
   ├── db.get_unprocessed_guest_messages() → unprocessedのまま残っているメッセージ取得
   └── 新着 + リトライを統合（seen_idsセットで重複排除）

1.7. booking_idグルーピング（★ ドキュメント上の重要ステップ）
   ├── 同一booking_idの複数メッセージ → 最新（sent_at最大）のみ処理対象に
   ├── 理由: AIは全スレッドを参照するため、最新1件でゲスト意図を網羅可能
   ├── 古いメッセージはAI生成後に draft_ready に一括更新（リトライループ防止）
   └── スキップ件数をログ出力

2-3. AI返信生成（generate_and_save_draft() が一括実行）
   ├── [データ充実化]
   │   ├── sync_thread_to_db(token, booking_id) → 会話履歴を全件DB同期
   │   ├── db.get_thread(booking_id) → DB上のスレッド取得
   │   ├── sync_booking_to_db(token, booking_id) → 予約情報をDB同期
   │   │   └── 取得フィールド（11項目）:
   │   │       guestName, checkIn, checkOut, propertyId, propertyName,
   │   │       numAdult, numChild, guestCountry, guestLanguage,
   │   │       guestArrivalTime, guestComments
   │   └── thread形式をBeds24スキーマ→AI入力用に変換
   │
   ├── [AI生成]
   │   ├── generate_reply(guest_message, property_id, thread, booking_info)
   │   │   ├── _load_property_rules(property_id) → rules/property_{id}.md 読み込み
   │   │   ├── プロンプト構築: ルール + 予約情報(ゲスト属性含む) + 会話履歴 + 最新メッセージ
   │   │   ├── 言語自動検出: guest_language優先 → _is_japanese()フォールバック
   │   │   └── Gemini 2.5 Flash (ai_engine.AI_MODEL) で生成
   │   ├── db.save_draft(msg_id, booking_id, draft_text, AI_MODEL) → ai_draftsに保存
   │   └── db.update_message_status(msg_id, "draft_ready")
   │
   └── ★ 例外発生時: unprocessedのまま残留 → 次回サイクルで自動リトライ
       （同一予約の古いメッセージもdraft_readyに更新されない）

4. LINE通知（AI生成成功後に実行）
   ├── データ準備:
   │   ├── db.get_draft(msg_id) → ドラフト取得
   │   ├── db.get_booking(booking_id) → 予約情報取得
   │   ├── db.get_thread(booking_id) → スレッド取得
   │   └── build_conversation_summary(thread, max_items=5) → 最新5件の要約テキスト
   │
   └── send_line_message(pending_id, booking_id, guest_message, ai_reply,
           conversation_history, guest_name, property_name)
       └── Flex Message送信（承認/修正/スキップ 3ボタン付き）
           └── push_message(to=LINE_OWNER_USER_ID)

5. オーナー承認（3つのチャネル）

   [LINE経由 — handle_postback() + handle_message()]
   ※ LINE は _send_to_beds24() ラッパーを使用（get_access_token → send_reply、リトライなし）

   ├── 「承認して送信」→ PostbackEvent → _send_to_beds24() → Beds24に送信
   │   ├── 成功: status='sent' + log_action(action='sent', channel='line')
   │   └── 失敗: status='draft_ready' のまま維持 → 「再度お試しください」と返信
   ├── 「修正する」→ db.save_editing_state(user_id, msg_id) → 修正モード
   │   └── テキスト入力 → handle_message() → _send_to_beds24() → Beds24に送信
   │       ├── 成功: status='sent' + log_action(action='edited', channel='line')
   │       └── 失敗: editing_state再保存 → 「もう一度送信文を入力してください」
   ├── 「スキップ」→ status='skipped' + log_action(action='skipped', channel='line')
   │
   └── ★ プロアクティブの場合: pending_idが "pro_" プレフィックス
       → _handle_proactive_postback() にルーティング
       ├── 承認: _send_to_beds24() → 成功: proactive_messages.status='sent'
       │                          └── 失敗: status='draft_ready' のまま維持
       ├── 修正: db.save_editing_state(user_id, "pro_{id}") → 修正モード
       │   └── handle_message() → "pro_" 検出 → _send_to_beds24()
       │       ├── 成功: proactive_messages.status='sent'
       │       └── 失敗: editing_state再保存
       ├── スキップ: proactive_messages.status='skipped'
       └── ※ プロアクティブはaction_logsに記録しない

   [Web Dashboard経由 — POST /api/send, POST /api/skip]
   ※ Web は send_reply() を直接使用 + トークンリトライあり

   ├── POST /api/send → send_reply(token, bookingId, message) → Beds24に送信
   │   ├── 送信失敗時: invalidate_token_cache() → トークン再取得 → 1回リトライ
   │   ├── action判定: body.message == original_draft ? 'sent' : 'edited'
   │   ├── 通常メッセージ: status='sent' + log_action(channel='web')
   │   └── プロアクティブ (pro_プレフィックス): proactive_messages.status='sent'
   ├── POST /api/skip
   │   ├── 通常メッセージ: status='skipped' + log_action(action='skipped', channel='web')
   │   └── プロアクティブ: proactive_messages.status='skipped'

   [CLI経由 — cli.py（開発・デバッグ用）]
   ├── [e] 編集 → テキスト入力 → 再度選択に戻る（ループ）
   ├── [s] 送信 → confirm_send() で最終確認（[y]/[n]）
   │   └── [y] → send_reply() → Beds24に送信
   │       ├── action判定: final_reply == draft_text ? 'sent' : 'edited'
   │       └── log_action(action, final_reply, channel='cli')
   └── [n] スキップ → status='skipped' + log_action(action='skipped', channel='cli')

6. 記録
   ├── 通常メッセージ:
   │   └── db.log_action(message_id, draft_id, action, final_text, channel)
   │       → action_logsテーブルに記録
   │       action: 'sent' / 'edited' / 'skipped'
   │       channel: 'line' / 'web' / 'cli'
   └── プロアクティブメッセージ:
       └── db.update_proactive_status(proactive_id, status)
           → proactive_messages.statusのみ更新（action_logsには記録しない）

7. プロアクティブメッセージ（run_once()の末尾で毎サイクル実行）
   check_proactive_triggers(token)
   ├── ★ メッセージがない場合でも必ず実行される
   │
   ├── [pre_checkin] チェックイン2日前の予約を検出
   │   ├── target_date = today_jst + 2日
   │   ├── get_bookings_by_date_range(token, target_str, target_str) → ページネーション対応
   │   ├── 各予約: db.has_proactive(booking_id, 'pre_checkin') → 重複チェック
   │   ├── db.has_recent_conversation(booking_id, hours=48) → 会話あり→スキップ
   │   └── _process_proactive_booking(booking, 'pre_checkin', metrics)
   │       ├── _upsert_booking_from_api(booking) → 既取得データでDB保存（追加API不要）
   │       ├── generate_proactive_message('pre_checkin', booking, property_id) → AI生成
   │       ├── db.save_proactive_draft() → proactive_messagesに保存
   │       └── send_proactive_line_message() → LINE通知（緑テーマ）
   │
   └── [post_checkout] チェックアウト翌日の予約を検出
       ├── target_date = today_jst - 1日（yesterday）
       ├── get_bookings_by_checkout_range(token, yesterday_str, yesterday_str)
       ├── 各予約: has_proactive() → 重複チェック
       ├── has_recent_conversation(hours=48) → 会話あり→スキップ
       └── _process_proactive_booking(booking, 'post_checkout', metrics) — 紫テーマ

   ※ JST（UTC+9）で日付計算。PROACTIVE_CHECKIN_DAYS_BEFORE = 2（定数）
```

---

## 6. デプロイ構成

**プラットフォーム:** Railway
**Procfile:** `web: uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}`
**DB:** Supabase PostgreSQL（Tokyo リージョン）

**依存パッケージ:**
| パッケージ | 用途 |
|-----------|------|
| `requests` | Beds24 APIクライアント |
| `google-genai` | Google Gemini AI SDK |
| `python-dotenv` | 環境変数読み込み |
| `fastapi` | Webフレームワーク |
| `uvicorn[standard]` | ASGIサーバー |
| `apscheduler` | バックグラウンドジョブスケジューラ |
| `jinja2` | テンプレートエンジン |
| `line-bot-sdk` | LINE Messaging API SDK |
| `psycopg2-binary` | PostgreSQLアダプタ |
| `pytest` | テストフレームワーク（開発用） |
| `httpx` | 非同期HTTPクライアント（FastAPIテスト用） |

---

## 7. ファイル一覧

| ファイル | 役割 | ステータス | 起動方法 |
|---------|------|----------|---------|
| `app.py` | FastAPI統合サーバー | **本番** | `uvicorn app:app` |
| `beds24.py` | Beds24 APIクライアント | **本番** | インポートされる |
| `ai_engine.py` | AI返信生成 + プロアクティブメッセージ生成 | **本番** | インポートされる |
| `line_notify.py` | LINE通知送信（通常+プロアクティブ） | **本番** | インポートされる |
| `sync_service.py` | バックグラウンド同期 + プロアクティブトリガー | **本番** | `python sync_service.py` or app.pyから呼出 |
| `db.py` | データベースレイヤー（6テーブル、21+関数） | **本番** | インポートされる |
| `cli.py` | CLI承認インターフェース | **本番** | `python main.py` |
| `main.py` | CLIエントリポイント | **本番** | `python main.py` |
| `templates/dashboard.html` | Webダッシュボード画面（プロアクティブ対応） | **本番** | app.pyが配信 |
| `rules/property_*.md` | 物件ルールファイル | **本番** | ai_engine.pyが読み込み |
| ~~`web_app.py`~~ | ~~Flaskダッシュボード~~ | **削除済** | app.pyに統合 |
| ~~`line_webhook.py`~~ | ~~Flask LINE Webhook + cloudflared~~ | **削除済** | app.pyに統合 |
| `.env.example` | 環境変数テンプレート | 設定 | `.env`にコピー |
| `requirements.txt` | Python依存パッケージ | 設定 | `pip install -r` |
| `Procfile` | Railway デプロイ設定 | 設定 | プラットフォームが読む |
| `.gitignore` | Git除外設定 | 設定 | — |
| `currentfeature.md` | システムドキュメント | ドキュメント | — |
| `airesponsebrainstorm.md` | AI改善ロードマップ | ドキュメント | — |
| `railwaydeploy.md` | Railwayデプロイ手順 | ドキュメント | — |
| `tests/` | テストスイート（pytest + httpx） | 開発用 | `pytest` |

---
---

# 詳細補足セクション

---

## 補足A: 物件ルールファイルの全文（rules/property_206100.md）

```markdown
# 平井戸建 (propertyId: 206100)

## 基本情報
- 住所: 東京都江戸川区平井1-18-7
- Amazon配送先: 〒132-0035 東京都江戸川区平井1-18-7 102号室
- チェックイン: 16:00〜23:00
- チェックアウト: 10:00

## 設備
- WiFi SSID: Hirai_Guest
- WiFi パスワード: 要確認（オーナーに確認）
- 騒音モニター: テレビ横に設置。会話は録音せず騒音レベルのみ計測。90dB超でアラート。プライバシーへの影響はなし。

## ハウスルール
- 全館禁煙（玄関前・建物外周も含む）
- ゴミは室内にまとめること。外の集積所には絶対に出さない（清掃員が処理する）
- 騒音・深夜の大声は禁止（近隣への配慮）

## アクセス・鍵
- 鍵の場所: 要確認
- チェックイン手順: 要確認
- チェックアウト手順: 要確認

## 緊急連絡先
- オーナー連絡先: 要確認

## よくある質問
- **騒音モニターについて**: テレビ横に設置されている装置は騒音モニターです。会話の内容は一切録音されず、騒音レベル（dB）のみを計測します。90dBを超えるとアラートが発生しますので、ご注意ください。
- **早期チェックイン・遅延チェックアウト**: 要確認（基本は対応不可）
- **駐車場**: 要確認
- **近隣のコンビニ・スーパー**: 要確認
```

**課題:**
- 「要確認」が多数 — オーナーから情報を埋める必要あり
- 周辺おすすめスポット・レストラン情報が一切ない
- ゲスト属性別の案内がない（家族向け、カップル向け等）
- 多言語対応の考慮なし（日本語のみ）
- クレーム防止の事前案内項目がない（虫、騒音レベル等の期待値調整）

---

## 補足B: LINE Flex Messageの完全なJSON構造

`line_notify.py` が生成するFlex Messageの完全なJSON:

```json
{
  "type": "bubble",
  "header": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {
        "type": "text",
        "text": "新着ゲストメッセージ",
        "weight": "bold",
        "size": "md",
        "color": "#1a73e8"
      },
      {
        "type": "text",
        "text": "{guest_name} | {property_name}",
        "size": "xs",
        "color": "#555555",
        "margin": "sm",
        "weight": "bold"
      }
    ],
    "backgroundColor": "#f0f6ff",
    "paddingAll": "15px"
  },
  "body": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      // --- 条件付き: guest_name or property_name がある場合 ---
      {
        "type": "text",
        "text": "予約ID: {booking_id}",
        "size": "xxs",
        "color": "#aaaaaa"
      },
      // --- 条件付き: conversation_history がある場合 ---
      {"type": "separator", "margin": "md"},
      {
        "type": "text",
        "text": "直近のやり取り",
        "weight": "bold",
        "size": "xs",
        "color": "#999999",
        "margin": "md"
      },
      {
        "type": "text",
        "text": "{conversation_history}",
        "size": "xxs",
        "color": "#aaaaaa",
        "wrap": true,
        "margin": "sm"
      },
      // --- 常に表示 ---
      {"type": "separator", "margin": "md"},
      {
        "type": "text",
        "text": "ゲスト",
        "weight": "bold",
        "size": "sm",
        "color": "#555555",
        "margin": "md"
      },
      {
        "type": "text",
        "text": "{guest_message (max 150 chars)}",
        "size": "sm",
        "wrap": true,
        "margin": "sm"
      },
      {"type": "separator", "margin": "md"},
      {
        "type": "text",
        "text": "AI返信案",
        "weight": "bold",
        "size": "sm",
        "color": "#555555",
        "margin": "md"
      },
      {
        "type": "text",
        "text": "{ai_reply (max 300 chars)}",
        "size": "sm",
        "wrap": true,
        "margin": "sm"
      }
    ],
    "paddingAll": "15px"
  },
  "footer": {
    "type": "box",
    "layout": "horizontal",
    "contents": [
      {
        "type": "button",
        "action": {
          "type": "postback",
          "label": "承認して送信",
          "data": "action=approve&pending_id={pending_id}"
        },
        "style": "primary",
        "color": "#1a73e8",
        "height": "sm"
      },
      {
        "type": "button",
        "action": {
          "type": "postback",
          "label": "修正する",
          "data": "action=edit&pending_id={pending_id}"
        },
        "style": "secondary",
        "height": "sm",
        "margin": "md"
      }
    ],
    "paddingAll": "15px"
  }
}
```

**ヘッダーサブタイトルの優先順位:**
1. `"{guest_name} | {property_name}"` — 両方ある場合
2. `"{guest_name}"` — ゲスト名のみ
3. `"{property_name}"` — 物件名のみ
4. `"予約ID: {booking_id}"` — フォールバック

**テキスト切り詰めルール:**
- `guest_message`: 最大150文字
- `ai_reply`: 最大300文字
- `conversation_history`: 最大500文字
- `alt_text`: `"新着: {guest_name or '予約'+booking_id} からのメッセージ"`

---

## 補足C: DB関数の全SQLクエリ

### 接続管理

```python
# PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
# try → conn.commit() / except → conn.rollback() / finally → conn.close()

# SQLite
conn = sqlite3.connect(_SQLITE_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
```

**プレースホルダー抽象化:** PostgreSQL=`%s`、SQLite=`?`（変数 `_PH` で統一）

### ヘルパー関数

```python
_fetchall(conn, sql, params) → list[dict]
  # PostgreSQL: RealDictCursor使用
  # SQLite: dict(row) で変換

_fetchone(conn, sql, params) → dict | None
  # 同上、1行のみ

_execute(conn, sql, params) → int | None
  # INSERT: lastrowid (SQLite) or RETURNING id (PostgreSQL)
  # 非INSERT: None を返す（ProgrammingError をキャッチ）
```

### 全SQLクエリ一覧

**1. upsert_message(beds24_message_id, booking_id, property_id, source, message, sent_at, is_read)**
```sql
-- 既存チェック
SELECT id FROM messages WHERE beds24_message_id = ?

-- 既存あり → 更新（is_readのみ）
UPDATE messages SET is_read = ? WHERE id = ?

-- 既存なし → 挿入
INSERT INTO messages
  (beds24_message_id, booking_id, property_id, source, message, sent_at, is_read)
VALUES (?, ?, ?, ?, ?, ?, ?)
```
戻り値: `(message_id: int, is_new: bool)`

**2. get_unprocessed_guest_messages()**
```sql
SELECT * FROM messages
WHERE status = 'unprocessed' AND source = 'guest'
ORDER BY sent_at
```

**3. get_draft_ready_messages()**
```sql
SELECT m.*, d.id AS draft_id, d.draft_text, d.model AS draft_model
FROM messages m
LEFT JOIN ai_drafts d ON d.id = (
    SELECT d2.id FROM ai_drafts d2
    WHERE d2.message_id = m.id
    ORDER BY d2.created_at DESC, d2.id DESC
    LIMIT 1
)
WHERE m.status = 'draft_ready'
ORDER BY m.sent_at
```

**4. get_thread(booking_id)**
```sql
SELECT * FROM messages WHERE booking_id = ? ORDER BY sent_at
```

**5. update_message_status(message_id, status)**
```sql
UPDATE messages SET status = ? WHERE id = ?
```

**6. get_message_by_id(message_id)**
```sql
SELECT * FROM messages WHERE id = ?
```

**7. save_draft(message_id, booking_id, draft_text, model)**
```sql
INSERT INTO ai_drafts (message_id, booking_id, draft_text, model)
VALUES (?, ?, ?, ?)
```
戻り値: `draft_id: int`

**8. get_draft(message_id)**
```sql
SELECT * FROM ai_drafts
WHERE message_id = ?
ORDER BY created_at DESC
LIMIT 1
```

**9. upsert_booking(beds24_booking_id, property_id, guest_name, check_in, check_out, property_name, num_adult, num_child, guest_country, guest_language, guest_arrival_time, guest_comments)**
```sql
-- PG/SQLite共通（ON CONFLICT構文はSQLite 3.24+でサポート）:
INSERT INTO bookings
  (beds24_booking_id, property_id, guest_name, check_in, check_out, property_name,
   num_adult, num_child, guest_country, guest_language, guest_arrival_time, guest_comments)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
  guest_comments = EXCLUDED.guest_comments
```

**10. get_booking(beds24_booking_id)**
```sql
SELECT * FROM bookings WHERE beds24_booking_id = ?
```

**11. log_action(message_id, draft_id, action, final_text, channel)**
```sql
INSERT INTO action_logs
  (message_id, draft_id, action, final_text, channel)
VALUES (?, ?, ?, ?, ?)
```

**12. has_proactive(beds24_booking_id, trigger_type)**
```sql
SELECT id FROM proactive_messages
WHERE beds24_booking_id = ? AND trigger_type = ?
LIMIT 1
```

**13. save_proactive_draft(beds24_booking_id, property_id, trigger_type, draft_text, model)**
```sql
-- UPSERT: 同一予約+トリガーの重複をON CONFLICTで防止（レースコンディション対策）
INSERT INTO proactive_messages
  (beds24_booking_id, property_id, trigger_type, draft_text, model)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(beds24_booking_id, trigger_type) DO UPDATE SET
  draft_text = EXCLUDED.draft_text,
  model = EXCLUDED.model,
  status = 'draft_ready'
```
戻り値: `proactive_id: int | None`

**14. get_proactive_by_id(proactive_id)**
```sql
SELECT * FROM proactive_messages WHERE id = ?
```

**15. get_draft_ready_proactive()**
```sql
SELECT * FROM proactive_messages
WHERE status = 'draft_ready'
ORDER BY created_at
```

**16. update_proactive_status(proactive_id, status)**
```sql
UPDATE proactive_messages SET status = ? WHERE id = ?
```

**17. has_recent_conversation(beds24_booking_id, hours=48)**
```sql
-- cutoff = Python で datetime.now(UTC) - timedelta(hours) を計算
SELECT id FROM messages
WHERE booking_id = ? AND sent_at > ?
LIMIT 1
```

**18. save_editing_state(user_id, message_id)**
```sql
INSERT INTO editing_state (user_id, message_id)
VALUES (?, ?)
ON CONFLICT(user_id) DO UPDATE SET message_id = EXCLUDED.message_id
```

**19. get_editing_state(user_id)**
```sql
SELECT message_id FROM editing_state WHERE user_id = ?
```

**20. delete_editing_state(user_id)**
```sql
DELETE FROM editing_state WHERE user_id = ?
```

**21. check_health()**
```sql
SELECT 1
```

### DDL（テーブル作成SQL）

**PostgreSQL版:**
```sql
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
    guest_country TEXT DEFAULT '',
    guest_language TEXT DEFAULT '',
    guest_arrival_time TEXT DEFAULT '',
    guest_comments TEXT DEFAULT '',
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
```

**SQLite版:**
```sql
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
-- 同様のINDEX

CREATE TABLE IF NOT EXISTS ai_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER REFERENCES messages(id),
    booking_id INTEGER NOT NULL,
    draft_text TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

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
    guest_country TEXT DEFAULT '',
    guest_language TEXT DEFAULT '',
    guest_arrival_time TEXT DEFAULT '',
    guest_comments TEXT DEFAULT '',
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
```

---

## 補足D: エラーハンドリング全パターン

### beds24.py のエラーハンドリング

| 関数 | エラー条件 | 処理 |
|------|-----------|------|
| `get_access_token()` | HTTP != 200 | `logger.error("認証エラー: ...")` → `None` 返却 |
| `get_access_token()` | `RequestException` | `logger.error("接続エラー: ...")` → `None` 返却 |
| `_fetch_messages_paginated()` | HTTP != 200 | `logger.error("メッセージ取得エラー (page N): ...")` → ループ中断 |
| `_fetch_messages_paginated()` | `RequestException` | `logger.error("接続エラー (page N): ...")` → ループ中断 |
| `get_booking_details()` | HTTP != 200 | `logger.error("予約詳細取得エラー: ...")` → `{}` 返却 |
| `get_booking_details()` | data が空リスト | `{}` 返却 |
| `get_booking_details()` | `RequestException` | `logger.error("接続エラー: ...")` → `{}` 返却 |
| `get_bookings_by_date_range()` | HTTP != 200 | `logger.error(...)` → ページネーション中断 |
| `get_bookings_by_checkout_range()` | HTTP != 200 | `logger.error(...)` → ページネーション中断 |
| `send_reply()` | HTTP != 200/201 | `logger.error("送信エラー: ...")` → `False` 返却 |
| `send_reply()` | `RequestException` | `logger.error("接続エラー: ...")` → `False` 返却 |

### app.py のエラーハンドリング

| 箇所 | エラー条件 | 処理 |
|------|-----------|------|
| `/callback` | `InvalidSignatureError` | HTTP 400 "Invalid signature" |
| `handle_postback` | action/pending_id が None | `return`（無視） |
| `handle_postback` | `int()` 変換で `ValueError` | `return`（無視）— LINE postbackデータの不正値によるクラッシュ防止 |
| `handle_postback` | メッセージがDBにない | LINE返信: "このメッセージは期限切れか、既に処理済みです。" |
| `handle_postback` | status != 'draft_ready' | LINE返信: "このメッセージは既に処理済みです。" |
| `handle_postback` (approve) | ドラフトがない | LINE返信: "AIドラフトが見つかりませんでした。" |
| `handle_postback` (approve) | Beds24送信失敗（`_send_to_beds24()` → False） | LINE返信: "送信失敗\n予約ID: {id}\n\n再度お試しください。" |
| `handle_message` | user_id が editing_state にない | LINE返信: "未読メッセージの返信案は自動で届きます。" |
| `handle_message` | メッセージがDBにない | LINE返信: "対象のメッセージが見つかりませんでした。" |
| `handle_message` | Beds24送信失敗 | `save_editing_state(user_id, message_id)` で復元 → LINE返信: "送信失敗\n予約ID: {id}\n\nもう一度送信文を入力してください。" |
| `_handle_proactive_postback` | プロアクティブがDBにない | LINE返信: "このメッセージは期限切れか、既に処理済みです。" |
| `_handle_proactive_postback` | Beds24送信失敗 | LINE返信: "送信失敗\n予約ID: {id}\n\n再度お試しください。" |
| `/api/send` | `int()` 変換で `ValueError` | HTTP 400 — Web APIパラメータの不正値によるクラッシュ防止 |
| `/api/send` | message が空 | HTTP 400 "messageは必須です" |
| `/api/send` | トークン取得失敗 | HTTP 500 "Beds24認証失敗" |
| `/api/send` | 1回目送信失敗 | トークン再取得して1回リトライ |
| `_sync_job` | 任意のException | `logger.error(f"sync job error: {e}")` → 次サイクルまで待機 |

### sync_service.py のエラーハンドリング

| 箇所 | エラー条件 | 処理 |
|------|-----------|------|
| `run_once()` | トークン取得失敗 | `logger.error("Beds24トークン取得失敗")` → メトリクスdict返却 |
| `run_once()` | AI生成失敗（`generate_and_save_draft()` 例外） | `logger.error(...)` → `continue`（次メッセージへ、次回サイクルでリトライ） |
| `run_once()` | LINE通知例外 | `logger.error(...)` → 次メッセージへ続行 |
| `check_proactive_triggers()` | プロアクティブAI生成/通知失敗 | `logger.error(...)` → 次予約へ続行、metrics['proactive_errors'] 加算 |
| `run_poll()` | `KeyboardInterrupt` | `logger.info("ポーリング終了")` → ループ終了 |
| `run_poll()` | 任意のException | `logger.error(...)` → 30秒待機 → 次サイクル |

### db.py のエラーハンドリング

| 箇所 | エラー条件 | 処理 |
|------|-----------|------|
| `_get_conn()` (PostgreSQL) | 任意のException | `conn.rollback()` → 例外を再送出 |
| `_get_conn()` (SQLite) | 任意のException | `conn.rollback()` → 例外を再送出 |
| `_execute()` (PostgreSQL) | `ProgrammingError` | `None` 返却（非INSERT文でRETURNINGが使えない場合） |

**注意点:**
- DB例外はキャッチされず上位に伝播する（sync_service.pyで最終的にキャッチ）
- 全ファイルで `logging` モジュール使用（print文はなし）
- LINE送信エラーは個別メッセージ単位でキャッチし、他メッセージの処理は続行

---

## 補足E: ステータス遷移の全パターン（エラー時含む）

```
                ┌──────────────────────────────────────────────┐
                │          messages.status 遷移図              │
                └──────────────────────────────────────────────┘

[新規メッセージ検出]
        │
        ▼
  ┌─────────────┐
  │ unprocessed │  ← sync_messages() で初回DB保存時
  └─────┬───────┘
        │
        │ generate_and_save_draft() 成功
        ▼
  ┌─────────────┐
  │ draft_ready │  ← AI生成完了、承認待ち
  └─────┬───────┘
        │
        ├─── [承認（LINE/Web/CLI）] ──→ send_reply() 成功 ──→ ┌──────┐
        │                                                      │ sent │
        │    send_reply() 失敗の場合:                          └──────┘
        │    ├─ LINE: editing_stateを復元、「再度お試しください」
        │    ├─ Web: /api/send がトークン再取得→リトライ→失敗なら {ok:false}
        │    └─ CLI: 「送信に失敗しました」表示
        │    ※ いずれもステータスは draft_ready のまま（変わらない）
        │
        ├─── [修正（LINE）] ──→ 修正テキスト送信 → send_reply()
        │    ├─ 成功 → status='sent', action='edited'
        │    └─ 失敗 → editing_state復元、draft_ready のまま
        │
        ├─── [修正（Web）] ──→ textareaの内容を送信 → send_reply()
        │    ├─ 成功 → status='sent', action='edited'(if changed)/'sent'(if same)
        │    └─ 失敗 → draft_ready のまま
        │
        └─── [スキップ（Web/CLI）] ──→ ┌─────────┐
                                        │ skipped │
                                        └─────────┘

※ LINEにもスキップボタンあり（Flex Messageフッターの3ボタン: 承認/修正/スキップ）

【プロアクティブメッセージのステータス遷移】
proactive_messages.status:
  draft_ready → sent（承認送信）
  draft_ready → skipped（スキップ）
  ※ 通常メッセージと同じ3チャネル（LINE/Web/CLI）で承認
  ※ IDは "pro_{id}" プレフィックスで通常メッセージと区別
  ※ pre_checkin/post_checkout 両方とも has_recent_conversation(48h) チェックあり

【エラー時のリトライ】
- generate_and_save_draft() が例外 → unprocessed のまま残留
  → 次回サイクルの run_once() で db.get_unprocessed_guest_messages() により再検出
  → 自動的にリトライされる（無限リトライ、サイクルごとに1回試行）

- 同じメッセージに対して複数のドラフトが生成される可能性
  → get_draft() は created_at DESC LIMIT 1 で最新を取得
  → 古いドラフトはDBに残るが使われない

- editing_state はDB永続化（editing_stateテーブル）
  → サーバー再起動しても修正モード状態が保持される
  → user_id PRIMARY KEY、ON CONFLICT DO UPDATE で上書き
```

---

## 補足F: APSchedulerの設定詳細

```python
# app.py での設定

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# ジョブ登録
scheduler.add_job(
    _sync_job,                    # 実行関数
    "interval",                   # トリガータイプ: 固定間隔
    seconds=SYNC_INTERVAL,        # 間隔（デフォルト300秒 = 5分）
    id="sync_beds24",             # ジョブID（一意識別子）
    replace_existing=True,        # 同一IDのジョブがあれば上書き
)

# ライフサイクル
scheduler.start()   # FastAPI起動時
scheduler.shutdown() # FastAPI終了時
```

**ジョブ実行の挙動:**
- 初回実行: `scheduler.start()` の後、`SYNC_INTERVAL` 秒後（即時実行なし）
- 以降: 前回実行**開始**から `SYNC_INTERVAL` 秒後（ただし前回が完了していない場合はスキップ）
- 並行実行: デフォルトでは `max_instances=1`（同一ジョブの並行実行なし）
- エラー時: `_sync_job` 内で全例外キャッチ → logger.error → 次サイクルまで待機
- メモリ内ジョブストア: 永続化なし（サーバー再起動でスケジュールリセット）

**改善済み:**
- ~~サーバー起動直後は同期が走らない~~ → `next_run_time=datetime.now()` で即時実行
- ~~ジョブの成功/失敗のメトリクスやアラートなし~~ → `run_once()` がメトリクスdict返却、`_sync_status` に累積、`/health` で公開

**制限事項:**
- ジョブが `SYNC_INTERVAL` より長くかかった場合、次の実行は前回完了後に開始（重複しない）
- メモリ内ジョブストア: 永続化なし（サーバー再起動でスケジュールリセット）

---

## 補足G: Webダッシュボード（dashboard.html）のUI/CSS/JS詳細

### CSSデザインシステム

**カラーパレット:**
| 用途 | 色コード | 説明 |
|------|---------|------|
| ナビバー背景 | `#1a1a2e` | ダークネイビー |
| メインアクセント | `#4cc9f0` | シアン |
| 送信ボタン | `#06d6a0` / hover: `#05b886` | グリーン |
| 未読バッジ | `#ef476f` | レッド |
| AIバッジグラデーション | `#4cc9f0 → #7209b7` | シアン→パープル |
| ゲストメッセージ背景 | `#dbeafe` | ライトブルー |
| ホストメッセージ背景 | `#f0f0f0` | ライトグレー |
| ゲストハイライト | `#fff8e1` / 左ボーダー: `#f4b942` | イエロー |
| 送信済みステータス | `#d1fae5` | ライトグリーン |
| pending ステータス | `#fef3c7` / テキスト: `#92400e` | イエロー |
| sending ステータス | `#dbeafe` / テキスト: `#1e40af` | ブルー |
| プロアクティブ(pre_checkin) | `#06d6a0` / 背景: `#f0fff4` | グリーン |
| プロアクティブ(post_checkout) | `#7209b7` / 背景: `#f8f0ff` | パープル |

**フォントスタック:**
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

**レイアウト:**
- ナビバー: sticky、高さ56px
- コンテンツ: max-width 920px、padding 24px
- カード: border-radius 12px、box-shadow 0 2px 8px rgba(0,0,0,0.06)
- カードボディ: 2カラムgrid（`1fr 1fr`）
- レスポンシブ: **対応済み**（640px以下で1カラム、ナビバー・チップ・ボタン・トースト全幅化）

**プロアクティブカード:**
- `.proactive-badge`: ヘッダーに表示、トリガー種別ラベル
  - `.pre_checkin`: 緑（#06d6a0 背景 #f0fff4）— "チェックイン前"
  - `.post_checkout`: 紫（#7209b7 背景 #f8f0ff）— "チェックアウト後"
- 左パネル: 会話履歴の代わりにトリガー種別とチェックイン/アウト日を表示
- ドラフトラベル: 通常メッセージは "返信案"、プロアクティブは "AIメッセージ案"
- IDは文字列として扱う（`String(id)` で onclick に渡す）

### JavaScript関数詳細

**状態管理:**
```javascript
let messages = [];           // 全メッセージ配列
const skipped = new Set();   // スキップ済みメッセージIDのSet
const sent = new Set();      // 送信済みメッセージIDのSet
```

#### `loadMessages()`
```javascript
async function loadMessages() {
  const btn = document.getElementById('refreshBtn');
  btn.disabled = true;
  showScreen('loading');
  try {
    const r = await fetch('/api/messages');
    const j = await r.json();
    messages = j.messages || [];
    renderCards();
  } catch(e) {
    // エラー時: 各カードにエラー表示
  } finally {
    btn.disabled = false;
  }
}
```

#### `renderCards()`
```javascript
function renderCards() {
  // 未読のみフィルタ（sent/skippedを除外）
  const unread = messages.filter(m => !sent.has(m.id) && !skipped.has(m.id));

  // バッジ更新
  document.getElementById('badge').textContent = unread.length;

  // 画面切り替え
  if (messages.length === 0) showScreen('empty');
  else showScreen('cards');

  // カード生成
  const html = messages.map(m => buildCard(m)).join('');
  document.getElementById('cards').innerHTML = html;
}
```

#### `buildCard(m)`
- **通常カード** (`m.type === 'reply'`):
  - スレッドフィルタ: 未読ゲストメッセージを除外（`!(source==='guest' && !read)`）
  - スレッド表示: 最後の5件（`.slice(-5)`）
  - メッセージ切り詰め: 120文字
- **プロアクティブカード** (`m.type === 'proactive'`):
  - ヘッダーにプロアクティブバッジ表示
  - 左パネル: トリガー種別 + チェックイン/アウト日
  - ドラフトラベル: "AIメッセージ案"
- 共通: 送信済み/スキップ済みカード → ボタン・textarea無効化、ステータスバッジ変更

#### `sendMessage(id, bookingId)`
```javascript
async function sendMessage(id, bookingId) {
  const ta = document.querySelector(`#card-${id} textarea`);
  const msg = ta.value.trim();
  if (!msg) return alert('返信を入力してください');

  setCardLoading(id, true);
  const r = await fetch('/api/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({messageId: String(id), bookingId, message: msg})
  });
  const j = await r.json();

  if (j.ok) {
    sent.add(id);
    updateCardStatus(id, 'sent', '送信済み');
    // バッジ更新
    const unread = messages.filter(m => !sent.has(m.id) && !skipped.has(m.id));
    document.getElementById('badge').textContent = unread.length;
    showToast('送信しました', true);
  } else {
    showToast('送信に失敗しました', false);
  }
  setCardLoading(id, false);
}
```

#### `skipMessage(id)`
```javascript
async function skipMessage(id) {
  try {
    await fetch('/api/skip', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({messageId: String(id)})
    });
  } catch(e) {}  // best-effort

  skipped.add(id);
  // ボタン・textarea無効化
  // ステータス更新
  updateCardStatus(id, 'skipped', 'スキップ');
  // バッジ更新
}
```

#### `showToast(msg, ok)`
```javascript
function showToast(msg, ok) {
  const t = document.getElementById('toast');
  t.textContent = (ok ? '✅ ' : '❌ ') + msg;
  t.className = 'show ' + (ok ? 'ok' : 'err');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { t.className = ''; }, 3500);
}
```
- 表示時間: 3500ms
- 成功: ✅ + 緑背景
- 失敗: ❌ + 赤背景

#### `escHtml(s)`
```javascript
function escHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '<br>');
}
```

---
---

## 8. 不完全な部分・既知の問題・改善が必要な箇所

---

### 8.1 解決済みの問題

#### ~~#1. AI生成失敗したメッセージが永久に放置される~~ → 解決済み (2026-03-11)
- **修正内容:** `sync_service.py` の `run_once()` に リトライ機構を追加。毎サイクルで `db.get_unprocessed_guest_messages()` を呼び出し、`unprocessed` のまま残っているメッセージを自動的に再処理する。さらに `generate_and_save_draft()` を try/except で囲み、1件の失敗が他のメッセージ処理をブロックしないようにした。

#### ~~#2. sync_service.pyのAI_MODEL定数とai_engine.pyの実際のモデルが不一致~~ → 解決済み (2026-03-11)
- **修正内容:** `AI_MODEL` 定数を `ai_engine.py` で一元定義し、`sync_service.py` は `from ai_engine import AI_MODEL` でインポートするように変更。DB記録のモデル名と実際のモデルが常に一致する。

#### ~~#3. 一時的なデバッグコードが本番に残っている~~ → 解決済み (2026-03-11)
- **修正内容:** `beds24.py` の全レスポンスログ出力（json.dumps）と `app.py` の `/debug/booking-fields` エンドポイントを削除

---

### 8.2 未解決: 機能の不完全さ

#### ~~#4. editing_stateがメモリ上のみ（揮発性）~~ → 解決済み (2026-03-11)
- **修正内容:** `editing_state` テーブルをDB（PG/SQLite）に追加。`app.py` のインメモリ dict を `db.save_editing_state()` / `db.get_editing_state()` / `db.delete_editing_state()` に置き換え。サーバー再起動後もLINE編集モードが維持される。プロアクティブメッセージの編集（`pro_` プレフィックス付きID）にも対応。

#### ~~#5. ゲスト属性データが未取得~~ → 解決済み (2026-03-11)
- **修正内容:** `beds24.py` の `get_booking_details()` を拡張し、6つの新フィールド（numAdult, numChild, guestCountry, guestLanguage, guestArrivalTime, guestComments）を返すように変更。`db.py` のbookingsテーブルDDLに6カラム追加、`upsert_booking()` を12パラメータに拡張、`_migrate_bookings_add_guest_fields()` で既存DBのマイグレーション対応。`sync_service.py` の `sync_booking_to_db()` も新フィールドを `db.upsert_booking()` に渡すように更新。

#### ~~#6. 返信言語が日本語固定~~ → 解決済み (2026-03-11)
- **修正内容:** `ai_engine.py` に `_is_japanese()` 関数を追加し、言語自動検出を実装。`generate_reply()` のプロンプトにゲスト属性（人数、国籍、到着時間、備考）を条件付きで注入。言語指示は3段階: (1) `guestLanguage` が非日本語なら明示指示、(2) メッセージに日本語文字がなければ「同じ言語で返信」指示、(3) それ以外は日本語デフォルト。

#### #7. 物件ルールファイルに「要確認」が多数
- **箇所:** `rules/property_206100.md`
- **問題:** 鍵の場所、チェックイン手順、WiFiパスワード、駐車場、近隣情報が全て「要確認」
- **影響:** AIがこれらの質問に正確に回答できない（「要確認」とそのまま返す可能性）
- **修正案:** オーナーから情報を収集してファイルを完成させる

#### #8. 物件ルールに周辺情報・おすすめスポットがない
- **箇所:** `rules/property_206100.md`
- **問題:** レストラン、観光スポット、コンビニ、交通アクセスなどの情報が未記載
- **影響:** パーソナライズされたおもてなし（Phase 2の機能）の基盤データがない
- **修正案:** 周辺情報をルールファイルに追加、またはDB管理に移行

#### ~~#9. LINEにスキップボタンがない~~ → 解決済み (2026-03-11)
- **修正内容:** `line_notify.py` のFlex Messageフッターに「スキップ」ボタンを追加（グレー、控えめ配置）。`app.py` の `handle_postback()` に `action=skip` ハンドラーを追加。`db.update_message_status` → `'skipped'`、`db.log_action` で `channel='line'` 記録。全3チャネル（LINE/Web/CLI）でスキップ可能に。

---

### 8.3 未解決: パフォーマンス・効率性

#### ~~#10. Beds24トークンが毎回取得される（キャッシュなし）~~ → 解決済み (2026-03-11)
- **修正内容:** `beds24.py` の `get_access_token()` に `threading.Lock` ベースのTTLキャッシュ（20分）を追加。`invalidate_token_cache()` で明示的な無効化も可能。`app.py` の送信リトライ時にキャッシュ無効化→再取得するように変更。

#### ~~#11. get_unread_guest_messages()が全メッセージをフェッチしてからフィルタ~~ → 解決済み (2026-03-11)
- **修正内容:** `beds24.py` の `get_unread_guest_messages()` にAPIフィルタパラメータ `{"source": "guest", "read": "false"}` を追加。レスポンス量を大幅削減。Python側フィルタは安全ネットとして残存。

#### ~~#12. サーバー起動直後に同期が走らない~~ → 解決済み (2026-03-11)
- **修正内容:** `app.py` の `scheduler.add_job()` に `next_run_time=datetime.now()` を追加。サーバー起動直後にバックグラウンドスレッドで初回同期が実行される（サーバーの起動自体はブロックしない）。

---

### 8.4 未解決: セキュリティ

#### ~~#13. Web DashboardにBasic認証がない~~ → 解決済み (2026-03-11)
- **修正内容:** HTTP Basic Auth を実装。`DASHBOARD_USER`/`DASHBOARD_PASS` 環境変数で認証。未設定時は503（ダッシュボード無効）。`secrets.compare_digest` でタイミング攻撃対策。IP別レートリミット（5回失敗→60秒ロックアウト）付き。認証失敗はログ記録。`POST /callback`（LINE webhook）と `GET /health` は認証不要のまま。

#### ~~#14. 環境変数の直接参照（バリデーションなし）~~ → 解決済み (2026-03-11)
- **修正内容:** `app.py` 起動時に5つの必須環境変数（REFRESH_TOKEN, GEMINI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, LINE_OWNER_USER_ID）を検証。未設定時はエラーログを出力するがサーバーは起動する（Railwayヘルスチェック対応）。`/health` エンドポイントで未設定変数を報告。

#### ~~#15. LINE Webhook URLのパスがドキュメントと実コードで不一致~~ → 解決済み
- **修正内容:** 問題のあったドキュメント（continuefrom.md等）は削除済み。コード内は統一的に `/callback`。実際のLINE Webhook URL: `https://minpakudx-production.up.railway.app/callback`

---

### 8.5 未解決: 監視・運用

#### ~~#16. ログが全てprint文（ログフレームワーク未使用）~~ → 解決済み (2026-03-11)
- **修正内容:** `beds24.py` と `sync_service.py` の全 `print()` を `logging` モジュールに変換。子ロガー（`minpaku-dx.beds24`, `minpaku-dx.sync`）を使用し `app.py` の既存ロガー（`minpaku-dx`）と統一。`sync_service.py` の `_now()` ヘルパーを削除（`logging.basicConfig` のタイムスタンプで代替）。`cli.py`/`main.py` のユーザー向けTUI出力は `print()` のまま維持。

#### ~~#17. ジョブの成功/失敗メトリクスがない~~ → 解決済み (2026-03-11)
- **修正内容:** `sync_service.py` の `run_once()` がメトリクス辞書（`messages_processed`, `drafts_generated`, `line_notifications_sent`, `errors`）を返すように変更。`app.py` の `_sync_job()` が累積カウンタ（`total_runs`, `total_messages_processed`, `total_drafts_generated`, `total_line_notifications_sent`, `total_errors`）を管理。`/health` エンドポイントで `sync` セクションとして公開。`_server_start_time` も追加。

#### ~~#18. ヘルスチェックがDB/外部サービスの状態を含まない~~ → 解決済み (2026-03-11)
- **修正内容:** `/health` エンドポイントを拡張。DB接続テスト（`SELECT 1`）、必須環境変数チェック、最終同期時刻・成功/失敗を含むレスポンスに変更。外部API（Beds24/Gemini/LINE）は呼ばない。`status` は `ok`/`degraded` の2値。HTTPステータスは常に200（Railway互換）。

---

### 8.6 未解決: 設計上の課題

#### ~~#19. レガシーファイルが残っている~~ → 解決済み (2026-03-11)
- **修正内容:** `web_app.py`（Flask版ダッシュボード）と `line_webhook.py`（Flask版LINE Webhook + cloudflaredランチャー）を削除。全機能は `app.py` に統合済み。

#### ~~#20. 1つの同期サイクルで複数メッセージを処理する際の順序制御がない~~ → 解決済み (2026-03-11)
- **修正内容:** `sync_service.py` の `run_once()` に booking_id グルーピングを追加。同一予約の複数メッセージは最新の1件のみAI生成+LINE通知。古いメッセージはAI生成成功後に `draft_ready` に更新（リトライループ防止）。AIは全スレッドを参照するので情報は失われない。

#### ~~#21. Webダッシュボードのレスポンシブ対応が最低限~~ → 解決済み (2026-03-11)
- **修正内容:** `templates/dashboard.html` に統合 `@media (max-width: 640px)` ブロックを追加。ナビバー縮小、チップフォント縮小、パネル左のborder-rightをborder-bottomに変更、アクションボタンを縦並び全幅化、トースト通知を画面幅に拡張、テキストエリア・ゲストメッセージのフォントサイズ調整。

#### ~~#22. get_draft_ready_messages()で複数ドラフト時に重複行が返る可能性~~ → 解決済み (2026-03-11)
- **修正内容:** `db.py` の `get_draft_ready_messages()` を相関サブクエリ方式に変更。`LEFT JOIN ai_drafts d ON d.id = (SELECT d2.id ... ORDER BY d2.created_at DESC, d2.id DESC LIMIT 1)` で最新ドラフトのみJOIN。PG/SQLite両対応。

#### ~~#23. send_line_text()が未使用~~ → 解決済み (2026-03-11)
- **修正内容:** `line_notify.py` から `send_line_text()` と未使用の `TextMessage` インポートを削除

#### ~~#24. flask がrequirements.txtに含まれていない~~ → 解決済み (2026-03-11)
- **修正内容:** Flaskを参照していた `web_app.py` と `line_webhook.py` を削除。本番はFastAPI（`app.py`）のみ。flaskは不要に。

#### ~~#25. get_token.py / import requests.py に招待コードがハードコード~~ → 解決済み (2026-03-11)
- **修正内容:** `get_token.py` と `import requests.py` を削除

#### ~~#26. プロアクティブメッセージの仕組みがない~~ → 解決済み (2026-03-11)
- **修正内容:** プロアクティブメッセージシステムを実装。2つのトリガータイプ:
  - **pre_checkin**: チェックイン2日前にAIウェルカムメッセージを自動生成（ゲスト属性に合わせたパーソナライズ推薦付き）
  - **post_checkout**: チェックアウト翌日にAIサンキューメッセージ+レビュー依頼を自動生成
  - スキップ条件: 既送信済み（UPSERT制約）、直近48時間に会話あり（pre_checkin/post_checkout両方）
  - 通常メッセージと同じLINE承認フロー（承認/修正/スキップ）で動作
  - Webダッシュボードにも表示（プロアクティブバッジ付きカード）
  - **変更ファイル:** `db.py`（proactive_messagesテーブル+CRUD）、`beds24.py`（日付範囲検索API）、`ai_engine.py`（`generate_proactive_message()`）、`sync_service.py`（`check_proactive_triggers()`）、`line_notify.py`（`send_proactive_line_message()`）、`app.py`（postback/API対応）、`dashboard.html`（プロアクティブカード表示）

---

### 変更履歴: Bugfix 5件の品質改善 (2026-03-11)

1. **`sync_service.py`**: post_checkoutプロアクティブにも`has_recent_conversation()`チェック追加（pre_checkinのみだった）
2. **`app.py`**: プロアクティブAPI送信リトライ時のステータス更新漏れ修正（1回目失敗→リトライ成功時に`draft_ready`のまま残るバグ。ステータス更新を`if success:`ブロック内に移動）
3. **`line_notify.py`**: Flex Message文字列の不要な`.replace('"', '\\"')`エスケープ処理削除（`FlexContainer.from_dict()`はPython dict直接受取のため不要）
4. **`app.py`**: LINE postback/Web APIの全`int()`変換にtry/except ValueError保護追加（不正データによるクラッシュ防止）
5. **`db.py`**: `save_proactive_draft()`をINSERTからUPSERT（`ON CONFLICT(beds24_booking_id, trigger_type) DO UPDATE`）に変更（レースコンディションによるUNIQUE制約違反防止）
