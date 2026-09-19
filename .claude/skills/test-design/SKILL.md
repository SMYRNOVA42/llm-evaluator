---
name: test-design
description: Design and write tests for this project with an automation-QA lens - the exact test shape required here (plain functions, fixtures, parametrized phrasings, judge verdict), what to cover per assistant method, and what to flag when reviewing tests. Use whenever writing, reviewing, or fixing tests, or when asked what to cover.
---

# Test design

Read `llm-eval-domain` alongside this.

## The shape of a test

```python
@pytest.mark.parametrize("msg", [
    "How many vacation days do I have left?",
    "Do I still have any sick days left?",
    "Hi, how many days can I reserve for my vacation?",
])
def test_get_vacation_balance_positive(msg, client, model, judge):
    vacation_days = client.vacation_balance()

    answer = model.ask(msg)
    assert answer.method == "vacation_balance"

    verdict = judge.verdict(
        backend_json=vacation_days,
        prompt="prompts/methods/vacation_balance.txt",
        user_msg=msg,
        llm_answer=answer.payload(),
    )
    assert verdict.passed
```

Rules this shape encodes — follow them exactly:

1. **Plain functions. No test classes**, ever. No shared setup between tests.
2. **Tests are independent.** Any order, any subset, in parallel. Nothing carries over.
   Mutating endpoints re-seed the stand rather than relying on what a previous test left.
3. **Everything comes from a fixture**: `client` (backend, already authenticated),
   `model` (assistant under test), `judge`. A test never constructs a client, opens a
   socket, reads a prompt file or picks a provider.
4. **`@pytest.mark.parametrize("msg", [...])`** over real user phrasings, one per line.
   One phrasing = one test = one Allure result. Do not fold several methods into one test.
5. **Test names say method and polarity**: `test_get_vacation_balance_positive`,
   `test_not_matched_out_of_scope`.
6. **English only** — phrasings, names, ids, assertion messages.
7. The body reads top to bottom as: fetch ground truth → ask the model → judge → assert.
   No branching, no loops, no try/except.
8. **Assert routing before calling the judge.** `answer.method` must be the expected
   assistant method. Wrong routing fails immediately and costs nothing — there is no
   point paying a judge to grade an answer to the wrong question.
9. **`payload()` is the final message text and nothing else** — that is what the judge
   grades. The chosen method is `answer.method`, and it is never shown to the judge:
   a judge told which method was picked starts justifying the answer against it.
10. **Attach evidence before you assert.** `attach_verdict(verdict)` and
    `attach_backend_data(...)` go *above* `assert verdict.passed` — anything below it
    never runs on a failure, which is the only result anyone opens the report for.
11. **Assert the verdict**, and let the failure message carry `judge_comment`.
12. Never assert the assistant's exact wording. Deterministic facts (routing, figures)
    are asserted directly; everything else is the judge's job.
13. **Infrastructure failure is not a quality failure.** A timeout, a 429 or a dead
    backend raises an `InfrastructureError` and reports as an error, not as a bad answer.
    Never retry an eval test to turn it green.

There are **no unit tests of the framework** in this project — the eval suite is the
suite. Do not add a `tests/unit/` directory.

## Allure

Decorate every test: `@allure.epic`, `@allure.feature`, `@allure.story`,
`@allure.testcase("HR-00N")`, `@allure.severity(...)`, and `@allure.title` with the
`{msg}` placeholder so each phrasing is named in the report.

## Coverage per assistant method

Two independent axes — keep them straight:

- **expectation** (`ANSWER` / `DECLINE`) — what the assistant should *do* with the message.
- **positive / negative** — whether the message should route to this method at all.

They cross. An out-of-scope question is positive for `not_matched` and `DECLINE` at the
same time. Per method, cover:

- Several natural phrasings, including a colloquial one and one that buries the question
  inside a greeting.
- Every expectation the method can legitimately produce.
- The negative side: phrasings that must *not* route here. No judge call — a misroute is
  a defect regardless of the wording, so assert the method and stop.
- Where the method has ground truth, a case whose figures must match the backend.

## Reviewing existing tests

Flag: test classes; tests that pass when the feature is deleted; asserts on
implementation details; `try/except` swallowing failures; conditionals or loops in test
bodies; order dependence; `sleep()`; a test that builds its own client or reads a prompt
file; a retry added to make a red test green.
