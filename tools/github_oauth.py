"""
GitHub OAuth helper functions.

Pure-ish module: URL building and state generation are pure; token
exchange and profile fetch make HTTP calls but accept their HTTP
client as an argument so tests can pass a fake. The web/backend/app.py
routes use these helpers; this module knows nothing about FastAPI.

The OAuth flow:
  1. Browser hits /api/auth/github/login.
  2. Backend generates a random `state` (CSRF), stores it server-side
     (signed cookie or short-TTL Redis), and 302-redirects to GitHub's
     authorize URL.
  3. User approves on GitHub; GitHub redirects back to our
     /api/auth/github/callback with `code` and the same `state`.
  4. Backend verifies state, swaps `code` for an access token, fetches
     the user's GitHub profile, upserts a row in our users table, and
     issues a Bujji JWT.
  5. Backend 302-redirects to the frontend with the JWT in a URL
     fragment (so it never touches server logs).

References:
  https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/
  authorizing-oauth-apps#web-application-flow
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlencode


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"

# OAuth scopes Bujji asks for. `read:user` is enough to identify the
# user; we don't need to write anything to their GitHub account.
DEFAULT_SCOPES = "read:user user:email"


@dataclass(frozen=True)
class GitHubProfile:
    """The subset of a GitHub user profile Bujji stores."""

    github_id: str
    username: str
    email: str
    avatar_url: Optional[str] = None
    name: Optional[str] = None


def generate_state() -> str:
    """Cryptographically-strong CSRF state for the OAuth redirect."""
    return secrets.token_urlsafe(32)


def build_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: str = DEFAULT_SCOPES,
) -> str:
    """Build the URL the browser is redirected to in step 2 of the flow."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "allow_signup": "true",
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


# HttpClient is a thin protocol so callers can inject `requests`,
# `httpx`, or a fake. We never import requests/httpx at the module
# level to keep this file importable in pure-unit tests.
HttpPost = Callable[..., object]  # (url, *, data, headers, timeout) -> Response
HttpGet = Callable[..., object]   # (url, *, headers, timeout) -> Response


def exchange_code_for_token(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    http_post: HttpPost,
) -> str:
    """Step 4a: trade the temporary `code` for a long-lived access_token.

    The returned token is what we use to call GitHub's user API. We do
    NOT store it server-side (only the resulting profile fields)."""
    response = http_post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    # http_post returns something with .status_code and .json() — pulling
    # them by attribute keeps the dep on requests/httpx out of this file.
    if getattr(response, "status_code", None) != 200:
        raise RuntimeError(
            f"GitHub token exchange failed: HTTP {getattr(response, 'status_code', '?')}"
        )
    body = response.json()
    token = body.get("access_token")
    if not token:
        raise RuntimeError(
            f"GitHub token exchange returned no access_token (got error={body.get('error')!r})"
        )
    return token


def fetch_profile(
    *,
    access_token: str,
    http_get: HttpGet,
) -> GitHubProfile:
    """Step 4b: fetch the user's profile using the access_token.

    GitHub may return null for the public email even when the user
    granted `user:email`. We then fall back to /user/emails and pick
    the primary verified address."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Bujji-Coder-AI",
    }
    user_resp = http_get(GITHUB_USER_URL, headers=headers, timeout=10)
    if getattr(user_resp, "status_code", None) != 200:
        raise RuntimeError(
            f"GitHub /user fetch failed: HTTP {getattr(user_resp, 'status_code', '?')}"
        )
    user = user_resp.json()

    email = user.get("email")
    if not email:
        emails_resp = http_get(GITHUB_USER_EMAILS_URL, headers=headers, timeout=10)
        if getattr(emails_resp, "status_code", None) == 200:
            for entry in emails_resp.json() or []:
                if entry.get("primary") and entry.get("verified"):
                    email = entry.get("email")
                    break
            if not email:
                # Last resort: first verified email at all.
                for entry in emails_resp.json() or []:
                    if entry.get("verified"):
                        email = entry.get("email")
                        break
    if not email:
        raise RuntimeError(
            "GitHub did not expose any verified email for this account."
        )

    return GitHubProfile(
        github_id=str(user["id"]),
        username=user["login"],
        email=email,
        avatar_url=user.get("avatar_url"),
        name=user.get("name"),
    )
