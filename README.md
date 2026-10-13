# Connect X/Twitter to Your Agent (cookie auth)

Turn any AI agent into a multi-account X/Twitter bot: **like, retweet, reply, quote, post, follow** — all from the terminal, scriptable, per-account isolated.

> No OAuth app, no paid API tier. Just your browser cookies (`auth_token` + `ct0`), the same session your browser already uses.

---

## How it works

The agent talks to X's **internal API** (the same endpoints the web app uses) using two cookies:

| Cookie | Length | What it is |
|---|---|---|
| `auth_token` | 40 hex | Your login session |
| `ct0` | 160 hex | CSRF token |

One file per account → the agent switches identity by pointing `X_CREDS` at a different file.

---

## Step 1 — Extract cookies (per account)

1. Log into X in your browser.
2. Open DevTools: `F12` → **Application** → **Cookies** → `https://x.com`.
3. Copy `auth_token` (exactly 40 hex) and `ct0` (exactly 160 hex).
4. Save them to a file, **plain `KEY=value`, no quotes, no `export`**:

```bash
# ~/.x_creds_akun1
X_AUTH=5e6175...61ba
X_CT0=4ae1e84c...b4769d
```

5. Lock it down:

```bash
chmod 600 ~/.x_creds_akun1
ls -la ~/.x_creds_akun1   # expect -rw-------
```

> ⚠️ These cookies are **full access to the account**. Never paste them into a chat or commit them to git. Write them straight to the file, and revoke the session when done (`x.com/settings/sessions`).

---

## Step 2 — Install the helper

```bash
curl -o ~/x.py https://raw.githubusercontent.com/<USER>/<REPO>/main/x.py
chmod +x ~/x.py
pip install requests   # (or use any venv that has requests)
```

---

## Step 3 — Use it

```bash
# Verify the account is alive
X_CREDS=~/.x_creds_akun1 python3 ~/x.py whoami

# Look up a user / a tweet
X_CREDS=~/.x_creds_akun1 python3 ~/x.py user-info elonmusk
X_CREDS=~/.x_creds_akun1 python3 ~/x.py get-tweet 1234567890123456789

# Engage
X_CREDS=~/.x_creds_akun1 python3 ~/x.py like 1234567890123456789
X_CREDS=~/.x_creds_akun1 python3 ~/x.py rt 1234567890123456789
X_CREDS=~/.x_creds_akun1 python3 ~/x.py reply 1234567890123456789 "nice thread 🙌"
X_CREDS=~/.x_creds_akun1 python3 ~/x.py quote 1234567890123456789 "quoting this 🔥"
X_CREDS=~/.x_creds_akun1 python3 ~/x.py post "gm"
X_CREDS=~/.x_creds_akun1 python3 ~/x.py follow elonmusk
```

Switch account = swap the `X_CREDS` path. That's it.

---

## Prompt for your agent (copy-paste)

Paste this to your agent, then give it the cookies when it asks:

> Bantu aku konekin akun X/Twitter supaya kamu bisa like, retweet, follow, reply, dan post. Pakai cookie auth (auth_token + ct0).
>
> 1. Minta aku `auth_token` (40 hex) + `ct0` (160 hex) dari browser (DevTools → Cookies → x.com). Simpan ke `~/.x_creds_<nama>` format plain `KEY=value`, `chmod 600`. Jangan echo/commit kredensial ke chat.
> 2. Simpan `x.py` dari `https://raw.githubusercontent.com/<USER>/<REPO>/main/x.py`. CLI-nya baca `X_CREDS` dari env buat switch akun.
> 3. Endpoint: like → GraphQL FavoriteTweet · rt → CreateRetweet · reply/quote/post → CreateTweet · follow → POST api.x.com/1.1/friendships/create.json (header wajib: UA Chrome, Origin, Referer, x-csrf-token).
> 4. Verifikasi dulu pakai `whoami` / `user-info <handle>`.
> 5. Anti-bot: jeda 30-60 detik antar akun, teks beda tiap akun (hindari kode 187 duplikat & 226 anti-bot), follow lewat REST.

---

## Common error codes (what they mean)

| Code | Meaning | Fix |
|---|---|---|
| `344` | Daily write limit (shared across post/reply/quote/RT) | Switch account, wait for reset |
| `226` | "Looks automated" anti-bot cooldown | Wait 15-30 min |
| `187` | Duplicate content | Vary the text |
| `32` | Dead token / not authenticated | Re-extract `auth_token` + `ct0` |
| `108` | v1.1 follow header gate | Add browser-shape headers (already in `x.py follow`) |

**Key distinction:** `32` = token problem (re-extract). `108` = just the follow endpoint needs browser headers (token is fine, and like/RT/quote still work). `226`/`344` = rate limits, not auth.

---

## Endpoint reference

| Action | Endpoint | Notes |
|---|---|---|
| Like | GraphQL `FavoriteTweet` | Most reliable, rarely rate-limited |
| Retweet | GraphQL `CreateRetweet` | Intermittent 404 → auto-retry built in |
| Reply / Post / Quote | GraphQL `CreateTweet` | Quote uses `attachment_url=https://x.com/i/status/<id>` |
| Follow | `POST api.x.com/1.1/friendships/create.json` | Needs UA + Origin + Referer headers |

---

## Security checklist

- [ ] `chmod 600` on every `~/.x_creds_*` file
- [ ] Creds never in chat / logs / git
- [ ] Revoke sessions when a campaign ends (`x.com/settings/sessions`)
- [ ] One account per file — never mix `auth_token` from one account with `ct0` from another

## Notes

- GraphQL hashes (the `H` dict in `x.py`) rotate occasionally. If every endpoint returns 404/empty, re-capture the current hash from browser DevTools → Network → `graphql/...` requests, and update `x.py`.
- This talks to X's internal API. Treat it as educational; respect X's ToS and rate limits.
