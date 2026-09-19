"""Claude as the judge.

The verdict shape is enforced by the API through structured outputs, not requested in
prose — assistant prefill, the old way of forcing JSON, returns a 400 on current models.

The judge echoes `user_msg` and `ai_msg` back as part of its answer. That echo is a
grounding device for the judge, not the record: the `Verdict` is built from what we
actually sent, so a paraphrase can never end up in a report as if it were the
assistant's words.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import anthropic

from evaluator.config import JUDGE_EFFORT, JUDGE_MAX_TOKENS, JUDGE_MODEL
from evaluator.core import Expectation, JudgeUnavailable, Verdict
from evaluator.prompt_composer import PromptComposer

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "user_msg": {"type": "string"},
        "ai_msg": {"type": "string"},
        "verdict": {"type": "boolean"},
        "judge_comment": {"type": "string"},
    },
    "required": ["user_msg", "ai_msg", "verdict", "judge_comment"],
    "additionalProperties": False,
}

# The judge occasionally degenerates into a loop of closing braces, blowing past the
# token limit and returning unparseable JSON. That is the measuring instrument breaking,
# not the assistant answering badly, so it earns exactly one retry - the kind of retry
# the eval suite allows, because no verdict was produced at all.
GRADING_ATTEMPTS = 2


class AnthropicJudge:
    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        composer: PromptComposer | None = None,
        model: str = JUDGE_MODEL,
    ) -> None:
        self.client = client or anthropic.Anthropic()
        self.composer = composer or PromptComposer()
        self.model = model

    def verdict(
        self,
        *,
        user_msg: str,
        llm_answer: str,
        prompt: str | Path,
        backend_json: Mapping[str, Any] | None = None,
        expectation: Expectation = Expectation.ANSWER,
    ) -> Verdict:
        composed = self.composer.compose(
            user_msg=user_msg,
            llm_answer=llm_answer,
            prompt=prompt,
            backend_json=backend_json,
            expectation=expectation,
        )
        graded = self._grade(composed.system, composed.user)
        return Verdict(
            user_msg=user_msg,
            ai_msg=llm_answer,
            passed=graded["verdict"],
            judge_comment=graded["judge_comment"],
            judge_model=self.model,
        )

    def _grade(self, system: str, user: str) -> dict[str, Any]:
        last_error: JudgeUnavailable | None = None
        for _ in range(GRADING_ATTEMPTS):
            try:
                return self._grade_once(system, user)
            except JudgeUnavailable as error:
                last_error = error
        raise JudgeUnavailable(f"the judge failed {GRADING_ATTEMPTS} times: {last_error}")

    def _grade_once(self, system: str, user: str) -> dict[str, Any]:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=JUDGE_MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={
                    "effort": JUDGE_EFFORT,
                    "format": {"type": "json_schema", "schema": VERDICT_SCHEMA},
                },
            )
        except anthropic.APIConnectionError as error:
            raise JudgeUnavailable(f"cannot reach the judge: {error}") from error
        except anthropic.RateLimitError as error:
            raise JudgeUnavailable(f"judge rate limited: {error}") from error
        except anthropic.APIStatusError as error:
            if error.status_code >= 500:
                raise JudgeUnavailable(f"judge server error {error.status_code}") from error
            raise

        if response.stop_reason == "refusal":
            raise JudgeUnavailable(f"the judge declined to grade: {response.stop_details}")
        if response.stop_reason == "max_tokens":
            raise JudgeUnavailable(
                f"the judge hit the {JUDGE_MAX_TOKENS} token ceiling and was cut off "
                "mid-answer, so there is no verdict to read"
            )

        return self._parse(response)

    @staticmethod
    def _parse(response: anthropic.types.Message) -> dict[str, Any]:
        text = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            raise JudgeUnavailable(f"the judge returned no text block: {response.stop_reason}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            # Structured outputs make the schema the API's job, so malformed JSON here
            # means the judge malfunctioned. Report the head of it, not all of a
            # thousand-character brace loop.
            raise JudgeUnavailable(
                f"the judge returned text that is not JSON: {text[:300]!r}"
            ) from error
