"""
judge.py – AI Judge that evaluates battle responses.
"""

from __future__ import annotations

from models import get_response, ModelResponse


JUDGE_META_PROMPT = """You are an impartial expert judge evaluating two AI responses.

**User's Original Question:**
{question}

**Persona Instruction Given to Both Models:**
{persona}

---

### Model A  –  {model_a}
{response_a}

---

### Model B  –  {model_b}
{response_b}

---

**Your task:**
1. Evaluate each answer on **Accuracy**, **Completeness**, **Style**, and **Persona Adherence**.
2. Give each model a score from 1-10 for every criterion.
3. Pick the overall **WINNER** (or declare a TIE).
4. Format your verdict exactly as:

**SCORES:**
| Criterion | Model A | Model B |
|-----------|---------|---------|
| Accuracy | X/10 | X/10 |
| Completeness | X/10 | X/10 |
| Style | X/10 | X/10 |
| Persona | X/10 | X/10 |

**WINNER:** [Model A / Model B / TIE]
**REASON:** [2-3 sentences explaining your decision]
"""


def get_judge_verdict(
    question: str,
    persona: str,
    model_a: str,
    response_a: str,
    model_b: str,
    response_b: str,
    judge_model: str = "llama3",
    judge_system_prompt: str = "You are a fair and impartial judge.",
) -> ModelResponse:
    """
    Ask an LLM judge to compare two responses and return a verdict.
    """
    prompt = JUDGE_META_PROMPT.format(
        question=question,
        persona=persona,
        model_a=model_a,
        response_a=response_a,
        model_b=model_b,
        response_b=response_b,
    )
    return get_response(
        model_name=judge_model,
        user_prompt=prompt,
        system_prompt=judge_system_prompt,
    )
