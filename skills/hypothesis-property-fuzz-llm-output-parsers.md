---
name: hypothesis-property-fuzz-llm-output-parsers
description: "EXECUTED procedure (verified-local) + pitfalls for adding Hypothesis property-based / fuzz tests for LLM-output string parsers in a pixi+pyproject dual-manifest Python repo. Use when: (1) adding property/fuzz tests for parsers that ingest free-form LLM output (verdict markers, ```json fences, bold/CRLF noise), (2) the goal is to assert a parser's FAIL-SAFE CONTRACT (never-raises + typed default) rather than parsed values, (3) you must add a new test/dev dependency (e.g. hypothesis) and need it in BOTH pyproject.toml [project.optional-dependencies].dev AND pixi.toml [feature.dev.dependencies] (conda path is what `pixi run test` uses), (4) deciding whether a new dep triggers a floor-consistency guard, (5) composing st.text() with crafted fragments so Hypothesis reaches structured parser branches, (6) deciding to append a Test<Parser>Properties class vs create a new _property sibling test file. RELATED but distinct: llm-output-verdict-parse-last-line-not-substring (parser CORRECTNESS, not fuzz-test planning) and dependency-manifest-single-source-of-truth (manifest alignment)."
category: testing
date: 2026-06-30
version: "1.1.0"
user-invocable: false
verification: verified-local
history: hypothesis-property-fuzz-llm-output-parsers.history
tags:
  - hypothesis
  - property-based-testing
  - fuzz-testing
  - llm-output-parsing
  - pixi
  - pyproject
  - dual-manifest
---

# Hypothesis Property/Fuzz Tests for LLM-Output Parsers

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Objective** | Add Hypothesis property-based / fuzz tests for four LLM-output string parsers (`parse_review_verdict`, `_parse_coordinator_results`, `latest_verdict`, `_parse_addressed_block`) and add `hypothesis` to dev/test deps — ProjectHephaestus issue #1470. |
| **Outcome** | EXECUTED end-to-end (verified-local). 14 new property tests added across 4 parsers; full automation suite green; PR CI pending at capture. |
| **Verification** | verified-local — executed end-to-end locally; PR CI not yet merged at capture. |
| **History** | [changelog](./hypothesis-property-fuzz-llm-output-parsers.history) |

## When to Use

- You are adding property-based / fuzz tests (Hypothesis) for parsers that consume **free-form LLM output**: verdict markers, ```json code fences, bold markers, CRLF, multi-line verdict noise.
- The parser's job is to be **fail-safe**: never raise on garbage, always return a typed default. You want tests that assert that *contract*, not specific parsed values.
- You must add a new **test/dev dependency** (e.g. `hypothesis`) in a **pixi + pyproject dual-manifest** repo and must not leave one manifest behind.
- You are deciding whether a new dependency trips an existing floor/lockstep consistency guard.
- `st.text()` alone is not exercising the structured branches of the parser and you need to bias the generator.
- You are deciding where the new tests live (append a class vs. new sibling file).

## Verified Workflow

### Quick Reference

```bash
# 1. Add the dep in BOTH manifests (conda path is what CI runs).
#    pyproject.toml  [project.optional-dependencies] dev   -> "hypothesis>=6.0,<7"   (pip path)
#    pixi.toml       [feature.dev.dependencies]  hypothesis = ">=6.0,<7"             (conda path)
#    hypothesis IS on conda-forge -> belongs in [feature.dev.dependencies], NOT [pypi-dependencies].

# 2. RESOLVE the env BEFORE trusting the floor.
pixi install            # EXECUTED: solved >=6.0,<7 cleanly -> hypothesis 6.155.7. Floor risk RETIRED.

# 3. Check whether a floor-consistency guard even applies to the new dep.
grep -nE "PyGithub|pytest|mypy" tests/unit/scripts/test_dependency_floor_consistency.py
#    -> guard only enforces PyGithub/pytest/mypy floors; arbitrary new deps are NOT lockstep-checked.
#       So no new consistency test is forced — but keep floors matched across manifests for hygiene.

# 4. Derive each parser's FAIL-SAFE CONTRACT by READING source, then assert THAT (not parsed values).

# 5. Compose generators so Hypothesis reaches structured branches.
#    st.text() | crafted fragments (verdict tokens, ```json fences, **bold**, \r\n, multiple verdict lines)

# 6. Place tests: append Test<Parser>Properties to the parser's EXISTING test module;
#    create a new test_*_property.py sibling only when the existing module is large or absent.

pixi run test           # property tests can be slow/flaky under --cov; tune deadline/profile if so.
```

### Detailed Steps

1. **Dual-manifest dependency add (the #1 footgun).** A new test dep must go in BOTH `pyproject.toml [project.optional-dependencies].dev` (pip install path) AND `pixi.toml [feature.dev.dependencies]` (conda path — this is what CI actually runs via `pixi run test`). Adding to only one leaves either CI or pip-dev installs missing the dep. `hypothesis` is on conda-forge, so it belongs in `[feature.dev.dependencies]`, **not** `[pypi-dependencies]`.

2. **Check the floor-consistency guard scope BEFORE assuming lockstep is enforced.** `tests/unit/scripts/test_dependency_floor_consistency.py` only enforces floor parity for **PyGithub, pytest, and mypy** — not arbitrary new deps. So a new `hypothesis` dep forces **no** new consistency test, but match the floor (`>=6.0,<7`) across both manifests anyway for hygiene.

3. **Assert the parser's documented FAIL-SAFE CONTRACT, not parsed values.** Derive the contract by reading the parser source. The four contracts captured here:
   - `parse_review_verdict` → always returns a `ReviewVerdict`; missing marker → `verdict="AMBIGUOUS"`, `raw == input`. Never raises.
   - `latest_verdict` → returns `"GO"` / `"NOGO"` / `None`; **last-match-wins** (`re.findall(...)[-1]`). Cross-ref the `llm-output-verdict-parse-last-line-not-substring` skill for *why* last-match-wins matters.
   - `_parse_coordinator_results` → returns `list[dict]`; malformed JSON inside a ```json fence is **skipped, not raised**; prose with no fence → `[]`.
   - `_parse_addressed_block` → delegates to `_review_utils.parse_json_block` (`use_last_block` default `True`); always returns a `dict`; junk → default `{"addressed": [], "replies": {}}`.

4. **Pure `st.text()` rarely reaches the structured branches.** Compose `st.text()` with crafted fragments — verdict tokens, ```json fences, `**bold**` markers, CRLF, multiple verdict lines — so Hypothesis exercises BOTH the "never crashes on noise" property AND **metamorphic invariants** (e.g. appending a later verdict line flips `latest_verdict`'s result → demonstrates last-match-wins).

5. **Mirror test structure to source.** Append a `Test<Parser>Properties` class to the parser's EXISTING test module. Only create a new `_property` sibling file when the existing module is large or the parser lacks a dedicated test file (here `_parse_addressed_block` got a new `test_address_review_property.py`).

6. **Resolve and run before claiming done.** Running `pixi install` resolved `hypothesis>=6.0,<7` cleanly to **6.155.7** and regenerated `pixi.lock` — the floor-solvability risk is **RETIRED** (no need to raise the floor). The dual-manifest placement (conda `[feature.dev.dependencies]`, not `[pypi-dependencies]`) and the floor-guard scope note (only PyGithub/pytest/mypy are lockstep-enforced, so no new floor-consistency test was forced) were both **confirmed correct**. In practice the parsers are pure/fast, so the property tests ran green under `--cov` with **no** `@settings(deadline=None)` needed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Plan to add `hypothesis` to only `pyproject.toml [optional-dependencies].dev`. | `pixi run test` (CI) installs from the conda/pixi env, not pip — the dep would be missing at CI runtime. | Dual-manifest repos need the dep in BOTH `pyproject` dev extras AND `pixi.toml [feature.dev.dependencies]`. |
| 2 | Assume a new dep must be added to a floor-consistency guard test. | `test_dependency_floor_consistency.py` only enforces PyGithub/pytest/mypy floors; arbitrary deps are not lockstep-checked. | Read the guard's scope before writing a "required" consistency test; don't invent enforcement that doesn't exist. |
| 3 | Plan property tests with bare `st.text()` and assert parsed values. | `st.text()` almost never produces a ```json fence or a verdict token, so structured branches go untested; asserting parsed values fights the fail-safe contract. | Compose generators with crafted fragments; assert the never-raises + typed-default CONTRACT, plus metamorphic invariants. |
| 4 | Pick floor `hypothesis>=6.0,<7` by convention and treat the plan as ready. | The floor was never resolved against `pixi.lock` (`pixi install` was never run) — solvability is unverified. | Run `pixi install` to confirm the floor solves before committing the constraint; an unverified floor is the top risk. (RESOLVED in execution: `pixi install` solved it to hypothesis 6.155.7.) |
| 5 | Wrote two separate import lines `from hypothesis import given` and `from hypothesis import strategies as st`. | Ruff `I001` flagged the import block as unsorted/collapsible — adding a second `from <pkg> import` line in an already-sorted block reliably trips I001. | Run `ruff check --fix` after adding test imports; ruff collapses them to `from hypothesis import given, strategies as st`. |
| 6 | Ran the new property suites as a PARTIAL selection (`pytest <file>::<Class>`) and read the coverage line. | Saw "FAIL Required test coverage of 83.0% not reached. Total coverage: 6.12%" — `--cov` lives in pytest `addopts`, so ANY partial selection trips the global coverage gate. (`-p no:cov` / `--no-cov` do NOT disable it because `--cov` is in addopts.) | The `N passed` line is the real signal; the trailing coverage FAIL on a partial run is EXPECTED, not a test failure. |
| 7 | Assumed `_parse_addressed_block` parses JSON itself. | It DELEGATES to `_review_utils.parse_json_block(text, default=_ADDRESS_PARSE_DEFAULT)` (`use_last_block` default) — the parsing logic is not in the function body. | Fuzz it through the public `_parse_addressed_block` entry point and assert the documented default shape `{"addressed": [], "replies": {}}` on junk; import `_ADDRESS_PARSE_DEFAULT` to assert against, don't hardcode the literal. |
| 8 | Anticipated property-test deadline-under-`--cov` flakiness and planned `@settings(deadline=None)`. | The flakiness was NOT observed — the parsers are pure/fast, so default Hypothesis deadlines never tripped under coverage. | Don't pre-emptively add `@settings(deadline=None)`; add it only if a real deadline trip is observed. |

## Results & Parameters

**Dependency add (both manifests, floor matched):**

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
  # ...
  "hypothesis>=6.0,<7",
]

# pixi.toml  (conda path — what `pixi run test` uses; hypothesis is on conda-forge)
[feature.dev.dependencies]
hypothesis = ">=6.0,<7"
```

**Parser fail-safe contracts (assert THESE, derived by reading source):**

| Parser | Return type | Garbage/empty behavior | Key invariant |
|--------|-------------|------------------------|---------------|
| `parse_review_verdict` | `ReviewVerdict` | `verdict="AMBIGUOUS"`, `raw == input` | never raises |
| `latest_verdict` | `"GO"` / `"NOGO"` / `None` | `None` when no marker | **last-match-wins** (`findall[-1]`) |
| `_parse_coordinator_results` | `list[dict]` | `[]` on prose; bad JSON-in-fence **skipped** | never raises on malformed fence |
| `_parse_addressed_block` | `dict` | default `{"addressed": [], "replies": {}}` | delegates to `_review_utils.parse_json_block` (`use_last_block=True`) |

**Generator composition sketch:**

```python
from hypothesis import given, strategies as st

VERDICT_TOKENS = st.sampled_from(["GO", "NOGO", "AMBIGUOUS", "go", "nogo"])
FENCE = st.builds(lambda body: f"```json\n{body}\n```", st.text())
NOISE = st.text() | st.just("\r\n") | st.just("**bold**")

llm_output = st.lists(st.one_of(NOISE, VERDICT_TOKENS, FENCE)).map("\n".join)

@given(llm_output)
def test_latest_verdict_never_raises_and_typed(s: str) -> None:
    assert latest_verdict(s) in {"GO", "NOGO", None}
```

### Executed results (verified-local)

**Dependency resolved:** `hypothesis` floor `>=6.0,<7` in BOTH manifests (pyproject `dev` extra + pixi `[feature.dev.dependencies]`); `pixi install` resolved it to **6.155.7** and regenerated `pixi.lock`. Confirmed:

```text
$ pixi run python -c "import hypothesis; print(hypothesis.__version__)"
6.155.7
```

**Tests added (test-only + dep add; NO source change) — 14 new property tests across 4 parsers:**

| Location | Class | Tests |
|----------|-------|-------|
| `tests/unit/automation/test_claude_invoke.py` | `TestParseReviewVerdictProperties` | 3 (never raises; `raw == input`; verdict ∈ {GO,NOGO,ERROR,AMBIGUOUS}; no "verdict" token → AMBIGUOUS; anchored `Verdict: <token>` line classifies) |
| `tests/unit/automation/test_review_state.py` | `TestLatestVerdictProperties` | 3 (GO/NOGO/None; no verdict line → None; last-match-wins metamorphic invariant) |
| `tests/unit/automation/test_audit_reviewer.py` | `TestParseCoordinatorResultsProperties` | 4 (list[dict]; no ```json fence → []; malformed fence skipped not raised; well-formed `pr_number` block parsed) |
| `tests/unit/automation/test_address_review_property.py` (NEW FILE) | `TestParseAddressedBlockProperties` | 4 (never raises/returns dict; non-JSON → default shape; malformed fence tolerated; well-formed block round-trips `replies`) |

New property suites: 10 passed (the 3 appended classes) + 4 passed (new file) = **14**.

**Verification commands & results (all green LOCAL):**

```text
pixi run pytest tests/unit/automation -q       -> 2319 passed
pixi run ruff check hephaestus tests            -> clean (after I001 auto-fix)
pixi run mypy                                    -> Success, 445 source files
pixi run python -c "import hypothesis"           -> 6.155.7
```

Note: PR CI was **not yet merged at capture** → this is **verified-local, NOT verified-ci**.

**Source anchors that PROVED correct against the executed tree:**

| Parser | Anchor | Behavior |
|--------|--------|----------|
| `parse_review_verdict` | `claude_invoke.py:364` | first-match `_VERDICT_RE.search`; miss → AMBIGUOUS |
| `latest_verdict` | `review_state.py:73` | `_GATE_VERDICT_RE.findall(...)[-1]`; miss → None |
| `_parse_coordinator_results` | `audit_reviewer.py:49` | `_FENCE_RE.finditer`; JSONDecodeError → skip |
| `_parse_addressed_block` | `address_review.py:81` | delegates to `_review_utils.parse_json_block` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1470 — executed Hypothesis fuzz tests for 4 LLM-output parsers end-to-end (branch `1470-auto-impl`): hypothesis 6.155.7, 14 new property tests, 2319 automation tests passed, mypy 445 files | verified-local (PR CI pending) |
