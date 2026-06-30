---
name: architecture-executable-convention-guard-pattern
description: "Turn an un-guarded documented invariant (a prose convention) into a tested, blocking, reusable executable check that CI or any consumer can call. Use when: (1) a contract like 'absence of artifact X means stage Y never ran' lives only in docstrings/comments and nothing asserts it, (2) you are adding an enforcement gate whose whole purpose is signal fidelity and must pick a collision-free exit code distinct from argparse's usage-error 2 and sibling CLIs, (3) a verification step must resolve its inputs strictly read-only and must NOT fabricate the very signal whose absence it checks (e.g. a resolver that mkdir()s the directory), (4) you classify a log/marker line and must anchor on the line prefix instead of a free substring scan vulnerable to user-controlled tokens, (5) you relax argparse requirements (nargs='?') for a new mode and must re-guard the original mode so it does not silently no-op, (6) the same convention is documented in two places (module docstring + sibling shell comment) and must be kept in sync when made executable, (7) you are planning a fix for any 'X mirrors Y' / parity / directory-structure invariant audit finding and must determine WHICH direction(s) the existing guard asserts — the defect is usually the un-asserted reverse direction (test_packages - src_packages), and the fix is an allowlist-with-rationale plus the reverse check, NOT deletion of flagged items, (8) you are adding an executable membership/coverage guard that ITERATES a population (all packages / dirs / files of a kind) — you MUST scope its iteration set AND its CI/pre-commit files: trigger to the issue's NAMED targets only when sibling members are partially compliant, or the guard fails its OWN acceptance test on the shipped tree."
category: architecture
date: 2026-06-30
version: "1.7.0"
user-invocable: false
verification: unverified
history: architecture-executable-convention-guard-pattern.history
tags:
  - executable-convention
  - invariant-guard
  - exit-code-collision
  - fail-safe
  - read-only-verification
  - log-line-anchoring
  - observability
  - cli-verify-mode
  - ci-gate
  - bidirectional-invariant
  - mirror-parity
  - allowlist-with-rationale
  - test-structure
  - commit-trailer
  - dco-signoff
  - precommit-hook
  - sibling-checker-mirror
  - coverage-altitude
  - negative-branch-test
  - argparse-default-branch
  - nogo-tightening
  - inferred-data-honesty
  - doc-table-code-parity
  - membership-only-guard
  - guard-scope-population
  - partial-compliance
  - scope-lock-test
  - ghost-directory-guard
  - prefiltered-population-fixture
  - hephaestus
---

# Architecture: Executable Convention Guard Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Turn an un-guarded documented invariant ("a missing `handler.log` means the handler never ran") into a tested, blocking, reusable check that CI or any consumer can call |
| **Outcome** | Success — shipped `verify_crash_bundle(log_dir) -> (verdict, detail)` library function + a CLI `--verify` mode with a distinct blocking exit code (3); full suite 4305 passed / 19 skipped; pre-commit clean. CI validation pending on PR #1247. |
| **Verification** | verified-local (CI on PR #1247 pending at capture time) |

## When to Use

Apply this pattern when a documented contract is currently enforced by nothing but prose, and a downstream consumer that forgets to honor it would silently lose a signal:

- A convention of the form **"absence of artifact X means stage Y never ran"** lives only in docstrings/comments. The original case: a kernel pipe handler's exit code is ignored by the kernel, so all failures are *logged* (to `handler.log`), never signalled via exit status — a downstream CI artifact step that forgot to check `handler.log` would silently drop the only failure signal.
- You are adding an **enforcement gate whose entire value is signal fidelity** — so it must be able to distinguish "the real defect happened" from "the gate was invoked wrong."
- A verification routine must **resolve its inputs strictly read-only**, and the obvious helper has a side effect (e.g. `resolve_target_dir()` does `mkdir(parents=True, exist_ok=True)`) that would *create* the very artifact whose absence is the signal.
- You **classify a log or marker line** and a free substring scan is unsafe because the line can embed a user-controlled token (a `%e` exe basename that can contain spaces).
- You **relax argparse requirements** (`nargs="?"`) to let a new mode run without the positionals the original mode required, and you must re-guard the original path.
- The **same convention is documented in two homes** (a Python module docstring AND a sibling shell handler comment) that will drift if only one is updated.

Also apply this pattern when the un-guarded convention is a **structural mirror / parity invariant** (see the dedicated sub-pattern below):

- You are planning a fix for an audit finding of the form **"X mirrors Y"** — e.g. "every `tests/unit/` subpackage mirrors a `hephaestus/` source subpackage," "every header has a matching `.cpp`," "every module has a doc page."
- An existing guard already enforces ONE direction of such an invariant (the forward direction) and you suspect the **reverse direction is silently unguarded** — that asymmetry is exactly where drift accumulates.
- The flagged "violations" are **intentional** (test dirs covering non-package targets such as a top-level `scripts/`, `docs/`, shell installers, or a single-file module) and the right answer is a **sanctioned allowlist with rationale**, not deletion.

Also apply this pattern when the guard **iterates a population and you must decide its iteration scope** (see the "Scope a Membership Guard to Named Targets" sub-pattern below):

- You are adding an executable **membership / coverage guard** that loops over a *population* (every package, every dir, every file of a kind) and asserts a global property (e.g. `find_violations() == []`) over the whole set — and the population's members are **not all equally compliant**.
- The issue names **a SUBSET of targets** (e.g. "add API tables to cli/system/version") but it is tempting to point the guard at the FULL population ("all seven Stable subpackages") "for completeness."
- A sibling member has a **pre-existing-but-PARTIAL** artifact (a table that exists but does not cover its full `__all__`, a doc that exists but is stale) — presence is NOT alignment, and folding it into the guard makes the guard red on the shipped tree.

**Key trigger:** you find yourself writing "we rely on convention that …" in a docstring with nothing that fails if the convention is violated — OR an audit says "N items break the mirror invariant" and you cannot point at the line of code that asserts BOTH directions of that mirror.

## Verified Workflow

> Verification level: **verified-local**. The full ProjectHephaestus test suite (4305 passed, 19 skipped) and `pre-commit run --all-files` both passed locally. CI validation pending on PR #1247.

### Quick Reference

```python
# Library-first: a reusable, importable, tested predicate — NOT a new CI YAML job.
# (grep first: confirm no existing CI step already guards this; one that adds
#  `test -f handler.log` to a non-existent job guards nothing.)

BUNDLE_OK = "OK"
BUNDLE_RAN_WITH_ERRORS = "RAN_WITH_ERRORS"
BUNDLE_NOT_RUN = "NOT_RUN"
VERIFY_SIGNAL_LOST_EXIT = 3  # distinct from argparse usage-error 2 and sibling CLI's 2


def verify_crash_bundle(log_dir: Path) -> tuple[str, str]:
    """Return (verdict, detail). Verdict is one of BUNDLE_OK /
    BUNDLE_RAN_WITH_ERRORS / BUNDLE_NOT_RUN. Strictly read-only."""
    ...


def _message_is_wrote(ln: str) -> bool:
    # Each log line is "<iso-timestamp> <message>". Anchor on the MESSAGE prefix,
    # never a free `" wrote " in line` scan (the path can embed " wrote ").
    parts = ln.split(maxsplit=1)
    return len(parts) == 2 and parts[1].startswith("wrote ")


# Read-only resolution — NO mkdir, so absence stays a real signal:
target = next((Path(c) for c in cleaned if Path(c).is_dir()), Path(cleaned[-1]))
```

```bash
# CLI contract: --verify exits 0 if the handler provably ran (OK or RAN_WITH_ERRORS),
# else exits 3 (NOT_RUN). JSON envelope on the blocking case:
#   {"status":"error","exit_code":3,"message":"...","verdict":"NOT_RUN"}
coredump_capture --verify /var/lib/crash || echo "signal lost (exit $?)"

# Find existing exit codes before picking a new one:
grep -rn "return [0-9]" path/to/module/
```

### Detailed Steps

1. **Ship the guard as a LIBRARY FUNCTION + a CLI `--verify` mode, not a new CI YAML job.** Grep first and confirm no crash-bundle CI step exists — adding a `test -f handler.log` to a job that doesn't exist guards nothing. A library function (`verify_crash_bundle(log_dir) -> (verdict, detail)`) is reusable across CI YAML, downstream tooling, and other consumers, and respects a library-first boundary. The convention lived purely in docstrings; making it an importable, tested function is the durable fix.

2. **Choose a collision-free exit code.** The invariant-violation code must be distinct from codes already in use. `argparse.ArgumentParser.error()` exits **2** on usage errors; a sibling CLI (`gdb_runner`) already returned **2**; `1` is the generic-error code. Reusing `1` or `2` would make a real lost-signal indistinguishable from a typo'd invocation — a masking hazard for a gate whose whole purpose is signal fidelity. `grep -rn "return [0-9]"` the module first, then pick an unused code (here **3**) and name it with a constant (`VERIFY_SIGNAL_LOST_EXIT = 3`) to document intent and prevent drift.

3. **Resolve the target read-only — never fabricate the signal.** Do NOT call the normal `resolve_target_dir()` helper in verify mode: it does `mkdir(parents=True, exist_ok=True)`, which would CREATE the very directory whose absence is the lost-signal indicator. Inline a read-only resolution (`next((Path(c) for c in cleaned if Path(c).is_dir()), Path(cleaned[-1]))` with NO mkdir). Lock it in with a test asserting the directory still does NOT exist after `--verify` runs.

4. **Anchor log-line classification on the line prefix, not a free substring scan.** Initial classifier used `" wrote " in line`, which substring-scans EVERY line including `ERROR:` lines; since the logged path embeds a user-controlled token (an exe basename `%e` that can contain spaces), an `ERROR: failed to write core to .../<name with ' wrote ' in it>` line could be misclassified as success. Each log line is `"<iso-timestamp> <message>"` — split off the timestamp (`line.split(maxsplit=1)`) and require the MESSAGE portion to `startswith("wrote ")`. This is the Python analogue of the inverse-grep / anchor-the-match lesson. Add a regression test with an ERROR line whose path embeds the literal `" wrote "`.

5. **Classify into three verdicts; map only the real-defect one to the blocking code.** `OK` (a `wrote` line present — even if a WARNING is also present, since a successful capture can still log a chmod/limit warning) and `RAN_WITH_ERRORS` (handler ran, no success line) both exit 0 — the handler RAN, the signal was not lost. Only `NOT_RUN` (missing/empty/unreadable log) exits the distinct blocking code. The blocking line is "was the failure SIGNAL lost", not "did the capture succeed". Surface the verdict via a discrete JSON field (`emit_json_status(exit_code, message=detail, verdict=verdict)`), not embedded in the message string, so it is aggregable.

6. **Keep the capture path loud after relaxing argument requirements.** To let `--verify` run without the kernel-supplied positionals, the positionals were made `nargs="?"` (optional), which silently weakened the capture path (a malformed `core_pattern` line missing tokens would no longer error at argparse time). Re-add an explicit guard in `main()`: if NOT `--verify` and any kernel token is missing, fail loudly (`return 1`) instead of silently no-opping. Test both: missing-positionals-without-verify returns 1, AND a full capture still writes the core (regression).

7. **Sync the documented contract in all its homes.** The same convention was documented in a Python module docstring AND a sibling shell handler comment. When you make it executable, update BOTH to reference the new guard (e.g. "a CI artifact step MUST run `--verify` and fail on exit 3 / NOT_RUN") so the two copies of the contract don't drift.

## Sub-Pattern: Bidirectional Mirror / Parity Invariants

> **Warning / scope of verification:** The **ghost-directory variant** of this sub-pattern (a name-only mirror gap where a `tests/unit/<pkg>/` exists with no `test_*.py` and the matching `hephaestus/<pkg>/` has no module beyond `__init__.py`) is now **verified-local for the ProjectHephaestus issue #1448 / PR #1703 instance** — `check_no_ghost_packages` was implemented and the full targeted test suite (42 passed) plus `pre-commit run --all-files` passed locally; CI on PR #1703 was still pending at capture time, so this is `verified-local`, NOT `verified-ci`. The ORIGINAL #1543 reverse-check material (`test_packages - src_packages - allowlist` allowlist guard) below remains **unverified** — it was a PLAN, the code was NOT executed or CI-validated. The v1.0.0 coredump material above remains `verified-local`. The other plan-only sub-patterns (#1506/#1507/#1516) remain **unverified**. Treat any still-PLAN material as a hypothesis until CI confirms.

When the prose invariant being made executable is a **structural mirror** ("every X has a matching Y"), the v1.0.0 steps still apply, but a distinct failure mode dominates: the guard enforces only ONE direction. This is the central, generalizable insight.

### The bidirectional gap (central insight)

A "mirror" / "parity" invariant has **TWO directions**. An existing guard frequently enforces only the **forward** one and leaves the **reverse** silently unguarded — which is precisely how drift accumulates:

| Direction | Set expression | Catches | Commonly guarded? |
| --------- | -------------- | ------- | ----------------- |
| Forward | `src_packages - test_packages` | a source subpackage with no test dir | usually YES |
| Reverse | `test_packages - src_packages - allowlist` | a test dir with no source counterpart | usually **NO** (the gap) |

When auditing or planning a fix for ANY "X mirrors Y" finding, **grep the existing checker and confirm WHICH direction(s) it asserts.** The defect is almost always the un-asserted direction. The fix **adds the reverse check** (`test_packages - src_packages - allowlist`) — it is NOT a rewrite of the forward check.

### Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

1. **Re-derive the violation set empirically — do NOT trust the audit's count.** Audit "N items violate" counts are often imprecise. The issue claimed "5 dirs"; ground truth found only 4 (the 5th, `scripts_lib/`, IS mirrored by a same-named source subpackage). Compute the real set:

   ```bash
   comm -23 \
     <(ls -d tests/unit/*/ | xargs -n1 basename | sort) \
     <(ls -d src/*/ | xargs -n1 basename | sort)
   ```

   Plan against ground truth and note the discrepancy with the audit explicitly.

2. **Confirm which direction the existing guard asserts.** Grep the checker (e.g. `check_test_structure()`). If it only does `src_packages - test_packages`, the reverse direction is the gap.

3. **Reuse the shared dir-filtering helper for BOTH directions.** The reverse check's correctness depends on the same `__pycache__`/dotdir filtering the forward check uses. Reuse the existing helper (e.g. `_get_subpackages`) — do NOT re-implement directory enumeration — so both directions share identical filtering semantics. (Reviewer must confirm the helper is reused, not re-implemented.)

4. **Allowlist legitimate "violations" with rationale — do NOT delete.** When flagged items are intentional (test dirs covering non-package targets), add a SANCTIONED allowlist (`frozenset`) where every entry carries an inline comment naming its non-package target. Deletion would drop real coverage. A new unsanctioned dir then fails the gate, forcing an explicit decision. This is the same "ignore + guard, never delete legitimate state" principle.

   ```python
   # Test dirs that intentionally do NOT mirror a hephaestus/ subpackage:
   _SANCTIONED_EXTRA_TEST_DIRS: frozenset[str] = frozenset({
       "scripts",    # tests for top-level scripts/, not a package
       "docs",       # doc-build / link tests, not a package
       # ...one entry per non-package target, each with its reason
   })

   def check_no_unsanctioned_test_dirs(src: Path, tests: Path) -> list[str]:
       extra = _get_subpackages(tests) - _get_subpackages(src) - _SANCTIONED_EXTRA_TEST_DIRS
       return sorted(extra)
   ```

5. **Fix prose AND code together.** The invariant lived only in prose (CLAUDE.md). Making it executable means BOTH adding the tested predicate AND correcting the prose to match the now-precise rule (mirror subpackages + a small sanctioned-extras set). Keep all documented copies of the contract in sync.

6. **Reuse the already-wired gate; do NOT add a new CI job.** The checker was already invoked in CI (`_required.yml`, `test.yml`) and pre-commit. Wire the new reverse check INTO the existing `check_test_structure()` so it rides the already-required gate — no new workflow. (ci-hygiene "already-wired" pattern.) Re-grep `hephaestus-check-test-structure` to find the wiring rather than trusting line numbers (`_required.yml:552` / `test.yml:101` / `.pre-commit-config.yaml:158` were read once and may drift).

7. **Cover the negative-path branch.** Adding a new function needs a `TestCheckNoUnsanctionedTestDirs` that exercises the `else` branch printing unsanctioned dirs, or module coverage can drop below the 83% gate. Prefer unit-test coverage over a manual mutation test (`mkdir tests/unit/rogue ... rmdir`) which mutates the working tree and can leave a stray dir if it fails mid-way.

8. **Test the orchestrator branch, not just the helper (coverage altitude).** This is the dominant lesson from the review iteration (issue #1543 re-plan, post-NOGO). A pure low-level predicate (`check_no_unsanctioned_test_dirs() -> (ok, set)`) is easy to unit-test directly, but when you ALSO wire it into a higher-level orchestrator (`check_test_structure()`), unit tests that call ONLY the helper leave the orchestrator's failure branch — specifically its `for name in sorted(unsanctioned): print(..., file=sys.stderr)` loop and remediation-hint print — **UNEXECUTED**. Under a line-coverage gate (here 83%) that uncovered print block can fail CI even though the logic is "tested." The fix: add a SEPARATE orchestrator-altitude test that drives the real failure path end-to-end and asserts on captured stderr via pytest's `capsys` — assert BOTH the offending dir name AND the remediation-hint string appear. Mirror the existing sibling tests for the other checks in the SAME orchestrator (e.g. `test_missing_src_root` / `test_missing_test_root`): **when you add Check N, add a Check-N-failure test at the SAME altitude as the existing Check-1/Check-2 tests, not just at the helper altitude.**

   - **Verification commands that mutate the real working tree are a hygiene risk.** A manual negative test like `mkdir tests/unit/rogue && <run checker> && rmdir tests/unit/rogue` leaves a stray dir if the checker aborts mid-run. Demote it BELOW the unit-level negative test (the primary guard) and wrap it in a subshell with `trap '... rmdir' EXIT` so cleanup runs even on abort. Prefer a `tmp_path`/`capsys` unit test over tree mutation whenever possible.
   - **When adding a new allowlist/skip set, confirm it doesn't visually collide with an existing one on a different axis.** Here `docs`/`scripts` appear in BOTH `_detect_src_package`'s `skip` set (source-package-detection axis) AND the new `SANCTIONED_EXTRA_TEST_DIRS` (test-dir-allowlist axis). There is no code conflict, but add an inline comment naming the distinct axis so a future reader doesn't conflate the two lists (POLA).

### Verified-local instance: the ghost-directory / name-only-mirror check (ProjectHephaestus #1448 / PR #1703)

> Verification level: **verified-local** for THIS instance. The full targeted test suite (42 passed) and `pre-commit run --all-files` both passed locally; CI on PR #1703 was still pending at capture time — do NOT claim `verified-ci`.

This is the FIRST end-to-end execution of the bidirectional-mirror sub-pattern (the rest above is still plan-only). It implemented the **ghost-directory sub-pattern**: a name-only mirror gap where a `tests/unit/<pkg>/` and a `hephaestus/<pkg>/` share a name but BOTH are content-free shells — the source dir has no module beyond `__init__.py` AND the test dir has no `test_*.py`. The durable, EXECUTED lessons:

1. **Add a content-aware predicate on the ALREADY-WIRED gate — NO new CI job.** Added `check_no_ghost_packages(src_root, test_root) -> (ok, ghosts)` in `hephaestus/validation/test_structure.py`, wired as a 4th check inside the already-required `check_test_structure` orchestrator. It rode the existing gate `hephaestus-check-test-structure` (pre-commit hook id `check-unit-test-structure`, plus `_required.yml` / `test.yml`). This CONFIRMS the "add a tested predicate on the already-wired gate" rule — no new workflow was created.

2. **A guard whose population is pre-filtered must have its in-scope failure fixture satisfy that pre-filter on BOTH sides.** The ghost predicate intersects `_get_subpackages(src) & _get_subpackages(test)`, and `_get_subpackages` already EXCLUDES `__pycache__`-only / stale-`.pyc` dirs (via `_has_python_source`). So the audit's LITERAL described state (a `tests/unit/git/` holding only stale `.pyc`) is NOT enumerable and is intentionally **out of scope** — the in-scope ghost is an `__init__.py`-only SHELL pair (source has no module beyond `__init__.py` AND test dir has no `test_*.py`). The FIRST test fixture used a BARE `tests/git/` (no `.py` at all); that dir is filtered OUT by `_get_subpackages`, so it would NOT appear in `shared` and the ghost would NOT be detected — the fixture silently exercised nothing. The fix: the in-scope failure fixture had to create `__init__.py` on BOTH sides to land in the `shared` population. **General rule: when a guard's population is pre-filtered (here, by "has Python source"), the in-scope failure fixture MUST satisfy that pre-filter on BOTH sides, or the test silently exercises nothing and passes vacuously.**

3. **Coverage-altitude lesson CONFIRMED in practice.** Added BOTH a helper-altitude test class (`TestCheckNoGhostPackages`, including `test_real_repo_has_no_ghosts` so the gate ships green on the real tree) AND an orchestrator-altitude `capsys` failure test (`test_ghost_package_fails`) driving the new stderr print loop in `check_test_structure`. `hephaestus/validation/test_structure.py` reached **91.37% line coverage** (>= the 83% gate). 42 tests passed.

4. **Document the guard's narrower-than-audit scope at the point of definition (POLA).** A PR-review thread (PR #1703) asked for a documentation-only clarification — a 3-line inline comment at the `shared = ...` line recording that a content-free pair must carry `__init__.py` to be enumerable, and that `__pycache__`-only shells are intentionally out of scope. **When a guard's scope is narrower than the audit's literal wording, document the boundary at the point of definition so a future reader doesn't expect detection the guard intentionally omits.**

5. **Re-derive the audit's described ground state — do NOT trust it.** The literal `hephaestus/git/` and `tests/unit/git/` dirs were ALREADY gone; the durable fix was the structural name-only-mirror gap, not a file deletion. The audit's described state must be re-verified, not trusted (same ground-truth-re-derivation rule as the `comm -23` lesson above).

## Sub-Pattern: The NOGO→GO Tightenings a Plan Reviewer Demands Even on a Sound Design

> **Warning:** This sub-pattern (added in v1.4.0, from ProjectHephaestus issue #1506 R0-NOGO → R1 re-plan) is **unverified** — it is a PLAN, the code was NOT executed or CI-validated. Treat as a hypothesis until CI confirms. The v1.0.0 coredump material remains `verified-local`; the v1.1.0–v1.5.0 sub-patterns are plan-only.

This is the **planning** companion to the coverage-altitude sub-pattern above. The #1506 case was another instance of the core pattern (add per-symbol API tables to `COMPATIBILITY.md` plus a bidirectional drift guard `api_table_docs.py` mirroring the sibling `cli_tier_docs.py`). The R0 plan was graded **B / NOGO** — yet the reviewer explicitly **affirmed the DESIGN as sound** (guard scope justified, bidirectional check correct, import-surface safe). The NOGO was driven entirely by a small set of MINOR tightenings. The durable lesson: **a sound design can still NOGO, and converging is about anticipating these specific reviewer-demanded tightenings, not redesigning.**

### The central insight

When a guard's logic is correct, the blockers a plan reviewer raises cluster into a small, predictable set. Pre-empt all of them in R0 and you skip the NOGO round:

1. **A sound design can still NOGO on negative-branch test coverage that is only INCIDENTAL.** R0's tests exercised the `table-not-found` error branch only as a side effect (a fixture with ONE package's table present makes the other six report `table-not-found` incidentally) and asserted only the one finding it cared about. Coverage tools read this as "covered"; a reviewer will still NOGO it. **Add a DEDICATED test that asserts the error/empty verdict DIRECTLY, with a fixture whose whole purpose is to trigger it** — e.g. a doc with NO parseable tables → assert EVERY package yields `table-not-found`. This generalizes to any guard with an error/empty verdict (`table-not-found`, "no rows parsed", etc.): incidental coverage of the error kind is not the same as a test that targets it.

2. **Test the orchestrator's argparse default branch explicitly.** R0 only tested `main(["--json", "--repo-root", str(REPO_ROOT)])`, which always supplies `--repo-root`, so the `args.repo_root or get_repo_root()` fallback was NEVER executed. Fix: a `test_main_repo_root_default` that calls `main([])` (flag ABSENT) with `get_repo_root` monkeypatched to a known path, exercising the default branch. **The `X or default()` fallback in `main()` is a real branch the 83%-coverage gate can expose; cover it by invoking with the flag absent and monkeypatching the default resolver.** (This is the argparse-default analogue of the coverage-altitude lesson above.)

3. **Verify the testability precondition before PROMISING the test.** Before writing `test_main_repo_root_default`, confirm the default resolver actually supports the no-arg call the test relies on: `get_repo_root(start_path=None)` accepts no args (`hephaestus/utils/helpers.py:99`), so `main([])` → `get_repo_root()` is callable. **When a re-plan promises a new test to close a coverage gap, verify the function under test supports the no-arg/default invocation path the test relies on — don't promise an untestable branch.**

4. **Inferred data shipped in an authoritative-looking doc cell needs an inline honesty caveat, not just a guard that ignores it.** R0 already had the guard skip the "Added" version column (it validates membership, not the version value) — yet the reviewer still flagged (MINOR) that the version cells SHIP as semi-authoritative contract claims. R1 added an italic note above each new table: *"the Added version for pre-1.0 symbols is a best-effort historical anchor, not an authoritative record."* **Not validating a fabricated/inferred field is necessary but NOT sufficient — if it appears in user-facing output it must be visibly labeled as inferred at the point of presentation (POLA).**

5. **Harden the hand-rolled parser pre-emptively when the reviewer flags fragility as MINOR-but-real.** The reviewer noted the table parser's only safety net was the live-tree alignment test. R1 hardened `load_documented_symbols`: factored the separator regex into a named constant AND added an explicit `## ` (next top-level section) break in ADDITION to the `### ` break, so the parser cannot run past a package table into `## Deprecation Policy`. **A "fragile but backstopped" parser flagged at MINOR is cheap to harden in the re-plan and removes a standing reviewer objection; pair the hardening with the existing alignment test as the backstop** (the hardening narrows known failure modes; the alignment test remains the real backstop).

### Risks the reviewer should STILL focus on (carry these forward)

- The "Added" version anchors remain **INFERRED** (now caveated inline) — only membership is CI-enforced.
- The hand-rolled markdown table parser is still hand-rolled; the **live-tree alignment test is the real backstop**, the regex hardening only narrows known failure modes.
- The guard imports the seven stable subpackages (`importlib.import_module`) — it MUST run in the `default` pixi env (the pre-commit `entry` pins `--environment default`).

## Sub-Pattern: Bidirectional Membership Guard for a Doc-Table↔Code Invariant

> **Warning:** This sub-pattern (added in v1.5.0, from ProjectHephaestus issue #1507 — the FIRST issue to actually CREATE `api_table_docs.py`, after #1506's plan never landed) is **unverified** — it is a PLAN, the code was NOT executed or CI-validated. Treat as a hypothesis until CI confirms. The v1.0.0 coredump material remains `verified-local`; the v1.1.0–v1.6.0 sub-patterns are plan-only.

This is the concrete SECOND instance of the bidirectional-membership-guard sub-pattern, applied not to a test-dir↔src-dir mirror but to a **DOC-TABLE↔CODE** invariant. It is the worked example that grounds the abstract "mirror existing guard, validate BOTH directions" rule in a doc-drift context — and the issue where `api_table_docs.py` is finally implemented (#1506's plan to create it never merged; `test -f` confirmed it was absent).

### The invariant and the guard

`api_table_docs.py` cross-checks each ``### `hephaestus.<pkg>` `` per-symbol API table in `COMPATIBILITY.md` against `importlib.import_module(pkg).__all__`, emitting in BOTH directions:

| Finding kind | Set expression | Catches |
| ------------ | -------------- | ------- |
| `missing-from-docs` | `__all__ - documented_rows` | a `__all__` symbol with no table row (incl. deprecated members like `retry_with_jitter`) |
| `missing-from-all` | `documented_rows - __all__` | a table row for a symbol no longer exported (stale doc) |

It mirrors `hephaestus/validation/cli_tier_docs.py` EXACTLY: a dataclass finding, a parse function, a `find_violations` function, a `main() -> 0/1`, and `add_json_arg`/`add_version_arg`. **When you build a new guard, mirror the nearest existing guard's full shape — dataclass + parser + find_violations + main + arg helpers — not just its core check.**

### The central lesson: guard a MIXED table by membership only

The `COMPATIBILITY.md` table has a VERIFIABLE column (symbol membership, derivable from live `__all__`) and an UNVERIFIABLE column (the "Added" semantic-version, inferred via `git log -S`). **Assert ONLY membership.** A guard that also asserted the inferred "Added" version would lend false authority to fabricated data — the guard must never validate a column it cannot derive from the source of truth. This is the doc-table analogue of the test-dir allowlist principle: assert the hard invariant, leave the soft/inferred field out of the gate.

### Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

1. **First verify the predecessor guard does NOT already exist.** #1506 planned `api_table_docs.py` but it never merged: `test -f hephaestus/validation/api_table_docs.py` -> NO. Do this before "extending" a guard that a prior plan only described — a captured plan is not a merged artifact.
2. **Mirror the sibling guard's FULL shape, not just its check.** Copy `cli_tier_docs.py`'s dataclass finding, parse fn, `find_violations` fn, `main()` returning 0/1, and `add_json_arg`/`add_version_arg`. Re-grep `cli_tier_docs` in `.pre-commit-config.yaml` and `pyproject.toml` for the live wiring rather than trusting remembered line numbers.
3. **Emit BOTH directions explicitly.** `missing-from-docs` (in `__all__`, no row — includes deprecated members) AND `missing-from-all` (row exists, not in `__all__`). The reverse direction is the silent drift surface, same as every mirror invariant.
4. **Guard membership ONLY; never the inferred "Added" column.** The version column is `git log -S`-inferred and unverifiable; asserting it would assert fiction.
5. **Add a defensive `parser-found-no-rows` finding.** If a table HEADER is present but zero rows parse (formatting drift), FAIL LOUD with a dedicated finding rather than silently reporting every symbol as `missing-from-docs`. This is the same anti-regression guard `cli_tier_docs` uses (its `parser-found-no-rows` / `scripts and not tiers` check) — a header-present-but-empty table is a parser bug, not a real "all symbols missing" condition.
6. **Pin the pre-commit `entry` to `pixi run --environment default`.** The guard imports packages via `importlib.import_module`, and the lint env lacks the installed packages — same rationale `cli_tier_docs` uses for its `--environment default` pin.
7. **Plan the reciprocal-gate edit — a new gate trips the OLDER gate.** Registering the new console script `hephaestus-check-api-table-docs` in `[project.scripts]` trips the SIBLING `cli_tier_docs` guard unless a `| hephaestus-check-api-table-docs | Internal | ... |` row is added to the Console-Script Stability Tiers table. Confirmed AGAIN here (after #1506): a new console-script gate always trips the older console-script-tiers gate — plan the reciprocal edit up front.

### Verification honesty

This #1507 work is **PLAN ONLY** — no code executed, no tests run, no CI. The frontmatter `verification` stays `unverified`; the #1507 additions are labeled `unverified`/plan-only and must NOT be read as `verified-local` or `verified-ci`.

## Sub-Pattern: Scope a Membership Guard to Named Targets, Not the Whole Population

> **Warning:** This sub-pattern (added in v1.6.0, from ProjectHephaestus issue #1506 R2 — a **critical D / NOGO** on the R1 re-plan) is **unverified** — it is a PLAN, the code was NOT executed or CI-validated. Treat as a hypothesis until CI confirms. The v1.0.0 coredump material remains `verified-local`; the v1.1.0–v1.6.0 sub-patterns are plan-only.

This is the **second** NOGO on the SAME #1506 session and a distinct, more severe lesson than the v1.4.0 MINOR tightenings. Where R1's NOGO was driven by incidental test coverage, the R2 NOGO was a **critical defect in the guard's iteration scope**: the guard's own acceptance test would FAIL on the shipped tree. (It is the planning sibling of the #1507 doc-table↔code membership guard above — same `api_table_docs.py` / `COMPATIBILITY.md` family, but the lesson is about WHICH packages the guard may iterate.)

### The central insight

**An executable membership-guard that iterates a POPULATION must be scoped to the issue's NAMED targets — never the whole population — when sibling members are only PARTIALLY compliant. Otherwise the guard fails its OWN acceptance test on the shipped tree.**

Concrete case (#1506): the plan added per-symbol API tables for THREE issue-named Stable subpackages (`cli`/`system`/`version`) plus a drift-guard (`api_table_docs.py`) cross-checking each package's `COMPATIBILITY.md` table against its live `__all__`. R0/R1 set `DOCUMENTED_PACKAGES` to ALL SEVEN Stable subpackages "for completeness." R2 found this is a CRITICAL defect:

- The OTHER four packages (`config`, `io`, `logging`, `utils`) have **pre-existing but PARTIAL** tables — they do NOT cover their full `__all__`. Verified this session via `ast` + an `awk` row-count: `config` had 13 names in `__all__` vs ~6 documented rows; `utils` 14 vs ~6; `io`/`logging` also not exactly aligned.
- Consequence: `find_violations()` returns ~17 `missing-from-docs` findings on the SHIPPED tree, so the plan's own `test_live_tree_is_aligned` (asserts `== []`) FAILS, the acceptance command `hephaestus-check-api-table-docs` exits 1 (not the promised "OK, exit 0"), and the pre-commit hook (whose `files:` regex included `config`/`utils`) would BLOCK every unrelated `config`/`utils` PR until 17 more symbols are documented — unplanned scope explosion.
- Fix: restrict `DOCUMENTED_PACKAGES` to exactly the three issue-named targets; narrow the pre-commit `files:` regex to `cli|system|version` only; add a `test_scope_is_three_named_packages` assertion that LOCKS the iteration set so a future widening (that would break alignment) fails loudly; and correct the module docstring (R0 falsely claimed "config/io/logging/utils already have tables" — they have PARTIAL tables).

### Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

1. **Before the guard iterates a population, MEASURE compliance of EVERY member — not just the issue's targets.** A sibling that is only partially compliant will make the guard red on the shipped tree. Run the actual measurement (`ast` for `__all__` membership, `awk`/row-count for the doc tables) across the WHOLE population and diff it against the guard's pass condition. Re-confirming a subset is NOT sufficient (see the process meta-lesson below).
2. **Scope the guard's iteration set AND its CI/pre-commit `files:` trigger to the issue's named targets.** Widening the iteration to the whole population is YAGNI scope-creep AND breaks the guard's own acceptance test (`find_violations() == []` over the full set fails because of the partially-compliant siblings). Set `DOCUMENTED_PACKAGES = {"cli", "system", "version"}` and `files: ...(cli|system|version)/COMPATIBILITY\.md` — not all seven.
3. **Lock the scope with an explicit equality test on the iteration set** (`test_scope_is_three_named_packages` asserting `DOCUMENTED_PACKAGES == {"cli", "system", "version"}`). An innocent future "just add the rest" widening then fails LOUDLY at test time instead of silently red-ing CI for unrelated PRs. This converts an implicit scope decision into an explicit, reviewed one.
4. **This is the EXECUTABLE-GUARD corollary of the audit-survey rule.** The survey rule says "a survey surfaces more non-compliant siblings — note them out-of-scope, don't fix them." Here the executable-guard analogue is stronger: you literally must NOT point the guard at those siblings, because the guard's acceptance test runs on the shipped tree and would go red.
5. **"Pre-existing artifact EXISTS" ≠ "pre-existing artifact is COMPLETE / aligned."** Verify completeness (row-count vs `__all__`), do NOT assume presence implies alignment. Fix any docstring/plan prose that conflates the two (R0's docstring falsely asserted the four siblings "already have tables"; they have PARTIAL tables).

### Process meta-lesson (how the defect survived R0 and R1)

The defect survived two review rounds because **alignment was re-confirmed ONLY for the three named packages, never for the OTHER members the guard folded in.** When a guard's acceptance test asserts a **global property over a SET** (`find_violations() == []` across ALL members), you must run/measure that assertion over the **ENTIRE set** before claiming it passes. Re-confirming a subset is not sufficient — it is exactly the blind spot that lets a partially-compliant sibling turn the guard red on the shipped tree.

### Risks the reviewer should STILL focus on (carry these forward)

- The "Added" version anchors remain **INFERRED** (caveated inline) — only membership is CI-enforced.
- The hand-rolled `COMPATIBILITY.md` table parser is still hand-rolled; `test_live_tree_is_aligned` is the real backstop for the three in-scope packages.
- The guard imports the covered subpackages via `importlib.import_module`, so the pre-commit `entry` MUST pin `--environment default`.

## Sub-Pattern: Commit-Trailer Convention Guards (DCO / Co-Authored-By)

> **Warning:** This sub-pattern (added in v1.3.0, from ProjectHephaestus issue #1516) is **unverified** — it is a PLAN, the code was NOT executed or CI-validated. Treat as a hypothesis until CI confirms. The v1.0.0 coredump material remains `verified-local`; the v1.1.0–v1.5.0 sub-patterns are plan-only.

A documented **commit-message-trailer convention** (DCO `Signed-off-by:`, `Co-Authored-By:`, `Implemented-By:`, etc.) enforced only in prose (CONTRIBUTING.md) is the SAME executable-convention-guard pattern: ship a stdlib predicate + a **dual gate** (a step in an ALREADY-WIRED required CI job + a `commit-msg` pre-commit hook), riding existing infrastructure rather than adding a new workflow. The DCO case (issue #1516) adds trailer-specific lessons that generalize to any trailer check.

### Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

1. **Mirror the repo's existing sibling checker VERBATIM.** The repo already had `scripts/check_conventional_commit.py` (subject-line check). Copy its exact shape for the new `scripts/check_dco_signoff.py`: `validate_*()` + `_*_from_args()` + `main() -> int`, exit `0`/`1`, dual invocation supporting BOTH `pass_filenames` file-path mode (pre-commit `commit-msg` hook hands a file path) AND a stdin `-` mode (the CI step pipes the message). One stdlib module, no deps. Re-grep for the sibling's name (`check_conventional_commit`) to confirm its shape before copying — do not trust remembered line numbers.

2. **Consume the FULL commit message — trailers live in the BODY, not the subject.** Unlike a subject-only check (conventional-commit takes `.commit.message | split("\n")[0]`), a trailer check must read the WHOLE message. The pr-policy GraphQL already fetches `.commit.message` (full message), so NO new GraphQL fetch is needed — reuse the existing `commits.json`. Pipe records with a **NUL (`\x00`) separator** (`jq -j ... + " "`) so multi-line bodies survive stdin; a newline separator would corrupt multi-line messages. (UNVERIFIED — the exact jq incantation and the `git log -z` / GraphQL `.commit.message` → Python `split("\x00")` round-trip were never executed; the implementer MUST run the CI snippet against a real multi-commit PR.)

3. **Anchor the trailer match on a line prefix + structural shape — never a free substring scan.** Require `^Signed-off-by: .+ <…@…>$`: a non-empty name AND an `@`-bearing bracketed email, so a bare `Signed-off-by:` (no identity) does NOT pass. This is the v1.0.0 log-line-anchoring lesson generalized to trailer lines: anchor on the line prefix and validate structure, do not scan for the substring `Signed-off-by` anywhere.

4. **In `commit-msg` file-path mode, strip `#`-comment lines before checking.** Git strips `#`-comment lines before applying the trailer, and `git commit -s` appends the `Signed-off-by` trailer BELOW the comment block in some templates. A naive whole-file read would miss the trailer or misclassify a commented-out one — strip `#`-prefixed lines first (matching git's own behavior).

5. **Exempt bot authors identically to the sibling checks.** Bot commits (`dependabot[bot]`) are not human DCO attestations. Reuse the EXACT `if [ "$PR_AUTHOR" = "dependabot[bot]" ]` short-circuit the other pr-policy checks already use, so the new gate does not block bot PRs. Do not invent a new bot-detection mechanism.

6. **Ride the already-wired required CI job — add a step, not a workflow.** The DCO check is wired as **Check 4** of the existing `pr-policy` job (already required, already fetches commits) plus a `commit-msg` pre-commit hook entry. Re-grep `dependabot\[bot\]`, `check_conventional_commit`, `default_install_hook_types`, and the DCO heading in CONTRIBUTING.md before editing — the line numbers cited in the plan (`_required.yml:382/419/425/435`, `.pre-commit-config.yaml:25/284`, `CONTRIBUTING.md:224-247`) were read ONCE and may drift. Verify the pr-policy `steps.fetch` output id and the `commits.json` filename in the ACTUAL workflow before appending Check 4.

7. **Beware the self-application bootstrap.** Once the `commit-msg` hook lands, the implementing commit ITSELF must carry a `Signed-off-by` trailer or the hook blocks its own creation. The plan's commit step MUST use `git commit -s -S` (sign-off AND cryptographic signature) — easy to forget, and the failure is circular (the commit that adds the rule can't be made).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Reuse exit code 2 | Used `2` for the invariant violation | Collides with argparse usage-error `2` and a sibling CLI's `2` — a CI gate can't tell "signal lost" from "bad command line" | Grep existing exit codes (`grep -rn "return [0-9]"`), pick a distinct code, name it with a constant (`VERIFY_SIGNAL_LOST_EXIT = 3`) |
| Trust the audit's "5 dirs" count | Planned the fix against the audit finding's stated number of violating dirs | Ground-truth `comm -23` found only 4 real violations — the 5th (`scripts_lib/`) IS mirrored by a same-named source subpackage, so it is not a violation | Re-derive the violation set empirically with `comm -23` of the two dir listings; plan against ground truth and note the discrepancy explicitly |
| Assume the existing guard was bidirectional | Took for granted that `check_test_structure()` enforced both directions of the mirror | It only enforced the FORWARD direction (`src_packages - test_packages`); the reverse (`test_packages - src_packages`) was silently unguarded — the actual drift surface | Grep the checker and confirm WHICH direction(s) it asserts; the defect is the un-asserted direction. Add the reverse check, do not rewrite the forward one |
| Delete the flagged test dirs | Considered removing the dirs that broke the mirror | The flagged dirs are intentional (test coverage for non-package targets: top-level `scripts/`, `docs/`, a single-file module); deletion drops real test coverage | Use a sanctioned `frozenset` allowlist with an inline rationale per entry; a NEW unsanctioned dir then fails the gate, forcing an explicit decision |
| Tested only the new low-level helper | Unit-tested `check_no_unsanctioned_test_dirs()` directly but not the orchestrator that consumes it | The orchestrator's `for name in sorted(unsanctioned): print(..., file=sys.stderr)` failure loop stayed UNCOVERED; under the 83% line-coverage gate that uncovered print block can fail CI even though the logic is "tested" | Add an orchestrator-altitude failure test (mirroring `test_missing_src_root` / `test_missing_test_root`) that drives the real failure path and asserts on captured stderr via `capsys` — assert both the offending dir name AND the remediation hint appear |
| Manual negative test mutated the real tree | Used `mkdir tests/unit/rogue && <run checker> && rmdir tests/unit/rogue` as the negative test | The stray dir persists if the checker aborts mid-run, polluting the working tree | Wrap in a subshell with `trap '... rmdir' EXIT` (cleanup runs even on abort) and make it OPTIONAL/secondary to a `tmp_path`/`capsys` unit test |
| Ghost-package failure fixture used a BARE test dir, not satisfying the guard's pre-filter (issue #1448 / PR #1703, **verified-local**) | The first `test_ghost_package_fails` fixture created a bare `tests/git/` with no `.py` files to simulate a ghost test dir | `check_no_ghost_packages` enumerates `_get_subpackages(src) & _get_subpackages(test)`, and `_get_subpackages` filters out dirs with no Python source (via `_has_python_source`) — the bare dir never entered `shared`, so the ghost was NOT detected and the test passed VACUOUSLY (exercised nothing) | When a guard's population is pre-filtered (here, "has Python source"), the in-scope failure fixture MUST satisfy that pre-filter on BOTH sides — create `__init__.py` on both the source and test side so the pair lands in the intersected population and the guard actually fires |
| Assert `status == 2` | Test asserted the JSON envelope as `payload["status"] == 2` (a number) | `emit_json_status` sets `status` to the STRING `"ok"`/`"error"` and puts the numeric code in `exit_code` — the assert always failed | Read the envelope helper's source before asserting its shape; assert `status=="error"`, `exit_code==3`, and the custom field via `**extra` |
| Call `resolve_target_dir()` in verify mode | Reused the normal resolver to find the log dir | It does `mkdir(parents=True, exist_ok=True)`, fabricating the very directory whose absence is the signal | Verification must be strictly read-only; inline a no-mkdir resolution and test that the dir is NOT created |
| Classify success via `" wrote " in line` | Free substring scan over every log line | Misclassifies an `ERROR:` line whose path embeds `" wrote "` as success (exe basename is user-controlled, can contain spaces) | Anchor on the log-line prefix (split timestamp, message `startswith`); add a regression test for the adversarial path |
| Make positionals optional without re-guarding | Set positionals to `nargs="?"` so `--verify` runs without kernel tokens | Silently weakened the capture path — a malformed `core_pattern` line missing tokens no longer errored | When you relax arg requirements for one mode, add an explicit missing-arg guard for the other mode and test it |
| Leave an unneeded `# noqa: SIM103` | Added a noqa the helper didn't actually need | Would trip RUF100 (unused-noqa) | Only add `noqa` for a rule that actually fires |
| Assumed `jq -j ... + "\x00"` NUL-joining round-trips without executing it | Planned to NUL-join commit messages in jq and `split("\x00")` in Python | The exact jq incantation and that `git log -z --format='%B'` / GraphQL `.commit.message` survive the round-trip were assumed, not tested | Must actually run the CI snippet against a real multi-commit PR with multi-line bodies and confirm Python `split("\x00")` reconstructs each full message |
| Trusted the cited line numbers (`_required.yml:382/419/425/435`, `.pre-commit-config.yaml:25/284`, `CONTRIBUTING.md:224-247`) | Planned edits against offsets read once | Line numbers drift between read and edit | Must re-grep `dependabot\[bot\]`, `check_conventional_commit`, `default_install_hook_types`, and the DCO heading before editing rather than trusting the offsets |
| Assumed the pr-policy `steps.fetch` id and `commits.json` filename matched the plan | Planned to append Check 4 reusing an assumed step-output id / artifact filename | The actual step id and filename were never verified against the real workflow | Must verify the existing pr-policy fetch-step id and the `commits.json` filename in the actual `_required.yml` before wiring Check 4 |
| Forgot the `commit-msg` hook's self-application bootstrap | Planned the implementing commit without ensuring it carries `Signed-off-by` | Once the hook lands, the very commit that adds it is blocked unless it has the trailer — a circular failure | Must verify the implementing commit step uses `git commit -s -S` so the new hook does not block its own creation |
| Covered the error verdict only INCIDENTALLY (issue #1506 R0-NOGO) | R0 fixture had ONE package's table present, so the other six reported `table-not-found` as a side effect; the test asserted only the one finding it cared about | Coverage tools read it as "covered," but the plan reviewer still graded it B / NOGO — incidental coverage of an error/empty verdict is not a test that targets it | Add a DEDICATED negative-branch test with a fixture whose whole purpose is to trigger the error verdict (a doc with NO parseable tables → assert EVERY package yields `table-not-found`) |
| Tested `main()` only with the flag always supplied (issue #1506 R0-NOGO) | R0 only called `main(["--json", "--repo-root", str(REPO_ROOT)])`, which always supplies `--repo-root` | The `args.repo_root or get_repo_root()` default branch was NEVER executed; under the 83% line-coverage gate that uncovered fallback can fail CI and the reviewer NOGO'd it | Add `test_main_repo_root_default` calling `main([])` (flag ABSENT) with `get_repo_root` monkeypatched to a known path, exercising the `X or default()` fallback |
| Promised a default-branch test without checking testability | Planned `test_main_repo_root_default` before confirming the default resolver supports a no-arg call | A re-plan that promises a test for a branch the function under test cannot be invoked into is an empty promise | Verify the precondition first: `get_repo_root(start_path=None)` accepts no args (`hephaestus/utils/helpers.py:99`), so `main([])` → `get_repo_root()` is callable — confirm before promising the test |
| Relied on the guard ignoring the inferred field, with no user-facing caveat (issue #1506 R0-NOGO) | R0 had the guard skip the "Added" version column (validates membership, not the value) but the cells still shipped looking authoritative | The reviewer flagged (MINOR) that the version cells SHIP as semi-authoritative contract claims — not validating an inferred field is necessary but NOT sufficient | Add an inline italic caveat at the point of presentation ("the Added version is a best-effort historical anchor, not an authoritative record") — POLA |
| Left a "fragile but backstopped" hand-rolled parser unhardened (issue #1506 R0-NOGO) | R0's table parser had only the live-tree alignment test as a safety net | The reviewer flagged the fragility as MINOR-but-real — a standing objection that is cheap to remove | Pre-emptively harden in the re-plan (factor the separator regex into a named constant; add an explicit `## ` next-section break in ADDITION to the `### ` break so the parser can't run past a package table) and keep the alignment test as the real backstop |
| Assumed #1506's `api_table_docs.py` guard already existed to extend (issue #1507, UNVERIFIED) | Treated the v1.3.0/v1.4.0 captured #1506 plan as if the guard had shipped | `test -f hephaestus/validation/api_table_docs.py` returned NO and `COMPATIBILITY.md` lacked the cli/system/version tables — the plan never merged; #1507 is the FIRST issue to create it | Verify the predecessor artifact exists on disk (`test -f`) before "extending" a guard a prior plan only described |
| Considered guarding the inferred "Added" version column too (issue #1507, UNVERIFIED) | Tempted to assert both the symbol AND its documented version, since both live in the table | The "Added" version is `git log -S`-inferred and unverifiable; a guard asserting it would assert fiction and lend false authority | Guard a MIXED table by MEMBERSHIP only — assert the column derivable from `__all__`, never the inferred one |
| Reporting every symbol as missing when a table header parsed but no rows did (issue #1507, UNVERIFIED) | A naive parser would, on formatting drift (header present, rows unparsed), emit `missing-from-docs` for every `__all__` symbol | That floods the output and hides the real cause (a parser bug, not a real "all symbols undocumented" condition) | Add a defensive `parser-found-no-rows` finding that fails loud when a header is present but zero rows parse — mirror `cli_tier_docs`'s same anti-regression guard |
| Mirrored only the sibling guard's core check, not its full shape (issue #1507, UNVERIFIED) | Almost copied just `cli_tier_docs`'s comparison logic | A guard needs the SHAPE too: dataclass finding, parse fn, `find_violations` fn, `main() -> 0/1`, `add_json_arg`/`add_version_arg` — and the `--environment default` pre-commit pin (importlib needs the installed packages) | Mirror the nearest existing guard's FULL structure and wiring, not just its check |
| Pointed the membership guard at the WHOLE population (issue #1506 R2 — critical D/NOGO) | R0/R1 set `DOCUMENTED_PACKAGES` to all SEVEN Stable subpackages "for completeness," but only cli/system/version were the issue's named targets and were fully documented | The other four (config/io/logging/utils) have pre-existing PARTIAL tables — `ast`+`awk` showed config 13-in-`__all__` vs ~6 rows, utils 14 vs ~6 — so `find_violations()` returns ~17 findings on the SHIPPED tree: the plan's own `test_live_tree_is_aligned` (asserts `== []`) FAILS, `hephaestus-check-api-table-docs` exits 1 not 0, and the pre-commit `files:` regex would BLOCK every unrelated config/utils PR | Scope the guard's iteration set AND its CI/pre-commit `files:` trigger to exactly the issue's named targets (`{cli, system, version}`); widening to the whole population is YAGNI scope-creep that breaks the guard's OWN acceptance test on the shipped tree |
| Assumed "table exists" meant "table is aligned" (issue #1506 R2 — critical D/NOGO) | R0's module docstring claimed config/io/logging/utils "already have tables," so they were assumed safe to fold into the guard | Presence ≠ completeness: the pre-existing tables do NOT cover their full `__all__`, so the guard's global `find_violations()==[]` assertion is red for them on the shipped tree | Verify completeness (row-count vs `__all__`), never assume presence implies alignment; fix any docstring/plan prose that conflates "exists" with "complete/aligned" |
| Re-confirmed alignment for only the named subset (issue #1506 R2 — process meta-lesson) | Across R0 and R1, alignment was re-checked ONLY for cli/system/version, never for the other members the guard folded in | A guard whose acceptance test asserts a GLOBAL property (`find_violations()==[]`) over a SET cannot be validated by re-confirming a subset — the partially-compliant siblings stay an unmeasured blind spot through two review rounds | Run/measure the global assertion over the ENTIRE iteration set before claiming it passes; MEASURE compliance of every member, not just the issue's targets, BEFORE the guard iterates the population |
| Left the guard's scope unlocked by any test (issue #1506 R2 — critical D/NOGO) | R0/R1 had no test pinning `DOCUMENTED_PACKAGES` to the named subset | An innocent future "just add the rest" widening would silently re-red CI for unrelated PRs with no guardrail | Add an explicit equality test (`test_scope_is_three_named_packages` asserting `DOCUMENTED_PACKAGES == {"cli","system","version"}`) that LOCKS the iteration set so a scope-widening fails LOUDLY at test time, converting an implicit scope decision into a reviewed one |

## Results & Parameters

**Reusable function signature (copy-paste ready):**

```python
def verify_crash_bundle(log_dir: Path) -> tuple[str, str]:
    """Return (verdict, detail). Strictly read-only; never creates log_dir."""

# Verdict constants:
BUNDLE_OK = "OK"
BUNDLE_RAN_WITH_ERRORS = "RAN_WITH_ERRORS"
BUNDLE_NOT_RUN = "NOT_RUN"
VERIFY_SIGNAL_LOST_EXIT = 3
```

**Prefix-anchored classifier core:**

```python
def _message_is_wrote(ln: str) -> bool:
    parts = ln.split(maxsplit=1)  # "<iso-timestamp> <message>"
    return len(parts) == 2 and parts[1].startswith("wrote ")
```

**Read-only resolution (NO mkdir):**

```python
target = next((Path(c) for c in cleaned if Path(c).is_dir()), Path(cleaned[-1]))
```

**CLI exit contract:** `--verify` exits `0` if the handler provably ran (`OK` or `RAN_WITH_ERRORS`), else `3` (`NOT_RUN`). JSON envelope on the blocking case:

```json
{"status": "error", "exit_code": 3, "message": "...", "verdict": "NOT_RUN"}
```

**Verdict → exit-code mapping:**

| Verdict | Meaning | Exit code | Blocking? |
| --------- | --------- | ----------- | ----------- |
| `OK` | a `wrote` line present (WARNING allowed) | 0 | no |
| `RAN_WITH_ERRORS` | handler ran, no success line | 0 | no |
| `NOT_RUN` | log missing / empty / unreadable | 3 | **yes** |

**Generalization (the durable, reusable pattern):** This applies to ANY documented "absence of artifact X means stage Y never ran" convention. Make it an **importable, tested predicate + a CLI verify mode** with a **distinct blocking exit code**; **resolve inputs read-only** (never fabricate the signal); **anchor any log/marker parsing** on a stable prefix rather than a free substring scan; and **keep all copies of the documented contract in sync**. The blocking decision is "was the SIGNAL lost," not "did the underlying operation succeed."

**Bidirectional-invariant generalization (v1.1.0, unverified):** For any structural "X mirrors Y" invariant, a guard has TWO directions and the existing one usually asserts only the forward one (`src - test`). The reverse direction (`test - src - allowlist`) is the silent drift surface — confirm which direction the checker asserts and ADD the missing one. Re-derive any "N violate" audit count empirically (`comm -23`) rather than trusting it. Encode legitimate exceptions as a **sanctioned `frozenset` allowlist with per-entry rationale** (never delete real coverage), reuse the **same dir-filtering helper for both directions**, **sync prose and code**, and **ride the already-wired gate** (no new CI job). Cover the new negative-path branch so module coverage stays above the gate.

**Ghost-directory generalization (v1.7.0, verified-local for the #1448 instance):** A name-only mirror gap — a `tests/unit/<pkg>/` and a `hephaestus/<pkg>/` that share a name but BOTH are content-free shells — is a CONTENT-aware variant of the bidirectional-mirror invariant. ProjectHephaestus #1448 / PR #1703 EXECUTED it end-to-end (the first verified instance of this sub-pattern): `check_no_ghost_packages(src_root, test_root) -> (ok, ghosts)` was added as a 4th check inside the already-required `check_test_structure` orchestrator, riding the existing `hephaestus-check-test-structure` gate with NO new CI job; tests + `pre-commit run --all-files` passed locally (42 tests, target module 91.37% coverage), CI on PR #1703 pending so this is `verified-local` not `verified-ci`. Durable rules: (1) a ghost is an `__init__.py`-only SHELL pair — source has no module beyond `__init__.py` AND test dir has no `test_*.py`; (2) the predicate intersects `_get_subpackages(src) & _get_subpackages(test)`, and `_get_subpackages` pre-filters out dirs with no Python source (`__pycache__`-only / stale-`.pyc`), so the audit's literal stale-`.pyc` directory is NOT enumerable and is intentionally out of scope; (3) **when a guard's population is pre-filtered, the in-scope failure fixture MUST satisfy that pre-filter on BOTH sides** — a bare test dir is filtered out and the test passes vacuously, so add `__init__.py` on both sides; (4) confirm the coverage-altitude split in practice — a helper-altitude test (incl. a `*_real_repo_has_no_ghosts` so the gate ships green) PLUS an orchestrator-altitude `capsys` failure test driving the stderr print loop; (5) document the guard's narrower-than-audit scope at the point of definition (an inline comment at the population-intersection line) so a future reader doesn't expect detection the guard intentionally omits (POLA); (6) re-derive the audit's described ground state — the literal `git/` dirs were already gone, the durable fix was the structural mirror gap, not a file deletion. The OTHER plan-only sub-patterns (#1506/#1507/#1516 and the #1543 allowlist reverse-check) remain UNVERIFIED.

**Commit-trailer generalization (v1.3.0, unverified):** A documented commit-message-TRAILER convention (DCO `Signed-off-by:`, `Co-Authored-By:`, etc.) enforced only in prose is the same executable-convention-guard pattern. Ship a stdlib predicate + a **dual gate** (a step in an already-wired required CI job + a `commit-msg` pre-commit hook) — do NOT add a new workflow. Mirror the repo's existing sibling checker VERBATIM (`scripts/check_conventional_commit.py`: `validate_*()` + `_*_from_args()` + `main() -> int`, exit 0/1, dual file-path + stdin `-` invocation). Trailers live in the message BODY, so consume the FULL `.commit.message` (already fetched by pr-policy — reuse `commits.json`, no new GraphQL); NUL-join multi-line records (`jq -j ... + "\x00"`) so they survive stdin. Anchor on a line prefix + structural shape (`^Signed-off-by: .+ <…@…>$`), never a free substring scan, so a bare `Signed-off-by:` fails. Strip `#`-comment lines in `commit-msg` file-path mode (git strips them; `git commit -s` may append the trailer below the comment block). Exempt bot authors identically to the sibling checks (`dependabot[bot]` short-circuit). Mind the self-application bootstrap — the implementing commit must use `git commit -s -S` or the new hook blocks its own creation. **Most-uncertain assumptions (all UNVERIFIED): the `jq` NUL round-trip, the cited line numbers, and the pr-policy step-id/`commits.json` filename must each be empirically confirmed before merge.**

**Coverage-altitude generalization (v1.2.0, unverified):** A tested low-level predicate does NOT cover the integration-level branch that consumes it. When a pure helper is wired into an orchestrator, a helper-only unit test leaves the orchestrator's failure branch (its `sys.stderr` print loop + remediation hint) unexecuted — which can drop module coverage below the line-coverage gate (83%) even though the logic is "tested." Add a SEPARATE orchestrator-altitude failure test using `capsys` that asserts both the offending name AND the remediation hint on stderr, mirroring the sibling failure tests for the other checks in the same orchestrator (add a Check-N-failure test at the same altitude as the existing Check-1/Check-2 tests). Demote any tree-mutating manual negative test below the unit test and wrap it in a `trap '... rmdir' EXIT` subshell. When a new allowlist/skip set shares names with an existing one on a different axis (e.g. `docs`/`scripts` in both the source-detection `skip` set and the test-dir allowlist), add an inline comment naming the distinct axis (POLA).

**NOGO→GO-tightening generalization (v1.4.0, unverified):** A plan reviewer can grade the DESIGN sound (guard scope justified, bidirectional check correct, import-surface safe) and STILL return B / NOGO purely on MINOR tightenings. Converging is anticipating those tightenings, not redesigning. The recurring set: (1) **negative-branch coverage must be DEDICATED, not incidental** — a guard with an error/empty verdict (`table-not-found`, "no rows parsed") needs a test whose fixture's whole purpose is to trigger that verdict for ALL inputs, because incidental coverage (one input present makes the rest report the error as a side effect) reads as "covered" but still NOGOs; (2) **test the argparse default branch explicitly** — `main(["--repo-root", X])` never exercises the `args.repo_root or get_repo_root()` fallback; add a `main([])` test with the default resolver monkeypatched; (3) **verify the testability precondition before promising the test** — confirm the default resolver accepts the no-arg call (`get_repo_root(start_path=None)`) before promising `main([])` works; (4) **inferred data in a user-facing cell needs an inline honesty caveat, not just a guard that skips validating it** (POLA — necessary but not sufficient to merely not-validate a fabricated field); (5) **pre-emptively harden a "fragile but backstopped" hand-rolled parser flagged at MINOR** (named separator-regex constant + an explicit next-top-level-section `## ` break in addition to the `### ` break) while keeping the live-tree alignment test as the real backstop. Carry-forward risks the reviewer should still focus on: the inferred version anchors remain inferred (only membership is CI-enforced); the parser is still hand-rolled (alignment test is the backstop, regex hardening only narrows known modes); the guard's `importlib.import_module` of stable subpackages MUST run in the `default` pixi env (pre-commit `entry` pins `--environment default`).

**Doc-table↔code membership-guard generalization (v1.5.0, unverified):** The bidirectional-membership-guard pattern applies to a DOC-TABLE↔CODE invariant, not just test-dir↔src-dir mirrors. `api_table_docs.py` (ProjectHephaestus #1507 — the FIRST issue to actually create it, after #1506's plan never merged: `test -f` confirmed it absent) cross-checks each ``### `hephaestus.<pkg>` `` table in `COMPATIBILITY.md` against `importlib.import_module(pkg).__all__`, emitting `missing-from-docs` (in `__all__`, no row — including deprecated members like `retry_with_jitter`) AND `missing-from-all` (row exists, not in `__all__`). It mirrors `cli_tier_docs.py` EXACTLY (dataclass finding, parse fn, `find_violations` fn, `main() -> 0/1`, `add_json_arg`/`add_version_arg`). Durable rules: (1) **guard a MIXED table by membership only** — assert the verifiable column (symbol membership) and NEVER the unverifiable one (the `git log -S`-inferred "Added" version), or you assert fiction; (2) add a defensive **`parser-found-no-rows`** finding so a header-present-but-empty table fails loud instead of reporting every symbol as missing (same anti-regression guard `cli_tier_docs` uses); (3) pin the pre-commit `entry` to `pixi run --environment default` because the guard imports packages via `importlib` and the lint env lacks them; (4) the reciprocal-gate cost recurs — registering `hephaestus-check-api-table-docs` in `[project.scripts]` trips the sibling `cli_tier_docs` guard unless a `| hephaestus-check-api-table-docs | Internal | ... |` Console-Script Stability Tiers row is added. All UNVERIFIED — plan only, no code/tests/CI.

**Scope-a-membership-guard generalization (v1.6.0, unverified):** An executable membership/coverage guard that ITERATES a population (all packages / dirs / files of a kind) and asserts a GLOBAL property (`find_violations()==[]`) over the whole set MUST be scoped to the issue's NAMED targets — never the whole population — when sibling members are only PARTIALLY compliant; otherwise the guard fails its OWN acceptance test on the shipped tree (the #1506 R2 critical D/NOGO: folding all seven Stable subpackages in made ~17 `missing-from-docs` findings fire because config/io/logging/utils have pre-existing PARTIAL tables, so `test_live_tree_is_aligned` fails, `hephaestus-check-api-table-docs` exits 1, and the pre-commit `files:` regex would block unrelated config/utils PRs). The durable rules: (1) BEFORE the guard iterates, MEASURE compliance of EVERY member (`ast` for `__all__`, row-count for tables), not just the issue's targets; (2) scope BOTH the iteration set AND the CI/pre-commit `files:` trigger to the named targets (`{cli, system, version}`) — widening is YAGNI scope-creep AND breaks the acceptance test; (3) LOCK the scope with an explicit equality test (`DOCUMENTED_PACKAGES == {…}`) so a future "just add the rest" widening fails LOUDLY; (4) this is the EXECUTABLE-GUARD corollary of the audit-survey rule (a survey notes non-compliant siblings out-of-scope; an executable guard must literally NOT iterate over them); (5) "artifact EXISTS" ≠ "artifact is COMPLETE/aligned" — verify completeness (row-count vs `__all__`), fix any docstring/plan prose that conflates presence with alignment. **Process meta-lesson:** the defect survived R0 and R1 because alignment was re-confirmed ONLY for the named subset — when an acceptance test asserts a global property over a SET, you must run/measure it over the ENTIRE set before claiming it passes; re-confirming a subset is not sufficient.

## Verified On

| Repository | Issue / PR | What was applied |
| ------------ | ------------ | ------------------ |
| ProjectHephaestus | issue #1207 / PR #1247 | coredump handler `verify_crash_bundle` + `--verify` mode; exit 3 distinct from argparse 2; read-only no-fabricate resolution; prefix-anchored log classification |
| ProjectHephaestus | issue #1543 (PLAN — **unverified**) | bidirectional mirror sub-pattern: reverse check `test_packages - src_packages - allowlist` added to existing `check_test_structure()`; sanctioned `frozenset` allowlist with per-entry rationale; prose + code synced; rides already-wired gate (no new CI job) |
| ProjectHephaestus | issue #1448 / PR #1703 (**verified-local** — tests + pre-commit green locally, CI pending) | ghost-directory variant of the bidirectional-mirror sub-pattern, EXECUTED end-to-end: `check_no_ghost_packages(src_root, test_root) -> (ok, ghosts)` added as a 4th check inside the already-required `check_test_structure` orchestrator, riding the existing `hephaestus-check-test-structure` gate (pre-commit `check-unit-test-structure` + `_required.yml`/`test.yml`), NO new CI job. Ghost = an `__init__.py`-only shell pair (source has no module beyond `__init__.py` AND test dir has no `test_*.py`); intersects `_get_subpackages(src) & _get_subpackages(test)`, whose pre-filter excludes `__pycache__`-only dirs — so the audit's literal stale-`.pyc` `tests/unit/git/` is out of scope. Key fixture lesson: a bare test dir is filtered out and detects nothing — fixture must add `__init__.py` on BOTH sides. Helper-altitude `TestCheckNoGhostPackages` (incl. `test_real_repo_has_no_ghosts`) + orchestrator-altitude `capsys` `test_ghost_package_fails`; module reached 91.37% coverage, 42 tests passed; 3-line scope comment at `shared = ...` per a PR-review thread |
| ProjectHephaestus | issue #1543 re-plan (PLAN — **unverified**, post-NOGO) | coverage-altitude lesson: orchestrator-vs-helper test gap — helper-only tests leave the orchestrator's stderr print loop uncovered under the 83% gate; add a `capsys` orchestrator-altitude failure test asserting dir name + remediation hint; `trap ... EXIT` for any tree-mutating manual test; POLA inline comment for cross-axis allowlist name collisions |
| ProjectHephaestus | issue #1506 R1 re-plan (PLAN — **unverified**, post-NOGO) | NOGO→GO-tightening sub-pattern: R0 plan for per-symbol API tables in `COMPATIBILITY.md` + bidirectional `api_table_docs.py` guard (mirroring `cli_tier_docs.py`) graded B/NOGO despite a sound design; R1 added a DEDICATED `table-not-found` negative-branch test (doc with no parseable tables → every package), a `test_main_repo_root_default` exercising the `args.repo_root or get_repo_root()` fallback via `main([])` (precondition verified: `get_repo_root(start_path=None)` at `helpers.py:99`), an inline honesty caveat above each inferred-"Added"-version table (POLA), and parser hardening (named separator regex + `## ` next-section break) backstopped by the live-tree alignment test |
| ProjectHephaestus | issue #1506 R2 (PLAN — **unverified**, critical D/NOGO on R1) | scope-a-membership-guard sub-pattern: R1 set `DOCUMENTED_PACKAGES` to all SEVEN Stable subpackages; R2 found config/io/logging/utils have pre-existing PARTIAL tables (config 13-in-`__all__` vs ~6 rows, utils 14 vs ~6 — measured via `ast`+`awk`), so `find_violations()` returns ~17 findings on the shipped tree, `test_live_tree_is_aligned` (asserts `== []`) FAILS and the pre-commit `files:` regex would block unrelated config/utils PRs; fix scopes the iteration set + `files:` regex to `{cli, system, version}`, adds a `test_scope_is_three_named_packages` scope-lock, and corrects the docstring's false "already have tables" claim (they have PARTIAL tables) |
| ProjectHephaestus | issue #1516 (PLAN — **unverified**) | commit-trailer sub-pattern: stdlib `scripts/check_dco_signoff.py` (mirrors `check_conventional_commit.py`) enforcing DCO `Signed-off-by` via a dual gate (pr-policy Check 4 + `commit-msg` hook); consume FULL `.commit.message` (reuse `commits.json`, NUL-joined); prefix+structure-anchored `^Signed-off-by: .+ <…@…>$`; strip `#`-comment lines in file-path mode; exempt `dependabot[bot]`; `git commit -s -S` to survive self-application |
| ProjectHephaestus | issue #1507 (PLAN — **unverified**) | doc-table↔code membership-guard sub-pattern: FIRST issue to actually create `hephaestus/validation/api_table_docs.py` (after #1506's plan never merged — `test -f` confirmed absent); bidirectional membership check of each ``### `hephaestus.<pkg>` `` COMPATIBILITY.md table vs live `__all__` (`missing-from-docs` incl. deprecated members like `retry_with_jitter` + `missing-from-all`); mirrors `cli_tier_docs.py` exactly (dataclass + parse fn + `find_violations` + `main()→0/1` + `add_json_arg`/`add_version_arg`); guards MEMBERSHIP ONLY (never the inferred "Added" column); defensive `parser-found-no-rows`; `--environment default` pin; reciprocal Console-Script Stability Tiers row for `hephaestus-check-api-table-docs` |

## Tags

`#executable-convention` `#invariant-guard` `#exit-code-collision` `#fail-safe` `#read-only-verification` `#log-line-anchoring` `#observability` `#cli-verify-mode` `#ci-gate` `#bidirectional-invariant` `#mirror-parity` `#allowlist-with-rationale` `#test-structure` `#commit-trailer` `#dco-signoff` `#precommit-hook` `#sibling-checker-mirror` `#coverage-altitude` `#negative-branch-test` `#argparse-default-branch` `#nogo-tightening` `#inferred-data-honesty` `#doc-table-code-parity` `#membership-only-guard` `#guard-scope-population` `#partial-compliance` `#scope-lock-test` `#ghost-directory-guard` `#prefiltered-population-fixture` `#hephaestus`
