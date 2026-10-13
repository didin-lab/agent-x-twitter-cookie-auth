#!/usr/bin/env python3
"""
x.py — minimal multi-account X/Twitter helper for agents.

Auth: cookie-based (auth_token + ct0), one file per account.
Switch accounts by setting X_CREDS to the creds file path.

Usage:
  X_CREDS=~/.x_creds_akun1 python3 x.py whoami
  X_CREDS=~/.x_creds_akun1 python3 x.py user-info <handle>
  X_CREDS=~/.x_creds_akun1 python3 x.py like <tweet_id>
  X_CREDS=~/.x_creds_akun1 python3 x.py rt <tweet_id>
  X_CREDS=~/.x_creds_akun1 python3 x.py reply <tweet_id> "text"
  X_CREDS=~/.x_creds_akun1 python3 x.py quote <tweet_id> "text"
  X_CREDS=~/.x_creds_akun1 python3 x.py post "text"
  X_CREDS=~/.x_creds_akun1 python3 x.py follow <user_id_or_screen_name>
  X_CREDS=~/.x_creds_akun1 python3 x.py get-tweet <tweet_id>

Creds file format (plain KEY=value, chmod 600):
  X_AUTH=<40 hex auth_token>
  X_CT0=<160 hex ct0>
"""
import os
import sys
import json
import time

import requests

# --------------------------------------------------------------------------
# Credentials
# --------------------------------------------------------------------------
CREDS_PATH = os.path.expanduser(os.environ.get("X_CREDS", "~/.x_creds"))

BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# GraphQL operation hashes (rotate if X bumps them — see README)
H = {
    "FavoriteTweet": "lI07N6Otwv1PhnEgXILM7A",
    "CreateRetweet": "mbRO74GrOvSfRcJnlMapnQ",
    "CreateTweet": "kMZ0FyJZB6qO1vV1FhZwXw",
    "UserByScreenName": "G3KGOASz96M-QuEmnNuGqW",
    "Viewer": "hu8YX1wKM4y2tGwMxH1Z0w",
    "TweetDetail": "0hWvDhmW8YQ-S_ib3azIrw",
}

FEATURES = {
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_api_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_media_download_video_enabled": False,
    "responsive_web_enhance_cards_enabled": False,
}

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def load_creds():
    with open(CREDS_PATH) as f:
        creds = {}
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
    auth = creds.get("X_AUTH", "").strip()
    ct0 = creds.get("X_CT0", "").strip()
    if not auth or not ct0:
        sys.stderr.write(f"[x.py] missing X_AUTH / X_CT0 in {CREDS_PATH}\n")
        sys.exit(1)
    return auth, ct0


def session(auth, ct0):
    s = requests.Session()
    s.headers.update({"user-agent": UA})
    s.cookies.set("auth_token", auth, domain=".x.com", path="/")
    s.cookies.set("ct0", ct0, domain=".x.com", path="/")
    return s


def gql(s, endpoint, variables, max_retries=3):
    qhash = H[endpoint]
    url = f"https://x.com/i/api/graphql/{qhash}/{endpoint}"
    payload = {"variables": variables, "features": FEATURES}
    last_code = last_body = None
    for attempt in range(max_retries):
        r = s.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            return r.json(), 200, None
        if r.status_code in (404, 429, 500, 502, 503) and attempt < max_retries - 1:
            last_code, last_body = r.status_code, r.text[:300]
            time.sleep(1.5 * (attempt + 1))
            continue
        return None, r.status_code, r.text[:300]
    return None, last_code, last_body


def cmd_whoami():
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = gql(s, "Viewer", {})
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    try:
        viewer = j["data"]["viewer"]["user_results"]["result"]
        print(json.dumps({"ok": True, "screen_name": viewer["legacy"]["screen_name"],
                          "user_id": viewer["rest_id"]}))
    except Exception:
        print(json.dumps({"ok": False, "error": "no viewer in response", "body": j}))


def cmd_user_info(handle):
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = gql(s, "UserByScreenName", {"screen_name": handle})
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    try:
        u = j["data"]["user"]["result"]
        print(json.dumps({"ok": True, "user_id": u["rest_id"],
                          "screen_name": u["legacy"]["screen_name"],
                          "followers": u["legacy"].get("followers_count"),
                          "following": u["legacy"].get("friends_count")}))
    except Exception:
        print(json.dumps({"ok": False, "error": "user not found", "body": j}))


def cmd_get_tweet(tid):
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = gql(s, "TweetDetail", {"focalTweetId": tid})
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    try:
        t = j["data"]["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"][0]
        res = t["content"]["itemContent"]["tweet_results"]["result"]
        print(json.dumps({"ok": True, "user_id": res["core"]["user_results"]["result"]["rest_id"],
                          "text": res["legacy"]["full_text"]}))
    except Exception:
        print(json.dumps({"ok": False, "error": "tweet not found", "body": j}))


def cmd_like(tid):
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = gql(s, "FavoriteTweet", {"tweet_id": tid})
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    if "favorite_tweet" in str(j):
        print(json.dumps({"ok": True, "liked": True}))
    else:
        print(json.dumps({"ok": False, "error": "like failed", "body": j}))


def cmd_rt(tid):
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = gql(s, "CreateRetweet", {"tweet_id": tid})
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    try:
        rt = j["data"]["create_retweet"]["retweet_results"]["result"]
        print(json.dumps({"ok": True, "retweeted": True, "retweet_id": rt.get("rest_id")}))
    except Exception:
        print(json.dumps({"ok": False, "error": "retweet failed", "body": j}))


def _create_tweet(s, text, reply_to=None, quote_tweet_id=None):
    variables = {
        "tweet_text": text,
        "dark_request": False,
        "media": {"media_entities": [], "possibly_sensitive": False},
        "semantic_annotation_ids": [],
    }
    if reply_to:
        variables["reply"] = {"in_reply_to_tweet_id": reply_to, "exclude_reply_user_ids": []}
    if quote_tweet_id:
        variables["attachment_url"] = f"https://x.com/i/status/{quote_tweet_id}"
    return gql(s, "CreateTweet", variables)


def cmd_post(text):
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = _create_tweet(s, text)
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    try:
        res = j["data"]["create_tweet"]["tweet_results"]["result"]
        print(json.dumps({"ok": True, "tweet_id": res["rest_id"],
                          "user": res["core"]["user_results"]["result"]["legacy"]["screen_name"]}))
    except Exception:
        print(json.dumps({"ok": False, "error": "post failed", "body": j}))


def cmd_reply(tid, text):
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = _create_tweet(s, text, reply_to=tid)
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    try:
        res = j["data"]["create_tweet"]["tweet_results"]["result"]
        print(json.dumps({"ok": True, "tweet_id": res["rest_id"],
                          "user": res["core"]["user_results"]["result"]["legacy"]["screen_name"]}))
    except Exception:
        print(json.dumps({"ok": False, "error": "reply failed", "body": j}))


def cmd_quote(tid, text):
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    j, code, err = _create_tweet(s, text, quote_tweet_id=tid)
    if code != 200:
        print(json.dumps({"ok": False, "error": err}))
        return
    try:
        res = j["data"]["create_tweet"]["tweet_results"]["result"]
        print(json.dumps({"ok": True, "tweet_id": res["rest_id"],
                          "user": res["core"]["user_results"]["result"]["legacy"]["screen_name"]}))
    except Exception:
        print(json.dumps({"ok": False, "error": "quote failed", "body": j}))


def cmd_follow(target):
    """Follow via v1.1 REST with browser-shape headers (GraphQL follow is flaky)."""
    auth, ct0 = load_creds()
    s = session(auth, ct0)
    # resolve screen name -> user id if needed
    target_uid = target
    if not target.isdigit():
        j, code, err = gql(s, "UserByScreenName", {"screen_name": target})
        if code == 200:
            try:
                target_uid = j["data"]["user"]["result"]["rest_id"]
            except Exception:
                pass
    headers = {
        "authorization": f"Bearer {BEARER}",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en",
        "x-twitter-active-user": "yes",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://x.com",
        "referer": f"https://x.com/{target}",
        "x-csrf-token": ct0,
    }
    r = s.post("https://api.x.com/1.1/friendships/create.json",
               data={"user_id": target_uid, "follow": "true"}, headers=headers, timeout=15)
    if r.status_code == 200:
        print(json.dumps({"ok": True, "following": True, "user_id": target_uid}))
    else:
        print(json.dumps({"ok": False, "status": r.status_code, "body": r.text[:300]}))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "whoami":
        cmd_whoami()
    elif cmd == "user-info":
        cmd_user_info(args[1]) if len(args) > 1 else print("usage: user-info <handle>")
    elif cmd == "get-tweet":
        cmd_get_tweet(args[1]) if len(args) > 1 else print("usage: get-tweet <id>")
    elif cmd == "like":
        cmd_like(args[1]) if len(args) > 1 else print("usage: like <id>")
    elif cmd == "rt":
        cmd_rt(args[1]) if len(args) > 1 else print("usage: rt <id>")
    elif cmd == "post":
        cmd_post(args[1]) if len(args) > 1 else print("usage: post \"text\"")
    elif cmd == "reply":
        cmd_reply(args[1], args[2]) if len(args) > 2 else print("usage: reply <id> \"text\"")
    elif cmd == "quote":
        cmd_quote(args[1], args[2]) if len(args) > 2 else print("usage: quote <id> \"text\"")
    elif cmd == "follow":
        cmd_follow(args[1]) if len(args) > 1 else print("usage: follow <user_id|screen_name>")
    else:
        print(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
