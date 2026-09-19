"""Client for the assistant under test, over WebSocket.

The evaluator reaches the assistant only through this class, and only over the socket.
Whatever answers at `MODEL_WS_URL` — the demo stand today, a real product tomorrow — the
tests do not change and nothing here imports a model vendor's SDK.

Unlike `HRClient`, this one does raise. A dead socket, a timeout or an `{"error": ...}`
frame means the measurement never happened, and that must surface as an infrastructure
error rather than as "the assistant answered badly".
"""

import json
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any

from websockets import WebSocketException
from websockets.sync.client import connect

from evaluator.core import AssistantUnavailable

from .config import MODEL_TIMEOUT_SECONDS, MODEL_WS_URL


@dataclass(frozen=True, slots=True)
class ModelReply:
    """One answer from the assistant.

    `method` is the assistant method the orchestration routed to — asserted in the test.
    `payload()` is the final message text, and that is the only part the judge ever sees.
    """

    raw: dict[str, Any]

    @property
    def method(self) -> str:
        return self.raw["method"]

    def payload(self) -> str:
        return self.raw["text"]


class ModelClient:
    def __init__(self, token: str, url: str = MODEL_WS_URL) -> None:
        self.url = f"{url}?token={token}"
        # `connect()` is a context manager; entering it through a stack lets this class
        # own the connection for its lifetime and still close it deterministically.
        self._stack = ExitStack()
        try:
            self.connection = self._stack.enter_context(
                connect(self.url, open_timeout=MODEL_TIMEOUT_SECONDS)
            )
        except (WebSocketException, OSError) as error:
            raise AssistantUnavailable(f"cannot connect to {url}: {error}") from error

    def ask(self, msg: str) -> ModelReply:
        try:
            self.connection.send(json.dumps({"text": msg}))
            frame = self.connection.recv(timeout=MODEL_TIMEOUT_SECONDS)
        except (WebSocketException, TimeoutError, OSError) as error:
            raise AssistantUnavailable(f"no answer to {msg!r}: {error}") from error

        raw = json.loads(frame)
        if "error" in raw:
            raise AssistantUnavailable(f"assistant refused {msg!r}: {raw['error']}")
        return ModelReply(raw)

    def close(self) -> None:
        self._stack.close()

    def __enter__(self) -> "ModelClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
