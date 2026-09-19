"""Turning a run into the text that lands in a chat.

Two jobs kept apart: `run_summary` decides what happened, this decides how to say it.
Swapping Telegram for Slack changes only the escaping and the link syntax, not this shape.
"""

from datetime import datetime, timezone

from evaluator.config import PROJECT_NAME, REPORT_URL
from evaluator.reporting.run_summary import RunSummary
from evaluator.reporting.telegram import escape_markdown

MAX_LISTED_FAILURES = 12
ERROR_EXCERPT = 180


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y/%m/%d - %H:%M:%S")


def _percent(part: int, total: int) -> str:
    return f"{part / total * 100:.0f}%" if total else "0%"


def build_message(summary: RunSummary) -> str:
    """A MarkdownV2 message. Every interpolated value is escaped; the markup is not."""
    lines = [
        f"🤖 *{escape_markdown(PROJECT_NAME)} — evaluation run*",
        f"🗓 {escape_markdown(now_utc())} UTC",
        "",
        f"🟢 *Passed* — {summary.passed} \\({_percent(summary.passed, summary.total)}\\)",
        f"🔴 *Failed* — {summary.failed} \\({_percent(summary.failed, summary.total)}\\)",
    ]
    if summary.skipped:
        lines.append(f"⚪️ *Skipped* — {summary.skipped}")
    lines.append(f"🎯 *Total* — {summary.total}")

    lines.extend(_verdict_section(summary))

    if REPORT_URL:
        lines += ["", f"📊 [Full report]({escape_markdown(REPORT_URL)})"]

    return "\n".join(lines)


def _verdict_section(summary: RunSummary) -> list[str]:
    if not summary.failures:
        return ["", "✅ *Every phrasing passed\\.*"]

    lines = []
    root_cause = summary.single_root_cause()

    if summary.everything_failed:
        lines += [
            "",
            f"🆘 *Nothing passed at all\\.* This usually means the environment is down "
            f"rather than the assistant being wrong\\. Check "
            f"*{escape_markdown(PROJECT_NAME)}* by hand before reading anything below\\.",
        ]

    if root_cause is not None:
        error, count = root_cause
        lines += [
            "",
            f"⚠️ *All {count} failures share one error* — likely a single root cause, "
            f"not {count} separate defects:",
            f"`{escape_markdown(error)}`",
        ]

    lines += ["", "⚠️ *Failures:*"]
    for failure in summary.failures[:MAX_LISTED_FAILURES]:
        error = failure.error
        if len(error) > ERROR_EXCERPT:
            error = f"{error[:ERROR_EXCERPT].rstrip()}..."
        lines.append(f"✖️ *{escape_markdown(failure.name)}*\n   {escape_markdown(error)}")
    if len(summary.failures) > MAX_LISTED_FAILURES:
        remaining = len(summary.failures) - MAX_LISTED_FAILURES
        lines.append(f"…and {remaining} more — see the full report\\.")

    return lines
