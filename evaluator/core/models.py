"""Domain models. No I/O, no SDKs, no knowledge of HTTP, WebSockets or any provider."""

import json
from dataclasses import dataclass
from enum import StrEnum

from .errors import InvalidVerdict


@dataclass(frozen=True, slots=True)
class Verdict:
    """The judge's answer.

    Mirrors the JSON the rubric demands — `{user_msg, ai_msg, verdict, judge_comment}` —
    with the wire field `verdict` bound to `passed`, so that call sites read as
    `verdict.passed` instead of `verdict.verdict`.

    `judge_model` is provenance added by the adapter, not something the judge reports.
    Verdicts from different judges are not comparable with each other.
    """

    user_msg: str
    ai_msg: str
    passed: bool
    judge_comment: str
    judge_model: str

    def as_json(self) -> str:
        """The wire shape the rubric asks for, plus provenance.

        `passed` goes back out as `verdict`: the attribute is named for readability at
        call sites, but a report should show the contract the judge was held to.
        """
        return json.dumps(
            {
                "user_msg": self.user_msg,
                "ai_msg": self.ai_msg,
                "verdict": self.passed,
                "judge_comment": self.judge_comment,
                "judge_model": self.judge_model,
            },
            indent=2,
            ensure_ascii=False,
        )

    def __post_init__(self) -> None:
        if not self.judge_comment.strip():
            raise InvalidVerdict(
                "the judge returned an empty judge_comment; a verdict without a stated "
                "reason is not evidence, and an empty one on a failure means the rubric "
                "does not say what to look for"
            )


class Expectation(StrEnum):
    """What the assistant was supposed to do with this request.

    Sent to the judge alongside the answer, because the same reply can be correct or
    wrong depending on which was expected. `ANSWER` is the default: the employee asked
    something the assistant may serve. `DECLINE` marks a negative case — the employee
    asked for something they are not entitled to, or that is out of scope, and a polite
    refusal is the passing behaviour. A `DECLINE` case has no backend data, by design.
    """

    ANSWER = "answer"
    DECLINE = "decline"
