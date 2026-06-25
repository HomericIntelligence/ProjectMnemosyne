---
name: architecture-executable-convention-guard-pattern
description: "Turn an un-guarded documented invariant (a prose convention) into a tested, blocking, reusable executable check that CI or any consumer can call. Use when: (1) a contract like 'absence of artifact X means stage Y never ran' lives only in docstrings/comments and nothing asserts it, (2) you are adding an enforcement gate whose whole purpose is signal fidelity and must pick a collision-free exit code distinct from argparse's usage-error 2 and sibling CLIs, (3) a verification step must resolve its inputs strictly read-only and must NOT fabricate the very signal whose absence it checks (e.g. a resolver that mkdir()s the directory), (4) you classify a log/marker line and must anchor on the line prefix instead of a free substring scan vulnerable to user-controlled tokens, (5) you relax argparse requirements (nargs='?') for a new mode and must re-guard the original mode so it does not silently no-op, (6) the same convention is documented in two places (module docstring + sibling shell comment) and must be kept in sync when made executable, (7) you are planning a fix for any 'X mirrors Y' / parity / directory-structure invariant audit finding and must determine WHICH direction(s) the existing guard asserts — the defect is usually the un-asserted reverse direction (test_packages - src_packages), and the fix is an allowlist-with-rationale plus the reverse check, NOT deletion of flagged items."
category: architecture
date: 2026-06-24
version: "1.1.0"
user-invocable: false
verification: verified-local
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

> **Warning:** This sub-pattern (added in v1.1.0 from ProjectHephaestus issue #1543) is **unverified** — it is a PLAN, the code was NOT executed or CI-validated. Treat as a hypothesis until CI confirms. The v1.0.0 coredump material above remains `verified-local`.

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Reuse exit code 2 | Used `2` for the invariant violation | Collides with argparse usage-error `2` and a sibling CLI's `2` — a CI gate can't tell "signal lost" from "bad command line" | Grep existing exit codes (`grep -rn "return [0-9]"`), pick a distinct code, name it with a constant (`VERIFY_SIGNAL_LOST_EXIT = 3`) |
| Trust the audit's "5 dirs" count | Planned the fix against the audit finding's stated number of violating dirs | Ground-truth `comm -23` found only 4 real violations — the 5th (`scripts_lib/`) IS mirrored by a same-named source subpackage, so it is not a violation | Re-derive the violation set empirically with `comm -23` of the two dir listings; plan against ground truth and note the discrepancy explicitly |
| Assume the existing guard was bidirectional | Took for granted that `check_test_structure()` enforced both directions of the mirror | It only enforced the FORWARD direction (`src_packages - test_packages`); the reverse (`test_packages - src_packages`) was silently unguarded — the actual drift surface | Grep the checker and confirm WHICH direction(s) it asserts; the defect is the un-asserted direction. Add the reverse check, do not rewrite the forward one |
| Delete the flagged test dirs | Considered removing the dirs that broke the mirror | The flagged dirs are intentional (test coverage for non-package targets: top-level `scripts/`, `docs/`, a single-file module); deletion drops real test coverage | Use a sanctioned `frozenset` allowlist with an inline rationale per entry; a NEW unsanctioned dir then fails the gate, forcing an explicit decision |
| Assert `status == 2` | Test asserted the JSON envelope as `payload["status"] == 2` (a number) | `emit_json_status` sets `status` to the STRING `"ok"`/`"error"` and puts the numeric code in `exit_code` — the assert always failed | Read the envelope helper's source before asserting its shape; assert `status=="error"`, `exit_code==3`, and the custom field via `**extra` |
| Call `resolve_target_dir()` in verify mode | Reused the normal resolver to find the log dir | It does `mkdir(parents=True, exist_ok=True)`, fabricating the very directory whose absence is the signal | Verification must be strictly read-only; inline a no-mkdir resolution and test that the dir is NOT created |
| Classify success via `" wrote " in line` | Free substring scan over every log line | Misclassifies an `ERROR:` line whose path embeds `" wrote "` as success (exe basename is user-controlled, can contain spaces) | Anchor on the log-line prefix (split timestamp, message `startswith`); add a regression test for the adversarial path |
| Make positionals optional without re-guarding | Set positionals to `nargs="?"` so `--verify` runs without kernel tokens | Silently weakened the capture path — a malformed `core_pattern` line missing tokens no longer errored | When you relax arg requirements for one mode, add an explicit missing-arg guard for the other mode and test it |
| Leave an unneeded `# noqa: SIM103` | Added a noqa the helper didn't actually need | Would trip RUF100 (unused-noqa) | Only add `noqa` for a rule that actually fires |

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

## Verified On

| Repository | Issue / PR | What was applied |
| ------------ | ------------ | ------------------ |
| ProjectHephaestus | issue #1207 / PR #1247 | coredump handler `verify_crash_bundle` + `--verify` mode; exit 3 distinct from argparse 2; read-only no-fabricate resolution; prefix-anchored log classification |
| ProjectHephaestus | issue #1543 (PLAN — **unverified**) | bidirectional mirror sub-pattern: reverse check `test_packages - src_packages - allowlist` added to existing `check_test_structure()`; sanctioned `frozenset` allowlist with per-entry rationale; prose + code synced; rides already-wired gate (no new CI job) |

## Tags

`#executable-convention` `#invariant-guard` `#exit-code-collision` `#fail-safe` `#read-only-verification` `#log-line-anchoring` `#observability` `#cli-verify-mode` `#ci-gate` `#bidirectional-invariant` `#mirror-parity` `#allowlist-with-rationale` `#test-structure` `#hephaestus`
