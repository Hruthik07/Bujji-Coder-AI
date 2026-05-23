"""
Smoke tests for Config.validate_for_production().

If any of these regress, the server would silently ship to prod with
a known placeholder JWT secret or wide-open CORS. The validation must
refuse to start the app in either case.
"""

import pytest

from config import Config


pytestmark = pytest.mark.unit


def _set_prod(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")


class TestValidateForProduction:
    def test_returns_empty_outside_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        assert Config.validate_for_production() == []

    def test_returns_empty_with_proper_prod_config(self, monkeypatch):
        _set_prod(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        monkeypatch.setenv("JWT_SECRET_KEY", "Z" * 48)  # real-looking secret
        assert Config.validate_for_production() == []

    def test_unset_cors_origins_is_fatal(self, monkeypatch):
        _set_prod(monkeypatch)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        monkeypatch.setenv("JWT_SECRET_KEY", "Z" * 48)
        errors = Config.validate_for_production()
        assert any("CORS_ORIGINS" in e for e in errors)

    def test_empty_cors_origins_is_fatal(self, monkeypatch):
        _set_prod(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "   ")
        monkeypatch.setenv("JWT_SECRET_KEY", "Z" * 48)
        errors = Config.validate_for_production()
        assert any("CORS_ORIGINS" in e for e in errors)

    @pytest.mark.parametrize(
        "placeholder",
        [
            "",
            "your-secret-key-change-in-production",
            "your-super-secret-jwt-key-change-this-in-production",
            "change-me-in-production",
            "test-secret-key-for-ci",
        ],
    )
    def test_known_placeholder_jwt_secret_is_fatal(self, monkeypatch, placeholder):
        _set_prod(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        if placeholder == "":
            monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        else:
            monkeypatch.setenv("JWT_SECRET_KEY", placeholder)
        errors = Config.validate_for_production()
        assert any("JWT_SECRET_KEY" in e for e in errors)

    def test_multiple_errors_are_collected_not_short_circuited(self, monkeypatch):
        """Both errors should report at once, not just the first."""
        _set_prod(monkeypatch)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        monkeypatch.setenv("JWT_SECRET_KEY", "change-me-in-production")
        errors = Config.validate_for_production()
        assert len(errors) >= 2
        assert any("CORS_ORIGINS" in e for e in errors)
        assert any("JWT_SECRET_KEY" in e for e in errors)
