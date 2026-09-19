"""Route a message to a method, gather whatever that method needs, then answer.

Kept as explicit steps so routing is observable. The reply carries the chosen method,
which lets the evaluator check orchestration deterministically instead of asking a judge
to guess what the assistant thought it was doing.

Methods are dispatched through a registry, not a chain of `if`s: adding a capability
means adding a handler and one line in `_handlers`.
"""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from . import prompts
from .backend_gateway import BackendGateway
from .config import OPENAI_MODEL
from .methods import ADD_EMPLOYEE, BY_NAME, FALLBACK, METHODS, VACATION_BALANCE, AssistantMethod


@dataclass(frozen=True, slots=True)
class AssistantReply:
    method: str
    text: str


class Orchestrator:
    def __init__(self, llm: AsyncOpenAI, gateway: BackendGateway, employee_id: int) -> None:
        self._llm = llm
        self._gateway = gateway
        self._employee_id = employee_id
        self._handlers: dict[str, Callable[[str], Awaitable[Any]]] = {
            VACATION_BALANCE.name: self._vacation_balance,
            ADD_EMPLOYEE.name: self._add_employee,
        }

    async def handle(self, user_message: str) -> AssistantReply:
        method = await self._route(user_message)
        handler = self._handlers.get(method.name)
        context = await handler(user_message) if handler else None
        text = await self._answer(user_message, method, context)
        return AssistantReply(method=method.name, text=text)

    async def _route(self, user_message: str) -> AssistantMethod:
        catalogue = "\n".join(f"- {m.name}: {m.description}" for m in METHODS)
        chosen = await self._ask_json(
            prompts.load("router").format(methods=catalogue), user_message
        )
        return BY_NAME.get(chosen.get("method", ""), FALLBACK)

    async def _vacation_balance(self, _: str) -> dict:
        return await self._gateway.vacation_balance(self._employee_id)

    async def _add_employee(self, user_message: str) -> dict:
        """Pull the fields out of the sentence, then actually try to create the record.

        Whatever the backend answers - created, refused, rejected - is handed to the
        answering step as data. The assistant is expected to report it truthfully.
        """
        departments = await self._gateway.departments()
        positions = await self._gateway.positions()
        fields = await self._ask_json(
            prompts.load("extract_employee").format(
                departments=json.dumps(departments), positions=json.dumps(positions)
            ),
            user_message,
        )
        status_code, body = await self._gateway.add_employee(fields)
        return {"requested": fields, "backend_status": status_code, "backend_response": body}

    async def _answer(
        self, user_message: str, method: AssistantMethod, context: Any | None
    ) -> str:
        instructions = prompts.load(f"methods/{method.name}")
        if context is not None:
            instructions = instructions.format(backend_data=json.dumps(context))
        completion = await self._llm.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"{prompts.load('system')}\n\n{instructions}"},
                {"role": "user", "content": user_message},
            ],
        )
        return (completion.choices[0].message.content or "").strip()

    async def _ask_json(self, system: str, user_message: str) -> dict:
        completion = await self._llm.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        )
        try:
            return json.loads(completion.choices[0].message.content or "")
        except json.JSONDecodeError:
            return {}
