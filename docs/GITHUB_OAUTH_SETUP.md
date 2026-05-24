# GitHub OAuth Setup

Bujji supports an optional "Sign in with GitHub" flow on top of the
default BYOK (Bring Your Own Key) mode. Sign-in is what gives a visitor
a stable identity for cross-device chat history and the per-user
dashboard. Without it, BYOK still works — keys live in `localStorage`
and history is keyed by an anonymous browser UUID.

The OAuth flow is **off by default** and self-activates only when both
`GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are present in the env.
The endpoints `/api/auth/github/login` and `/api/auth/github/callback`
return `503` until you set those.

## 1. Create a GitHub OAuth App

1. Sign in to GitHub and open
   https://github.com/settings/developers (or, for an org-owned app,
   `https://github.com/organizations/<org>/settings/applications`).
2. Click **New OAuth App**.
3. Fill in the form:
   - **Application name:** `Bujji Coder AI` (or whatever you want users
     to see on the consent screen).
   - **Homepage URL:** the public URL of your frontend, e.g.
     `https://bujji.vercel.app`. Use `http://localhost:3001` for local
     dev.
   - **Authorization callback URL:** the public URL of your backend +
     `/api/auth/github/callback`, e.g.
     `https://bujji-api.up.railway.app/api/auth/github/callback`.
     Use `http://localhost:8010/api/auth/github/callback` for local dev.
4. Click **Register application**.
5. On the next page, note the **Client ID** and click
   **Generate a new client secret**. Copy the secret immediately —
   GitHub only shows it once.

You can register two separate apps if you want to keep dev and prod
isolated (recommended).

## 2. Set the env vars

### Local dev (`.env`)

```
GITHUB_CLIENT_ID=Iv1.abc123
GITHUB_CLIENT_SECRET=ghs_xyz789
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8010/api/auth/github/callback
FRONTEND_URL=http://localhost:3001
```

### Railway (backend)

In the Railway project settings, set these as environment variables:

| Variable                     | Value                                                            |
|------------------------------|------------------------------------------------------------------|
| `GITHUB_CLIENT_ID`           | from step 1                                                      |
| `GITHUB_CLIENT_SECRET`       | from step 1                                                      |
| `GITHUB_OAUTH_REDIRECT_URI`  | `https://<your-railway-domain>/api/auth/github/callback`         |
| `FRONTEND_URL`               | `https://<your-vercel-domain>`                                   |

The redirect URI **must** exactly match the "Authorization callback
URL" you set on GitHub — different scheme, host, or path = GitHub
rejects the callback.

### Vercel (frontend)

No GitHub vars are needed on Vercel. The frontend just hits
`/api/auth/github/login` on the backend, which handles everything.

## 3. How the flow works at runtime

```
Browser            Bujji backend                      GitHub
  |                      |                              |
  |--- click "Sign in" ->|                              |
  |                      |--- 302 to authorize URL ---->|
  |<-- 302 redirect -----|                              |
  |--- follows redirect ------------------------------->|
  |                      |                              |
  |<-- consent screen ----------------------------------|
  |--- approve --------------------------------------->|
  |                      |                              |
  |<-- 302 to /callback?code=...&state=... ------------|
  |--- follows redirect ->|                              |
  |                      |--- POST code -> token ------>|
  |                      |--- GET /user (auth) -------->|
  |                      |<- profile ------------------|
  |                      |  upsert user, mint JWT       |
  |<-- 302 to frontend ---|                              |
  |     #access_token=... |                              |
```

The state cookie is the CSRF guard: the backend sets it on `/login` and
verifies it matches the `state` query param on `/callback`. The Bujji
JWT comes back in a URL fragment (`#access_token=...`) so it never
appears in nginx, Railway, or Vercel access logs.

## 4. Test the flow end-to-end

1. Start both backend and frontend locally.
2. Open `http://localhost:3001`.
3. Click the GitHub sign-in button.
4. After GitHub approves, you should land back on the frontend with the
   JWT picked up automatically — the header should show your GitHub
   username.

Failure modes you might hit:

| Symptom                                          | Likely cause                                                                 |
|--------------------------------------------------|------------------------------------------------------------------------------|
| `/api/auth/github/login` returns 503             | `GITHUB_CLIENT_ID` or `GITHUB_CLIENT_SECRET` is unset                       |
| GitHub shows "redirect URI mismatch"             | Callback URL on GitHub doesn't exactly match `GITHUB_OAUTH_REDIRECT_URI`     |
| Callback returns 400 "OAuth state mismatch"      | Cookies blocked (third-party-cookie browser settings) or you used two tabs   |
| Callback returns 502 "GitHub did not expose..."  | User's GitHub email is private and they didn't grant the `user:email` scope  |

## 5. Disabling

To turn the feature off, unset (or blank out) `GITHUB_CLIENT_ID` and
`GITHUB_CLIENT_SECRET`. The endpoints will return 503 and the frontend
sign-in button hides itself automatically (it checks the backend on
mount).
