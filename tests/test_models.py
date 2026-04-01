"""
tests/test_models.py – Unit tests for models.py (Ollama interaction layer).
"""

import types
from unittest.mock import patch, MagicMock

import pytest

from models import (
    ModelResponse,
    list_available_models,
    check_ollama_health,
    get_response,
    stream_response,
    run_battle,
)


# ── list_available_models ─────────────────────────────────────────────────────

class _FakeModel:
    def __init__(self, name):
        self.model = name


class _FakeListResult:
    def __init__(self, names):
        self.models = [_FakeModel(n) for n in names]


@patch("models.ollama.list")
def test_list_available_models_returns_sorted(mock_list):
    mock_list.return_value = _FakeListResult(["mistral", "llama3", "gemma:2b"])
    result = list_available_models()
    assert result == sorted(["gemma:2b", "llama3", "mistral"])


@patch("models.ollama.list", side_effect=Exception("conn refused"))
def test_list_available_models_fallback(mock_list):
    result = list_available_models(fallback=["fallback1"])
    assert result == ["fallback1"]


# ── check_ollama_health ───────────────────────────────────────────────────────

@patch("models.ollama.list")
def test_health_ok(mock_list):
    mock_list.return_value = _FakeListResult([])
    ok, msg = check_ollama_health()
    assert ok is True


@patch("models.ollama.list", side_effect=Exception("down"))
def test_health_fail(mock_list):
    ok, msg = check_ollama_health()
    assert ok is False
    assert "down" in msg


# ── get_response ──────────────────────────────────────────────────────────────

@patch("models.ollama.chat")
def test_get_response_success(mock_chat):
    mock_chat.return_value = {
        "message": {"content": "Hello world"},
        "eval_count": 5,
    }
    resp = get_response("llama3", "Hi", "You are helpful.")
    assert isinstance(resp, ModelResponse)
    assert resp.content == "Hello world"
    assert resp.error is None
    assert resp.elapsed > 0


@patch("models.ollama.chat", side_effect=Exception("timeout"))
def test_get_response_error(mock_chat):
    resp = get_response("llama3", "Hi", "system")
    assert resp.error is not None
    assert "timeout" in resp.error


# ── run_battle ────────────────────────────────────────────────────────────────

@patch("models.get_response")
def test_run_battle_parallel(mock_get):
    mock_get.side_effect = [
        ModelResponse(model="a", content="A answer", elapsed=1.0),
        ModelResponse(model="b", content="B answer", elapsed=2.0),
    ]
    a, b = run_battle("a", "b", "prompt", "system")
    assert a.content == "A answer"
    assert b.content == "B answer"
    assert mock_get.call_count == 2


# ── stream_response ──────────────────────────────────────────────────────────

@patch("models.ollama.chat")
def test_stream_response_yields_chunks(mock_chat):
    mock_chat.return_value = iter([
        {"message": {"content": "Hello "}},
        {"message": {"content": "world"}},
    ])
    chunks = list(stream_response("llama3", "Hi", "system"))
    assert len(chunks) == 2
    assert chunks[0][0] == "Hello "
    assert chunks[1][0] == "world"
