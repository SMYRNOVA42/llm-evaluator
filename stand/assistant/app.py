"""HR assistant of the demo stand, reached over WebSocket.

The evaluator connects here and knows nothing about what is behind the socket — that is
the point of the stand. Protocol:

    connect  ws://host/ws?token=<backend token>
    send     {"text": "How many vacation days do I have??"}
    receive  {"method": "vacation_balance", "text": "..."}
    on error {"error": "<reason>"}   -- infrastructure, not a bad answer
"""

import json

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI

from .backend_gateway import BackendGateway
from .config import REQUEST_TIMEOUT_SECONDS
from .orchestrator import Orchestrator

app = FastAPI(title="HR assistant (demo stand)")

INVALID_TOKEN = 4401
BAD_REQUEST = 4400


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness only. Does not call OpenAI, so it costs nothing to poll."""
    return {"status": "ok", "service": "assistant"}


@app.websocket("/ws")
async def chat(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=INVALID_TOKEN, reason="token query param is required")
        return

    await websocket.accept()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
        gateway = BackendGateway(token=token, client=http)
        try:
            employee = await gateway.whoami()
        except httpx.HTTPError:
            await websocket.close(code=INVALID_TOKEN, reason="backend rejected the token")
            return

        orchestrator = Orchestrator(AsyncOpenAI(), gateway, employee_id=employee["id"])
        try:
            while True:
                await _exchange(websocket, orchestrator)
        except WebSocketDisconnect:
            return


async def _exchange(websocket: WebSocket, orchestrator: Orchestrator) -> None:
    raw = await websocket.receive_text()
    try:
        user_message = json.loads(raw)["text"]
    except (json.JSONDecodeError, KeyError, TypeError):
        await websocket.send_json({"error": 'expected {"text": "..."}'})
        return

    try:
        reply = await orchestrator.handle(user_message)
    except Exception as error:  # noqa: BLE001 - reported to the client, never swallowed
        await websocket.send_json({"error": f"{type(error).__name__}: {error}"})
        return

    await websocket.send_json({"method": reply.method, "text": reply.text})
