# Demo stand

Two independent services that stand in for the product under evaluation.
The evaluator treats them as a black box and imports nothing from here.

```
stand/backend/     HR backend  — REST, token auth, in-memory storage (port 8001)
stand/assistant/   HR assistant — WebSocket /ws, routes + answers via OpenAI (port 8000)
```

## Run it yourself

From the project root, with the virtualenv active (`source .venv/bin/activate`):

```bash
pip install -r stand/requirements.txt
cp .env.example .env        # then put your OPENAI_API_KEY in it
```

Two terminals:

```bash
uvicorn stand.backend.app:app --port 8001      # 1: HR backend
uvicorn stand.assistant.app:app --port 8000    # 2: HR assistant
```

Then check both are answering:

```bash
python -m stand.healthcheck
```

It hits `GET /health` on each service and exits non-zero if either is down. It never
calls OpenAI, so polling it is free.

Stop the services with `Ctrl+C`, or `pkill -f "uvicorn stand."` if they run in the
background.

Exercise the backend by hand, without an OpenAI key:

```bash
curl -s -X POST localhost:8001/auth/token \
     -H 'Content-Type: application/json' \
     -d '{"login":"e.carter","password":"demo"}'

curl -s localhost:8001/employees/1/vacation-balance -H "Authorization: Bearer <token>"
```

Interactive API docs: <http://127.0.0.1:8001/docs>.

## Backend

**Credentials.** Every seeded employee shares the same password, `demo`, taken from
`STAND_PASSWORD` in `.env`. There is no user registry to look up — the stand issues a
token to any seeded login with that password.

| id | login | name |
|---|---|---|
| 1 | `e.carter` | Emily Carter |
| 2 | `m.brooks` | Michael Brooks |
| 3 | `a.reed` | Ashley Reed |

| Method | Endpoint | Notes |
|---|---|---|
| issue token | `POST /auth/token` | `{"login", "password"}` → bearer token |
| whoami | `GET /auth/me` | |
| list departments | `GET /departments` | |
| list positions | `GET /positions` | |
| list employees | `GET /employees` | the company directory, open to any authenticated caller |
| add new employee | `POST /employees` | `{full_name, date_of_birth, position, department}`; `position`/`department` are ids — an unknown one gives 422, a non-HR caller gets 403 |
| get vacation balance | `GET /employees/{id}/vacation-balance` | `{all_days, vacation, sick_leave, additional}` |
| reset | `POST /_stand/reset` | stand-only; re-seeds state between runs |
| health | `GET /health` | liveness, no auth |

Storage is in memory behind the `HrRepository` protocol — no database to run.
Swapping in SQLite means adding one class in `repository.py`.

## Assistant

```
connect  ws://127.0.0.1:8000/ws?token=<backend token>
send     {"text": "how many vacation days do I have left?"}
receive  {"method": "vacation_balance", "text": "..."}
error    {"error": "..."}          # infrastructure, never "the answer was bad"
```

Assistant methods (`stand/assistant/methods.py`) are capabilities of the model, not
backend endpoints: `vacation_balance` (needs backend data) and `not_matched`
(greetings, farewells, out of scope — the fallback).

The reply carries the chosen `method` so orchestration can be asserted in Python;
only the wording goes to the judge.

The system prompts here are intentionally plain. A suite that is always green proves
nothing — the assistant is meant to be fallible on some phrasings.

## Observed weaknesses (manual run, 2026-09-08)

Real defects seen on five English phrasings, every one of them routed correctly.
Recorded here as material for the judge's rubric — the eval suite is what will catch
them from now on:

- **Wrong language.** "do I still have sick days?" was answered in Spanish. The system
  prompt says to reply in the employee's language and the model simply did not.
- **Invented capabilities.** On an out-of-scope question the assistant offered help with
  "payroll, benefits, or employee policies" — none of which it can do.
- **Inconsistent format.** Markdown bullets in one answer, a single prose sentence in
  the next, for the same method.
- **Redundant framing.** "You have a total of 28 days off ... Currently, you have 21
  vacation days remaining" invites the reader to mistake the totals.

Routing and the figures were correct every time. This is the shape of the demo: assert
routing and numbers in Python, and let the judge catch language, scope, tone and format —
none of which a substring assert would ever have found.

## Caught by the eval suite (first run, 8 tests, 6 passed)

- **Routing breaks when the question follows a greeting.** "Hi, how many days can I
  reserve for my vacation?" routes to `not_matched` instead of `vacation_balance`.
  Caught by the routing assert, before any judge call.
- **Another employee's balance is answered with the caller's own figures.** Asked "How
  many vacation days does Michael Brooks have?", the assistant replied with employee 1's
  numbers presented as Michael Brooks's. Not merely bad wording — the wrong person's
  data under someone else's name, which no substring assert would detect.

**Capability overclaiming.** The assistant declines correctly and then names help it
cannot give - "benefits or pay information", "salary details or benefit policies". One
root defect, surfacing across the out-of-scope tests: the system prompt never states the
boundary of what the assistant can do, so the model fills the gap from its prior of what
an HR assistant usually does. A hallucination about its own feature list rather than
about the employee's data.

The rubric draws the line at specificity: naming a service it cannot perform is a false
statement and fails, while a vague friendly offer of help is courtesy and passes.

All of it is left unfixed on purpose. The stand is meant to be fallible.
