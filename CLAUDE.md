# LLM Evaluator

Automated quality evaluation of an LLM assistant (HR self-service) via LLM-as-judge.
The deliverable **is a pytest suite**: a test sends a user phrasing to the model under
test over WebSocket, collects the answer, and asks a judge LLM to grade it against a
rubric + a method-specific prompt, optionally comparing with backend data.

Status: greenfield, rebuilt from the author's memory of a previous work project.
Portfolio project — design clarity and test quality are the point.

## Demo domain: HR assistant

**Two different things are called "method". Never conflate them.**

- **API method** — a backend endpoint. `GET /employees/{id}/vacation-balance`,
  `POST /employees`. Plain REST, deterministic, used by the evaluator as ground truth.
- **Assistant method** — a capability the model routes to. `vacation_balance`,
  `not_matched`. This is what the eval suite tests: did orchestration pick the right
  method, and is the answer for that method correct and well-formed.

Assistant methods today:

| Assistant method | Example phrasing | Backend data |
|---|---|---|
| `vacation_balance` | "how many vacation days do I have left?" | yes — `{all_days, vacation, sick_leave, additional}` |
| `add_employee` | "hire Grace Miller as a Backend Engineer" | yes — the directory, read back after the attempt |
| `not_matched` | "hi", "bye", "what is the weather today?" | no — fallback for greetings, farewells, out of scope |

`add_employee` is the one capability that **changes state**. Its tests verify the
consequence before the wording: read the directory, confirm the person exists (or does
not), and only then ask the judge about the sentence. An assistant can produce a perfect
confirmation while nothing happened, and no amount of judging the text will catch that.
Hiring is restricted to People & Culture, enforced by the backend with a 403 — not by the
assistant's prompt.

The assistant's reply carries the chosen method, so **routing is asserted in Python and
only the wording goes to the judge**.

## Demo stand — `stand/`, deliberately outside the evaluator package

Built and smoke-tested. See `stand/README.md` for endpoints, logins and run commands.

- **`stand/backend/`** (port 8001) — FastAPI: bearer auth, HR endpoints, in-memory
  storage behind an `HrRepository` protocol. `position` and `department` are integer ids
  into their own collections; an unknown id gives 422. `POST /_stand/reset` re-seeds.
- **`stand/assistant/`** (port 8000) — FastAPI `/ws`. Two-step orchestration: route the
  message to an assistant method, fetch backend data if that method needs it, then answer
  with the method's prompt. Both steps call **OpenAI**.

`python -m stand.healthcheck` reports whether both are up (exit 1 if not). It is a
liveness probe, not a test — anything that actually verifies behaviour goes into pytest.

So: SUT = OpenAI behind a WebSocket, judge = **Anthropic**. Different providers on
purpose — a model grading its own output has a self-preference bias.

The assistant's system prompts are intentionally plain. A suite that is always green
proves nothing; real failures on some phrasings are the demo. **Do not "fix" the stand
to make the suite pass** — the red tests are the product.

Rules: the evaluator imports nothing from `stand/` and never imports `openai`. The
assistant's `BackendGateway` and the evaluator's `ApiClient` stay separate classes — the
tests need a source of truth independent of the product's own data path.

## How the evaluator reaches things

```
test --ws--> stand/assistant --openai lib--> OpenAI
  '---http--> stand/backend                (ground truth)
```

The evaluator **never imports `openai`** and never calls a model vendor's SDK for the
assistant under test. It speaks WebSocket to whatever is at `MODEL_WS_URL`; today that is
the stand, tomorrow it could be a real product. `openai` is a dependency of `stand/` only.
The judge is the one and only vendor SDK the evaluator itself imports (`anthropic`).

## Backend client design

Written the way an automation engineer writes against a Swagger page, without seeing the
backend's source:

- **`BaseClient`** — transport only: `get`/`post`/`put`/`delete`, header building, base
  URL from env. Callers pass an endpoint, not a full URL.
- **`HRClient(BaseClient)`** — one method per API method, and nothing else. Inheritance
  here is deliberate: it shares implementation, which is what inheritance is for.
- **Endpoints are constants** in their own module, not string literals in methods.
- **Every client method returns the `Response` object**, never a parsed body. The test
  decides what it needs — `.json()`, `.status_code`, headers. Wrapping the response would
  hide backend failures behind evaluator failures.
- **No validation, no type coercion, no try/except in client methods.** Input validation
  is the backend's job; if the client sanitises input, a test can no longer tell a
  backend defect from a client defect. Sending a wrong type on purpose is a valid test.
- **Authentication happens in `__init__`**: `self.token = self.get_token()`, where
  `get_token` calls the auth endpoint and pulls the token string out of the response.
- Helper methods are allowed only for things the backend does not offer, such as
  filtering a list the API returns whole.

A test pulls what it needs out of the `Response` itself — there is no wrapper model.

`ModelClient` is the one client that raises. A dead socket, a timeout or an
`{"error": ...}` frame means no measurement happened, so it raises `AssistantUnavailable`
rather than returning something a judge could mistake for a bad answer. It imports that
exception from `evaluator.core.errors` so the whole project has a single infrastructure
taxonomy and a fixture needs one `except InfrastructureError`.

`ModelReply` exposes `.method` (asserted in the test) and `.payload()` (the final message
text, the only part the judge sees).

## Judge implementation notes

- Model: **`claude-sonnet-5`**, chosen deliberately — the judge runs once per phrasing,
  so Opus-tier cost adds up fast on a full suite. Judge and assistant stay on different
  vendors. Changing this model invalidates every stored verdict: results from two judges
  are not comparable, so re-baseline rather than mixing them.
- **Assistant prefill is removed on current Claude models and returns a 400.** The old
  "prefill an opening brace to force JSON" trick is gone. Get the `Verdict` JSON with
  structured outputs — `output_config={"format": {...}}` — so the schema is enforced by
  the API rather than requested in prose.
- The rubric therefore describes what the fields *mean*; it does not beg for valid JSON.
- Prompt composition order: `rubric.txt`, then the method file, then the tagged inputs
  (`<user_msg>`, `<ai_msg>`, `<expectation>`, `<backend_data>`, `<method>`).
- **The judge sometimes degenerates into a loop of closing braces**, runs into the token
  ceiling and returns unparseable JSON. Observed in real runs. That is the measuring
  instrument breaking, not the assistant answering badly, so it raises
  `JudgeUnavailable` and gets exactly one retry. This is the one retry the suite allows:
  it recovers a missing measurement, it never turns a red verdict green.

## Stack
Evaluator: Python · pytest · pytest-asyncio · `websockets` · `requests` · `anthropic` ·
Allure · Slack + Telegram notifications. Deps in `requirements.txt`.
Stand: FastAPI · uvicorn · `openai`. Deps in `stand/requirements.txt`.

Secrets (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) come from `.env` via `python-dotenv`.
`.env` is gitignored and never read outside config.

## Vocabulary
- **SUT** (system under test) — the assistant being evaluated. Non-deterministic:
  the same phrasing yields a different answer every run. It is the thing that may fail.
- **Judge** — an external LLM (OpenAI *or* Anthropic, one active at a time) that grades
  the SUT answer. Never both in parallel.
- **Rubric** — the always-sent part of the judge prompt: judge role, strictness level,
  cross-cutting criteria (tone, politeness, format, no hallucinated numbers).
- **Method prompt** — per-capability expectations, one file per assistant method.
  Lives in `prompts/back_tools/` when the capability is backed by backend data
  (`vacation_balance.txt`), or `prompts/tools/` when it is not (`not_matched.txt`).
  The folder is the answer to "does this method have ground truth".
- **Expectation** — `Expectation.ANSWER` (default) or `Expectation.DECLINE`, sent to the
  judge with everything else. It says what the assistant was supposed to *do*: serve the
  request, or refuse it. A `DECLINE` case has no backend data, and the rubric says so.

**`expectation` and positive/negative are two different axes. Do not conflate them.**

- *expectation* is about behaviour: should the assistant answer, or refuse?
- *positive/negative* is about routing: should this message land in this method at all?

For `not_matched` the two come apart clearly. An out-of-scope question is a **positive**
case for the method — this is exactly what the fallback is for — while its expectation is
**DECLINE**, because the assistant must refuse. The genuine negative for `not_matched` is
the opposite: a real HR question that must *not* fall back here. That test needs no judge
at all; a misroute is a defect whatever the reply says, and it fails before the judge is
billed.
- **Backend context** — optional live JSON from the product backend that the judge uses
  as ground truth. Fetched inside the test through an authenticated `ApiClient` fixture.
  Some methods have none (e.g. `not_matched`).
- **Verdict** — the judge's structured answer, always JSON:
  `{user_msg, ai_msg, verdict: bool, judge_comment}`. `verdict: false` fails the test;
  `judge_comment` is the evidence of what the SUT got wrong.

## Architecture — ports & adapters

Three top-level packages: `clients/` (talking to the product), `evaluator/` (judging it),
`stand/` (the product stand-in).

| Layer | Status | Responsibility |
|---|---|---|
| `clients/` | done | `BaseClient`, `HRClient`, `ModelClient`, `endpoints.py`, `config.py`. Its own package at the repo root, not inside the evaluator. |
| `evaluator/core/` | done | `Verdict`, `Expectation`, the exception taxonomy. Zero I/O, zero SDK imports. |
| `evaluator/judges/` | done | `Judge` protocol + `AnthropicJudge` on `claude-sonnet-5`, structured outputs. |
| `evaluator/prompt_composer.py` | done | Rubric into `system`, per-case tagged inputs into the user turn. |
| `evaluator/config.py` | done | The only place the environment is read. |
| `prompts/` | done | `rubric.txt` plus `back_tools/` and `tools/`. Root-level package of text, like `clients/`. |
| `evaluator/reporting/` | done | Allure attachments, `RunSummary` read from `allure-results`, message builder, `Notifier` protocol + `TelegramNotifier`, `python -m evaluator.reporting.notify`. |
| `tests/` | done | The evaluation suite, plus `conftest.py` with `client` / `hr_client` / `model` / `hr_model` / `judge` / `clean_backend`. Live by nature, `@pytest.mark.live`. There are no unit tests of the framework — do not add any. |
| `tests/test_judge_agreement.py` | done | Eleven human-labelled answers checked against the judge. The only file that tests the instrument, not the assistant. Needs no stand. |

`Verdict` binds the rubric's wire field `verdict` to the attribute `passed`, so call
sites read `verdict.passed`. The JSON contract the judge must produce is unchanged.
Infrastructure failures raise `InfrastructureError` subclasses and are reported as
errors, never as "the assistant answered badly".

Dependency rule: arrows point inward. `core` imports nothing from other layers.

## Language: English only

Every character written into this repository is English. No exceptions, anywhere:

identifiers · comments · docstrings · log and error messages · commit messages ·
documentation · seed and fixture data · prompt files, both the product's and the
judge's · user phrasings in test parameters · pytest ids · Allure titles ·
Slack and Telegram message templates.

This is not a style preference — the repository is a CV artefact read by people who do
not read Russian, and a single stray line breaks that. Conversation with the author
happens in Russian; the repository does not.

## Non-negotiables
- Data crossing a layer boundary inside the evaluator is a typed model, never a raw
  dict. The backend client is the deliberate exception: it returns `Response`, and the
  test converts what it needs into `BackendContext`.
- A test never builds a client, reads a prompt file, or picks a judge — fixtures do.
  Fixture names are `client` (backend), `model` (assistant under test), `judge`.
- `model.ask(msg)` returns a reply exposing `.method` (the assistant method it routed to)
  and `.payload()` (the final message text, nothing else). Routing is asserted in the
  test before the judge is called; the judge only ever sees `payload()`.
- Tests are plain functions. No test classes anywhere.
- Adding a method = new prompt file + new parametrized test. No framework change.
- Swapping the judge provider touches config only.
- Every eval test attaches to Allure **before asserting**: `attach_backend_data(...)`
  and `attach_verdict(verdict)`. The verdict JSON already carries the user message, the
  assistant's answer, the outcome, `judge_comment` and the judge model, so one
  attachment is the whole evidence chain. Attaching after the assert means the failures
  — the only results anyone opens — carry no evidence at all.
- One phrasing = one test. No aggregate threshold: if a phrasing's verdict is false,
  that test fails, so the report points at the exact wording the SUT mishandled.
- Backend data is fetched live inside the test (`client.get_x().json()`), never hardcoded.
- **Ground truth must be complete enough to adjudicate the answer.** A judge given less
  than the assistant legitimately knew will call a true statement invented. When a test
  cannot observe something the assistant saw, give the judge what it *can* read — the
  catalogue of valid values, say — so the claim is checkable.
- Tests that change state take the `clean_backend` fixture, which re-seeds before and
  after. No database to roll back, so the seed file is the rollback.
- `services_are_up` is **not** autouse: the client fixtures require it, so judge-only
  checks still run with the stand down — which is when you want them, right after editing
  a prompt.
- **Editing `rubric.txt`, a method prompt, or `JUDGE_MODEL` changes what every verdict in
  the suite means.** Run `pytest tests/test_judge_agreement.py` after any of the three.

## Skills
- `code-quality` — production code: OOP design + code literacy
- `test-design` — writing tests (both suites; they have different rules)
- `llm-eval-domain` — judge design, non-determinism, thresholds, prompts
