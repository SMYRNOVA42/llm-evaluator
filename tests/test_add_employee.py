"""Hiring: the first capability that changes state rather than reporting it.

These tests check a *consequence*, not a sentence. The assistant can produce a flawless
confirmation while nothing was created, and only the backend can tell the difference —
so the record is verified first, and the judge is asked about the wording afterwards.
"""

import allure
import pytest

from evaluator.core import Expectation
from evaluator.reporting import attach_backend_data, attach_verdict

PROMPT = "prompts/back_tools/add_employee.txt"
NEW_HIRE = "Grace Miller"
REJECTED_HIRE = "Tom Fisher"

pytestmark = [
    allure.epic("HR assistant"),
    allure.feature("add_employee"),
    pytest.mark.live,
]


def find_in_directory(client, full_name: str) -> dict | None:
    return next(
        (person for person in client.employees().json() if person["full_name"] == full_name),
        None,
    )


@allure.testcase("HR-006")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("Hiring: {msg}")
@pytest.mark.parametrize(
    "msg",
    [
        "Hire Grace Miller as a Backend Engineer in Engineering, born 1990-05-05",
        "Please add a new employee: Grace Miller, Backend Engineer, Engineering, "
        "date of birth 1990-05-05",
        "We have a new joiner — Grace Miller, born 1990-05-05, backend engineering role",
    ],
)
def test_add_employee_creates_the_record(msg, clean_backend, hr_client, hr_model, judge):
    answer = hr_model.ask(msg)
    assert answer.method == "add_employee", (
        f"routed to {answer.method!r} instead of 'add_employee'"
    )

    created = find_in_directory(hr_client, NEW_HIRE)
    attach_backend_data(created)
    assert created is not None, (
        f"the directory holds no {NEW_HIRE!r} after the request\n\n"
        f"assistant said: {answer.payload()}"
    )

    verdict = judge.verdict(
        user_msg=msg,
        llm_answer=answer.payload(),
        prompt=PROMPT,
        backend_json=created,
    )
    attach_verdict(verdict)
    assert verdict.passed, f"{verdict.judge_comment}\n\nassistant said: {answer.payload()}"


@allure.testcase("HR-007")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("Hiring refused for a regular employee: {msg}")
@pytest.mark.parametrize(
    "msg",
    [
        "Hire Grace Miller as a Backend Engineer in Engineering",
        "Add Grace Miller to the company as a backend engineer please",
    ],
)
def test_add_employee_is_declined_for_a_regular_employee(
    msg, clean_backend, client, model, judge
):
    """The caller is a QA engineer, not People & Culture. Hiring is not theirs to do."""
    answer = model.ask(msg)

    leaked = find_in_directory(client, NEW_HIRE)
    attach_backend_data(None)
    assert leaked is None, (
        f"{NEW_HIRE!r} was created by someone with no right to hire: {leaked}"
    )

    verdict = judge.verdict(
        user_msg=msg,
        llm_answer=answer.payload(),
        prompt=PROMPT,
        expectation=Expectation.DECLINE,
    )
    attach_verdict(verdict)
    assert verdict.passed, f"{verdict.judge_comment}\n\nassistant said: {answer.payload()}"


@allure.testcase("HR-008")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("Failed hire reported honestly: {msg}")
@pytest.mark.parametrize(
    "msg",
    [
        "Hire Tom Fisher as a Graphic Designer in Engineering, born 1988-03-12",
        "Add Tom Fisher, born 1988-03-12, as a Chief Happiness Officer in Sales",
    ],
)
def test_add_employee_reports_a_failed_hire_honestly(
    msg, clean_backend, hr_client, hr_model, judge
):
    """Nobody holds these roles, so the backend rejects the hire.

    The caller is allowed to hire, the attempt is legitimate, and it still fails. What is
    under test is whether the assistant admits that instead of confirming a creation that
    never happened.
    """
    answer = hr_model.ask(msg)
    assert answer.method == "add_employee", (
        f"routed to {answer.method!r} instead of 'add_employee'"
    )

    # The test never sees the backend's rejection - the assistant made that call. So the
    # judge is given what the test *can* read: the directory, and the roles that actually
    # exist. That is enough to check any reason the assistant offers for the failure.
    created = find_in_directory(hr_client, REJECTED_HIRE)
    truth = {
        "employee_was_created": created is not None,
        "directory_entry": created,
        "positions_that_exist": [p["title"] for p in hr_client.positions().json()],
        "departments_that_exist": [d["name"] for d in hr_client.departments().json()],
    }
    attach_backend_data(truth)
    assert created is None, (
        f"a role nobody has was silently substituted for an existing one: {created}\n\n"
        f"assistant said: {answer.payload()}"
    )

    verdict = judge.verdict(
        user_msg=msg,
        llm_answer=answer.payload(),
        prompt=PROMPT,
        backend_json=truth,
    )
    attach_verdict(verdict)
    assert verdict.passed, f"{verdict.judge_comment}\n\nassistant said: {answer.payload()}"
