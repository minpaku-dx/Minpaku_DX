# バックエンド設計書 — メッセージ一元管理

**最終更新**: 2026-03-09
**目的**: Beds24からのメッセージを全てバックエンドDBで管理し、全エントリーポイントが同じデータソースを参照する構造を作る

---

## 現状の問題

### 1. メッセージが「使い捨て」になっている

```
現状のフロー:
  ai_reply.py 実行 → Beds24 API叩く → メッセージ取得 → AI生成 → LINE送信 → 終了
  web_app.py アクセス → Beds24 API叩く → メッセージ取得 → AI生成 → 表示 → 終了
  main.py 実行 → Beds24 API叩く → メッセージ取得 → AI生成 → CLI表示 → 終了
```

- 毎回Beds24に問い合わせるので、過去の処理結果がどこにも残らない
- AI返信案を再生成するたびにAPI料金がかかる
- 「さっき生成したドラフト」をWebとLINEで共有できない

### 2. pending.jsonの限界

- LINEの承認フローでしか使っていない
- Web/CLIで送信した記録は残らない
- ファイルベースなので検索・集計ができない
- 複数プロセスから同時アクセスすると壊れる

### 3. エントリーポイントごとにデータが分離している

```
LINE: pending.json に保存 → 承認/修正
Web:  何も保存しない → 送信して終わり
CLI:  何も保存しない → 送信して終わり
```

→ 「Webでドラフトを見て、LINEで承認する」ができない

---

## 設計方針

### 原則

1. **Beds24は「データソース」、DBは「真のデータストア」**
2. **全エントリーポイントがDBを参照する**（Beds24を直接叩くのはSyncサービスだけ）
3. **メッセージの状態管理はDB側で行う**（pending.json廃止）

### あるべきフロー

```
┌──────────────────────────────────────────────────────┐
│                   Sync サービス                        │
│  （定期的にBeds24をポーリング → DBに新着メッセージ保存）  │
│  （新着があればAI返信案を生成してDBに保存）              │
│  （LINE/Web通知をトリガー）                             │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│                     DB（Supabase）                     │
│                                                        │
│  messages        → 全メッセージ（ゲスト+ホスト）        │
│  ai_drafts       → AI返信案（メッセージに紐づく）       │
│  bookings        → 予約情報キャッシュ                   │
│  properties      → 物件情報・ルール                     │
│  action_logs     → 送信/編集/スキップの記録             │
└──────────────┬───────────────────────────────────────┘
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
     LINE    Web     CLI
   (通知・   (管理    (開発用)
    承認)    画面)
```

---

## DBスキーマ

### messages（全メッセージを蓄積）

```sql
CREATE TABLE messages (
  id SERIAL PRIMARY KEY,
  beds24_message_id INT UNIQUE,        -- Beds24側のID（重複取り込み防止）
  booking_id INT NOT NULL,
  property_id INT,
  source TEXT NOT NULL,                 -- 'guest' / 'host'
  message TEXT NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL,        -- Beds24上の送信時刻
  is_read BOOLEAN DEFAULT FALSE,       -- Beds24上の既読ステータス
  status TEXT DEFAULT 'unprocessed',   -- 'unprocessed' / 'draft_ready' / 'sent' / 'skipped'
  synced_at TIMESTAMPTZ DEFAULT NOW()  -- DBに取り込んだ時刻
);

CREATE INDEX idx_messages_booking ON messages(booking_id);
CREATE INDEX idx_messages_status ON messages(status);
CREATE INDEX idx_messages_beds24_id ON messages(beds24_message_id);
```

### ai_drafts（AI返信案）

```sql
CREATE TABLE ai_drafts (
  id SERIAL PRIMARY KEY,
  message_id INT REFERENCES messages(id),  -- どのゲストメッセージに対するドラフトか
  booking_id INT NOT NULL,
  draft_text TEXT NOT NULL,
  model TEXT NOT NULL,                      -- 'gemini-2.5-flash' etc.
  property_rules_version TEXT,              -- 使用したルールのハッシュ
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drafts_message ON ai_drafts(message_id);
```

### action_logs（承認・編集・スキップの記録）

```sql
CREATE TABLE action_logs (
  id SERIAL PRIMARY KEY,
  message_id INT REFERENCES messages(id),
  draft_id INT REFERENCES ai_drafts(id),
  action TEXT NOT NULL,                  -- 'sent' / 'edited' / 'skipped'
  final_text TEXT,                       -- 実際に送信したテキスト（editedの場合）
  channel TEXT NOT NULL,                 -- 'line' / 'web' / 'cli'
  acted_at TIMESTAMPTZ DEFAULT NOW()
);
```

### bookings（予約情報キャッシュ）

```sql
CREATE TABLE bookings (
  id SERIAL PRIMARY KEY,
  beds24_booking_id INT UNIQUE NOT NULL,
  property_id INT,
  guest_name TEXT,
  check_in DATE,
  check_out DATE,
  property_name TEXT,
  synced_at TIMESTAMPTZ DEFAULT NOW()
);
```

### properties（物件情報・ルール）

```sql
CREATE TABLE properties (
  id SERIAL PRIMARY KEY,
  beds24_property_id INT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  rules_content TEXT,                    -- 現在のmdファイルの内容
  reply_tone TEXT DEFAULT 'polite',      -- 'polite' / 'casual' / 'business'
  signature TEXT DEFAULT '民泊スタッフ一同',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## メッセージのライフサイクル

```
1. Sync: Beds24 → DB
   beds24_message_id で重複チェック → 新着のみINSERT
   status = 'unprocessed'

2. AI Draft生成
   status == 'unprocessed' のゲストメッセージを取得
   会話スレッド（同じbooking_idのmessages）をDBから取得
   予約情報（bookingsテーブル）をDBから取得
   物件ルール（propertiesテーブル）をDBから取得
   ai_engine.generate_reply() でドラフト生成
   ai_drafts にINSERT
   messages.status = 'draft_ready' に更新

3. 通知
   status == 'draft_ready' のメッセージをLINE/Webに通知
   LINE: Flex Message（現行通り）
   Web: リアルタイム更新（WebSocket or ポーリング）

4. オーナーアクション
   承認 → action_logs に 'sent' を記録 → Beds24に送信 → messages.status = 'sent'
   編集 → action_logs に 'edited' を記録 → Beds24に送信 → messages.status = 'sent'
   スキップ → action_logs に 'skipped' を記録 → messages.status = 'skipped'

5. 全エントリーポイントがDBの同じstatusを見る
   LINE: draft_readyのメッセージが来たら通知、承認したらsent
   Web:  draft_readyのメッセージをカード表示、送信したらsent
   CLI:  draft_readyのメッセージを表示、送信したらsent
```

---

## Syncサービスの設計

### sync_service.py（新規）

Beds24 → DB の同期を担当する唯一のプロセス。

```
処理フロー:
1. Beds24からメッセージを全ページ取得（beds24.py使用）
2. beds24_message_id でDBと照合、新着のみINSERT
3. 新着ゲストメッセージの予約情報をDBに保存/更新
4. 新着ゲストメッセージに対してAIドラフトを生成
5. ai_draftsに保存、messages.statusを'draft_ready'に更新
6. LINE通知をトリガー（line_notify.py使用）
```

### 実行方式

| 方式 | 用途 |
|---|---|
| `python sync_service.py` | ワンショット（手動実行） |
| `python sync_service.py --poll --interval 300` | 定期ポーリング（5分間隔） |
| APScheduler / Celery（将来） | 本番用バックグラウンドジョブ |

---

## 各エントリーポイントの変更

### ai_reply.py → 廃止

sync_service.py に統合。以下が変わる：

| 現状 | 変更後 |
|---|---|
| Beds24から直接取得 | DBから取得 |
| AI生成して使い捨て | DBに保存 |
| pending.jsonに保存 | DBに保存 |
| LINE通知 | sync_service.py内で通知 |

### line_webhook.py → DBを参照

| 現状 | 変更後 |
|---|---|
| pending.jsonから読み込み | DBからdraft_readyのメッセージ取得 |
| pending.jsonに書き込み | DBのstatus更新 + action_logsにINSERT |
| 独自のBeds24送信関数 | beds24.send_reply()使用（変更なし） |

### web_app.py → DBを参照

| 現状 | 変更後 |
|---|---|
| /api/messages → Beds24直接取得 + AI生成 | DBからdraft_readyのメッセージ + ai_drafts取得 |
| /api/send → Beds24に直接送信 | Beds24送信 + DB更新 + action_logsにINSERT |
| 毎回AI再生成（コスト大） | 保存済みドラフトを表示（コストゼロ） |

### main.py / cli.py → DBを参照

| 現状 | 変更後 |
|---|---|
| Beds24直接取得 + AI生成 | DBからdraft_readyのメッセージ取得 |
| 送信結果を保存しない | DB更新 + action_logsにINSERT |

---

## 修正後のファイル構成

```
minpaku-dx/
├── beds24.py           # Beds24 API（変更なし）
├── ai_engine.py        # AI返信生成（変更なし）
├── db.py               # DB接続・クエリ関数（新規）
├── sync_service.py     # Beds24→DB同期 + AI生成 + 通知（新規）
├── line_notify.py      # LINE Flex Message送信（変更なし）
├── line_webhook.py     # LINE Webhook → DB参照に変更
├── web_app.py          # Webダッシュボード → DB参照に変更
├── main.py             # CLIエントリーポイント → DB参照に変更
├── cli.py              # CLI承認フロー → DB参照に変更
├── rules/
│   └── property_206100.md  # → 将来DBに移行
├── templates/
│   └── dashboard.html
├── pending_store.py    # → 廃止（DBに移行）
├── pending.json        # → 廃止（DBに移行）
└── serviceplan.md
```

---

## DB選定

### 開発段階: SQLite

- セットアップ不要（ファイル1つ）
- Python標準ライブラリで使える
- ローカル開発に最適
- pending.jsonからの移行がスムーズ

### サービス化段階: Supabase（PostgreSQL）

- serviceplan.md フェーズ1で移行
- db.pyの接続先を切り替えるだけ（SQLは同じ）
- Auth / Realtime / RLS が使える

### 移行戦略

```
Step 1: db.py を SQLite で実装
Step 2: 全エントリーポイントをdb.py経由に切り替え
Step 3: pending_store.py / pending.json を廃止
Step 4: サービス化時に db.py の接続先をSupabaseに変更
```

---

## 実装順序

| 順番 | 作業 | 影響 |
|---|---|---|
| 1 | db.py を作成（SQLite、テーブル作成、CRUD関数） | 新規 |
| 2 | sync_service.py を作成（Beds24→DB同期 + AI生成 + LINE通知） | 新規（ai_reply.pyの置き換え） |
| 3 | line_webhook.py をDB参照に切り替え | line_webhook.py |
| 4 | web_app.py をDB参照に切り替え | web_app.py |
| 5 | main.py / cli.py をDB参照に切り替え | main.py, cli.py |
| 6 | ai_reply.py / pending_store.py / pending.json を廃止 | 削除 |
| 7 | 動作確認（全パスでDB経由の動作を検証） | 全体 |

---

## db.py のインターフェース設計

```python
# ── 初期化 ──
init_db()
# テーブルが存在しなければ作成

# ── メッセージ ──
upsert_message(beds24_message_id, booking_id, property_id, source, message, sent_at, is_read) -> int
# beds24_message_idで重複チェック。新規ならINSERT、既存ならUPDATE。message_idを返す。

get_unprocessed_guest_messages() -> list[dict]
# status == 'unprocessed' かつ source == 'guest' のメッセージを返す

get_draft_ready_messages() -> list[dict]
# status == 'draft_ready' のメッセージ + ai_draftsを結合して返す

get_thread(booking_id) -> list[dict]
# 指定booking_idの全メッセージを時系列順で返す

update_message_status(message_id, status) -> None
# メッセージのstatusを更新

# ── AIドラフト ──
save_draft(message_id, booking_id, draft_text, model) -> int
# ai_draftsにINSERT。draft_idを返す。

get_draft(message_id) -> dict | None
# message_idに紐づく最新のドラフトを返す

# ── 予約情報 ──
upsert_booking(beds24_booking_id, property_id, guest_name, check_in, check_out, property_name) -> None
# 予約情報を保存/更新

get_booking(beds24_booking_id) -> dict | None
# 予約情報を返す

# ── アクションログ ──
log_action(message_id, draft_id, action, final_text, channel) -> None
# 送信/編集/スキップの記録をINSERT

# ── 物件 ──
get_property_rules(beds24_property_id) -> str
# 物件ルールを返す（初期はrulesディレクトリから、将来はDBから）
```

---

## 移行による改善まとめ

| 問題 | 現状 | 改善後 |
|---|---|---|
| メッセージが使い捨て | 毎回Beds24に問い合わせ | DBに蓄積、再利用可能 |
| AI生成コスト | 毎回再生成 | 一度生成してDBに保存 |
| エントリーポイント間のデータ共有 | なし | 全てDBを参照 |
| 状態管理 | pending.json（LINEのみ） | DB（全チャネル統一） |
| 送信記録 | LINEのみ（pending.json） | 全チャネルでaction_logs |
| 過去メッセージの検索 | 不可能 | SQLで自由にクエリ |
| 分析（AI採用率、返信時間） | 不可能 | action_logsから集計可能 |
| 同時アクセス | ファイル破損リスク | DB排他制御で安全 |
