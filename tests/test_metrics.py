"""
tests/test_metrics.py – Unit tests for metrics.py.
"""

import pytest

from metrics import compute_metrics, ResponseMetrics


def test_compute_metrics_basic():
    text = "The quick brown fox jumps over the lazy dog. It was a sunny day."
    m = compute_metrics(text)
    assert isinstance(m, ResponseMetrics)
    assert m.word_count > 0
    assert m.char_count > 0
    assert m.sentence_count >= 1
    assert -100 <= m.reading_ease <= 121.22  # Flesch range


def test_compute_metrics_word_count():
    text = "One two three four five."
    m = compute_metrics(text)
    assert m.word_count == 5


def test_compute_metrics_token_fallback():
    text = "hello world"
    m = compute_metrics(text, token_count=0)
    # When token_count is 0, falls back to word count
    assert m.token_count == m.word_count


def test_compute_metrics_token_override():
    text = "hello world"
    m = compute_metrics(text, token_count=42)
    assert m.token_count == 42


def test_sentiment_fields_exist():
    text = "I love this wonderful amazing product!"
    m = compute_metrics(text)
    assert isinstance(m.sentiment_polarity, float)
    assert isinstance(m.sentiment_subjectivity, float)
