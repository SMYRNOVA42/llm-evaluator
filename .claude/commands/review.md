---
description: Review production code for OOP design and code literacy
argument-hint: "[path, or empty for uncommitted changes]"
---

Review framework code using the `code-quality` skill. Also load `llm-eval-domain`
if the code touches judges, prompts, verdicts, or thresholds.

Target: $1 — if empty, review uncommitted changes (`git diff HEAD`; if not a git repo
yet, review the source tree).

Output only the severity-ranked findings (`file:line — problem — fix`).
Fix nothing unless I ask.
