"""
Smoke tests for the ENABLE_WRITE_OPERATIONS feature flag.

Pins the contract for the single switch a public BYOK deploy uses to
disable filesystem writes and shell-exec endpoints. If these regress,
arbitrary visitors could mutate the host workspace or open shell
sessions on a deployed Bujji.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from tools.security import require_writes_enabled, writes_enabled


pytestmark = pytest.mark.unit


class TestWritesEnabledResolution:
    @pytest.mark.parametrize("truthy", ["true", "1", "yes", "on", "TRUE", "On"])
    def test_truthy_override_enables_writes_even_in_prod(self, monkeypatch, truthy):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("ENABLE_WRITE_OPERATIONS", truthy)
        assert writes_enabled() is True

    @pytest.mark.parametrize("falsy", ["false", "0", "no", "off", "FALSE", "Off"])
    def test_falsy_override_disables_writes_even_in_dev(self, monkeypatch, falsy):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ENABLE_WRITE_OPERATIONS", falsy)
        assert writes_enabled() is False

    def test_unset_in_production_defaults_to_disabled(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("ENABLE_WRITE_OPERATIONS", raising=False)
        assert writes_enabled() is False

    def test_unset_in_development_defaults_to_enabled(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("ENABLE_WRITE_OPERATIONS", raising=False)
        assert writes_enabled() is True

    def test_unknown_value_falls_through_to_env_default(self, monkeypatch):
        """Garbage value should not be treated as truthy."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("ENABLE_WRITE_OPERATIONS", "maybe")
        assert writes_enabled() is False


class TestRequireWritesEnabledDependency:
    @pytest.fixture
    def app(self):
        app = FastAPI()

        @app.post("/mutate")
        def mutate(_: None = Depends(require_writes_enabled)):
            return {"ok": True}

        return TestClient(app)

    def test_writes_enabled_returns_200(self, app, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("ENABLE_WRITE_OPERATIONS", raising=False)
        resp = app.post("/mutate")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_writes_disabled_returns_403(self, app, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("ENABLE_WRITE_OPERATIONS", raising=False)
        resp = app.post("/mutate")
        assert resp.status_code == 403
        assert "disabled" in resp.json()["detail"].lower()

    def test_explicit_false_overrides_dev_default(self, app, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ENABLE_WRITE_OPERATIONS", "false")
        assert app.post("/mutate").status_code == 403
