"""Attaching evidence to the Allure report.

A failed eval test is only useful if the report shows what was asked, what came back and
why the judge rejected it. `attach_verdict` carries all of that in one JSON, because the
verdict already echoes the query and the answer.

Call these **before** the assertion. Anything after `assert verdict.passed` never runs on
the failures — which are exactly the results worth looking at.
"""

import json
from collections.abc import Mapping
from typing import Any

import allure

from evaluator.core import Verdict


def attach_verdict(verdict: Verdict) -> None:
    """The evidence chain: user message, assistant answer, verdict, reason, judge model."""
    allure.attach(
        verdict.as_json(),
        name="judge verdict",
        attachment_type=allure.attachment_type.JSON,
    )


def attach_backend_data(payload: Mapping[str, Any] | None) -> None:
    """The ground truth the answer was judged against, or a note that there was none."""
    body = (
        "no backend data for this case"
        if payload is None
        else json.dumps(dict(payload), indent=2, sort_keys=True)
    )
    allure.attach(
        body,
        name="backend data",
        attachment_type=allure.attachment_type.JSON
        if payload is not None
        else allure.attachment_type.TEXT,
    )
