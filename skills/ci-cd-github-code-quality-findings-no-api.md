---
name: ci-cd-github-code-quality-findings-no-api
description: "Fixing GitHub Code Quality (/security/quality) findings — a product distinct from CodeQL code-scanning, with NO public REST API. Use when: (1) a /security/quality/rules/py%2F... URL reports open findings, (2) deciding how to locate Code Quality violations when the code-scanning alerts API returns them empty, (3) reconciling ruff vs CodeQL semantic differences for py/unused-local-variable, py/unused-global-variable, py/repeated-import, py/import-and-import-from, py/empty-except, py/undefined-export, (4) a Copilot/AI-findings autofix PR fails to merge, (5) a Code Quality finding is a false positive and you must refactor working code to satisfy the analyser without changing behaviour."
category: ci-cd
date: 2026-05-21
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [github-code-quality, codeql, ruff, code-quality, static-analysis]
---

# GitHub Code Quality Findings — No Public API

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-21 |
| **Objective** | Locate and fix open GitHub Code Quality (`/security/quality`) findings when the code-scanning REST API reports them empty, distinguish real violations from false positives, and refactor code to satisfy the analyser without changing behaviour |
| **Outcome** | Confirmed Code Quality is a separate product from CodeQL code-scanning with no public REST API; established a reliable workflow (UI findings list + `ruff` reconstruction) and per-rule fix patterns; merged fixes for `py/import-and-import-from`, `py/repeated-import`, `py/empty-except`, `py/undefined-export`, `py/unused-local-variable`, and `py/unused-global-variable` |
| **Verification** | verified-ci — all fixes merged to `HomericIntelligence/ProjectHephaestus` `main` in PRs #428, #430, #423; CI green, 2320 unit tests pass |

## When to Use

1. A `/security/quality/rules/py%2F...` URL (or the **Code Quality** tab in the GitHub Security UI) reports open findings.
2. You need to decide how to locate Code Quality violations and `gh api repos/OWNER/REPO/code-scanning/alerts` returns them empty (or only shows unrelated code-scanning alerts).
3. You must reconcile `ruff` vs CodeQL semantic differences for `py/unused-local-variable`, `py/unused-global-variable`, `py/repeated-import`, `py/import-and-import-from`, `py/empty-except`, or `py/undefined-export`.
4. A Copilot / AI-findings autofix PR (branch `ai-findings-autofix/...`) fails to merge.
5. A Code Quality finding is a false positive and you must refactor working code to satisfy the analyser without changing behaviour — never delete code that is genuinely used.

## Verified Workflow

> **Verification level:** verified-ci — all fixes landed on `HomericIntelligence/ProjectHephaestus` `main` via PRs #428, #430, #423; full CI green, 2320 unit tests pass.

### Core facts

- **GitHub Code Quality is a separate product from CodeQL code-scanning.** The `/security/quality` UI tab is *not* the same as the code-scanning alerts surface. `gh api repos/OWNER/REPO/code-scanning/alerts` returns **only** code-scanning alerts (e.g. `actions/missing-workflow-permissions`) and shows **0** for Code Quality findings. There is **no public REST API** for Code Quality findings — `repos/.../code-quality/analysis` returns **404**.
- **Locate the violations yourself.** Two reliable methods:
  - (a) Ask the user to paste the findings list from the `/security/quality` UI — it gives exact `file:line`.
  - (b) Run `ruff`, whose rules approximately map to the CodeQL Code Quality rules (see mapping table below).
- **CRITICAL semantic difference:** `ruff` treats a leading-underscore name (`_major`, `_modified`, `_unused`) as *intentionally* unused and does **not** flag it. CodeQL's `py/unused-local-variable` **does** flag underscore-prefixed names. A clean `ruff` run is therefore **not proof** that the Code Quality rules are satisfied.
- **CodeQL scoping for `py/repeated-import` is narrower than naive scans assume.** A single module-level `import X` *plus* a function-local `import X` inside a function **is** flagged by `py/repeated-import`. But two function-local `import X` statements in two **different** functions are **not** flagged. Docstring `import` examples are never violations. Always verify a suspected violation against the actual UI finding rather than guessing CodeQL scoping.

### Quick Reference

```bash
# 1. Code Quality findings are NOT in the code-scanning API — this returns only code-scanning alerts
gh api repos/OWNER/REPO/code-scanning/alerts            # 0 Code Quality findings
gh api repos/OWNER/REPO/code-quality/analysis           # 404 — no public API

# 2. Get the real findings: ask the user to paste the /security/quality UI list (gives file:line),
#    OR reconstruct approximately with ruff (NOT authoritative — see semantic gap below):
ruff check --select F811,F841,F822,S110,SIM105 hephaestus/ tests/

# 3. Fix per rule (see patterns below), then verify behaviour is unchanged:
pixi run pytest tests/unit          # all 2320 tests must pass

# 4. If an AI-autofix PR's check fails, first check the branch is not behind main:
gh api repos/OWNER/REPO/pulls/N/update-branch -X PUT
```

### Per-rule fix patterns

- **`py/import-and-import-from`** — a module imported both `import X` / `import X as Y` *and* `from X import ...`. Fix: consolidate to **one** form. E.g. drop `from datetime import timezone` and use `dt.timezone.utc`; drop `from contextlib import contextmanager` and use `@contextlib.contextmanager`.
- **`py/repeated-import`** — remove the redundant function-local `import X` when `X` is already imported at module level.
- **`py/empty-except`** — replace `try: <body> except X: pass` with `with contextlib.suppress(X): <body>` — behaviour-identical, idiomatic, clears the finding. Verify the try-body's control flow (early `return` inside the body, fallthrough after) is preserved.
- **`py/undefined-export`** — `__all__` lists names with no static definition (common with PEP 562 `__getattr__` lazy loading). Fix **without** breaking laziness: add module-level annotation-only declarations (see snippet in Results & Parameters).
- **`py/unused-local-variable` from tuple-unpacking of a side-effect call** — if the function is called only to validate (raises on bad input), call it **without** binding the result. If it is a test that discards a return whose value the test's own comment claims to check, fix the test to actually `assert` on the return — a genuine test-quality improvement, not just silencing.
- **`py/unused-global-variable` false positives** — CodeQL flagged `_shutdown_requested` (genuinely read inside a nested signal-handler closure via `global`) and `_CLAUDE_IMPL_TIMEOUT` (genuinely imported + asserted by another module's tests). Deleting either breaks working code/tests. Refactor to satisfy the analyser **without** behaviour change:
  - (a) Wrap the closure-mutated flag in a single-element list so the closure mutates `flag[0]` instead of rebinding a `global` — CodeQL's flow analysis then tracks it.
  - (b) Add a module `__all__` declaring the constant as public API — a legitimate "this is exported" signal CodeQL respects.

### Stale AI-autofix PR that will not merge

- A Copilot / AI-findings autofix PR (branch `ai-findings-autofix/...`, title "Potential fix for N code quality finding") failed its `security/dependency-scan` required check. **Root cause:** the PR branch was 2 commits **behind** `main` and ran `pip-audit` against a stale dependency tree (an old vulnerable `idna` that `main` had already bumped). **Fix:** `gh api repos/OWNER/REPO/pulls/N/update-branch -X PUT` to merge current `main` into the PR branch; CI re-runs on the new head and the check passes. **Lesson:** when an autofix PR's check fails, first check whether the branch is behind `main` before assuming the diff itself is broken.
- AI-autofix PRs are created with only boilerplate bodies and **no** `Closes #N` line, so a `pr-policy`-style gate fails them. Fix: create a tracking issue, then `gh pr edit N --body` to add `Closes #<issue>`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Queried `gh api repos/.../code-scanning/alerts` to enumerate Code Quality findings | Returns only CodeQL code-scanning alerts; Code Quality findings are a different product with no overlap | Code Quality has no REST API — get findings from the `/security/quality` UI or reconstruct via ruff |
| 2 | Trusted a clean `ruff check --select F841,F811` as proof the Code Quality rules were satisfied | ruff ignores leading-underscore names; CodeQL py/unused-local-variable flags `_major`/`_modified` anyway | ruff and CodeQL Code Quality have different semantics — a clean ruff run is not proof |
| 3 | An Explore agent listed 35 py/repeated-import "violations" by flagging every function-local and docstring-example import | py/repeated-import only flags re-importing within the same/overlapping scope, not once-per-function imports | Verify suspected violations against the actual UI finding; do not guess CodeQL scoping |
| 4 | Considered deleting `_shutdown_requested` / `_CLAUDE_IMPL_TIMEOUT` flagged as unused-global | Both are genuinely used (closure read; cross-module test assertion) — deletion breaks behaviour/tests | Some unused-global findings are false positives; refactor to satisfy the analyser, never delete used code |
| 5 | First instinct on an unfixable transitive CVE was `--ignore-vuln` | User rejected silent suppression | Suppression is a last resort; fix the root cause or document explicitly why no fix exists |

## Results & Parameters

### ruff ↔ CodeQL Code Quality rule mapping

| CodeQL Code Quality rule | Approx. ruff rule(s) | Notes |
|--------------------------|----------------------|-------|
| `py/repeated-import` | `F811` | ruff misses function-local re-imports of a module-level name; CodeQL flags them |
| `py/import-and-import-from` | `F811` | Same module imported both `import X` and `from X import ...` |
| `py/unused-local-variable` | `F841` | **Semantic gap:** ruff ignores `_`-prefixed names, CodeQL flags them |
| `py/unused-global-variable` | *(no ruff rule)* | Must rely on the UI findings list |
| `py/undefined-export` | `F822` | `__all__` entry with no static definition |
| `py/empty-except` | `S110` / `SIM105` | `except: pass` — fix with `contextlib.suppress` |

A clean `ruff` run is **not** authoritative for Code Quality — always cross-check the `/security/quality` UI.

### Annotation-only `__all__` pattern (`py/undefined-export` with PEP 562 lazy loading)

When `__all__` lists names provided lazily via `__getattr__`, declare them with annotation-only statements. With `from __future__ import annotations` the annotation is **never evaluated**, creates **no runtime attribute**, and `__getattr__` still fires on first access:

```python
from __future__ import annotations

from typing import Callable

__all__ = ["slugify"]

# Annotation-only declaration: satisfies py/undefined-export's static check,
# but creates NO runtime attribute, so PEP 562 __getattr__ lazy loading still works.
slugify: Callable[..., str]


def __getattr__(name: str):
    if name == "slugify":
        from hephaestus.utils.text import slugify as _impl
        return _impl
    raise AttributeError(name)
```

Verified at runtime: the declared names are **not** in `vars(module)` before first access, so laziness is preserved.

### Single-element-list closure refactor (`py/unused-global-variable` false positive)

CodeQL's flow analysis does not see a `global` flag mutated inside a nested closure as "used". Wrap the flag in a one-element list so the closure mutates an element instead of rebinding a global:

```python
# Before — CodeQL flags `_shutdown_requested` as unused-global (false positive):
_shutdown_requested = False

def install_handler():
    def _handler(signum, frame):
        global _shutdown_requested
        _shutdown_requested = True   # rebinds the global; CodeQL loses the data flow
    signal.signal(signal.SIGINT, _handler)

# After — behaviour-identical, CodeQL tracks the mutation:
_shutdown_requested = [False]

def install_handler():
    def _handler(signum, frame):
        _shutdown_requested[0] = True   # mutates an element; flow analysis tracks it
    signal.signal(signal.SIGINT, _handler)
```

For a constant genuinely consumed by another module's tests, the simpler fix is to add a module `__all__` declaring it public:

```python
__all__ = ["_CLAUDE_IMPL_TIMEOUT"]   # legitimate "this is exported" signal CodeQL respects
```

### Update a stale AI-autofix PR branch

```bash
# Merge current main into the PR branch so its required checks (e.g. security/dependency-scan)
# re-run against the up-to-date dependency tree:
gh api repos/OWNER/REPO/pulls/N/update-branch -X PUT
```

### Key parameters

- **Never** trust `gh api .../code-scanning/alerts` as a Code Quality inventory — it covers a different product.
- **Never** delete a name flagged `py/unused-*` without confirming it is not used by a closure or another module's tests.
- **Always** re-run the full unit suite (`pixi run pytest tests/unit`) after a Code Quality fix to prove behaviour is unchanged.
- Suppression (`--ignore-vuln`, `# noqa`) is a last resort — fix the root cause or explicitly document why no fix exists.

## Related Skills

- `ci-cd-failure-diagnosis-log-analysis` — general CI failure triage when a required check fails for a non-obvious reason.
- `ci-cd-dependabot-conflict-resolution-pattern` — branch-behind-main / stale-dependency-tree handling for dependency PRs.
