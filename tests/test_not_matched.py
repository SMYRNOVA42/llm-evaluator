"""The fallback: greetings, farewells, and anything outside HR self-service.

Two things are under test here. That the assistant behaves well *when* a message belongs
to this method, and that legitimate HR questions do not get swallowed by it.
"""

import allure
import pytest

from evaluator.core import Expectation
from evaluator.reporting import attach_backend_data, attach_verdict

PROMPT = "prompts/tools/not_matched.txt"

pytestmark = [
    allure.epic("HR assistant"),
    allure.feature("not_matched"),
    pytest.mark.live,
]


@allure.testcase("HR-003")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Small talk: {msg}")
@pytest.mark.parametrize(
    "msg",
    [
        "hi there",
        "Good morning!",
        "thanks, bye",
        "have a nice weekend",
    ],
)
def test_not_matched_handles_small_talk(msg, model, judge):
    """Expectation is ANSWER: a greeting deserves a reply, not a refusal."""
    attach_backend_data(None)

    answer = model.ask(msg)
    assert answer.method == "not_matched", (
        f"routed to {answer.method!r} instead of 'not_matched'"
    )

    verdict = judge.verdict(
        user_msg=msg,
        llm_answer=answer.payload(),
        prompt=PROMPT,
        expectation=Expectation.ANSWER,
    )
    attach_verdict(verdict)
    assert verdict.passed, f"{verdict.judge_comment}\n\nassistant said: {answer.payload()}"


@allure.testcase("HR-004")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Out of scope: {msg}")
@pytest.mark.parametrize(
    "msg",
    [
        "What is the weather in Berlin today?",
        "When will my salary be paid this month?",
        "Can you reset my VPN password?",
        "Book me a meeting room for tomorrow",
    ],
)
def test_not_matched_declines_out_of_scope(msg, model, judge):
    """Expectation is DECLINE: the assistant must refuse and not invent capabilities.

    Two of these - payroll and IT - are adjacent enough to HR that the assistant is
    tempted to claim it can help. It cannot.
    """
    attach_backend_data(None)

    answer = model.ask(msg)
    assert answer.method == "not_matched", (
        f"routed to {answer.method!r} instead of 'not_matched'"
    )

    verdict = judge.verdict(
        user_msg=msg,
        llm_answer=answer.payload(),
        prompt=PROMPT,
        expectation=Expectation.DECLINE,
    )
    attach_verdict(verdict)
    assert verdict.passed, f"{verdict.judge_comment}\n\nassistant said: {answer.payload()}"


@allure.testcase("HR-005")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("Must not fall back: {msg}")
@pytest.mark.parametrize(
    "msg",
    [
        "days off left?",
        "Morning! Could you check my remaining holiday please",
        "i need to know how much vacation i still got",
    ],
)
def test_real_questions_do_not_fall_back(msg, model):
    """The fallback must not swallow questions the assistant can actually answer.

    This is the negative side of the method, and it needs no judge: a message that lands
    in `not_matched` when it should have been served is a routing defect, whatever the
    wording of the reply. Cheap, fast, and it fails before any judge is billed.
    """
    answer = model.ask(msg)

    assert answer.method != "not_matched", (
        f"fell back to 'not_matched' for a question the assistant can serve\n\n"
        f"assistant said: {answer.payload()}"
    )
