---
name: code-quality
description: Review or write production (framework) code against OOP design and code-literacy rules for this project. Use before committing framework code, when adding a class/module/client/judge, when a review is requested, or when code smells like a god object, an if-chain over providers, or a leaking abstraction.
---

# Code quality review

Applies to framework code under `core/`, `clients/`, `judges/`, `prompts/`, `reporting/`.
Test code → `test-design`. Report findings as `file:line — problem — fix`,
severity-ranked. No praise, no restating the code.

## OOP design

1. **Abstraction is a protocol, not a base class.** `Judge`, `ModelClient`, `Notifier`
   are `typing.Protocol`. Inherit only to share implementation; prefer composition.
   `HRClient(BaseClient)` is the sanctioned exception — `BaseClient` exists purely to
   share transport, which is what inheritance is for. Do not "improve" it into a protocol.
2. **Open/closed.** Adding a judge provider, a notifier, or an evaluated method must not
   edit existing code beyond config or a registry entry.
   `if provider == "openai": ... elif "anthropic"` is the defect this project exists to avoid.
3. **Dependency injection.** A class never constructs its own client, config, socket,
   clock, or file handle. Pass them in. If it can't be tested without `patch()`,
   the design is wrong.
4. **Single responsibility, measured by reasons to change.** A class that opens a
   websocket, composes a prompt, and posts to Slack has three.
5. **Layer purity.** Check imports against the table in CLAUDE.md. An SDK or `requests`
   import inside `core/` is a blocker.
6. **Value objects are frozen.** `@dataclass(frozen=True, slots=True)` for domain models.
   Mutable state lives in clients and the runner, not in the domain.
7. **Behaviour lives with data.** Anemic model + a `utils.py` of functions taking that
   model is a smell. Prompt composition belongs to a `PromptComposer`, not to a test.
8. **No inheritance deeper than 2**, no `isinstance` branching over your own hierarchy,
   no optional constructor args that switch a class into a different mode.

## Code literacy

- **English only.** Any Cyrillic character anywhere in the repository is a **blocker** —
  identifiers, comments, docstrings, log lines, error messages, docs, fixture and seed
  data, prompt files. No exceptions, including "temporary" ones.
- **Names**: intention-revealing. No `data`, `info`, `mgr`, `do_work`, `helper`, `tmp`,
  `resp2`. A name needing a comment is the wrong name.
- **Types**: full annotations on public signatures. No bare `dict` / `list` / `Any`
  crossing a boundary — a raw judge JSON must become a `Verdict` at the adapter edge.
  `Optional` only where `None` is a real domain state (backend context legitimately is).
- **Errors**: domain exceptions from `core`; never bare `except:` or
  `except Exception: pass`. A swallowed websocket or judge error becomes a silently
  wrong verdict — **blocker**.
- **No defensive code in the API client.** Client methods do not validate arguments,
  coerce types, check status codes or catch exceptions — they build the request and
  return the `Response`. Guarding there makes a backend defect indistinguishable from a
  client defect, and sending a deliberately wrong type is a legitimate test. This
  overrides the general "validate at the edge" instinct.
- **Resources**: websocket and HTTP sessions are context-managed or fixture-scoped with
  guaranteed teardown. A leaked connection between tests is a blocker.
- **Secrets**: API keys and wss URLs come from env/config only. A key, token, host, or
  real account number in source or in an Allure attachment is a blocker.
- **Comments** explain *why*. Delete commented-out code and ownerless TODOs.
- **Magic values**: timeouts, retry counts, strictness levels, pass thresholds, model
  names, URLs → named constants or config, never inline.
- **Functions**: one level of abstraction each; flag >30 lines or >3 nesting levels.
- **Duplication**: three occurrences means extract; two may be coincidence — say so.
- **Purity**: no I/O, no `print`, no `datetime.now()` in domain logic. Logging and
  injected clocks instead.

## Severity

- **Blocker** — wrong verdicts, swallowed errors, layer violation, leaked secret or
  connection, untestable design.
- **Major** — violates open/closed or SRP; will hurt at the next method or provider.
- **Minor** — naming, duplication, readability.

If the code is fine, say so in one line. Do not invent findings.
