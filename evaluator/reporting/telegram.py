"""Sending a run report to Telegram."""

import re

import requests

from evaluator.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

API_URL = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT_SECONDS = 30

# Telegram rejects a MarkdownV2 message containing any of these unescaped.
RESERVED = r"_*[]()~`>#+-=|{}.!"
RESERVED_PATTERN = re.compile(f"([{re.escape(RESERVED)}])")

MESSAGE_LIMIT = 4096


class TelegramError(RuntimeError):
    """Telegram refused. A failed notification never fails a test run — it is reported."""


def escape_markdown(text: str) -> str:
    """Escape MarkdownV2 reserved characters in a *value*.

    Escaping, not stripping: a judge's comment quotes the assistant, and deleting
    characters would silently alter the evidence. Apply this to interpolated values only
    — running it over a whole composed message would escape the formatting too.
    """
    return RESERVED_PATTERN.sub(r"\\\1", text)


class TelegramNotifier:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID) -> None:
        if not token or not chat_id:
            raise TelegramError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env"
            )
        self.token = token
        self.chat_id = chat_id

    def send_message(self, text: str) -> None:
        self._call(
            "sendMessage",
            data={
                "chat_id": self.chat_id,
                "text": text[:MESSAGE_LIMIT],
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            },
        )

    def _call(self, method: str, data: dict) -> dict:
        response = requests.post(
            API_URL.format(token=self.token, method=method),
            data=data,
            timeout=TIMEOUT_SECONDS,
        )
        payload = response.json()
        if not payload.get("ok"):
            raise TelegramError(f"{method} failed: {payload.get('description', payload)}")
        return payload
