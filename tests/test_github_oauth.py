"""
Smoke tests for the GitHub OAuth helper module and AuthManager extension.

What this pins down:
  * Authorize URL contains every required param (client_id, redirect_uri,
    scope, state). Missing any of these silently breaks sign-in.
  * State is unique per call (CSRF protection).
  * Token exchange happy path + failure surfaces a clear error.
  * Profile fetch falls back to /user/emails when /user.email is null.
  * AuthManager.upsert_github_user creates / links / collision-suffixes
    correctly — the three branches a new sign-in can take.
"""

import json
import tempfile
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from tools.auth import OAUTH_NO_PASSWORD_SENTINEL, AuthManager
from tools.github_oauth import (
    GITHUB_AUTHORIZE_URL,
    GITHUB_TOKEN_URL,
    GITHUB_USER_URL,
    GITHUB_USER_EMAILS_URL,
    build_authorize_url,
    exchange_code_for_token,
    fetch_profile,
    generate_state,
)


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestStateAndUrl:
    def test_generate_state_is_unique(self):
        s1, s2 = generate_state(), generate_state()
        assert s1 != s2
        assert len(s1) >= 32  # token_urlsafe(32) gives ~43 chars

    def test_authorize_url_includes_all_params(self):
        url = build_authorize_url(
            client_id="cid",
            redirect_uri="https://example.com/cb",
            state="abc123",
        )
        assert url.startswith(GITHUB_AUTHORIZE_URL)
        assert "client_id=cid" in url
        assert "state=abc123" in url
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcb" in url
        assert "scope=read%3Auser+user%3Aemail" in url

    def test_authorize_url_custom_scopes(self):
        url = build_authorize_url(
            client_id="cid",
            redirect_uri="https://x/cb",
            state="s",
            scopes="public_repo",
        )
        assert "scope=public_repo" in url


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------


@dataclass
class FakeResponse:
    status_code: int
    body: dict

    def json(self):
        return self.body


class TestTokenExchange:
    def test_happy_path_returns_token(self):
        captured = {}

        def fake_post(url, *, data, headers, timeout):
            captured["url"] = url
            captured["data"] = data
            return FakeResponse(200, {"access_token": "ghs_abc", "scope": "read:user"})

        token = exchange_code_for_token(
            code="the-code",
            client_id="cid",
            client_secret="csec",
            redirect_uri="https://x/cb",
            http_post=fake_post,
        )
        assert token == "ghs_abc"
        assert captured["url"] == GITHUB_TOKEN_URL
        assert captured["data"]["code"] == "the-code"
        assert captured["data"]["client_secret"] == "csec"

    def test_non_200_raises(self):
        fake_post = lambda *a, **k: FakeResponse(500, {})
        with pytest.raises(RuntimeError, match="HTTP 500"):
            exchange_code_for_token(
                code="c", client_id="ci", client_secret="cs",
                redirect_uri="r", http_post=fake_post,
            )

    def test_200_but_no_token_raises(self):
        """GitHub returns 200 with {"error": "bad_verification_code"} on bad code."""
        fake_post = lambda *a, **k: FakeResponse(200, {"error": "bad_verification_code"})
        with pytest.raises(RuntimeError, match="bad_verification_code"):
            exchange_code_for_token(
                code="c", client_id="ci", client_secret="cs",
                redirect_uri="r", http_post=fake_post,
            )


# ---------------------------------------------------------------------------
# Profile fetch
# ---------------------------------------------------------------------------


class TestFetchProfile:
    def test_happy_path_with_public_email(self):
        def fake_get(url, *, headers, timeout):
            assert headers["Authorization"] == "Bearer tok"
            return FakeResponse(200, {
                "id": 42,
                "login": "octocat",
                "email": "octocat@github.com",
                "avatar_url": "https://...png",
                "name": "Octo Cat",
            })

        prof = fetch_profile(access_token="tok", http_get=fake_get)
        assert prof.github_id == "42"
        assert prof.username == "octocat"
        assert prof.email == "octocat@github.com"

    def test_falls_back_to_emails_endpoint_when_public_email_null(self):
        responses_by_url = {
            GITHUB_USER_URL: FakeResponse(200, {
                "id": 7, "login": "alice", "email": None,
            }),
            GITHUB_USER_EMAILS_URL: FakeResponse(200, [
                {"email": "alt@x.com", "primary": False, "verified": True},
                {"email": "primary@x.com", "primary": True, "verified": True},
            ]),
        }

        def fake_get(url, **kwargs):
            return responses_by_url[url]

        prof = fetch_profile(access_token="tok", http_get=fake_get)
        assert prof.email == "primary@x.com"

    def test_raises_when_no_verified_email_anywhere(self):
        responses_by_url = {
            GITHUB_USER_URL: FakeResponse(200, {"id": 1, "login": "n", "email": None}),
            GITHUB_USER_EMAILS_URL: FakeResponse(200, [
                {"email": "x@x", "primary": True, "verified": False},
            ]),
        }
        fake_get = lambda url, **kw: responses_by_url[url]
        with pytest.raises(RuntimeError, match="verified email"):
            fetch_profile(access_token="tok", http_get=fake_get)


# ---------------------------------------------------------------------------
# AuthManager.upsert_github_user
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_mgr(tmp_path, monkeypatch):
    # Suppress the "[WARN] Default admin user created..." print on first init
    db = tmp_path / "auth.db"
    return AuthManager(db_path=str(db))


class TestUpsertGitHubUser:
    def test_creates_new_user_on_first_signin(self, auth_mgr):
        user = auth_mgr.upsert_github_user(
            github_id="999", username="newbie", email="newbie@x.com"
        )
        assert user.github_id == "999"
        assert user.username == "newbie"
        assert user.email == "newbie@x.com"
        assert user.hashed_password == OAUTH_NO_PASSWORD_SENTINEL

    def test_returns_existing_user_on_repeat_signin(self, auth_mgr):
        first = auth_mgr.upsert_github_user(
            github_id="111", username="bob", email="bob@x.com"
        )
        second = auth_mgr.upsert_github_user(
            github_id="111", username="bob", email="bob@x.com"
        )
        assert first.id == second.id

    def test_links_existing_password_account_by_email(self, auth_mgr):
        # User signed up with password first
        original = auth_mgr.create_user(
            username="carol", email="carol@x.com", password="secret123"
        )
        assert original.github_id is None

        linked = auth_mgr.upsert_github_user(
            github_id="222", username="carol-gh", email="carol@x.com"
        )
        # Same Bujji user_id — we LINKED, not duplicated
        assert linked.id == original.id
        assert linked.github_id == "222"
        # Password preserved (sentinel did NOT overwrite it)
        assert linked.hashed_password != OAUTH_NO_PASSWORD_SENTINEL

    def test_collision_suffix_on_username_conflict(self, auth_mgr):
        # Existing password account named "dave"
        auth_mgr.create_user(username="dave", email="dave1@x.com", password="p")
        # GitHub user also named "dave" but different email
        gh = auth_mgr.upsert_github_user(
            github_id="333abcdef", username="dave", email="dave2@x.com"
        )
        # Username got a -gh<6chars> suffix to avoid the UNIQUE collision
        assert gh.username.startswith("dave-gh")
        assert gh.username != "dave"
        assert gh.email == "dave2@x.com"

    def test_get_user_by_github_id_returns_linked_user(self, auth_mgr):
        auth_mgr.upsert_github_user(
            github_id="444", username="eve", email="eve@x.com"
        )
        found = auth_mgr.get_user_by_github_id("444")
        assert found is not None
        assert found.username == "eve"

    def test_get_user_by_github_id_returns_none_for_unknown(self, auth_mgr):
        assert auth_mgr.get_user_by_github_id("nonexistent") is None
