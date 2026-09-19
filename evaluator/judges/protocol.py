"""The contract every judge implementation satisfies.

A test depends on this shape and never on a vendor. Swapping the judge is a config
change — but note that verdicts from two judges are not comparable, so a swap means a
new baseline, not a continuation of the old one.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from evaluator.core import Expectation, Verdict


class Judge(Protocol):
    def verdict(
        self,
        *,
        user_msg: str,
        llm_answer: str,
        prompt: str | Path,
        backend_json: Mapping[str, Any] | None = None,
        expectation: Expectation = Expectation.ANSWER,
    ) -> Verdict: ...
