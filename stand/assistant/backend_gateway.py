"""The assistant's own client to the HR backend.

Separate from the evaluator's `HRClient`: this one belongs to the product, the other
belongs to the tests. They must never be shared — the evaluator needs an independent
source of truth to judge the assistant against.

Write calls return the status code alongside the body instead of raising. A refusal from
the backend is information the assistant has to relay honestly, not an exception to
swallow.
"""

from typing import Any

import httpx

from .config import BACKEND_URL, REQUEST_TIMEOUT_SECONDS


class BackendGateway:
    def __init__(self, token: str, client: httpx.AsyncClient) -> None:
        self._token = token
        self._client = client

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def _get(self, path: str) -> Any:
        response = await self._client.get(
            f"{BACKEND_URL}{path}", headers=self._headers, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()

    async def whoami(self) -> dict:
        return await self._get("/auth/me")

    async def vacation_balance(self, employee_id: int) -> dict:
        return await self._get(f"/employees/{employee_id}/vacation-balance")

    async def departments(self) -> list[dict]:
        return await self._get("/departments")

    async def positions(self) -> list[dict]:
        return await self._get("/positions")

    async def add_employee(self, payload: dict) -> tuple[int, Any]:
        response = await self._client.post(
            f"{BACKEND_URL}/employees",
            json=payload,
            headers=self._headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return response.status_code, response.json()
