# X-Post-Transfer-to-Discord
Xの投稿URLをDiscordに転送する
XのAPI無料枠を使用。
1日に2回（12:30, 21:30）投稿チェックしてDiscordサーバーに投稿する。
# 実装
```mermaid
flowchart TD
  subgraph "GitHub Actions Workflow"
    A[Schedule: cron '30 3,12 * * *'] --> B[actions/checkout@v3\n(persist-credentials: true)]
    B --> C[setup-python@v4\n(python 3.x)]
    C --> D[Install dependencies\n`pip install requests`]
    D --> E[Fetch last_tweet_id\n(from .github/last_tweet_id.txt)]
    E --> F[Run fetch_and_post.py]
    F --> G{NEW_LAST_ID\nset?}
    G -->|yes| H[git-auto-commit-action@v4\n(Update last_tweet_id.txt)]
    G -->|no| I[Skip commit]
  end

  subgraph "fetch_and_post.py"
    F1[Load env vars:\nBEARER_TOKEN, USER_ID,\nUSERNAME, SINCE_ID,\nDISCORD_WEBHOOK_URL] --> F2{GET\n/2/users/:id/tweets\nwith retry on 429}
    F2 --> F3[resp.raise_for_status()]
    F3 --> F4[Parse tweets list]
    F4 -->|empty| F5[Print "No new tweets."\nset-output NEW_LAST_ID:""\nexit(0)]
    F4 -->|non-empty| F6[Sort tweets by ID]
    F6 --> J{SINCE_ID is null?}
    J -->|yes| F7[Initial run:\nSave new_last_id only\nexit(0)]
    J -->|no| F8[Loop tweets_sorted\n→ POST to Discord webhook]
    F7 --> F9[Write .github/last_tweet_id.txt]
    F8 --> F9
    F9 --> F10[Print set-output NEW_LAST_ID]
  end
