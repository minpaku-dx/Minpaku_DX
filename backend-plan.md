# 統合実装プラン — Minpaku DX バックエンド

**最終更新**: 2026-03-09
**目的**: 完全自動化 — ユーザーはLINEで承認するだけ

---

## 完了済み

### フェーズ0: リファクタリング ✅

- [x] ai_reply.py → beds24.py / ai_engine.py からimport（重複削除）
- [x] pending_store.py 切り出し
- [x] beds24.py ページネーション追加
- [x] line_webhook.py → beds24.py + pending_store.py 利用に統一
- [x] 全エントリーポイントが同じコードパスを通る構造

---

### フェーズ1: DB + Syncサービス ✅

**ゴール**: `sync_service.py --poll` を起動するだけで、Beds24の新着メッセージが自動でAIドラフト生成 → LINE通知まで流れる

#### Step 1: db.py 作成

SQLiteで実装（サービス化時にSupabaseに切り替え）。

**テーブル:**

```sql
-- 全メッセージ蓄積
messages (
  id INTEGER PRIMARY KEY,
  beds24_message_id INT UNIQUE,     -- 重複防止キー
  booking_id INT NOT NULL,
  property_id INT,
  source TEXT NOT NULL,              -- 'guest' / 'host'
  message TEXT NOT NULL,
  sent_at TEXT NOT NULL,             -- Beds24上の送信時刻
  is_read BOOLEAN DEFAULT 0,
  status TEXT DEFAULT 'unprocessed', -- unprocessed → draft_ready → sent / skipped
  synced_at TEXT DEFAULT CURRENT_TIMESTAMP
)

-- AI返信案
ai_drafts (
  id INTEGER PRIMARY KEY,
  message_id INT REFERENCES messages(id),
  booking_id INT NOT NULL,
  draft_text TEXT NOT NULL,
  model TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
)

-- 予約情報キャッシュ
bookings (
  id INTEGER PRIMARY KEY,
  beds24_booking_id INT UNIQUE NOT NULL,
  property_id INT,
  guest_name TEXT,
  check_in TEXT,
  check_out TEXT,
  property_name TEXT,
  synced_at TEXT DEFAULT CURRENT_TIMESTAMP
)

-- 送信/編集/スキップの記録
action_logs (
  id INTEGER PRIMARY KEY,
  message_id INT REFERENCES messages(id),
  draft_id INT REFERENCES ai_drafts(id),
  action TEXT NOT NULL,     -- 'sent' / 'edited' / 'skipped'
  final_text TEXT,
  channel TEXT NOT NULL,    -- 'line' / 'web' / 'cli'
  acted_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**関数:**

```python
init_db()                          # テーブル作成
upsert_message(...)  -> int        # beds24_message_idで重複チェック、message_id返す
get_unprocessed_guest_messages()   # status='unprocessed', source='guest'
get_draft_ready_messages()         # status='draft_ready' + ai_drafts JOIN
get_thread(booking_id)             # 同一予約の全メッセージ（時系列）
update_message_status(id, status)
save_draft(message_id, ...) -> int
get_draft(message_id)
upsert_booking(...)
get_booking(beds24_booking_id)
log_action(message_id, draft_id, action, final_text, channel)
```

#### Step 2: sync_service.py 作成

ai_reply.py の置き換え。Beds24 → DB同期の**唯一のプロセス**。

```
処理フロー:
1. Beds24からメッセージ取得（beds24.py）
2. beds24_message_id でDB照合 → 新着のみINSERT
3. 新着ゲストメッセージの予約情報をDB保存
4. 新着に対してAIドラフト生成（ai_engine.py）
5. ai_drafts保存 → status='draft_ready'
6. LINE通知（line_notify.py）
```

実行方式:
- `python sync_service.py` — ワンショット
- `python sync_service.py --poll --interval 300` — 5分間隔で常駐

#### Step 3: line_webhook.py をDB参照に切り替え

```
変更前: pending.json → 承認/修正
変更後: DB(draft_ready) → 承認/修正 → DB(status更新) + action_logs
```

#### Step 4: web_app.py をDB参照に切り替え

```
変更前: /api/messages → Beds24直接 + AI毎回再生成
変更後: /api/messages → DBからdraft_ready取得（コストゼロ）
```

#### Step 5: main.py / cli.py をDB参照に切り替え

```
変更前: Beds24直接 + AI生成
変更後: DBからdraft_ready取得
```

#### Step 6: 廃止

- ai_reply.py → 削除（sync_service.pyに統合済み）
- pending_store.py → 削除（DBに移行済み）
- pending.json → 削除

---

### フェーズ2: クラウドデプロイ + LINE Bot本番化

**ゴール**: cloudflaredトンネル廃止、クラウドで安定稼働

- [x] FastAPIへの統合（app.py: LINE Webhook + Web + Background Sync 統合）
- [x] db.py PostgreSQL/Supabase対応（DATABASE_URL環境変数で自動切り替え）
- [x] APSchedulerでsync_serviceをバックグラウンド実行（app.py lifespan内）
- [x] Flex Messageデザイン改善（ゲスト名・物件名ヘッダー追加）
- [x] Procfile + requirements.txt 更新（Railway対応）
- [ ] Supabaseプロジェクト作成 → DATABASE_URL設定（ユーザー作業）
- [ ] Railwayにデプロイ → 固定URL取得（ユーザー作業）
- [ ] LINE Webhook URLを固定URLに変更（ユーザー作業）

---

### フェーズ3以降

serviceplan.md を参照:
- フェーズ3: マルチテナント + 多言語対応
- フェーズ4: 自動メッセージ（チェックイン案内・リマインダー）
- フェーズ5: 清掃自動手配
- フェーズ6: AIダイナミックプライシング
- フェーズ7: Web管理画面本格化
- フェーズ8: 収益化・ローンチ

---

## 完成時のアーキテクチャ

```
sync_service.py (常駐)
  │ 5分ごとにBeds24ポーリング
  │ 新着 → DB保存 → AI生成 → LINE通知
  ▼
┌─────────────────────────────────┐
│            DB (SQLite → Supabase)           │
│  messages | ai_drafts | bookings | action_logs │
└──────────────┬──────────────────┘
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
     LINE    Web     CLI
    (承認)  (管理)  (開発用)
       │       │       │
       └───────┼───────┘
               ▼
          beds24.py → Beds24に返信送信
```

**ユーザーの操作**: LINEで「承認」or「修正」ボタンを押すだけ

---

## ファイル構成（フェーズ1完了後）

```
minpaku-dx/
├── beds24.py           # Beds24 API（変更なし）
├── ai_engine.py        # AI返信生成（変更なし）
├── db.py               # DB接続・CRUD（新規）
├── sync_service.py     # Beds24→DB同期（新規、ai_reply.pyの後継）
├── line_notify.py      # LINE通知送信（変更なし）
├── line_webhook.py     # LINE Webhook → DB参照に変更
├── web_app.py          # Web → DB参照に変更
├── main.py             # CLI → DB参照に変更
├── cli.py              # CLI承認フロー → DB参照に変更
├── rules/
│   └── property_206100.md
├── templates/
│   └── dashboard.html
├── minpaku.db          # SQLiteファイル（新規、.gitignore対象）
└── serviceplan.md
```

廃止済み: `ai_reply.py`, `pending_store.py`, `pending.json`

---

## これから実装するもの
