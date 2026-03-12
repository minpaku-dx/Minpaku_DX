# Railway デプロイ手順

> このファイルはデプロイ時に必要な作業をまとめたもの。
> 新しい変更がある度に追記する。

---

## 現在のデプロイ情報

- **URL:** `https://minpakudx-production.up.railway.app`
- **ヘルスチェック:** `GET /health`
- **LINE Webhook:** `POST /callback`

---

## 今回のデプロイで必要な作業

### 1. 環境変数の追加 (Railway Dashboard → Variables)

| 変数名 | 値 | 備考 |
|--------|-----|------|
| `DASHBOARD_USER` | 任意のユーザー名 | Web Dashboard Basic Auth用。未設定だとダッシュボードが503になる |
| `DASHBOARD_PASS` | 強いパスワード | `python -c "import secrets; print(secrets.token_urlsafe(16))"` で生成推奨 |

既存の環境変数（変更不要）:
- `REFRESH_TOKEN` — Beds24
- `GEMINI_API_KEY` — Google Gemini
- `LINE_CHANNEL_ACCESS_TOKEN` — LINE
- `LINE_CHANNEL_SECRET` — LINE
- `LINE_OWNER_USER_ID` — LINE
- `DATABASE_URL` — Supabase PostgreSQL
- `SYNC_INTERVAL_SECONDS` — 300（デフォルト）

### 2. DBマイグレーション（自動）

`db.py` のインポート時に `_migrate_bookings_add_guest_fields()` が自動実行される。
bookingsテーブルに6カラム追加（`num_adult`, `num_child`, `guest_country`, `guest_language`, `guest_arrival_time`, `guest_comments`）。
既にカラムが存在する場合はスキップ（冪等）。

**手動作業は不要。** デプロイ後の初回起動時に自動適用される。

### 3. デプロイ後の確認事項

- [ ] `GET /health` が `{"status":"ok"}` を返すこと
- [ ] 起動直後に初回同期が走ること（`next_run_time=datetime.now()` 追加済み）
- [ ] Web Dashboard (`GET /`) にアクセスするとBasic Authダイアログが表示されること
- [ ] 正しい認証情報でダッシュボードが表示されること
- [ ] 間違った認証情報で401が返ること
- [ ] 5回失敗後に429（ロックアウト）が返ること
- [ ] LINE通知に「スキップ」ボタンが表示されること
- [ ] LINEで「スキップ」タップ後にステータスが `skipped` になること

---

## 変更履歴（今回含む全コード変更）

### Path A: コードクリーンアップ (2026-03-11)
- `beds24.py`: デバッグログ（json.dumps）削除
- `app.py`: `/debug/booking-fields` エンドポイント削除
- `line_notify.py`: 未使用の `send_line_text()` と `TextMessage` インポート削除

### Path B: ゲスト属性拡張 (2026-03-11)
- `beds24.py`: `get_booking_details()` に6フィールド追加（numAdult, numChild, guestCountry, guestLanguage, guestArrivalTime, guestComments）
- `db.py`: bookingsテーブルDDLに6カラム追加 + `upsert_booking()` を12パラメータに拡張 + `_migrate_bookings_add_guest_fields()` マイグレーション追加
- `sync_service.py`: `sync_booking_to_db()` で新フィールドを渡すように更新
- `ai_engine.py`: `_is_japanese()` 追加、プロンプトにゲスト属性注入、言語自動検出

### Fix #22: 重複ドラフト行 (2026-03-11)
- `db.py`: `get_draft_ready_messages()` を相関サブクエリに変更（最新ドラフトのみJOIN）

### Fix #9: LINEスキップボタン (2026-03-11)
- `line_notify.py`: Flex Messageフッターに「スキップ」ボタン追加
- `app.py`: `handle_postback()` に `action=skip` ハンドラー追加

### Fix #12: 起動直後の同期 (2026-03-11)
- `app.py`: `scheduler.add_job()` に `next_run_time=datetime.now()` 追加

### Fix #13: Web Dashboard認証 (2026-03-11)
- `app.py`: HTTP Basic Auth実装（`verify_credentials()`）、レートリミット（5回失敗→60秒ロックアウト）、認証失敗ログ
- 環境変数追加: `DASHBOARD_USER`, `DASHBOARD_PASS`

### Fix #20: 同一予約メッセージのグルーピング (2026-03-11)
- `sync_service.py`: `run_once()` に booking_id グルーピング追加。同一予約の複数メッセージは最新のみAI生成+LINE通知

### Legacy cleanup + cli.py強化 (2026-03-11)
- `web_app.py`: 削除（app.pyに統合済み）
- `line_webhook.py`: 削除（app.pyに統合済み、cloudflaredランチャー含む）
- `cli.py`: `display_booking_header()` にゲスト属性（人数、国籍、言語、到着時間、備考）表示を追加

### Code polish: #16, #10, #14, #18 (2026-03-11)
- `beds24.py`: 全print→logging変換、TTLトークンキャッシュ（20分）+ `invalidate_token_cache()` 追加
- `sync_service.py`: 全print→logging変換、`_now()` ヘルパー削除、スタンドアロン実行時のlogging.basicConfig追加
- `app.py`: 環境変数バリデーション（5必須変数）、同期ステータス追跡（`_sync_status`）、ヘルスチェック拡張（DB接続・env・同期状態）、送信リトライ時のトークンキャッシュ無効化
- `db.py`: `check_health()` 関数追加

### Final polish: #11, #17, #21 (2026-03-11)
- `beds24.py`: `get_unread_guest_messages()` にAPIフィルタパラメータ追加（レスポンス量削減）
- `sync_service.py`: `run_once()` がメトリクス辞書を返すように変更（messages_processed, drafts_generated, line_notifications_sent, errors）
- `app.py`: `_sync_status` に累積カウンタ追加、`_server_start_time` 追加、`/health` にメトリクス公開
- `templates/dashboard.html`: モバイルレスポンシブCSS追加（ナビバー・チップ・ボタン・トースト全幅化）

### Feature: #26 プロアクティブメッセージ (2026-03-11)
- `db.py`: `proactive_messages` テーブル追加（PG/SQLite両方）。CRUD関数6個追加（has_proactive, save_proactive_draft, get_proactive_by_id, get_draft_ready_proactive, update_proactive_status, has_recent_conversation）
- `beds24.py`: `get_bookings_by_date_range()` と `get_bookings_by_checkout_range()` 追加（日付範囲で予約検索、ページネーション対応）
- `ai_engine.py`: `generate_proactive_message()` 追加（pre_checkin: ウェルカム+おすすめスポット / post_checkout: サンキュー+レビュー依頼）
- `sync_service.py`: `check_proactive_triggers()` 追加。`run_once()` の各ポイント（メッセージ無し時含む）からプロアクティブチェックを実行。JST時刻ベースの日付計算
- `line_notify.py`: `send_proactive_line_message()` 追加（トリガー別カラーテーマのFlex Message）
- `app.py`: postbackハンドラーが `pro_` プレフィックスでプロアクティブを識別。`/api/messages` がプロアクティブ含む統合レスポンス返却。`/api/send` `/api/skip` がプロアクティブID対応。メッセージ編集もプロアクティブ対応。SendRequest.messageIdを `str | int | None` に変更
- `templates/dashboard.html`: プロアクティブバッジCSS追加。`buildCard()` がプロアクティブカードを区別表示（バッジ・左パネル・ラベル変更）。送信/スキップのID引数を文字列化

**DBマイグレーション**: `proactive_messages` テーブルと `editing_state` テーブルは `init_db()` で自動作成される（DDL内に `CREATE TABLE IF NOT EXISTS`）。手動作業不要。

### Code polish: #4 + dedup + fixes (2026-03-11)
- `beds24.py`: `_normalize_booking()` ヘルパー抽出。`get_booking_details()`, `get_bookings_by_date_range()`, `get_bookings_by_checkout_range()` の重複コードを統一
- `db.py`: `has_recent_conversation()` を修正（`synced_at` → `sent_at`、文字列補間 → パラメータ化クエリ）。`editing_state` テーブル + CRUD 3関数追加（`save_editing_state`, `get_editing_state`, `delete_editing_state`）
- `sync_service.py`: `_upsert_booking_from_api()` と `_process_proactive_booking()` ヘルパー抽出。pre/post重複コード統一。冗長なBeds24 APIコールを排除（既取得データで直接DB upsert）
- `app.py`: `editing_state` をインメモリ dict → DB永続化に変更（#4解決）。`/api/messages` の通常メッセージに `type: "reply"` 追加

### Bugfix: 5件の品質改善 (2026-03-11)
- `sync_service.py`: post_checkoutプロアクティブにも`has_recent_conversation()`チェック追加
- `app.py`: プロアクティブAPI送信リトライ時のステータス更新漏れ修正
- `line_notify.py`: Flex Message文字列の不要なエスケープ処理削除
- `app.py`: LINE postback/Web APIの`int()`変換にValueError保護追加
- `db.py`: `save_proactive_draft()`をUPSERTに変更（UNIQUE制約違反防止）
