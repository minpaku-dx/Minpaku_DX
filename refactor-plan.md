# リファクタリング計画

**最終更新**: 2026-03-09
**目的**: サービス化の前に、現行コードの重複・不整合を解消し、信頼できる土台を作る

---

## 現状の問題

### 1. コードが重複している

`ai_reply.py`が`beds24.py`と`ai_engine.py`の機能をコピペで再実装している。

| 関数 | beds24.py / ai_engine.py | ai_reply.py |
|---|---|---|
| `get_unread_guest_messages()` | limit: 50 | limit: 20（別実装） |
| `get_message_thread()` | 7フィールド返す | 3フィールドしか返さない |
| `generate_reply()` | 引数4個（message, property_id, thread, booking_info） | 引数2個（message, history文字列） |

→ 同じ機能が2箇所にあり、挙動もバラバラ。

### 2. エントリーポイントごとにコードパスが違う

| エントリーポイント | 使っているモジュール |
|---|---|
| CLI（main.py / cli.py） | beds24.py + ai_engine.py |
| Web（web_app.py） | beds24.py + ai_engine.py |
| LINE（ai_reply.py） | **独自実装**（beds24.pyを使っていない） |

→ LINE経由だけ別の動きをする。バグ修正も2箇所やる羽目になる。

### 3. ai_reply.pyが肥大化している

1ファイルに以下が全部入っている：
- Beds24 API呼び出し（重複）
- AI返信生成（重複）
- LINE通知送信
- pending.json管理
- メインループ

→ 責務が混在していて修正しづらい。

### 4. pending.jsonによる状態管理

承認待ちの返信をJSONファイルで管理している。
- 同時アクセスで壊れる可能性
- 再起動するとデータが残ったまま
- 検索・フィルタができない

---

## 修正方針

### ステップ1: ai_reply.pyから重複コードを削除

- `get_access_token()`、`get_unread_guest_messages()`、`get_message_thread()`、`get_booking_details()` → `beds24.py`からimportに切り替え
- `generate_reply()` → `ai_engine.py`からimportに切り替え
- ai_reply.pyに残すのは**LINE通知の送信ロジックだけ**

### ステップ2: ai_reply.pyを分割

現在のai_reply.pyを以下に分割：

| 新ファイル | 責務 |
|---|---|
| `line_notify.py`（既存） | Flex Message組み立て・送信 |
| `ai_reply.py` | メインフロー（未読取得→AI生成→LINE通知→pending保存）|

ai_reply.pyは薄いオーケストレーターにする。ロジックは全て共通モジュールに委譲。

### ステップ3: beds24.pyの改善

- ページネーション対応（全件取得できるようにする）
- 未読メッセージの取得limitを設定可能にする
- booking_idでのメッセージ取得時に、最新のものだけでなく全スレッドを確実に返す

### ステップ4: ai_engine.pyの改善

- 会話履歴のフォーマットをai_engine.py内に統一（ai_reply.pyの`build_conversation_history`を移動）
- プロンプトの改善（現状のまま使えるが、整理する）

### ステップ5: pending.jsonの改善

- 現段階ではファイルベースのまま維持（DB化はサービス化フェーズで対応）
- ただしread/writeを専用の関数にまとめて、ai_reply.pyとline_webhook.pyから共通利用する
- `pending_store.py` として切り出す

### ステップ6: line_webhook.pyの整理

- beds24.pyからimportして使うように統一（現状は既にそうなっているか確認）
- pending_store.pyを使うように切り替え

---

## 修正後のファイル構成

```
minpaku-dx/
├── beds24.py           # Beds24 API（唯一の窓口）
├── ai_engine.py        # AI返信生成（唯一の窓口）
├── pending_store.py    # pending.json の読み書き（新規）
├── line_notify.py      # LINE Flex Message 組み立て・送信
├── line_webhook.py     # LINE Webhook受信・承認処理
├── ai_reply.py         # LINE通知フロー（オーケストレーター）
├── web_app.py          # Webダッシュボード
├── main.py             # CLIエントリーポイント
├── cli.py              # CLI承認フロー
├── rules/
│   └── property_206100.md
├── templates/
│   └── dashboard.html
└── serviceplan.md
```

**原則: beds24.py と ai_engine.py は全エントリーポイントから共通で使う。重複実装は許さない。**

---

## 修正後のデータフロー

```
全エントリーポイント
  │
  ├── CLI (main.py → cli.py)
  ├── Web (web_app.py)
  └── LINE (ai_reply.py → line_notify.py)
        │
        ▼
  ┌─────────────┐     ┌──────────────┐
  │  beds24.py   │     │ ai_engine.py │
  │  (API統一)   │────▶│  (AI統一)    │
  └─────────────┘     └──────────────┘
```

---

## 作業順序

| 順番 | 作業 | 影響範囲 | 状態 |
|---|---|---|---|
| 1 | pending_store.pyを切り出し | ai_reply.py, line_webhook.py | 完了 |
| 2 | ai_reply.pyの重複関数を削除、beds24.py/ai_engine.pyをimport | ai_reply.py | 完了 |
| 3 | line_webhook.pyをbeds24.py + pending_store.py利用に切り替え | line_webhook.py | 完了 |
| 4 | beds24.pyにページネーション追加 | 全体 | 完了 |
| 5 | 動作確認（CLI / Web / LINE 全パスをテスト） | 全体 | 未着手 |
