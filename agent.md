# Agent Coordination File
# Minpaku DX — 2-Agent Development System

**最終更新**: 2026-03-07
**読むべき人**: Agent 1 (Frontend) と Agent 2 (Backend) 両方

---

## 役割分担

| | Agent 1 (Frontend) | Agent 2 (Backend) |
|---|---|---|
| **担当** | CLI UI / 通知 / ユーザー操作 | API連携 / AI / データ処理 |
| **ファイル** | `cli.py`, `main.py` | `beds24.py`, `ai_engine.py`, `rules/` |
| **責任範囲** | 表示・入力・フロー制御 | データ取得・AI生成・送信 |

---

## インターフェース契約（両エージェントが守るべき仕様）

Agent 1 は Agent 2 が作る以下の関数を呼び出す。
**引数・返り値の型を変えるときは必ずこのファイルを更新すること。**

### `beds24.py`

```python
get_access_token() -> str | None
# Beds24のアクセストークンを返す。失敗時はNone。

get_unread_guest_messages(token: str) -> list[dict]
# 未読かつsource=="guest"のメッセージリストを返す。
# 各dictの構造:
# {
#   "id": int,
#   "bookingId": int,
#   "propertyId": int,
#   "message": str,
#   "time": str (ISO8601),
#   "source": "guest"
# }

get_message_thread(token: str, booking_id: int) -> list[dict]
# 指定bookingIdの会話スレッド全件を時系列順で返す。
# 各dictは get_unread_guest_messages と同じ構造 + "read": bool

get_booking_details(token: str, booking_id: int) -> dict
# 予約詳細を返す。
# {
#   "guestName": str,
#   "checkIn": str (YYYY-MM-DD),
#   "checkOut": str (YYYY-MM-DD),
#   "propertyId": int,
#   "propertyName": str
# }

send_reply(token: str, booking_id: int, message: str) -> bool
# Beds24にメッセージを送信。成功時True、失敗時False。
```

### `ai_engine.py`

```python
generate_reply(
    guest_message: str,
    property_id: int,
    thread: list[dict],       # get_message_thread の返り値
    booking_info: dict        # get_booking_details の返り値
) -> str
# AI返信案のテキストを返す。
```

---

## ファイル構成（完成形）

```
Minpaku_DX/
├── agent.md          # 本ファイル（進捗・仕様の共有）
├── plan.md           # 全体ロードマップ
├── .env              # APIキー（gitignore対象）
├── .gitignore
├── requirements.txt
├── main.py           # エントリーポイント（Agent 1が管理）
├── cli.py            # CLI UI・承認フロー（Agent 1）
├── beds24.py         # Beds24 API操作（Agent 2）
├── ai_engine.py      # Gemini AI・プロンプト構築（Agent 2）
└── rules/
    ├── property_206100.md   # 平井戸建（Agent 2が作成）
    └── ...
```

---

## 進捗トラッカー

### Agent 2 (Backend) タスク
- [x] Phase 1: `.env` + `requirements.txt` + `.gitignore` 作成
- [x] Phase 1: `beds24.py` に `get_access_token()` を移植（既存コードから）
- [x] Phase 1: `beds24.py` に `get_unread_guest_messages()` を移植
- [x] Phase 2: `beds24.py` に `get_message_thread()` を追加
- [x] Phase 2: `beds24.py` に `get_booking_details()` を追加
- [x] Phase 2: `beds24.py` に `send_reply()` を追加
- [x] Phase 2: `ai_engine.py` を作成（RAG + Gemini生成）
- [x] Phase 2: `rules/property_206100.md` を作成（平井戸建）
- [ ] Phase 2: 全物件のrulesファイルを揃える

### Agent 1 (Frontend) タスク
- [x] Phase 1: `cli.py` の基本構造を作成
- [x] Phase 1: メッセージ一覧表示ロジック（モックで動作確認済み）
- [x] Phase 2: s/e/n 承認フロー実装
- [x] Phase 2: 編集モード（テキスト書き換え）実装
- [x] Phase 2: `main.py` エントリーポイント作成（--poll フラグ対応）
- [x] Phase 3: macOS通知連携（osascript）
- [x] Phase 3: ポーリングループ実装（--poll --interval オプション）
- [ ] Phase 4: LINE通知連携

---

## 現在のブロッカー

| ブロッカー | 影響 | 担当 |
|---|---|---|
| なし | — | — |

---

## 変更ログ

| 日付 | Agent | 変更内容 |
|---|---|---|
| 2026-03-07 | Agent 1 | agent.md 作成、役割・インターフェース定義 |
| 2026-03-07 | Agent 1 | cli.py 完成（表示・承認フロー・編集モード）|
| 2026-03-07 | Agent 1 | main.py 完成（single run / --poll / macOS通知 / モックフォールバック）|
| 2026-03-07 | Agent 2 | .env / .gitignore / requirements.txt 作成 |
| 2026-03-07 | Agent 2 | beds24.py 完成（全5関数: get_access_token / get_unread_guest_messages / get_message_thread / get_booking_details / send_reply）|
| 2026-03-07 | Agent 2 | ai_engine.py 完成（RAG対応 generate_reply）|
| 2026-03-07 | Agent 2 | rules/property_206100.md 作成（平井戸建、要確認項目あり）|
