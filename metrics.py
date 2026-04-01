"""
metrics.py – Response quality metrics for the AI Arena.
"""

from __future__ import annotations

from dataclasses import dataclass

import textstat

try:
    from textblob import TextBlob
    _HAS_TEXTBLOB = True
except ImportError:
    _HAS_TEXTBLOB = False


@dataclass
class ResponseMetrics:
    """All computed metrics for a single response."""
    word_count: int
    char_count: int
    sentence_count: int
    reading_ease: float          # Flesch Reading Ease
    grade_level: float           # Flesch-Kincaid Grade Level
    sentiment_polarity: float    # -1 (negative) → +1 (positive)
    sentiment_subjectivity: float  # 0 (objective) → 1 (subjective)
    token_count: int             # From the model (or word-based fallback)


def compute_metrics(text: str, token_count: int = 0) -> ResponseMetrics:
    """Compute all quality metrics for a response string."""
    word_count = len(text.split())
    char_count = len(text)
    sentence_count = textstat.sentence_count(text)
    reading_ease = textstat.flesch_reading_ease(text)
    grade_level = textstat.flesch_kincaid_grade(text)

    if _HAS_TEXTBLOB:
        blob = TextBlob(text)
        polarity = round(blob.sentiment.polarity, 3)
        subjectivity = round(blob.sentiment.subjectivity, 3)
    else:
        polarity = 0.0
        subjectivity = 0.0

    return ResponseMetrics(
        word_count=word_count,
        char_count=char_count,
        sentence_count=sentence_count,
        reading_ease=round(reading_ease, 1),
        grade_level=round(grade_level, 1),
        sentiment_polarity=polarity,
        sentiment_subjectivity=subjectivity,
        token_count=token_count or word_count,
    )
