"""
history.py – Battle history persistence & leaderboard using TinyDB.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tinydb import TinyDB, Query


def _get_db(db_path: str = "battle_history.json") -> TinyDB:
    return TinyDB(db_path)


# ── Write ─────────────────────────────────────────────────────────────────────

def save_battle(
    db_path: str,
    prompt: str,
    persona: str,
    model_a: str,
    response_a: str,
    time_a: float,
    model_b: str,
    response_b: str,
    time_b: float,
    winner: str,
    judge_verdict: str = "",
) -> int:
    """Persist a battle record. Returns the inserted document ID."""
    db = _get_db(db_path)
    doc = {
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt": prompt,
        "persona": persona,
        "model_a": model_a,
        "response_a": response_a,
        "time_a": round(time_a, 3),
        "model_b": model_b,
        "response_b": response_b,
        "time_b": round(time_b, 3),
        "winner": winner,
        "judge_verdict": judge_verdict,
    }
    return db.insert(doc)


# ── Read ──────────────────────────────────────────────────────────────────────

def get_all_battles(db_path: str) -> list[dict[str, Any]]:
    """Return all battle records, newest first."""
    db = _get_db(db_path)
    records = db.all()
    return sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)


def get_leaderboard(db_path: str) -> dict[str, dict[str, int]]:
    """
    Build a leaderboard: { model_name: { wins, losses, ties, battles } }.
    """
    records = get_all_battles(db_path)
    board: dict[str, dict[str, int]] = {}

    def _ensure(model: str) -> None:
        if model not in board:
            board[model] = {"wins": 0, "losses": 0, "ties": 0, "battles": 0}

    for rec in records:
        ma, mb, winner = rec["model_a"], rec["model_b"], rec.get("winner", "")
        _ensure(ma)
        _ensure(mb)
        board[ma]["battles"] += 1
        board[mb]["battles"] += 1

        if winner == ma:
            board[ma]["wins"] += 1
            board[mb]["losses"] += 1
        elif winner == mb:
            board[mb]["wins"] += 1
            board[ma]["losses"] += 1
        else:
            board[ma]["ties"] += 1
            board[mb]["ties"] += 1

    return board


def clear_history(db_path: str) -> None:
    """Wipe all battle records."""
    db = _get_db(db_path)
    db.truncate()
