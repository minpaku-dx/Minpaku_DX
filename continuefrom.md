# やることリスト — Railway デプロイ完了まで

## 完了済み
- [x] Supabase プロジェクト作成（Tokyo リージョン）
- [x] Supabase Session Pooler URL 取得・接続テスト済み
- [x] LINE Developers Console — プロバイダー + チャンネル作成（@752nblny）
- [x] LINE Webhook URL 設定済み
- [x] Railway デプロイ（GitHub連携済み）
- [x] Beds24 REFRESH_TOKEN 取得済み
- [x] GEMINI_API_KEY 取得済み（要確認: `AIzaSy...` 形式か？現在の値が違う可能性あり）

## Step 1: Railway URL 確認
- [ ] Railway ダッシュボード → Settings → Networking → Public Domain
- [ ] URL が `minpakudx-production` か `minpaku-dx-production` か確認
- [ ] LINE に設定した Webhook URL と一致するか確認
- [ ] 不一致なら LINE Developers Console で Webhook URL を修正

## Step 2: Railway に環境変数を設定
- [ ] Railway ダッシュボード → Variables タブ
- [ ] 以下を全て入力（値はローカルの .env ファイルを参照）:

```
DATABASE_URL=（.env の値をコピー）
REFRESH_TOKEN=（.env の値をコピー）
GEMINI_API_KEY=（.env の値をコピー）
LINE_CHANNEL_SECRET=（.env の値をコピー）
LINE_CHANNEL_ACCESS_TOKEN=（.env の値をコピー）
LINE_OWNER_USER_ID=later（Step 4 で設定）
PORT=8080
SYNC_INTERVAL_SECONDS=300
```

- [ ] 自動で再デプロイされる（または Deploy をクリック）

## Step 3: デプロイ確認
- [ ] Railway URL + `/health` にアクセス
- [ ] `{"status":"ok","sync_interval":300}` が返ればOK
- [ ] エラーなら Railway → Deployments → View Logs で確認

## Step 4: LINE_OWNER_USER_ID 取得
- [ ] スマホの LINE で @752nblny を友達追加
- [ ] Bot に何かメッセージを送る（例:「テスト」）
- [ ] Railway → Deployments → View Logs
- [ ] ログに表示される `U` で始まる32文字の文字列をコピー
- [ ] Railway Variables で `LINE_OWNER_USER_ID` をその値に更新

## Step 5: Webhook 疎通確認
- [ ] LINE Developers Console → Messaging API → 「Verify」ボタン
- [ ] 成功すれば全セットアップ完了

## Step 6: GEMINI_API_KEY 確認（要対応）
- [ ] https://aistudio.google.com/apikey にアクセス
- [ ] API Key が `AIzaSy...` 形式であることを確認
- [ ] もし違っていたら新しく作成して Railway Variables と .env を更新

## 完了後
5分ごとに自動で:
1. Beds24 の新着ゲストメッセージを検出
2. AI が返信案を生成
3. LINE に通知が届く
4. 「承認」か「修正」ボタンを押すだけ

## セキュリティ対応
- [ ] Supabase ダッシュボードでデータベースパスワードを変更（チャットに残っているため）
- [ ] 変更後、Railway の DATABASE_URL と .env も新パスワードに更新
