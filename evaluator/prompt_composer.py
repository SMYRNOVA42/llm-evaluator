"""Builds the judge's prompt out of the rubric, a method file and the case at hand.

Composition lives here and nowhere else — a test never reads a prompt file.

The split is deliberate: the rubric is the judge's standing instruction and goes in the
system prompt, while everything that varies per case goes in the user turn, wrapped in
tags the rubric names.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, PROMPTS_DIR
from .core import Expectation, PromptNotFound

NO_BACKEND_DATA = "NONE"


@dataclass(frozen=True, slots=True)
class ComposedPrompt:
    system: str
    user: str


class PromptComposer:
    def __init__(self, prompts_dir: Path = PROMPTS_DIR) -> None:
        self.prompts_dir = prompts_dir

    def rubric(self) -> str:
        return self._read(self.prompts_dir / "rubric.txt")

    def method(self, prompt: str | Path) -> str:
        """`prompt` is a path, as written in the test: `prompts/back_tools/<method>.txt`."""
        path = Path(prompt)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return self._read(path)

    def compose(
        self,
        *,
        user_msg: str,
        llm_answer: str,
        prompt: str | Path,
        backend_json: Mapping[str, Any] | None,
        expectation: Expectation,
    ) -> ComposedPrompt:
        backend = (
            NO_BACKEND_DATA
            if backend_json is None
            else json.dumps(dict(backend_json), indent=2, sort_keys=True)
        )
        user = "\n".join(
            (
                f"<user_msg>\n{user_msg}\n</user_msg>",
                f"<ai_msg>\n{llm_answer}\n</ai_msg>",
                f"<expectation>{expectation.value}</expectation>",
                f"<backend_data>\n{backend}\n</backend_data>",
                f"<method>\n{self.method(prompt)}\n</method>",
            )
        )
        return ComposedPrompt(system=self.rubric(), user=user)

    @staticmethod
    def _read(path: Path) -> str:
        if not path.is_file():
            raise PromptNotFound(f"no prompt file at {path}")
        return path.read_text(encoding="utf-8").strip()
