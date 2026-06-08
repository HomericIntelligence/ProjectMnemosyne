---
name: ruff-specific-rule-fixes
description: "Patterns for fixing specific Ruff lint rule violations and addressing systemic linter policy failures. Use when: (1) fixing Ruff S101 violations in production code by replacing bare assert guards with explicit RuntimeError raises, (2) fixing Ruff C901 cyclomatic complexity violations by extracting helper functions, (3) the same policy violation reappears in two or more independent documents or configs — indicating the linter/validator that should enforce the policy is absent or misconfigured (root-cause fix: add the lint rule, not re-fix every instance), (4) deciding between adding a noqa suppression, fixing the violation, or promoting the rule to error-level enforcement."
category: tooling
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: ruff-specific-rule-fixes.history
tags:
  - ruff
  - lint
  - S101
  - C901
  - assert
  - runtimeerror
  - cyclomatic-complexity
  - method-extraction
  - noqa
  - linter-policy
  - root-cause
  - pre-commit
---

# Ruff-Specific Rule Fixes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Consolidate the concrete patterns for fixing specific Ruff rule violations (S101 assert-in-production, C901 cyclomatic complexity) and the systemic principle that recurring policy violations are a linter-configuration bug, not N independent file bugs |
| **Outcome** | ✅ Verified across ProjectScylla and ProjectHephaestus — S101 fully eliminated from production source, C901 functions extracted below the limit, wrong-direction linters re-sequenced as root-cause fixes |
| **Verification** | verified-ci |

## When to Use

Use this skill when:

- **S101 (assert in production)**: Ruff reports `S101` (`use of assert`) in production source, or you see `assert x is not None  # noqa: S101` suppressions in non-test code. `assert` is unsafe in production because Python's `-O` flag disables it; legitimate runtime guards must `raise`.
- **C901 (cyclomatic complexity)**: pre-commit or CI fails with `... is too complex (N > 10)`, or adding conditional blocks pushes an existing function over the C901 limit.
- **Recurring policy violation**: an audit flags the SAME policy violation in 2+ independent files/configs — the linter that should enforce the policy is the FIRST suspect (absent, misconfigured, or wrong-direction). Fix the linter before re-fixing every instance.
- **Suppress vs. fix vs. enforce**: deciding between adding a `noqa`, fixing the violation, or promoting the rule to error-level enforcement.

## Verified Workflow

### Quick Reference

```bash
# --- S101: find & eliminate assert guards in production code ---
grep -rn "noqa: S101" <src>/                 # must end empty for production code
# Replace each:  assert x is not None  ->  if x is None: raise RuntimeError(...)

# --- C901: find & extract over-complex functions ---
# CI error:  _fn is too complex (11 > 10)
# Extract self-contained conditional blocks into module-level / instance helpers.
pre-commit run --all-files                   # ruff C901 + any custom CC hook

# --- Systemic: same rule violated in >=2 unrelated files ---
audit_output | grep "Rule: <id>" | awk '{print $2}' | sort -u | wc -l   # >=2 => linter suspect
grep -rn "<rule-keyword>" <validation-module>/ <validation-tests>/      # locate linter
grep -n  "<rule-keyword>" CLAUDE.md CONTRIBUTING.md                     # locate META policy
# If linter disagrees with META: fix linter PR FIRST, dependent fixes SECOND.

# Ruff format reflows the longer if/raise form — run pre-commit TWICE.
```

### Detailed Steps

#### A. Fixing Ruff S101 — assert guards → RuntimeError

1. **Discovery.** Find every suppression in production code (exclude legitimate test asserts):

   ```bash
   grep -rn "noqa: S101" <src>/ <scripts>/
   # broader view including tests:
   grep -rn "noqa: S101" <src>/ <scripts>/ tests/
   ```

   Grep reveals the real current line numbers — issue line numbers are often stale.

2. **Classify each site** and pick the replacement:

   | Assert pattern | Replacement |
   | --------------- | ------------- |
   | `assert x is not None` | `if x is None: raise RuntimeError("x must be set before calling <method>")` |
   | `assert x is not None, "msg"` | `if x is None: raise RuntimeError("msg")` (reuse the message verbatim) |
   | `assert cond` guarding logic | `if not cond: raise RuntimeError("<cond description>")` |
   | `assert x is not None` before `raise x` (for-else) | `if x is None: raise RuntimeError("invariant msg")` then `raise x` |

3. **Apply the minimum targeted edit** — no surrounding refactor:

   ```python
   # BEFORE
   assert self.experiment_dir is not None  # noqa: S101
   return self.experiment_dir / "checkpoint.json"

   # AFTER
   if self.experiment_dir is None:
       raise RuntimeError("experiment_dir must be set before getting checkpoint path")
   return self.experiment_dir / "checkpoint.json"
   ```

   Message format: `"<attribute> must be set before <operation it blocks>"` — describe the blocked
   operation, not just the restated condition.

4. **For-else defensive invariant** (common idiom — keep the guard, do not delete it):

   ```python
   # BEFORE:
   for _attempt in range(max_attempts):
       try:
           result = parse(response)
           break
       except ValueError as e:
           last_parse_error = e
   else:
       assert last_parse_error is not None  # noqa: S101
       raise last_parse_error

   # AFTER:
   else:
       if last_parse_error is None:
           raise RuntimeError("Retry loop exhausted but last_parse_error is None")
       raise last_parse_error
   ```

5. **Add regression tests** (extend existing test classes; no new files unless required):

   ```python
   def test_method_raises_if_x_none(self, tmp_path: Path) -> None:
       """<method> raises RuntimeError when <attr> is None."""
       obj = MyClass(attr=None, ...)
       with pytest.raises(RuntimeError, match="attr must be set before calling method"):
           obj.method()
   ```

   For logically-unreachable guards (the for-else case), test the **observable adjacent
   behavior** instead of contriving a path into the guard:

   ```python
   def test_raises_value_error_not_runtime_error_when_parse_fails(self, tmp_path: Path) -> None:
       """All retries fail with ValueError -> ValueError re-raised (guard never fires)."""
       bad = "Not valid JSON at all"
       with pytest.raises(ValueError):
           self._run_with_call_side_effects(tmp_path, [(bad, "", bad)] * 3)
   ```

6. **Verify, format, commit.** S101 grep must be empty; run pre-commit twice (Ruff format
   reflows the longer `if/raise` form on the first pass):

   ```bash
   grep -rn "noqa: S101" <src>/            # must be empty
   pre-commit run --all-files              # may reformat: "files were modified"
   pre-commit run --all-files              # all hooks Passed
   pixi run python -m pytest tests/ -q
   ```

#### B. Fixing Ruff C901 — extract helper functions

1. **Identify the violation.** CI shows the function and its score, e.g.
   `_restore_run_context is too complex (11 > 10)`.

2. **Count branches.** A function starts at CC=1; each `if`/`elif`/`else`/`for`/`while`/`except`/`and`/`or` adds +1.

   | CC | Status | Action |
   | -- | ------ | ------ |
   | 1–7 | Safe | Can add 1–3 branches freely |
   | 8–9 | Warning zone | One more block hits the limit |
   | 10 | At limit | Any new branch fails CI |
   | 11+ | Failure | Must extract helpers |

3. **Extract self-contained conditional blocks** — those with their own imports, operating on a
   clear parameter subset, sharing no mutable state beyond a context object:

   ```python
   # Parent keeps the guard clause, delegates the body. Helper gets a fresh CC budget (starts at 1).
   if is_at_or_past_state(run_state, RunState.JUDGE_COMPLETE) and ctx.judgment is None:
       _restore_judgment(ctx)

   def _restore_judgment(ctx: Any) -> None:
       """Restore ctx.judgment from on-disk judge result."""
       from <module> import _has_valid_judge_result, _load_judge_result
       judge_dir = get_judge_dir(ctx.run_dir)
       if _has_valid_judge_result(ctx.run_dir):
           ctx.judgment = _load_judge_result(judge_dir)
   ```

4. **Multi-pass rendering — return-value threading.** When a method has sequential passes where
   each computes state feeding the next, extract each pass into an instance method that returns
   the next offset (avoids shared mutable state):

   ```python
   # AFTER: each pass ~20-25 lines, CC < 10, no noqa needed
   def _refresh_display(self, screen, height, width):
       start_row = 0
       start_row = self._draw_workers(start_row, height, width)
       start_row = self._draw_separator(start_row, height, width)
       start_row = self._draw_logs(start_row, height, width)

   def _draw_workers(self, start_row: int, height: int, width: int) -> int:
       ...
       return next_row
   ```

   Test each helper independently for boundary handling and return values:

   ```python
   def test_draw_separator_at_boundary(self):
       rows = self.display._draw_separator(start_row=8, height=10, width=80)
       assert rows == 9 and rows <= 10
   ```

5. **Verify locally** (both ruff C901 and any custom CC hook must pass):

   ```bash
   pre-commit run --all-files
   pixi run python -m pytest tests/unit/<area>/ -x -q
   ```

   Do **not** reach for `# noqa: C901` — extract-method is the correct fix. Projects that prohibit
   `--no-verify` and lint suppression require the real refactor.

#### C. Systemic — linter as root cause of repeated violations

When an audit flags the SAME rule in **2+ unrelated files**, the file-count (not line-count) is
the signal: two violations in one file are a localized bug; two violations in two unrelated
directories are a systemic linter bug.

1. **PAUSE — do not open per-file fix PRs yet.** Tally findings by rule ID:

   ```bash
   audit_output.json | jq -r '.findings[].rule' | sort | uniq -c | sort -rn
   ```

2. **Locate the linter** that enforces the rule (read its accept-list AND reject-list / good AND
   bad pattern):

   ```bash
   grep -rn "<rule-keyword>" <validation-module>/ <validation-tests>/ scripts/lint_*.py
   ```

3. **Locate the META source** the rule purports to enforce, and read it verbatim:

   ```bash
   grep -n "<rule-keyword>" CLAUDE.md CONTRIBUTING.md README.md
   ```

4. **Diff linter vs. META:**

   | Linter says | META says | Verdict |
   | ----------- | --------- | ------- |
   | Accept X, reject Y | Require X, prohibit Y | Linter correct → violations are real, do per-file fixes |
   | Accept Y, reject X | Require X, prohibit Y | **Linter wrong-direction → fix linter FIRST** |
   | No assertion | Require X, prohibit Y | Linter gap → add the rule, then fix files |

   If wrong-direction, the dependent files were written to comply with the wrong linter — they are
   downstream consumers of a wrong contract, not independently buggy.

5. **Re-sequence the PRs.** Linter fix (validator + flipped test assertions, as one atomic PR)
   lands FIRST; dependent doc/config fixes land SECOND, each re-running CI on top of the merged
   linter. Add pair-direction regression tests so future drift is caught:

   ```python
   def test_accepts_required_pattern():
       assert validator.is_valid("<required-pattern>")

   def test_rejects_prohibited_pattern():
       assert not validator.is_valid("<prohibited-pattern>")
   ```

   A single-direction test is insufficient — a contributor with the same wrong mental model could
   re-flip it. If BOTH linter and META are wrong, the deployed configuration (e.g.
   `gh api repos/<owner>/<repo>/branches/<branch>/protection`) is the ultimate source of truth:
   fix META first, then linter, then dependents.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Suppress C901 with `# noqa: C901` | Considered suppressing the complexity warning instead of refactoring | Project policy prohibits `--no-verify` and lint suppression; suppression hides the design smell | Extract-method is the correct fix, not suppression |
| Inline all restore logic in one function | Added new `if` blocks to a function already near the limit | CC went from ~8 to 11, exceeding the C901 limit of 10 | Check the CC budget before adding conditional blocks to functions near the limit |
| Delete the for-else `assert last_parse_error is not None` instead of converting | Considered removing the "unreachable" guard entirely | Removing the invariant check loses protection against future code changes that break the invariant | Convert defensive invariants to `if x is None: raise RuntimeError(...)`, do not delete them |
| Contrive a test that reaches the unreachable guard path | First S101 test attempt used a `StopIteration` trick to trigger the for-else guard | The guard is logically unreachable in normal operation; the contrived test was brittle | Test observable adjacent behavior (normal retry path with exhausted attempts) instead |
| Open N parallel PRs to fix N files violating the same rule | 2 PRs to fix two skill files for a merge-strategy policy | The linter was wrong-direction (required the wrong pattern, rejected the correct one); each PR would fail CI | When ≥2 files violate the same rule, the linter is the FIRST suspect — read its definition first |
| Fix the linter and the dependent files in one mega-PR | Bundled validator + doc corrections together | Different test surfaces make CI feedback ambiguous when either side fails | Keep the linter fix atomic; land dependent fixes afterward |
| Flip only the validator code, not its tests | Planned to update the validator without its test assertions | The validator's own tests still asserted the wrong direction → linter PR itself fails CI | Validator source + tests are a single atomic change; flip them in lock-step |
| Single-direction regression test only | Asserted only that the correct pattern is accepted | A future contributor could re-flip the assertion and ship the wrong direction again | Pair tests: assert correct accepted AND wrong rejected |
| Trust the stale issue line numbers | Edited at the line numbers listed in the issue | Code had evolved; the issue listed 6 asserts but grep found 10 | Always grep for current locations; the deliverable ("no S101 in file X") defines scope, not the line list |

## Results & Parameters

### S101 elimination (ProjectScylla)

```text
PR #1142 (#1066): 16 asserts replaced across runner.py + stages.py; 16 noqa removed; 3185 tests pass, 78.09% cov
PR #1211 (#1143): 4 remaining sites converted (workspace_manager, llm_judge, executor/runner); 3261 tests pass, 78.39% cov
S101 suppressions in production src: 0 (eliminated)
```

S101 replacement reference (representative — full table in history):

| Location | Variable | Error Message |
| -------- | -------- | ------------- |
| `runner.py:_get_checkpoint_path` | `self.experiment_dir` | "experiment_dir must be set before getting checkpoint path" |
| `stages.py:finalize_run` | `ctx.agent_result` | "agent_result must be set before finalize_run" |
| `workspace_manager.py:_checkout_commit` | `self.commit` | "commit must be set before calling _checkout_commit" |
| `llm_judge.py` retry-loop else | `last_parse_error` | "Judge retry loop exhausted but last_parse_error is None" |
| `executor/runner.py:_finalize_test_summary` | `self._state` | "_state must be initialized before finalizing test summary" |

### C901 configuration & results

- **Ruff C901**: `max-complexity = 10` (in `pyproject.toml` or `.pre-commit-config.yaml`).
- **Custom hook**: a separate `Check Cyclomatic Complexity` pre-commit hook may run at the same
  threshold — both must be green.

```text
ProjectScylla   #1546: _restore_judgment() + _restore_run_result() extracted from _restore_run_context(); CC 11 -> ~7
ProjectHephaestus #1050: _draw_workers/_draw_separator/_draw_logs extracted from _refresh_display(); 69 lines -> 3 methods; 8 -> 23 tests; removed # noqa: C901
```

### Systemic linter re-sequencing (ProjectHephaestus 2026-05-31)

| PR | Target | Order |
| -- | ------ | ----- |
| #863 | `validation/doc_policy.py` — flip `POLICY_RULES` to correct direction + flip tests | MERGED first (root cause) |
| #865 | `README.md` + `CONTRIBUTING.md` examples | after #863 |
| #866 / #867 | dependent skill files | after #863 |

Decision matrix — suppress vs. fix vs. enforce:

| Situation | Action |
| --------- | ------ |
| Single legitimate exception (e.g. test asserts) | `# noqa` is acceptable |
| Real production bug / design smell | Fix the violation (convert assert, extract method) |
| Same violation in ≥2 unrelated files | Fix/add the linter rule (root cause), then fix instances |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | S101 assert→RuntimeError migration in e2e/executor modules | PRs #1142 (#1066), #1211 (#1143) |
| ProjectScylla | C901 extract-method on `_restore_run_context()` | PR #1546 |
| ProjectHephaestus | C901 multi-pass rendering extraction on `_refresh_display()` | PR #1050 |
| ProjectHephaestus | Wrong-direction linter root-cause re-sequencing (merge-strategy policy) | PRs #863, #865, #866, #867 |
