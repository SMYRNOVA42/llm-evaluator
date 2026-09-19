"""Send the last run's results to chat.

    python -m evaluator.reporting.notify

Run it after pytest. A notification failure is reported on stderr and returns a non-zero
exit code, but it says nothing about the suite: the tests have already run and their
result is whatever it was.
"""

import sys

from evaluator.reporting.message import build_message
from evaluator.reporting.notifier import Notifier
from evaluator.reporting.run_summary import read_run_summary
from evaluator.reporting.telegram import TelegramError, TelegramNotifier


def main(notifier: Notifier | None = None) -> int:
    summary = read_run_summary()
    if summary.total == 0:
        print("no results in allure-results - run pytest first", file=sys.stderr)
        return 1

    try:
        notifier = notifier or TelegramNotifier()
        notifier.send_message(build_message(summary))
    except TelegramError as error:
        print(f"could not notify: {error}", file=sys.stderr)
        return 1

    print(f"sent: {summary.passed} passed, {summary.failed} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
