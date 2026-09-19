"""Prompt loading for the assistant.

These are the *product's* prompts. The evaluator has its own, unrelated set (rubric and
per-method judging prompts) — do not merge the two.
"""

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


@lru_cache
def load(name: str) -> str:
    """`load("router")` or `load("methods/vacation_balance")`."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"no prompt file for {name!r} at {path}")
    return path.read_text(encoding="utf-8").strip()
