"""
Shared pytest fixtures for all test suites.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# LLM provider mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_response():
    """A minimal LLMResponse-like object."""
    from tools.llm_provider import LLMResponse
    return LLMResponse(
        content="Mocked LLM response",
        model="mock-model",
        input_tokens=10,
        output_tokens=20,
        finish_reason="stop",
    )


@pytest.fixture
def mock_provider(mock_llm_response):
    """A mock LLM provider that returns a fixed response."""
    provider = MagicMock()
    provider.chat_completion.return_value = mock_llm_response
    return provider


# ---------------------------------------------------------------------------
# Assistant mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_assistant(mock_provider):
    """
    CodingAssistant with all external dependencies mocked.
    Suitable for unit tests that don't need real LLM/RAG/DB.
    """
    from assistant import CodingAssistant
    assistant = CodingAssistant.__new__(CodingAssistant)

    # Providers
    assistant.openai_provider = None
    assistant.deepseek_provider = mock_provider
    assistant.anthropic_provider = None

    # Core subsystems — mocked
    assistant.rag_system = None
    assistant.incremental_indexer = None
    assistant.diff_editor = MagicMock()
    assistant.diff_extractor = MagicMock()
    assistant.diff_extractor.extract_diffs.return_value = []
    assistant.file_ops = MagicMock()
    assistant.terminal = MagicMock()
    assistant.error_parser = MagicMock()
    assistant.error_parser.is_python_error.return_value = False
    assistant.error_debugger = None
    assistant.task_classifier = MagicMock()
    assistant.task_classifier.classify.return_value = {
        "provider": "deepseek",
        "model": "deepseek-coder",
        "reason": "mock",
        "confidence": 1.0,
    }
    assistant.context_manager = MagicMock()
    assistant.context_manager.assemble_context.return_value = {
        "messages": [{"role": "user", "content": "test"}]
    }
    assistant.context_manager.update_memory = MagicMock()
    assistant.cost_tracker = MagicMock()
    assistant.cost_tracker.record_usage.return_value = 0.0
    assistant.performance_monitor = None
    assistant.logger = MagicMock()
    assistant.debug_mode = None
    assistant._session_id = None

    return assistant


# ---------------------------------------------------------------------------
# WebSocket mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_websocket():
    """AsyncMock WebSocket for testing WebSocket handlers."""
    ws = AsyncMock()
    ws.query_params = {}
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "auth", "token": ""}')
    return ws


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url():
    """Base URL for integration tests pointing to a running backend."""
    import os
    return os.getenv("TEST_BASE_URL", "http://localhost:8010")
