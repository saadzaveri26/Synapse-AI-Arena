"""
utils.py – Shared helpers: config loading, export, etc.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import yaml


# ── Config ────────────────────────────────────────────────────────────────────

_CONFIG_CACHE: dict[str, Any] | None = None


def load_config(path: str = "config.yaml") -> dict[str, Any]:
    """Load and cache the YAML config file."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    config_path = Path(path)
    if not config_path.exists():
        _CONFIG_CACHE = {}
        return _CONFIG_CACHE
    with open(config_path, "r", encoding="utf-8") as f:
        _CONFIG_CACHE = yaml.safe_load(f) or {}
    return _CONFIG_CACHE


def cfg(key: str, default: Any = None) -> Any:
    """
    Dot-notation config lookup.
    Example: cfg("ollama.host") → "http://localhost:11434"
    """
    config = load_config()
    keys = key.split(".")
    node: Any = config
    for k in keys:
        if isinstance(node, dict):
            node = node.get(k)
        else:
            return default
    return node if node is not None else default


# ── Export ────────────────────────────────────────────────────────────────────

def export_battle_markdown(
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
) -> str:
    """Return a Markdown-formatted battle report."""
    lines = [
        "# ⚔️ Synapse AI Arena – Battle Report\n",
        f"**Prompt:** {prompt}\n",
        f"**Persona:** {persona}\n",
        "---\n",
        f"## Model A: {model_a}",
        f"**Time:** {time_a:.2f}s\n",
        response_a,
        "\n---\n",
        f"## Model B: {model_b}",
        f"**Time:** {time_b:.2f}s\n",
        response_b,
        "\n---\n",
        f"## Winner: {winner}\n",
    ]
    if judge_verdict:
        lines += ["## Judge's Verdict\n", judge_verdict, "\n"]
    return "\n".join(lines)


def export_battle_pdf_bytes(
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
) -> bytes:
    """Generate a PDF battle report and return raw bytes."""
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Synapse AI Arena - Battle Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    # Prompt
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Prompt:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, prompt)
    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 11)
    pdf.cell(0, 8, f"Persona: {persona}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Model A
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Model A: {model_a}  ({time_a:.2f}s)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, response_a.encode("latin-1", "replace").decode("latin-1"))
    pdf.ln(4)

    # Model B
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Model B: {model_b}  ({time_b:.2f}s)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, response_b.encode("latin-1", "replace").decode("latin-1"))
    pdf.ln(4)

    # Winner
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Winner: {winner}", new_x="LMARGIN", new_y="NEXT", align="C")

    if judge_verdict:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Judge Verdict:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, judge_verdict.encode("latin-1", "replace").decode("latin-1"))

    return bytes(pdf.output())
