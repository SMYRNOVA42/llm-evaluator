"""What a notifier has to be able to do.

Only Telegram is implemented. Slack is the same shape and is not a separate design
problem: a `SlackNotifier` implements this protocol, posts to `chat.postMessage` (or an
incoming webhook) with a bot token and a channel id, and uses Slack's `mrkdwn` - which
wants `*bold*` and `<url|text>` links, and does not need MarkdownV2's aggressive
escaping. Nothing else in this package changes: whoever sends the report depends on this
protocol, not on a vendor.

Telegram is the one that ships here because it needs no workspace to demonstrate.
"""

from typing import Protocol


class Notifier(Protocol):
    def send_message(self, text: str) -> None: ...
