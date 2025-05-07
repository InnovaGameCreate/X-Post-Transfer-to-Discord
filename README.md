# X-Post-Transfer-to-Discord
## 概要
X（@tugameproject）でポストした投稿のURLをWebhookでDiscordチャンネルに転送するためのワークフロー
XのAPI無料枠を使用しています。
1日に2回（12:30, 21:30）新規ポストの有無をチェックし、あれば転送されます。

---

## ワークフロー（x-to-discord.yml）の流れ
     
1. **前回のポストID取得**  
   - `.github/last_tweet_id.txt` から前回までに通知済みの最新ポストIDを読み込み、環境変数 `SINCE_ID` にセットします。
     
2. **新着ポストの取得・Discord 通知・最新IDの更新**  
   - `.github/scripts/fetch_and_post.py` を実行し、新着ポストの取得・Discord 通知・最新IDの更新を行います。
     
3. **前回のポストIDのキャッシュ**  
   - 新しいツイートがあった場合のみ、`.github/last_tweet_id.txt` を更新し、自動でコミット＆プッシュします。

---

## `fetch_and_post.py` の処理詳細
- **API 呼び出しフロー**  
  1. `GET /2/users/{USER_ID}/tweets` を実行  
  2. **429 (Too Many Requests)** が返ってきたら、`x-rate-limit-reset` ヘッダーに従って待機し、再試行  
  3. 成功後、ツイートリストを取得  
- **初回実行時**  
  - `SINCE_ID` が未設定なら、Discord 通知を行わず最新IDのみ保存して終了  
- **通常実行時**  
  - `SINCE_ID` 以降のツイートを昇順で Discord に転送  
  - 処理後、最新のツイートIDを `.github/last_tweet_id.txt` に保存  

---

## レート制限対策
- **無償プラン** の読み取り制限：月100回、かつ 15分あたり5回  
- **実行頻度**：1日2回（約60回／月）に抑えて、月100回の上限内に収めています  
- **スクリプト内リトライ**：429 応答時に自動で待機→再試行し、安定稼働を実現  

---

## セットアップ手順
1. **GitHub Secrets の登録**  
   - `TW_BEARER_TOKEN`：X API の Bearer Token  
   - `TWITTER_USER_ID`：対象ユーザーの数値ID  
   - `TWITTER_USERNAME`：`@` を除いたハンドル名  
   - `DISCORD_WEBHOOK_URL`：Discord の Webhook URL
     
2. **ファイル配置**  
   - `.github/workflows/x-to-discord.yml`（ワークフロー定義）  
   - `.github/scripts/fetch_and_post.py`（処理スクリプト）  
   - `.github/last_tweet_id.txt`（空ファイルとして作成）
     
3. **動作確認**  
   - 初回実行では Discord 通知せずに ID を初期化  
   - 2回目以降で新着ツイートがあれば Discord に転送  

---

## 処理
```mermaid
flowchart TD
  subgraph "GitHub Actions Workflow"
    A["Schedule: cron '30 3,12 * * *'"] --> B["actions/checkout@v3<br>(persist-credentials: true)"]
    B --> C["setup-python@v4<br>(python 3.x)"]
    C --> D["Install dependencies<br><code>pip install requests</code>"]
    D --> E["Fetch last_tweet_id<br>(from .github/last_tweet_id.txt)"]
    E --> F["Run fetch_and_post.py"]
    F --> G{NEW_LAST_ID set?}
    G -->|yes| H["git-auto-commit-action@v4<br>(Update last_tweet_id.txt)"]
    G -->|no| I["Skip commit"]
  end

  subgraph "fetch_and_post.py"
    F1["Load env vars: BEARER_TOKEN, USER_ID, USERNAME, SINCE_ID, DISCORD_WEBHOOK_URL"] --> F2{"GET /2/users/:id/tweets<br>with retry on 429"}
    F2 --> F3["resp.raise_for_status()"]
    F3 --> F4["Parse tweets list"]
    F4 -->|empty| F5["Print “No new tweets.”<br>set-output NEW_LAST_ID:“”<br>exit(0)"]
    F4 -->|non-empty| F6["Sort tweets by ID"]
    F6 --> J{SINCE_ID is null?}
    J -->|yes| F7["Initial run: save new_last_id only<br>exit(0)"]
    J -->|no| F8["Loop tweets_sorted → POST to Discord webhook"]
    F7 --> F9["Write .github/last_tweet_id.txt"]
    F8 --> F9
    F9 --> F10["Print set-output NEW_LAST_ID"]
  end
