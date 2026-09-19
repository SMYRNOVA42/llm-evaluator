---
description: Add a new evaluated method to the eval suite
argument-hint: "<method name, e.g. balances>"
---

Add evaluation for method: $1

Read `llm-eval-domain` and section B of `test-design` first.

Steps:
1. Ask me (briefly, batched) for: the expected answer contract, whether backend data is
   needed, and the pass threshold — unless I already said.
2. Write `prompts/methods/$1.txt`: contract, expected shape, backend-comparison rule.
3. Write `tests/eval/test_$1.py`: parametrized user phrasings with readable ids,
   fixtures for wiring, verdict assertion with a reason-carrying failure message,
   Allure attachments.
4. Change no framework code. If you cannot add the method without touching
   `core/`, `clients/`, or `judges/`, stop and tell me what the design is missing.
