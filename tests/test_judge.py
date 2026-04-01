"""
tests/test_judge.py – Unit tests for judge.py.
"""

from unittest.mock import patch

import pytest

from models import ModelResponse
from judge import get_judge_verdict, JUDGE_META_PROMPT


@patch("judge.get_response")
def test_judge_returns_verdict(mock_get):
    mock_get.return_value = ModelResponse(
        model="llama3",
        content="**WINNER:** Model A\n**REASON:** Better answer.",
        elapsed=3.0,
    )
    result = get_judge_verdict(
        question="What is AI?",
        persona="Standard Assistant",
        model_a="llama3",
        response_a="AI is artificial intelligence.",
        model_b="mistral",
        response_b="AI mimics human brains.",
    )
    assert "WINNER" in result.content
    assert result.error is None


@patch("judge.get_response")
def test_judge_passes_all_context(mock_get):
    mock_get.return_value = ModelResponse(model="llama3", content="ok", elapsed=1.0)
    get_judge_verdict(
        question="Q",
        persona="Pirate",
        model_a="a",
        response_a="ra",
        model_b="b",
        response_b="rb",
        judge_model="custom-judge",
        judge_system_prompt="Be fair.",
    )
    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs["model_name"] == "custom-judge"
    assert call_kwargs.kwargs["system_prompt"] == "Be fair."
    assert "Pirate" in call_kwargs.kwargs["user_prompt"]
