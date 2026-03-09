# やることリスト — Railway デプロイ完了まで

## Step 1: Railway URL 確認
- [ ] Railway ダッシュボード → Settings → Networking → Public Domain
- [ ] 表示されている URL をコピー（`minpakudx` か `minpaku-dx` か確認）
- [ ] もし LINE に設定した Webhook URL と違っていたら、LINE Developers Console で修正

## Step 2: Beds24 REFRESH_TOKEN 取得
- [ ] https://beds24.com にログイン
- [ ] Settings → Apps & Integrations → API に移動
- [ ] API V2 セクションで Refresh Token をコピー（なければ Generate）

## Step 3: GEMINI_API_KEY 取得
- [ ] https://aistudio.google.com/apikey にアクセス
- [ ] 「Create API Key」→ API Key をコピー（`AIza...` で始まる）

## Step 4: Railway に環境変数を設定
- [ ] Railway ダッシュボード → Variables タブ
- [ ] 以下を全て入力:

```
DATABASE_URL=postgresql://postgres.dtkttpsnxirhtpjmogvd:[PASSWORD]@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres
REFRESH_TOKEN=（Step 2 の値）
GEMINI_API_KEY=（Step 3 の値）
LINE_CHANNEL_SECRET=b1adb998586a7680aea942a4554df857
LINE_CHANNEL_ACCESS_TOKEN=JNlYUpgJ6oFsaPuaiFxb+BhLa/d9LPc8yJMz25lhq7WVE1hXEMrl18TWk4BrxzFwOjzlBzDoeIFHtGMj8/DxQNTawHqrk3240r7zkXzxIzhwPa2lVvqzvS8OdTXzw7dkSzQUMJ8a8/ZktgdC8tMUKgdB04t89/1O/w1cDnyilFU=
LINE_OWNER_USER_ID=later（Step 6 で設定）
PORT=8080
SYNC_INTERVAL_SECONDS=300
```

- [ ] Deploy をクリック（自動で再デプロイされる場合もある）

## Step 5: デプロイ確認
- [ ] Railway URL + `/health` にアクセス（例: https://xxxxx.up.railway.app/health）
- [ ] `{"status":"ok","sync_interval":300}` が返ればOK

## Step 6: LINE_OWNER_USER_ID 取得
- [ ] スマホの LINE で @752nblny を友達追加
- [ ] Bot に何かメッセージを送る（例:「テスト」）
- [ ] Railway → Deployments → 最新のデプロイ → View Logs
- [ ] ログに表示される `U` で始まる32文字の文字列をコピー
- [ ] Railway Variables で `LINE_OWNER_USER_ID` をその値に更新

## Step 7: Webhook URL 確認
- [ ] LINE Developers Console → Messaging API → Webhook URL が正しいか確認
- [ ] 正しい形式: `https://（Railway URL）/callback`
- [ ] 「Verify」ボタンで疎通確認 → 成功すればOK

## 完了！
全て完了すると、5分ごとに自動で:
1. Beds24 の新着ゲストメッセージを検出
2. AI が返信案を生成
3. LINE に通知が届く
4. あなたは「承認」か「修正」ボタンを押すだけ
