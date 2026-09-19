---
name: llm-eval-domain
description: Domain rules for this LLM evaluator - judge design and its biases, rubric and method prompts, non-determinism, pass thresholds, backend ground truth, reporting. Use when adding or changing a judge, a prompt, a method under evaluation, thresholds, or any test involving model output.
---

# LLM-evaluator domain

## The evaluation loop

```
user phrasing ──wss──> SUT ──> answer
                                  │
backend JSON (optional) ──────────┤
rubric.txt + methods/<m>.txt ─────┤
                                  ▼
                            Judge (OpenAI | Anthropic) ──> Verdict JSON
```

## Prompts

- **English only**, like the rest of the repository — rubric, method prompts, and the
  user phrasings they are exercised with.
- **`rubric.txt`** is sent every time. It states: the judge's role ("you are an evaluator,
  not an assistant — do not answer the user"), the strictness level, the output format,
  and cross-cutting criteria (tone, politeness, language, format, no invented numbers).
- **`methods/<method>.txt`** states the method's contract, the expected answer shape, and
  whether backend data must be compared. One file per method; file name = method name.
- Prompts are **versioned** (hash or explicit version in the file). Changing a prompt
  invalidates historical results — the report must say so, not silently diff.
- Composition happens in one place (`PromptComposer`), never inline in a test.
- Backend block is included only when context exists. Absent context must produce a
  prompt that says "no backend data for this method", not a dangling empty section.

## Judge — treat it as a system under test, not an oracle

Biases to design against and to name in review:
- **Position bias** — in pairwise comparison the first option wins more often.
  Mitigation: run both orders; keep the result only if consistent.
- **Verbosity bias** — longer answers score higher. Put length expectations in the rubric.
- **Self-preference** — a model prefers its own outputs. Judge provider should differ
  from the SUT's; record both model ids in every verdict.
- **Scale compression** — a 1–10 scale collapses to 7–9. Prefer a short scale with
  written anchors per level, or a boolean per criterion plus an aggregate.
- **Sycophancy to the prompt** — a rubric that says "check politeness" nudges toward
  "polite". Ask for evidence quoted from the answer, not just a score.

Design rules:
- Judge output is **structured JSON**, validated at the adapter edge into a `Verdict`:
  `{user_msg, ai_msg, verdict: bool, judge_comment: str}`. The rubric states this schema.
  A parse failure is an `error` outcome — never a silent fail or a silent pass.
- `judge_comment` is mandatory and must quote or point at what the answer got wrong.
  An empty comment on `verdict: false` means the rubric is underspecified — fix the rubric.
- Extra metrics may be added to the JSON later; the parser must ignore unknown fields
  rather than break.
- Judge calls get retries with backoff for 429/5xx; exhausted retries = infrastructure
  error, distinct from a quality failure.
- A malformed or truncated judge response is the same category: the judge malfunctioned
  and produced no verdict, so retry it once and report it as infrastructure. Retrying a
  *verdict* is forbidden; retrying a *failed measurement* is required.
- The judge itself needs **meta-evaluation**: a small human-labelled set of
  (query, answer, expected verdict), reported as agreement with the human labels.
  An unvalidated judge is an opinion. In this project that lives in
  `tests/test_judge_agreement.py`; keep it in step with every rubric change, and keep both
  polarities in it — a judge that fails everything scores perfectly on an all-bad set.
- Swapping OpenAI → Anthropic changes results. Re-baseline; never compare across judges.

## Testing an action, not an answer

When a capability changes state, the sentence is the lesser half of the test.

1. Verify the **consequence** first, from the backend: did the record appear, change, or
   correctly fail to appear?
2. Only then ask the judge about the wording.

The defect this ordering exists to catch is a confident report of success for something
that never happened. The text looks flawless, so a judge grading text alone passes it.

Give the judge enough ground truth to adjudicate. If the assistant saw something the test
cannot — the body of a failed write, say — the judge will read a true statement as
invented. Hand it what the test *can* read, such as the catalogue of valid values, so the
claim becomes checkable. A failing test always deserves the question: is the assistant
wrong, or was my evidence too narrow?

## Backend ground truth

- Fetched per test case, kept as a typed `BackendContext`, passed to the judge as data
  the answer must be consistent with.
- Numeric comparison is the judge's weakest skill. Where the check is "the numbers match",
  do it deterministically in Python and give the judge the *result*; let the judge grade
  wording, completeness, and format.
- Backend data is live and changes between runs — never hardcode expected balances.
- Mask account identifiers and personal data before attaching anything to Allure.

## Non-determinism

- The SUT gives a different answer to the same phrasing every run. Never assert exact text.
- **One phrasing = one independent test.** `verdict: false` fails that test. There is no
  "N of M passed" aggregate — the value of the suite is knowing *which wording* broke it.
- Consequence: the suite is expected to be partially red, and that is a result, not a
  flake. Do not add retries to make an eval test green — a retry hides the finding.
  Retries exist only for infrastructure errors (429, timeout, dropped connection).
- A phrasing failing across several runs is a real defect; one failing once is a signal.
  That judgement belongs to the human reading the report, not to the code.

## Reporting

- Allure per phrasing, with the full evidence chain attached.
- Aggregate per method **and** per criterion — an overall mean hides one broken method.
- Slack/Telegram summary: pass rate per method, list of failed phrasings with judge
  reasons, run metadata (SUT version, judge model, prompt versions, timestamp), link to
  the Allure report. Notification failure must never fail the run.
