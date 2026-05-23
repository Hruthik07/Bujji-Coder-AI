"""
Smoke tests for the BYOK (Bring Your Own Key) credential plumbing.

This locks the contract for the credential path that the public deploy
depends on. If any of these fail, server-side key leakage or per-request
provider injection has regressed.
"""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from tools.byok import (
    UserKeys,
    _dev_fallback,
    get_user_keys,
    user_keys_from_ws_query,
)
from tools.llm_provider import (
    AnthropicProvider,
    DeepSeekProvider,
    OpenAIProvider,
)


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# UserKeys: shape, has_any, require_any
# ---------------------------------------------------------------------------

class TestUserKeysDataclass:
    def test_empty_keys_has_any_is_false(self):
        assert UserKeys().has_any() is False

    def test_any_single_key_means_has_any_true(self):
        assert UserKeys(anthropic="x").has_any() is True
        assert UserKeys(openai="x").has_any() is True
        assert UserKeys(deepseek="x").has_any() is True

    def test_require_any_raises_400_on_empty(self):
        with pytest.raises(HTTPException) as exc:
            UserKeys().require_any()
        assert exc.value.status_code == 400
        assert "Settings" in exc.value.detail  # user-facing hint

    def test_require_any_passes_when_any_key_present(self):
        # Must not raise
        UserKeys(anthropic="sk-test").require_any()


# ---------------------------------------------------------------------------
# UserKeys.provider_for: builds the right provider class with the right key
# ---------------------------------------------------------------------------

class TestProviderFor:
    def test_anthropic_provider_built_with_user_key(self):
        keys = UserKeys(anthropic="sk-ant-test")
        provider = keys.provider_for("anthropic")
        assert isinstance(provider, AnthropicProvider)

    def test_openai_provider_built_with_user_key(self):
        keys = UserKeys(openai="sk-openai-test")
        provider = keys.provider_for("openai")
        assert isinstance(provider, OpenAIProvider)

    def test_deepseek_provider_built_with_user_key(self):
        keys = UserKeys(deepseek="sk-ds-test")
        provider = keys.provider_for("deepseek")
        assert isinstance(provider, DeepSeekProvider)

    def test_missing_key_for_requested_provider_raises_400(self):
        keys = UserKeys(openai="sk-only-openai")
        with pytest.raises(HTTPException) as exc:
            keys.provider_for("anthropic")
        assert exc.value.status_code == 400

    def test_unknown_provider_name_raises_value_error(self):
        with pytest.raises(ValueError):
            UserKeys(anthropic="x").provider_for("not-a-provider")


# ---------------------------------------------------------------------------
# get_user_keys FastAPI dependency: header extraction over the wire
# ---------------------------------------------------------------------------

@pytest.fixture
def app_with_byok_dep():
    """Minimal FastAPI app that echoes the UserKeys it received."""
    app = FastAPI()

    @app.get("/whoami")
    def whoami(keys: UserKeys = Depends(get_user_keys)):
        return {
            "anthropic": keys.anthropic,
            "openai": keys.openai,
            "deepseek": keys.deepseek,
            "has_any": keys.has_any(),
        }

    return TestClient(app)


class TestGetUserKeysDependency:
    def test_headers_are_parsed_into_user_keys(self, app_with_byok_dep, monkeypatch):
        # Force prod-mode so the dev fallback doesn't shadow header parsing
        monkeypatch.setattr("tools.byok.PROD_ENV", True)
        resp = app_with_byok_dep.get(
            "/whoami",
            headers={
                "X-Anthropic-Key": "sk-ant-123",
                "X-OpenAI-Key": "sk-oai-456",
                "X-DeepSeek-Key": "sk-ds-789",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["anthropic"] == "sk-ant-123"
        assert body["openai"] == "sk-oai-456"
        assert body["deepseek"] == "sk-ds-789"
        assert body["has_any"] is True

    def test_partial_headers_only_populate_what_was_sent(
        self, app_with_byok_dep, monkeypatch
    ):
        monkeypatch.setattr("tools.byok.PROD_ENV", True)
        resp = app_with_byok_dep.get(
            "/whoami", headers={"X-Anthropic-Key": "sk-ant-only"}
        )
        body = resp.json()
        assert body["anthropic"] == "sk-ant-only"
        assert body["openai"] is None
        assert body["deepseek"] is None

    def test_prod_mode_no_headers_returns_empty_keys(
        self, app_with_byok_dep, monkeypatch
    ):
        """In production, missing headers must NOT fall back to server env."""
        monkeypatch.setattr("tools.byok.PROD_ENV", True)
        resp = app_with_byok_dep.get("/whoami")
        body = resp.json()
        assert body["has_any"] is False


# ---------------------------------------------------------------------------
# Dev-env fallback: CLI / pytest paths keep working when no headers arrive
# ---------------------------------------------------------------------------

class TestDevFallback:
    def test_dev_fallback_pulls_from_config(self, monkeypatch):
        monkeypatch.setattr("tools.byok.PROD_ENV", False)
        monkeypatch.setattr("tools.byok.Config.ANTHROPIC_API_KEY", "env-ant-key")
        monkeypatch.setattr("tools.byok.Config.OPENAI_API_KEY", "env-oai-key")
        monkeypatch.setattr("tools.byok.Config.DEEPSEEK_API_KEY", "")
        keys = _dev_fallback()
        assert keys.anthropic == "env-ant-key"
        assert keys.openai == "env-oai-key"
        assert keys.deepseek is None  # empty string -> None

    def test_prod_fallback_is_empty(self, monkeypatch):
        monkeypatch.setattr("tools.byok.PROD_ENV", True)
        monkeypatch.setattr("tools.byok.Config.ANTHROPIC_API_KEY", "should-not-leak")
        assert _dev_fallback().has_any() is False


# ---------------------------------------------------------------------------
# WebSocket query-param fallback (browsers can't set headers on the handshake)
# ---------------------------------------------------------------------------

class TestWebSocketFallback:
    def test_query_params_populate_user_keys(self, monkeypatch):
        monkeypatch.setattr("tools.byok.PROD_ENV", True)
        keys = user_keys_from_ws_query(
            anthropic_key="ws-ant",
            openai_key=None,
            deepseek_key="ws-ds",
        )
        assert keys.anthropic == "ws-ant"
        assert keys.deepseek == "ws-ds"
        assert keys.openai is None

    def test_prod_mode_no_query_returns_empty(self, monkeypatch):
        monkeypatch.setattr("tools.byok.PROD_ENV", True)
        assert user_keys_from_ws_query().has_any() is False


# ---------------------------------------------------------------------------
# CodingAssistant._select_provider: BYOK keys win over self.* defaults
# ---------------------------------------------------------------------------

class TestSelectProviderBYOK:
    def test_byok_anthropic_wins_over_self_deepseek(self, mock_assistant):
        """When BYOK supplies anthropic but task router asks for deepseek,
        and only the user's anthropic key is available, the system must
        pick a fresh AnthropicProvider built from the user key — never
        fall through to the server-side default."""
        # Force task classifier to route to anthropic for this case
        mock_assistant.task_classifier.classify.return_value = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "reason": "test",
            "confidence": 1.0,
        }
        user_keys = UserKeys(anthropic="sk-ant-from-user")

        provider, model, name = mock_assistant._select_provider(
            user_message="hi",
            conversation_history=None,
            model_override=None,
            user_keys=user_keys,
        )

        assert name == "anthropic"
        # MUST be a fresh per-request provider, NOT the server default
        # (which is None on the mock — so any non-None AnthropicProvider proves it)
        assert isinstance(provider, AnthropicProvider)
        assert provider is not mock_assistant.anthropic_provider

    def test_no_user_keys_falls_back_to_self_providers(self, mock_assistant):
        """When user_keys is None, must use the server-side provider singletons."""
        provider, model, name = mock_assistant._select_provider(
            user_message="hi",
            conversation_history=None,
            model_override=None,
            user_keys=None,
        )
        # mock_assistant has deepseek_provider set, others None
        assert provider is mock_assistant.deepseek_provider
        assert name == "deepseek"

    def test_empty_user_keys_falls_back_to_self_providers(self, mock_assistant):
        """UserKeys() with no fields set must behave identically to None."""
        provider, _, name = mock_assistant._select_provider(
            user_message="hi",
            conversation_history=None,
            model_override=None,
            user_keys=UserKeys(),
        )
        assert provider is mock_assistant.deepseek_provider
        assert name == "deepseek"
