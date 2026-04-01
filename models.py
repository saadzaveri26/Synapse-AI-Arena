"""
models.py – Ollama model interaction layer with parallel execution & streaming.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Generator

import ollama


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ModelResponse:
    """Container for a single model's response."""
    model: str
    content: str = ""
    elapsed: float = 0.0
    error: str | None = None
    token_count: int = 0


# ── Core helpers ──────────────────────────────────────────────────────────────

def list_available_models(fallback: list[str] | None = None) -> list[str]:
    """
    Query Ollama for locally-pulled models.
    Falls back to *fallback* list if Ollama is unreachable.
    """
    try:
        models_info = ollama.list()
        names = sorted(
            {m.model for m in models_info.models}
        )
        return names if names else (fallback or [])
    except Exception:
        return fallback or []


def check_ollama_health() -> tuple[bool, str]:
    """Return (is_healthy, message) for the Ollama backend."""
    try:
        ollama.list()
        return True, "Ollama is running."
    except Exception as exc:
        return False, f"Cannot reach Ollama: {exc}"


def get_response(
    model_name: str,
    user_prompt: str,
    system_prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    num_ctx: int = 2048,
) -> ModelResponse:
    """Send a prompt to a model and return the full response."""
    start = time.time()
    try:
        resp = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature, "top_p": top_p, "num_ctx": num_ctx},
        )
        elapsed = time.time() - start
        content = resp["message"]["content"]
        token_count = resp.get("eval_count", len(content.split()))
        return ModelResponse(
            model=model_name,
            content=content,
            elapsed=elapsed,
            token_count=token_count,
        )
    except Exception as exc:
        return ModelResponse(model=model_name, error=str(exc))


def stream_response(
    model_name: str,
    user_prompt: str,
    system_prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    num_ctx: int = 2048,
) -> Generator[tuple[str, float], None, None]:
    """
    Yield (token_chunk, elapsed_so_far) tuples as the model streams.
    The *last* yielded tuple contains the full text and final time.
    """
    start = time.time()
    try:
        stream = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature, "top_p": top_p, "num_ctx": num_ctx},
            stream=True,
        )
        for chunk in stream:
            token = chunk["message"]["content"]
            yield token, time.time() - start
    except Exception as exc:
        yield f"\n\n**Error:** {exc}", time.time() - start


# ── Parallel execution ────────────────────────────────────────────────────────

def run_battle(
    model_a: str,
    model_b: str,
    user_prompt: str,
    system_prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    num_ctx: int = 2048,
) -> tuple[ModelResponse, ModelResponse]:
    """Run both models in parallel and return their responses."""
    kwargs = dict(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        top_p=top_p,
        num_ctx=num_ctx,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a: Future[ModelResponse] = pool.submit(get_response, model_a, **kwargs)
        future_b: Future[ModelResponse] = pool.submit(get_response, model_b, **kwargs)
        return future_a.result(), future_b.result()
