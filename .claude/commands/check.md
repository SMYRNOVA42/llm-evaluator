---
description: Run lint and the offline test suite, then fix what breaks
---

1. `ruff check . --fix` (skip if ruff is not configured yet — say so)
2. `pytest tests/unit -q`

Never run `tests/eval` here — it hits the live model and costs money.

Report one line per step. Never delete a test, loosen an assert, or add
`# type: ignore` to make a step pass — fix the cause or stop and explain.
