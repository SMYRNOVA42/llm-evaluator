"""Does the judge agree with a human on answers whose quality is already known?

This is the only file here that does not test the assistant. It tests the instrument.
An unvalidated judge is an opinion, and every verdict in the rest of the suite rests on
this one being trustworthy.

Run it after touching `prompts/rubric.txt`, any method prompt, or `JUDGE_MODEL` — those
are the three things that can silently change what every other test means. It needs no
stand: the answers are fixed, because a judge cannot be measured against a
non-deterministic assistant. If a verdict disagreed there, you could not tell which of
the two was wrong.
"""

import json
from pathlib import Path

import allure
import pytest

from evaluator.core import Expectation
from evaluator.reporting import attach_backend_data, attach_verdict

CASES = json.loads((Path(__file__).with_name("judge_cases.json")).read_text(encoding="utf-8"))

pytestmark = [
    allure.epic("Evaluator itself"),
    allure.feature("judge agreement"),
    pytest.mark.live,
]


@allure.testcase("JUDGE-001")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("{case[id]}")
@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_judge_agrees_with_the_human_label(case, judge):
    attach_backend_data(case["backend_json"])

    verdict = judge.verdict(
        user_msg=case["user_msg"],
        llm_answer=case["ai_msg"],
        prompt=case["prompt"],
        backend_json=case["backend_json"],
        expectation=Expectation(case["expectation"]),
    )
    attach_verdict(verdict)

    assert verdict.passed is case["expected_verdict"], (
        f"human label: {case['expected_verdict']} — {case['why']}\n\n"
        f"judge said: {verdict.judge_comment}"
    )
