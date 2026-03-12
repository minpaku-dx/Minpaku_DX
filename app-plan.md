# Minpaku DX Mobile App — アプリ設計書

> ステータス: 計画段階
> 作成日: 2026-03-12
> アプリ言語: 日本語（オーナー向け）

---

## 1. アプリ概要

### What
民泊オーナー向けゲストメッセージ管理アプリ。Beds24に届くゲストメッセージにAIが返信案を生成し、オーナーがアプリで承認・修正・送信する。

### Why（LINEの限界）
| LINEの制約 | アプリで解決 |
|---|---|
| 無料枠200通/月、超過は従量課金 | プッシュ通知は無制限（FCM） |
| Flex Messageの文字数制限（150/300/500文字） | 全文表示、スクロール可能 |
| テキスト入力でしか修正できない | リッチテキストエリアでインライン編集 |
| 単一オーナー（LINE_OWNER_USER_ID固定） | 複数スタッフ、権限管理 |
| 会話履歴が断片的 | 全スレッドをチャットUIで閲覧 |
| 操作が煩雑（ボタン→入力→確認） | ワンスワイプ承認、片手操作 |

### Who
- 民泊オーナー（ビジネス層 — 複数物件、効率重視）
- 民泊オーナー（おもてなし層 — ゲスト満足度、星5重視）
- 将来: 運営スタッフ（オーナーから権限委譲）

### コアUX原則
1. **3秒で承認** — 通知タップ → メッセージ確認 → スワイプ承認。最短3タップ
2. **片手操作** — 主要アクションは画面下半分に配置。移動中でも使える
3. **ゼロ設定で始まる** — Supabase Authでログイン → Beds24トークン入力 → 即使える
4. **情報は段階開示** — まずプレビュー、タップで詳細、必要なら会話全文

---

## 2. 技術スタック

### Frontend（モバイルアプリ）
| 要素 | 選択 | 理由 |
|---|---|---|
| フレームワーク | **React Native (Expo)** | JS/TSベース、iOS/Android同時、Expo Goで即テスト |
| 状態管理 | **TanStack Query + Zustand** | サーバーステート（API）はTanStack Query、UIステートはZustand |
| ナビゲーション | **Expo Router** | ファイルベースルーティング、ディープリンク組み込み |
| アニメーション | **React Native Reanimated 3** | 60fps スワイプ、シート、トランジション |
| ジェスチャー | **React Native Gesture Handler** | スワイプ承認、プルリフレッシュ |
| プッシュ通知 | **Expo Notifications + FCM** | Expoならセットアップが容易 |
| UI基盤 | **自前デザインシステム** | ブランドに合わせたカスタム。後述のデザイントークン使用 |
| フォーム | **React Hook Form** | テキストエリア編集のバリデーション |

### Backend（既存FastAPI拡張）
| 要素 | 現状 | 変更 |
|---|---|---|
| API | FastAPI (app.py) | 新エンドポイント追加 |
| 認証 | Basic Auth | **Supabase Auth**（既にSupabase使用中。JWT自前実装不要） |
| DB | Supabase PostgreSQL | テーブル追加（devices, user_settings） |
| プッシュ通知 | LINE push_message | **FCM** 追加（firebase-admin） |
| リアルタイム | なし | **MVP: プッシュ通知 + プルリフレッシュ**。Phase 2でSSE検討 |

> **判断: WebSocketはMVPではやらない。** プッシュ通知でメッセージ到着を知らせ、アプリを開いたらAPI呼び出しで最新取得。十分な即時性がある。WebSocketは複数スタッフ同時編集が必要になるPhase 3で検討。

> **判断: Supabase Auth を使う。** 既にSupabase PostgreSQLを使っているのでAuth統合が自然。JWT発行・検証・リフレッシュをSupabaseが管理するため、自前実装のセキュリティリスクがない。RLS（Row Level Security）でDB直接のアクセス制御も可能。

---

## 3. デザインシステム

### 3.1 デザインコンセプト

**ビジュアルスタイル: "Calm Professional"**
- クリーンで余白が多い。情報過多にしない
- 角丸は大きめ（16px）で柔らかい印象
- シャドウは最小限（elevation 1-2）。フラットに近いがカードは浮かせる
- アクセントカラーは控えめに。重要なアクションだけ色を使う
- 参考: Linear, Notion, Airbnb Host アプリ

### 3.2 カラーパレット

```
■ Primary（ブランドカラー）
  primary-500: #2563EB    — メインアクション（承認ボタン、リンク）
  primary-600: #1D4ED8    — ホバー/プレス
  primary-50:  #EFF6FF    — 背景ハイライト

■ Semantic（意味のある色）
  success-500: #059669    — 送信完了、承認済み
  success-50:  #ECFDF5    — 送信済みカード背景
  warning-500: #D97706    — 承認待ち（注意を引く）
  warning-50:  #FFFBEB    — 承認待ちカード背景
  danger-500:  #DC2626    — エラー、削除
  danger-50:   #FEF2F2    — エラー背景
  skip-400:    #9CA3AF    — スキップ済み

■ Neutral（テキスト・背景）
  gray-900:    #111827    — 見出し、メインテキスト
  gray-700:    #374151    — 本文テキスト
  gray-500:    #6B7280    — サブテキスト、ラベル
  gray-300:    #D1D5DB    — ボーダー、ディバイダー
  gray-100:    #F3F4F6    — カード背景、セクション背景
  gray-50:     #F9FAFB    — ページ背景
  white:       #FFFFFF    — カード表面

■ Proactive（プロアクティブメッセージ）
  checkin:     #059669    — チェックイン前ウェルカム（緑系、success流用）
  checkout:    #7C3AED    — チェックアウト後サンキュー（紫）
  checkout-50: #F5F3FF    — 紫背景

■ Dark Mode
  bg-primary:  #0F172A    — ページ背景
  bg-card:     #1E293B    — カード背景
  bg-elevated: #334155    — モーダル、シート背景
  text-primary:#F1F5F9    — メインテキスト
  text-secondary:#94A3B8  — サブテキスト
  border:      #334155    — ボーダー
```

### 3.3 タイポグラフィ

```
フォント: System Default（iOS: SF Pro, Android: Roboto）
日本語: システムフォント（Noto Sans CJK が自動適用）

■ スケール
  heading-xl:  24px / bold   / line-height 32px  — 画面タイトル
  heading-lg:  20px / bold   / line-height 28px  — セクション見出し
  heading-md:  17px / 600    / line-height 24px  — カードタイトル（ゲスト名）
  body-lg:     17px / normal / line-height 24px  — メッセージ本文
  body-md:     15px / normal / line-height 22px  — 標準テキスト
  body-sm:     13px / normal / line-height 18px  — サブ情報（日時、物件名）
  caption:     11px / normal / line-height 16px  — ラベル、バッジ
```

### 3.4 スペーシング

```
基本単位: 4px

xs:   4px   — アイコンとラベルの間
sm:   8px   — 要素内パディング
md:   12px  — リスト項目の間
lg:   16px  — カード内パディング
xl:   24px  — セクション間
2xl:  32px  — 画面内の大きな余白
3xl:  48px  — 画面間の切り替え余白
```

### 3.5 コンポーネント

```
■ カード（MessageCard）
  border-radius: 16px
  padding: 16px
  shadow: 0 1px 3px rgba(0,0,0,0.08)
  背景: white (light) / bg-card (dark)
  ボーダー左: 3px solid — ステータス色
    承認待ち: warning-500
    プロアクティブ(checkin): checkin
    プロアクティブ(checkout): checkout
    送信済み: success-500
    スキップ: skip-400

■ ボタン
  高さ: 48px（タッチターゲット最小44px確保）
  border-radius: 12px
  フォント: body-md / 600
  Primary: bg primary-500, text white
  Secondary: bg gray-100, text gray-700
  Danger: bg danger-50, text danger-500
  プレス: scale(0.97) + opacity 0.9（Reanimated）

■ テキストエリア（AI返信案編集）
  border-radius: 12px
  border: 1.5px solid gray-300
  フォーカス時: border primary-500 + shadow primary-50
  padding: 12px
  min-height: 120px
  フォント: body-lg（読みやすさ重視）

■ バッジ
  border-radius: 999px（完全丸）
  padding: 2px 8px
  フォント: caption / 600
  種類:
    未読数: bg danger-500, text white
    承認待ち: bg warning-50, text warning-500, border warning-200
    送信済み: bg success-50, text success-500
    プロアクティブ: bg checkin/checkout-50, text checkin/checkout

■ ボトムタブ
  高さ: 84px（SafeArea含む）
  背景: white / bg-card (dark)
  上ボーダー: 1px gray-200
  アイコン: 24px, 非選択 gray-400, 選択 primary-500
  ラベル: caption, 非選択 gray-400, 選択 primary-500

■ ヘッダー
  高さ: 56px
  背景: 透明（コンテンツの上に重なるblur効果）
  iOS: large title → scroll で collapse
```

### 3.6 アニメーション・インタラクション

```
■ スワイプアクション（受信トレイ）
  右スワイプ: 承認して送信（緑背景 + チェックマークアイコン）
  左スワイプ: スキップ（グレー背景 + スキップアイコン）
  閾値: 40%スワイプで確定
  フィードバック: iOS haptic (medium impact)
  アニメーション: カードがスライドアウト → リストが詰まる（300ms spring）

■ プルリフレッシュ
  カスタムインジケーター: ブランドアイコン回転
  トリガー距離: 80px

■ 画面遷移
  Push: 右からスライドイン（iOS標準）
  モーダル: 下からスライドアップ（ボトムシート）
  タブ切り替え: クロスフェード（150ms）

■ カードタップ
  プレス: scale(0.98) + opacity(0.95)（100ms）
  リリース: spring back（200ms）

■ 承認完了
  カード: success色にフラッシュ → チェックマーク → フェードアウト
  トースト: 画面上部からスライドダウン（3秒で自動消去）
  ハプティック: success notification

■ ローディング
  スケルトン: shimmer効果のプレースホルダー（カード型）
  送信中: ボタンにスピナー + disabled
  初回ロード: ブランドロゴ → フェードインでコンテンツ表示

■ エラー
  シェイク: テキストフィールドが横に振動（validation error）
  トースト: 赤背景、画面上部、タップで消去可能
  ハプティック: error notification
```

---

## 4. 画面構成

### 4.1 画面ツリー

```
[認証フロー]
├── スプラッシュ（自動ログイン試行）
├── ログイン
├── 新規登録
└── オンボーディング（初回のみ）
    ├── Step 1: Beds24リフレッシュトークン入力
    ├── Step 2: 物件の自動検出・確認
    └── Step 3: プッシュ通知の許可

[メイン — ボトムタブ]
├── Tab 1: 受信トレイ
│   ├── 受信トレイ一覧（承認待ち + プロアクティブ）
│   └── → メッセージ詳細（モーダルプッシュ）
│       └── 会話スレッド全文（インライン展開）
│
├── Tab 2: 履歴
│   ├── 処理済み一覧（送信済み / スキップ）
│   └── → 履歴詳細
│
├── Tab 3: 物件（Phase 2）
│   ├── 物件一覧
│   ├── → 物件詳細
│   │   ├── 予約カレンダー
│   │   └── 予約詳細
│   └── → 物件ルール編集
│
└── Tab 4: 設定
    ├── アカウント
    ├── 通知設定
    ├── AI設定（Phase 2）
    ├── Beds24接続
    └── LINE併用 ON/OFF
```

### 4.2 各画面の詳細

---

#### 画面: スプラッシュ / 自動ログイン

```
目的: アプリ起動時、保存済みセッションでの自動認証
遷移:
  セッション有効 → 受信トレイ
  セッション期限切れ → ログイン画面
  初回起動 → ログイン画面

表示:
  中央にアプリロゴ（Minpaku DX）
  下部にローディングインジケーター
  背景: primary-500のグラデーション
```

---

#### 画面: ログイン

```
目的: メール + パスワードでログイン
レイアウト:
  ┌─────────────────────────────────┐
  │                                 │
  │         [Minpaku DX ロゴ]        │   ← 上部1/3
  │         民泊メッセージ管理        │
  │                                 │
  │  ┌─────────────────────────┐    │
  │  │ メールアドレス             │    │   ← テキストフィールド
  │  └─────────────────────────┘    │
  │  ┌─────────────────────────┐    │
  │  │ パスワード         [👁]   │    │   ← パスワード表示切替
  │  └─────────────────────────┘    │
  │                                 │
  │  [       ログイン       ]       │   ← Primary ボタン（幅100%）
  │                                 │
  │  パスワードを忘れた場合           │   ← テキストリンク
  │                                 │
  │  ─── または ───                  │
  │                                 │
  │  アカウントを作成                │   ← テキストリンク → 新規登録
  │                                 │
  └─────────────────────────────────┘

バリデーション:
  メール: リアルタイムフォーマットチェック
  パスワード: 最低8文字
  エラー: フィールド下に赤テキスト + フィールド赤ボーダー
  認証失敗: トースト「メールアドレスまたはパスワードが違います」

状態:
  ローディング: ボタンにスピナー + 入力フィールド disabled
```

---

#### 画面: オンボーディング（初回のみ、3ステップ）

```
目的: Beds24接続 → 物件確認 → 通知許可
共通: 上部にステッププログレス（● ● ○）、下部に「次へ」ボタン

Step 1: Beds24接続
  「Beds24のリフレッシュトークンを入力してください」
  [テキストフィールド: リフレッシュトークン]
  [接続テスト] ← タップで即時API検証
  成功: 緑チェック + 「接続成功」
  失敗: 赤テキスト + 「トークンを確認してください」
  ？ヘルプ: 「トークンの取得方法」→ ボトムシートで手順説明

Step 2: 物件確認
  接続成功後、Beds24から物件一覧を自動取得して表示
  「以下の物件が見つかりました」
  ☑ 平井戸建 (ID: 206100)
  ☑ 渋谷マンション (ID: 207200)
  チェックボックスで管理対象を選択

Step 3: 通知許可
  「新着メッセージをすぐにお知らせします」
  [イラスト: 通知のイメージ]
  [通知を許可する] ← OS通知許可ダイアログを呼び出し
  「あとで設定する」← スキップ可能
```

---

#### 画面: 受信トレイ（メイン画面、Tab 1）

```
目的: 承認待ちメッセージを一覧し、素早く処理する
重要度: ★★★ アプリの最重要画面

レイアウト:
  ┌─────────────────────────────────┐
  │ 受信トレイ              🔔 3    │   ← ヘッダー + 未読バッジ
  ├─────────────────────────────────┤
  │ [すべて]  [返信]  [プロアクティブ] │   ← セグメントフィルター
  ├─────────────────────────────────┤
  │                                 │
  │  ┌─ warning左ボーダー ─────────┐ │
  │  │ 平井戸建                    │ │   ← body-sm, gray-500
  │  │ John Smith           5分前  │ │   ← heading-md + caption
  │  │ 🇦🇺 大人2 子供1              │ │   ← ゲスト属性バッジ（小さく）
  │  │ "What time can I check..."  │ │   ← body-md, gray-700, 2行打ち切り
  │  │ ┌────────────────────────┐  │ │
  │  │ │ 🤖 Dear John, Thank... │  │ │   ← AI返信プレビュー（1行）
  │  │ └────────────────────────┘  │ │      bg gray-50, body-sm
  │  └────────────────────────────┘ │
  │          12px gap               │
  │  ┌─ checkin左ボーダー ─────────┐ │
  │  │ 渋谷マンション               │ │
  │  │ Marie Dupont         10分前 │ │
  │  │ [チェックイン前] IN 3/17     │ │   ← プロアクティブバッジ（緑）
  │  │ ┌────────────────────────┐  │ │
  │  │ │ 🤖 Bonjour Marie...   │  │ │
  │  │ └────────────────────────┘  │ │
  │  └────────────────────────────┘ │
  │                                 │
  └─────────────────────────────────┘

スワイプアクション:
  → 右スワイプ: 承認して送信
    背景: success-500
    アイコン: チェックマーク（白）
    40%超えでトリガー → ハプティック → カードスライドアウト → トースト「送信しました」
    AI返信案をそのまま送信（修正なし）

  ← 左スワイプ: スキップ
    背景: gray-400
    アイコン: スキップ矢印（白）
    40%超えでトリガー → カード消去 → トースト「スキップしました」

カードタップ → メッセージ詳細画面へ遷移

プルリフレッシュ: 下に引っ張って最新取得

空の状態（メッセージ0件）:
  中央にイラスト + 「承認待ちのメッセージはありません」
  サブテキスト: 「新着メッセージが届くと通知でお知らせします」

エラー状態（API失敗）:
  中央にエラーアイコン + 「読み込みに失敗しました」
  [再試行] ボタン

ローディング状態:
  スケルトンカード × 3（shimmer animation）
```

---

#### 画面: メッセージ詳細 / 承認画面

```
目的: メッセージの全文確認 + AI返信案の編集 + 送信
重要度: ★★★ コア体験

レイアウト:
  ┌─────────────────────────────────┐
  │ ← 戻る           予約 #28445   │   ← ヘッダー
  ├─────────────────────────────────┤
  │                                 │
  │  ┌─ ゲスト情報ヘッダー ────────┐ │
  │  │ John Smith                  │ │   ← heading-lg
  │  │ 平井戸建                    │ │   ← body-sm, gray-500
  │  │ IN 3/15 → OUT 3/18         │ │
  │  │ 🇦🇺 オーストラリア            │ │
  │  │ 大人2名 子供1名              │ │
  │  │ 到着予定: 16:30              │ │   ← 属性があれば表示
  │  └────────────────────────────┘ │
  │                                 │   ← スクロール可能エリア
  │  ── 会話 ──                     │
  │                                 │
  │     ┌─────────────────────┐    │
  │     │ Hi, what time can I │    │   ← ゲスト吹き出し（左寄せ）
  │     │ check in?           │    │      bg gray-100, 角丸
  │     └─────────────────────┘    │
  │     3/12 14:00                  │   ← caption, gray-400
  │                                 │
  │  ┌─────────────────────┐       │
  │  │ Check-in is from    │       │   ← ホスト吹き出し（右寄せ）
  │  │ 16:00. We can...    │       │      bg primary-50, 角丸
  │  └─────────────────────┘       │
  │                     3/12 14:30  │
  │                                 │
  │     ┌─────────────────────┐    │
  │     │ Thanks! Is there a │    │   ← 最新メッセージ
  │     │ parking spot?      │ 🔴 │      赤ドット = 未読
  │     └─────────────────────┘    │
  │     3/14 09:00                  │
  │                                 │
  ├─────────────────────────────────┤
  │                                 │   ← 固定フッター（画面下部固定）
  │  AI返信案 🤖                     │   ← ラベル
  │  ┌─────────────────────────┐   │
  │  │ Dear John,              │   │   ← TextArea（編集可能）
  │  │                         │   │      body-lg, min-height 120px
  │  │ Thank you for your      │   │      タップでキーボード表示
  │  │ message! Unfortunately  │   │      フォーカス時: blue border
  │  │ there is no dedicated   │   │
  │  │ parking spot...         │   │
  │  └─────────────────────────┘   │
  │                                 │
  │  [  承認して送信  ]  [ スキップ ] │   ← 2ボタン横並び
  │                                 │      承認=Primary(幅2/3)
  │                                 │      スキップ=Secondary(幅1/3)
  └─────────────────────────────────┘

操作フロー:
  A. そのまま承認:
     「承認して送信」タップ → 確認なし、即送信
     → ボタンがスピナーに → 成功: チェックマーク + ハプティック → 自動で受信トレイに戻る
     → 失敗: ボタン戻る + エラートースト「送信に失敗しました。再試行してください」

  B. 修正して送信:
     テキストエリアをタップ → キーボード表示 → 自由編集
     → テキスト変更済み: ボタン「修正して送信」に変化（テキスト+色が変わる）
     → 送信フローはAと同じ

  C. スキップ:
     「スキップ」タップ → 確認ダイアログ「スキップしますか？」
     → はい: status=skipped → トースト → 受信トレイに戻る

プロアクティブメッセージの場合:
  会話履歴セクションの代わりに:
  ┌────────────────────────────────┐
  │ [チェックイン前ウェルカム]       │  ← 緑バッジ or 紫バッジ
  │ チェックイン: 3/17              │
  │ チェックアウト: 3/20            │
  │ このゲストとの会話はまだありません │  ← プロアクティブは先制メッセージ
  └────────────────────────────────┘
```

---

#### 画面: 履歴（Tab 2）

```
目的: 処理済みメッセージの確認
レイアウト: 受信トレイと同じカードUI、ただし:
  - 左ボーダー色がステータスに応じて変わる（success=送信済み, gray=スキップ）
  - カードにステータスバッジ表示（「送信済み」「スキップ」「編集済み」）
  - カードにチャネル表示（「LINE」「App」「Web」）
  - スワイプアクションなし（タップで詳細のみ）

フィルター: [すべて] [送信済み] [スキップ]
ソート: 新しい順（処理日時）
ページネーション: 無限スクロール（20件ずつ）

空の状態:
  「まだ処理済みのメッセージはありません」
```

---

#### 画面: 物件一覧（Tab 3, Phase 2）

```
目的: 管理物件の概要とアクセス

カードごとに:
  - 物件名
  - 住所（1行）
  - 今月の予約数
  - 承認待ちメッセージ数（バッジ）

タップ → 物件詳細

物件詳細:
  - 基本情報（住所、チェックイン/アウト時間）
  - 予約カレンダー（月表示、日付セルにチェックイン/アウトのドット表示）
  - 直近の予約一覧
  - [ルール編集] → 物件ルールのマークダウンエディタ
```

---

#### 画面: 設定（Tab 4）

```
目的: アプリ・アカウント設定

セクション構成（iOS Settings風グループリスト）:

[アカウント]
  プロフィール（名前、メール）
  パスワード変更
  ログアウト

[通知]
  プッシュ通知 ← トグルスイッチ
  新着メッセージ通知 ← トグル
  プロアクティブ通知 ← トグル
  未処理リマインダー（30分後） ← トグル

[接続]
  Beds24 接続状態: 🟢 接続中 / 🔴 切断
  リフレッシュトークン変更
  LINE通知（併用モード） ← トグル

[AI設定] (Phase 2)
  返信トーン: [フォーマル / フレンドリー / カジュアル]
  デフォルト署名: [テキストフィールド]

[アプリ]
  ダークモード: [システム / ライト / ダーク]
  バージョン情報
```

---

## 5. 通知設計

### 5.1 プッシュ通知

| トリガー | 通知テキスト | アクション |
|---------|------------|----------|
| AI返信案生成完了 | 「{ゲスト名}から新着メッセージ」<br>「{メッセージプレビュー30文字}」 | タップ → メッセージ詳細画面に直接遷移 |
| プロアクティブ生成完了 | 「ウェルカムメッセージ準備完了」<br>「{ゲスト名} - {物件名}」 | タップ → プロアクティブ詳細画面 |
| 30分未処理リマインダー | 「未対応メッセージが{n}件あります」 | タップ → 受信トレイ |

### 5.2 ディープリンク

```
通知ペイロード:
{
  "type": "new_message" | "proactive" | "reminder",
  "messageId": 123,          // メッセージ詳細に直接遷移
  "screen": "message_detail"  // Expo Router で画面を解決
}

Expo Router パス:
  /messages/{id} → メッセージ詳細
  /messages      → 受信トレイ
```

### 5.3 アプリアイコンバッジ

- 未処理メッセージ数をアプリアイコンバッジに表示
- メッセージ処理後にバッジ数を更新
- Expo Notifications の `setBadgeCountAsync()` を使用

---

## 6. オフライン・エラーハンドリング

### 6.1 ネットワーク状態

```
■ オフライン時:
  - 画面上部にバナー表示: 「オフラインです。接続を確認してください」（warning-50背景）
  - キャッシュされたデータは閲覧可能（TanStack Queryのキャッシュ）
  - 送信/承認ボタンは disabled + グレーアウト
  - オンライン復帰時: バナー消去 + 自動リフレッシュ

■ API エラー時:
  - 401 Unauthorized → 自動リフレッシュ試行 → 失敗ならログイン画面へ
  - 500 Server Error → エラートースト + リトライボタン
  - タイムアウト → 「サーバーに接続できませんでした」 + リトライ

■ Beds24 送信失敗時:
  - エラートースト「送信に失敗しました」
  - メッセージはdraft_readyのまま残る（データロスなし）
  - リトライ可能
```

### 6.2 オプティミスティックUI

```
スワイプ承認時:
  1. カードを即座にリストから除去（楽観的更新）
  2. バックグラウンドでAPI呼び出し
  3. 成功: そのまま（トースト表示）
  4. 失敗: カードをリストに復元 + エラートースト
     TanStack Query の onMutate / onError / onSettled で管理
```

---

## 7. API設計（バックエンド拡張）

### 7.1 認証（Supabase Auth）

```
Supabase Authを使用するため、自前のauth APIは不要。
クライアントは supabase-js を使って直接認証:

  supabase.auth.signUp({ email, password })
  supabase.auth.signInWithPassword({ email, password })
  supabase.auth.signOut()
  supabase.auth.getSession()  → access_token を取得

FastAPI側:
  Authorization: Bearer {supabase_access_token}
  → supabase.auth.get_user(token) でユーザー検証
  → RLSが有効なら直接DBアクセスも権限制御される
```

### 7.2 既存API（認証方式を変更）

| メソッド | パス | 変更内容 |
|---------|------|---------|
| GET | `/api/messages` | Basic Auth → Supabase JWT。レスポンスは変更なし |
| POST | `/api/send` | 同上 |
| POST | `/api/skip` | 同上 |
| GET | `/health` | 変更なし（認証不要） |

### 7.3 新規API

| メソッド | パス | 用途 | レスポンス概要 |
|---------|------|------|--------------|
| GET | `/api/messages/history` | 処理済み一覧 | `{ messages: [...], hasMore, cursor }` |
| GET | `/api/messages/{id}` | 詳細（スレッド込み） | `{ message, booking, thread[], draft }` |
| GET | `/api/bookings` | 予約一覧 | `{ bookings: [...] }` |
| GET | `/api/bookings/{id}` | 予約詳細 | `{ booking, messages[], proactives[] }` |
| GET | `/api/properties` | 物件一覧 | `{ properties: [{ id, name, pendingCount }] }` |
| GET | `/api/properties/{id}` | 物件詳細 | `{ property, rules, stats }` |
| PUT | `/api/properties/{id}/rules` | ルール更新 | `{ ok: true }` |
| POST | `/api/devices` | FCMトークン登録 | `{ ok: true }` |
| DELETE | `/api/devices/{token}` | FCMトークン削除 | `{ ok: true }` |
| GET | `/api/me` | 自分のユーザー情報 | `{ user, properties[] }` |

### 7.4 リアルタイム（MVP）

```
MVPではWebSocket/SSEなし。代わりに:
  1. FCMプッシュ通知でメッセージ到着を知らせる
  2. アプリフォアグラウンド時は60秒ポーリング（TanStack Query refetchInterval）
  3. プルリフレッシュで手動取得
  4. 通知タップでアプリ復帰時に自動リフレッシュ

Phase 2以降で検討:
  - Supabase Realtime（PostgreSQLのCHANGE通知を購読）
  - または SSE endpoint
```

---

## 8. DB拡張

### 8.1 新規テーブル

```sql
-- FCMデバイストークン管理
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    supabase_user_id UUID NOT NULL,     -- Supabase Auth のユーザーID
    fcm_token TEXT UNIQUE NOT NULL,
    platform TEXT NOT NULL,             -- 'ios' / 'android'
    app_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_devices_user ON devices(supabase_user_id);

-- ユーザーごとの設定
CREATE TABLE IF NOT EXISTS user_settings (
    supabase_user_id UUID PRIMARY KEY,
    notify_new_message BOOLEAN DEFAULT TRUE,
    notify_proactive BOOLEAN DEFAULT TRUE,
    notify_reminder BOOLEAN DEFAULT TRUE,
    line_fallback BOOLEAN DEFAULT TRUE,  -- LINE併用モード
    ai_tone TEXT DEFAULT 'friendly',     -- 'formal' / 'friendly' / 'casual'
    ai_signature TEXT DEFAULT '民泊スタッフ一同',
    theme TEXT DEFAULT 'system',         -- 'system' / 'light' / 'dark'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ユーザーと物件の紐付け（Phase 2 マルチスタッフ用）
CREATE TABLE IF NOT EXISTS user_properties (
    supabase_user_id UUID NOT NULL,
    property_id INTEGER NOT NULL,       -- Beds24のpropertyId
    permission TEXT DEFAULT 'manage',   -- 'manage' / 'view'
    PRIMARY KEY (supabase_user_id, property_id)
);
```

### 8.2 既存テーブルへの変更

```
なし。既存テーブル（messages, ai_drafts, bookings, action_logs,
proactive_messages, editing_state）はそのまま使用。
action_logsのchannel列に 'app' が新たに記録されるようになるだけ。
```

---

## 9. プッシュ通知（バックエンド実装）

### 9.1 通知フロー

```
sync_service.run_once()
  └── AI返信案生成完了 or プロアクティブ生成完了
      ├── [既存] send_line_message() — LINE通知（user_settings.line_fallback=true時）
      └── [新規] send_push_notification(property_id, message_type, payload)
          ├── user_properties で property_id に紐づくユーザーを取得
          ├── 各ユーザーの user_settings で通知設定を確認
          ├── devices テーブルからFCMトークンを取得
          └── firebase_admin.messaging.send_each() でバッチ送信
```

### 9.2 新規ファイル: push_notify.py

```python
# push_notify.py の責務:
# - Firebase Admin SDK 初期化
# - send_push_notification(property_id, message_type, data)
# - FCMトークンの無効化ハンドリング（送信失敗時にdevicesテーブルから削除）
```

---

## 10. 機能一覧（フェーズ別）

### Phase 1: MVP

| # | 機能 | 説明 |
|---|------|------|
| F1 | 受信トレイ | 承認待ち一覧、スワイプ承認/スキップ、プルリフレッシュ |
| F2 | メッセージ詳細 | 会話スレッド全文、AI返信案編集、承認/スキップ |
| F3 | プロアクティブ管理 | ウェルカム/サンキューの承認・修正 |
| F4 | プッシュ通知 | FCM経由、ディープリンク対応、アイコンバッジ |
| F5 | 認証 | Supabase Auth（メール+パスワード） |
| F6 | オンボーディング | Beds24トークン入力、物件検出、通知許可 |
| F7 | 履歴 | 送信済み/スキップ一覧、フィルター |
| F8 | ダークモード | システム設定に追従 + 手動切替 |
| F9 | オフライン対応 | キャッシュ表示、ネットワーク状態バナー |

### Phase 2: 管理機能

| # | 機能 |
|---|------|
| F10 | 物件一覧・詳細 |
| F11 | 予約カレンダー |
| F12 | 物件ルール編集 |
| F13 | AI設定（トーン、署名） |
| F14 | 通知の詳細設定（物件別、時間帯） |
| F15 | LINE併用モード切替 |

### Phase 3: スケール

| # | 機能 |
|---|------|
| F16 | マルチスタッフ（招待、権限管理） |
| F17 | リアルタイム同期（Supabase Realtime or SSE） |
| F18 | アナリティクス（応答時間、AI採用率） |
| F19 | クイック返信テンプレート |
| F20 | 天気/イベント連携（airesponsebrainstorm Phase 3） |

---

## 11. 既存システムへの影響

### 変更が必要

| ファイル | 変更 |
|---------|------|
| `app.py` | Supabase Auth検証ミドルウェア追加。新APIエンドポイント追加。action_logsのchannel='app'対応 |
| `sync_service.py` | AI生成完了後に `send_push_notification()` 呼び出し追加 |
| `db.py` | 新テーブル（devices, user_settings, user_properties）のDDL + CRUD追加 |
| `requirements.txt` | `firebase-admin`, `supabase` 追加 |

### 新規ファイル

| ファイル | 役割 |
|---------|------|
| `push_notify.py` | FCMプッシュ通知送信 |
| `auth.py` | Supabase Auth検証ヘルパー |

### 変更不要

| ファイル | 理由 |
|---------|------|
| `beds24.py` | API層は変更不要 |
| `ai_engine.py` | AI生成ロジックは変更不要 |
| `line_notify.py` | 併用モードとして残す |
| `cli.py` | 開発用として残す |
| `rules/property_*.md` | そのまま |
| `templates/dashboard.html` | Web版も並行稼働 |

---

## 12. ディレクトリ構成（React Native）

```
minpaku-dx-app/
├── app/                          # Expo Router（ファイルベースルーティング）
│   ├── _layout.tsx               # ルートレイアウト（認証チェック）
│   ├── (auth)/                   # 認証フロー（未ログイン時）
│   │   ├── login.tsx
│   │   ├── register.tsx
│   │   └── onboarding.tsx
│   ├── (tabs)/                   # メインタブ（ログイン後）
│   │   ├── _layout.tsx           # ボトムタブレイアウト
│   │   ├── index.tsx             # Tab 1: 受信トレイ
│   │   ├── history.tsx           # Tab 2: 履歴
│   │   ├── properties.tsx        # Tab 3: 物件（Phase 2）
│   │   └── settings.tsx          # Tab 4: 設定
│   └── messages/
│       └── [id].tsx              # メッセージ詳細（モーダル）
│
├── components/                   # 共通コンポーネント
│   ├── ui/                       # デザインシステム基盤
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Toast.tsx
│   │   ├── TextArea.tsx
│   │   └── Skeleton.tsx
│   ├── MessageCard.tsx           # 受信トレイのカード
│   ├── SwipeableCard.tsx         # スワイプアクション付きカード
│   ├── ChatBubble.tsx            # 会話スレッドの吹き出し
│   ├── GuestInfo.tsx             # ゲスト属性表示
│   └── EmptyState.tsx            # 空状態表示
│
├── hooks/                        # カスタムフック
│   ├── useMessages.ts            # TanStack Query: メッセージ取得
│   ├── useSendMessage.ts         # TanStack Query: 送信mutation
│   ├── useAuth.ts                # Supabase Auth
│   └── useNotifications.ts       # Expo Notifications
│
├── lib/                          # ユーティリティ
│   ├── api.ts                    # API クライアント（fetch wrapper）
│   ├── supabase.ts               # Supabase クライアント初期化
│   ├── theme.ts                  # デザイントークン（色、フォント、スペーシング）
│   └── store.ts                  # Zustand ストア
│
├── assets/                       # 静的アセット
│   ├── icon.png
│   ├── splash.png
│   └── adaptive-icon.png
│
├── app.json                      # Expo設定
├── tsconfig.json
└── package.json
```
