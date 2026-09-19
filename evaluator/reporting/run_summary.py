"""Reads what a run produced, straight out of `allure-results`.

Deliberately not out of `allure-report`: that directory only exists after
`allure generate`, which needs the Java CLI installed on the machine and in CI.
`allure-results` is written by the test run itself, so this works anywhere.
"""

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from evaluator.config import ALLURE_RESULTS_DIR

FAILED_STATUSES = frozenset({"failed", "broken"})
NOISE_PREFIXES = ("evaluator.core.errors.", "clients.model_client.", "clients.")
GROUPING_KEY_LENGTH = 100


@dataclass(frozen=True, slots=True)
class FailedTest:
    name: str
    error: str

    @property
    def grouping_key(self) -> str:
        """Identical keys mean one root cause, not several separate defects."""
        return self.error[:GROUPING_KEY_LENGTH]


@dataclass(frozen=True, slots=True)
class RunSummary:
    passed: int
    failed: int
    skipped: int
    failures: tuple[FailedTest, ...]

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def everything_failed(self) -> bool:
        """Nothing passed at all — far more likely a dead environment than a bad build."""
        return self.total > 0 and self.passed == 0

    def single_root_cause(self) -> tuple[str, int] | None:
        """The one error behind every failure, when there is one."""
        if len(self.failures) < 2:
            return None
        keys = Counter(failure.grouping_key for failure in self.failures)
        key, count = keys.most_common(1)[0]
        return (key, count) if count == len(self.failures) else None


def strip_module_paths(error: str) -> str:
    """`evaluator.core.errors.AssistantUnavailable: ...` reads better without the path."""
    for prefix in NOISE_PREFIXES:
        error = error.replace(prefix, "")
    return error


def read_run_summary(results_dir: Path = ALLURE_RESULTS_DIR) -> RunSummary:
    counts: Counter[str] = Counter()
    failures: list[FailedTest] = []

    for result_file in results_dir.glob("*-result.json"):
        result = json.loads(result_file.read_text(encoding="utf-8"))
        status = result.get("status", "unknown")
        counts[status] += 1
        if status in FAILED_STATUSES:
            message = result.get("statusDetails", {}).get("message", "no error message")
            failures.append(
                FailedTest(
                    name=result.get("name", result.get("fullName", "unnamed test")),
                    error=strip_module_paths(message.strip().splitlines()[0]),
                )
            )

    return RunSummary(
        passed=counts["passed"],
        failed=counts["failed"] + counts["broken"],
        skipped=counts["skipped"],
        failures=tuple(sorted(failures, key=lambda failure: failure.name)),
    )
