import os
import requests
import time

# 環境変数から設定を読み込む
BEARER      = os.environ['BEARER_TOKEN']
USER_ID     = os.environ['USER_ID']
USERNAME    = os.environ['USERNAME']
SINCE_ID    = os.environ.get('SINCE_ID') or None
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']

# API のエンドポイント＆パラメータ
url     = f'https://api.twitter.com/2/users/{USER_ID}/tweets'
headers = {'Authorization': f'Bearer {BEARER}'}
params  = {'tweet.fields': 'created_at', 'max_results': 5}
if SINCE_ID:
    params['since_id'] = SINCE_ID

# ─── レートリミット (429) のリトライループ ───
while True:
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 429:
        break
    reset_ts = resp.headers.get("x-rate-limit-reset")
    if reset_ts and reset_ts.isdigit():
        wait_secs = max(int(reset_ts) - time.time(), 0) + 1
    else:
        wait_secs = 60
    print(f"[Rate limit] sleeping {wait_secs:.0f}s until reset")
    time.sleep(wait_secs)

# エラーがあればここで例外を投げる
resp.raise_for_status()

# ツイートデータを取得
tweets = resp.json().get('data', [])

if not tweets:
    # 新規ツイートなし
    print("No new tweets.")
    print("::set-output name=NEW_LAST_ID::")
    exit(0)

# ID昇順にソートして最新IDを取り出す
tweets_sorted = sorted(tweets, key=lambda t: int(t['id']))
new_last_id   = tweets_sorted[-1]['id']

# 初回実行時は通知しないで最新IDだけ保存
if SINCE_ID is None:
    print("Initial run: setting last tweet ID without sending notifications.")
    with open('.github/last_tweet_id.txt', 'w') as f:
        f.write(new_last_id)
    print(f"::set-output name=NEW_LAST_ID::{new_last_id}")
    exit(0)

# ─── 2回目以降は Discord へ通知 ───
for t in tweets_sorted:
    link = f'https://x.com/{USERNAME}/status/{t["id"]}'
    r = requests.post(WEBHOOK_URL, json={'content': link})
    r.raise_for_status()

# 最新IDをファイルに書き込んで次回へ引き継ぎ
with open('.github/last_tweet_id.txt', 'w') as f:
    f.write(new_last_id)

print(f"::set-output name=NEW_LAST_ID::{new_last_id}")
