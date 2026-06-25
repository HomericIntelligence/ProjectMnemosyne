---
name: python-protocol-stub-ellipsis-not-pass
description: "Convention + planning pattern for the S4 lint nitpick of replacing `pass` with `...` (Ellipsis) in Python typing.Protocol / abc / .pyi method stub bodies. Use when: (1) a lint/audit nitpick asks to change empty Protocol/ABC/stub method bodies from `pass` to `...`, (2) planning any mechanical multi-occurrence token replacement where the token repeats and you must anchor each edit unambiguously, (3) you need an AST-based acceptance check that no Protocol method body still contains an ast.Pass node (more robust than `grep pass`), (4) you want the in-repo precedent rule: grep the SAME package for the existing idiom before importing an external style preference. Headline: in Protocol/stub bodies `...` is the canonical interface marker and `pass` is a runtime-statement smell, but the two are behaviorally identical (bodies never execute under structural typing) so it is purely a readability nitpick — anchor edits on the unique preceding docstring, verify with AST not grep, and mark verification verified-local (ruff/pytest/mypy were reasoned-not-run)."
category: architecture
date: 2026-06-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: ["protocol", "typing", "ellipsis", "stub-body", "pass-vs-ellipsis", "pep8", "lint-nitpick", "ast-verification", "edit-anchoring", "in-repo-precedent", "dry", "pola"]
---

# Python Protocol Stub Bodies: `...` Not `pass`

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-24 |
| **Objective** | Capture the durable convention + planning pattern behind an S4 lint nitpick: replace `pass` with `...` (Ellipsis) in Protocol method stub bodies (ProjectHephaestus issue #1546) |
| **Outcome** | Convention is well-established and the AST acceptance check is sound; the ProjectHephaestus #1546 application is **plan-stage / unverified** — the specific ruff/pytest/mypy commands in the plan were NOT executed this session |
| **Verification** | verified-local — convention + AST check are sound; the repo-specific lint/test run was reasoned, not executed |

> **Warning (honesty gate):** The convention itself is verified-local (well-established
> idiom, AST check is correct). The application to ProjectHephaestus #1546 is plan-stage:
> ruff-clean, pytest-clean, and mypy-clean were *assumed from convention, not run* in the
> session that produced this skill. Treat the "Verified Workflow" below as verified for the
> convention and acceptance check only — re-run the repo's actual lint/test suite before
> claiming the #1546 edit is done.

## When to Use

- A lint/audit/review NITPICK (severity S4 / cosmetic) asks to change empty `typing.Protocol`,
  `abc.ABC`, or `.pyi` method bodies from `pass` to `...`.
- You are planning a mechanical replacement where the token to change (`pass`) repeats many
  times in one file and a blind `replace_all` would be ambiguous or over-broad.
- You want an acceptance check that survives false matches — e.g. the substring "pass" inside
  an identifier (`bypass`), a string literal, or a `passlib` import.
- Before relying on any code-style convention, to confirm the SAME package already follows it
  (in-repo precedent) rather than importing an external preference.

## Verified Workflow

### Quick Reference

```bash
# 1. Find the in-repo precedent for the idiom BEFORE planning the edit
grep -n '^class \w\+(Protocol)' path/to/pkg/*.py     # locate sibling Protocols
# inspect a sibling that already uses `...` — that is your in-repo precedent (DRY/POLA)

# 2. AST acceptance check: no Protocol method body contains an ast.Pass node
python -c "import ast,sys; t=ast.parse(open(F).read()); \
cls=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='PlannerHost'); \
bad=[f.name for f in cls.body if isinstance(f,ast.FunctionDef) and any(isinstance(s,ast.Pass) for s in f.body)]; \
sys.exit(1 if bad else 0)"
```

### Detailed Steps

1. **Establish the convention.**

   In `typing.Protocol` (and `abc`/`.pyi` stub) method bodies, the idiomatic empty body is
   `...` (Ellipsis), not `pass`. `pass` reads as "intentionally empty *runtime* statement";
   `...` is the canonical stub/interface marker. Protocol method bodies are never executed
   (structural typing resolves conformance), so the two are **behaviorally identical** — this
   is purely a readability/idiom nitpick, never a correctness fix. Do not over-state its
   severity.

   ```python
   # No docstring: inline ellipsis is canonical
   class PlannerHost(Protocol):
       def plan(self, task: str) -> Plan: ...

   # With a one-line docstring: keep the docstring, put `...` on its own line
   class PlannerHost(Protocol):
       def plan(self, task: str) -> Plan:
           """Produce a plan for the given task."""
           ...
   ```

2. **Find the in-repo precedent BEFORE importing an external style.**

   Grep the SAME package for the existing pattern to follow rather than asserting a preference
   from outside the repo (DRY / POLA). In this session a sibling Protocol already used inline
   `...`, which made it the authoritative in-repo precedent — the edit conforms the file to
   its own package, not to a foreign style guide.

   ```bash
   grep -n '^class \w\+(Protocol)' path/to/pkg/*.py
   ```

3. **Anchor each edit on the UNIQUE preceding line, not a blind `replace_all`.**

   For a mechanical multi-occurrence replacement where `pass` repeats, do NOT `replace_all`
   the token — anchor each edit on the unique line immediately preceding it (typically the
   method's one-line docstring). Each edit is then unambiguous and scoped to exactly one
   method. Never hard-code line numbers in the anchor: the exact lines (e.g. 109/121/125/140/
   154 in this session) are point-in-time and drift as the file changes — anchor on the
   docstring TEXT instead.

4. **Use an AST-based acceptance check, not `grep pass`.**

   Parse the module, locate the Protocol `ClassDef` by name, and assert no method body
   contains an `ast.Pass` node. This won't false-match the substring "pass" in identifiers
   (`bypass`), imports (`passlib`), or string literals — which a `grep -n pass` would.

   ```bash
   python -c "import ast,sys; t=ast.parse(open(F).read()); \
   cls=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='PlannerHost'); \
   bad=[f.name for f in cls.body if isinstance(f,ast.FunctionDef) and any(isinstance(s,ast.Pass) for s in f.body)]; \
   sys.exit(1 if bad else 0)"
   ```

5. **Run the repo's real lint/test suite before claiming done (NOT done this session).**

   The plan assumed ruff (`D`/`B`/`SIM`/`RUF` selected) does not flag docstring-then-`...`,
   and that no test asserts on the stub body. Both were reasoned, not executed. Close the gate
   by actually running:

   ```bash
   pixi run ruff check path/to/pkg/module.py
   pixi run pytest tests/ -q
   pixi run mypy path/to/pkg/module.py
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Blind `replace_all` of `pass` → `...` | Considered replacing every `pass` token in the file at once | `pass` recurs across multiple methods (and can appear in unrelated bodies); a single global replace is ambiguous and can hit code that should keep `pass` | Anchor each edit on the unique preceding docstring line; one scoped edit per method |
| Hard-coding line numbers in the edit anchor | Plan referenced specific lines (109/121/125/140/154) for each `pass` | Line numbers are point-in-time and drift as soon as any earlier edit lands | Anchor on the docstring TEXT, never on a line number |
| `grep pass` as the acceptance check | Considered `grep -n pass module.py` to confirm no stub body still uses `pass` | `grep` false-matches the substring "pass" in identifiers, imports, and strings (`bypass`, `passlib`) | Use an AST check that walks the Protocol ClassDef and looks for `ast.Pass` nodes |
| Claiming ruff/pytest/mypy clean | Reasoned that docstring-then-`...` passes ruff and no test asserts the stub body (tests grep showed only `.pyc` binary matches) | Neither ruff nor the test suite was actually run; a grep over compiled bytecode is a weak signal | Mark verification verified-local at most and state plainly that the lint/test run was assumed; run the real suite before claiming the edit is complete |

## Results & Parameters

### Convention summary

| Context | Empty body idiom | Rationale |
|---------|------------------|-----------|
| `typing.Protocol` method, no docstring | `def f(self) -> T: ...` | inline `...` is the canonical interface marker |
| `typing.Protocol` method, with docstring | docstring line, then `...` on its own line | keep the docstring; `...` marks the empty stub body |
| `abc.ABC` / `.pyi` stub | `...` | same idiom; bodies are not executed |
| Behavioral effect of `pass` vs `...` | identical | Protocol bodies never run under structural typing — this is readability only |

### Acceptance-check parameters

| Parameter | Value |
|-----------|-------|
| `F` | path to the module file under test |
| Protocol class name | the `ClassDef` name to assert on (e.g. `PlannerHost`) |
| Pass node | `ast.Pass` — presence in any method body = failure (exit 1) |
| Robustness vs `grep` | no false match on `bypass`, `passlib`, or "pass" in string literals |

### Risks recorded for the reviewer

- **ruff clean: assumed, not run.** `D`/`B`/`SIM`/`RUF` selectors were reasoned to permit
  docstring-then-`...`; this was never executed in-session.
- **No test asserts the stub body: weak signal.** Verified only by a grep of `tests/` that
  returned `.pyc` binary matches — a grep over compiled bytecode is not a substitute for
  running the suite.
- **Line numbers drift.** Never embed the point-in-time line numbers in the edit anchor.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1546 — S4 lint nitpick, `pass` → `...` in Protocol stub bodies | Plan-stage / unverified: convention + AST check sound; repo ruff/pytest/mypy NOT run this session |

## References

- [python-abc-protocol-contract-test-regression.md](python-abc-protocol-contract-test-regression.md) — Implementation-phase ABC/Protocol enforcement patterns
- [architecture-ocp-dip-abc-protocol-planning-risks.md](architecture-ocp-dip-abc-protocol-planning-risks.md) — Planning risks when introducing Protocol/ABC abstractions
- [planning-audit-doc-nitpick-stamp-and-document.md](planning-audit-doc-nitpick-stamp-and-document.md) — Sibling pattern for handling cosmetic audit nitpicks conservatively
