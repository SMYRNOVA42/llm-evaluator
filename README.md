# LLM Evaluator

A pytest suite that measures the answer quality of an LLM assistant, using another LLM
as the judge.

Each test sends one user phrasing to the assistant over WebSocket, takes the answer,
pulls the matching ground truth from the product backend, and asks a judge model to grade
the answer against a rubric. Routing and figures are asserted in Python; wording, tone and
scope are left to the judge. Evidence goes to Allure, a summary goes to Telegram.

**The suite is expected to be partially red.** The assistant under test is deliberately
fallible — red tests are findings, not breakage. What has been caught so far is listed in
[stand/README.md](stand/README.md).

## Layout

| Package | What it is |
|---|---|
| `stand/` | A tiny fake product, so there is something real to talk to. An HR backend (REST, port 8001) and an HR assistant (WebSocket, port 8000) that answers via OpenAI. Treated as a black box. |
| `clients/` | How the tests reach the product: `BaseClient` + `HRClient` over HTTP, `ModelClient` over WebSocket. |
| `prompts/` | `rubric.txt` (the judge's standing instruction) plus one file per assistant method, split into `back_tools/` (has backend ground truth) and `tools/` (does not). |
| `evaluator/` | The judging framework: domain models, the Anthropic judge, prompt composition, Allure attachments and the run report. |
| `tests/` | The evaluation suite itself. |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r stand/requirements.txt
cp .env.example .env
```

Then fill in `.env`:

| Variable | Needed for |
|---|---|
| `OPENAI_API_KEY` | the assistant under test |
| `ANTHROPIC_API_KEY` | the judge |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | the run report — optional |

Everything else has a working default.

## Start the stand

Two terminals:

```bash
uvicorn stand.backend.app:app --port 8001      # HR backend
uvicorn stand.assistant.app:app --port 8000    # HR assistant
```

Check both answer:

```bash
python -m stand.healthcheck
# UP    backend     http://127.0.0.1:8001  ok
# UP    assistant   http://127.0.0.1:8000  ok
```

Backend API docs: <http://127.0.0.1:8001/docs>. Logins and endpoints:
[stand/README.md](stand/README.md).

## Run the tests

```bash
pytest                              # everything
pytest -k vacation_balance          # one capability
pytest -k "not declines"            # skip the negative cases
pytest tests/test_not_matched.py    # one file
pytest -v                           # one line per phrasing
```

Every run costs money — one assistant call and one judge call per phrasing — and refuses
to start if the stand is down, rather than reporting a meaningless green.

Results are written to `allure-results/`, wiped at the start of each run so a report never
mixes two runs together.

## Check the judge itself

```bash
pytest tests/test_judge_agreement.py
```

Eleven answers whose quality a human has already decided — six that must fail, five that
must pass — run past the judge, and the verdicts are compared with those labels. It needs
no stand, because the answers are fixed: a judge cannot be measured against a
non-deterministic assistant, since a disagreement would not say which of the two was wrong.

Run it after editing `prompts/rubric.txt`, a method prompt, or `JUDGE_MODEL`. Those three
are the only things that can silently change what every other test in the suite means.
The set includes both sides of the calibration line the rubric draws — a vague friendly
sign-off must pass, naming a capability the assistant lacks must fail — so loosening one
without loosening the other shows up immediately.

## Read the report locally

Needs the Allure CLI: `brew install allure`.

```bash
allure serve allure-results
```

That builds a temporary report and opens it in the browser. To keep it:

```bash
allure generate allure-results -o allure-report --clean
allure open allure-report
```

Open a failed test to see its evidence: the backend data it was judged against, the user
message, the assistant's answer, the verdict and the judge's reason.

## Send the report to Telegram

```bash
python -m evaluator.reporting.notify
```

Reads the last run from `allure-results/` and posts pass/fail counts plus every failure
with the judge's reason. When all failures share one error it says so, instead of
presenting one root cause as N separate defects. When nothing passed at all it says the
environment is probably down — a different problem from a bad build, and not to be read
as one.

Set `REPORT_URL` to put a link to the published report in the message. CI sets it to the
GitHub Pages URL automatically.

Getting the credentials: a token from [@BotFather](https://t.me/BotFather); for the chat
id, send `/start@your_bot` in the group, then read `result[].message.chat.id` from
`https://api.telegram.org/bot<TOKEN>/getUpdates` — note `bot` and the token run together,
with no slash. Group ids are negative.

## Continuous evaluation

[`.github/workflows/evaluation.yml`](.github/workflows/evaluation.yml) runs the whole
thing on GitHub: it starts the stand, runs the suite, publishes the Allure report to
GitHub Pages and posts the summary to Telegram with a link to it.

It runs on Mondays at 06:07 UTC, and on demand from the Actions tab. It deliberately does
**not** run on push or pull request: this suite measures an LLM's answers, not the code.
It is slow, it costs money on every run, and it is expected to be partially red — none of
which belongs in a merge gate.

The schedule lives in the YAML, not in a settings page, so changing it is a commit — and
only the copy on the default branch is ever read. Two things about GitHub's cron are worth
knowing: it is UTC and ignores daylight saving, so a fixed local time drifts by an hour
twice a year; and **a scheduled workflow is disabled automatically after 60 days without
activity in the repository**. GitHub emails a warning first, and one commit re-arms it.

Two jobs. The stand lives inside the first one, next to the tests, because each job gets
a fresh machine and a service cannot outlive its job.

| Job | Does |
|---|---|
| `evaluate` | Starts the stand, runs the suite, uploads `allure-results` as an artifact. A red suite does not stop it. |
| `report` | Builds the Allure report, publishes it to Pages, sends the summary, and fails the run only when *nothing* passed. |

The published report is the last run and only the last run: each deployment replaces the
whole site, and nothing expires it. Older runs survive as the `allure-results` artifact on
their own workflow run, for 30 days.

That last rule is the point: a partially red suite is the product, so it must not fail the
workflow. A run where nothing passed at all means the environment never came up, and that
is a real failure worth a red build.

### Setting it up

Repository → Settings → Secrets and variables → Actions:

| Secret | For |
|---|---|
| `OPENAI_API_KEY` | the assistant under test |
| `ANTHROPIC_API_KEY` | the judge |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | the summary message |

Then Settings → Pages → Source: **GitHub Actions**. On a free plan, Pages only works for
public repositories — on a private one the publish step fails and the report stays
available as the workflow artifact instead.

## Stop the stand

`Ctrl+C` in each terminal, or:

```bash
pkill -f "uvicorn stand."
```

## The whole thing, start to finish

```bash
source .venv/bin/activate
uvicorn stand.backend.app:app --port 8001 &
uvicorn stand.assistant.app:app --port 8000 &

until python -m stand.healthcheck; do sleep 1; done

pytest
allure generate allure-results -o allure-report --clean
python -m evaluator.reporting.notify

pkill -f "uvicorn stand."
```
