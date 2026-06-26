---
name: ruff-specific-rule-fixes
description: "Patterns for fixing specific Ruff lint rule violations and addressing systemic linter policy failures. Use when: (1) fixing Ruff S101 violations in production code by replacing bare assert guards with explicit RuntimeError raises, (2) fixing Ruff C901 cyclomatic complexity violations by extracting helper functions, (3) fixing Ruff RUF022 (__all__ not sorted) or I001 (import block un-sorted) — both are [*]-fixable; never manually reorder because isort uses the alias name not the original symbol, always use `ruff check --fix`, (4) the same policy violation reappears in two or more independent documents or configs — indicating the linter/validator that should enforce the policy is absent or misconfigured (root-cause fix: add the lint rule, not re-fix every instance), (5) deciding between adding a noqa suppression, fixing the violation, or promoting the rule to error-level enforcement, (6) main goes red after a ruff/mypy version-floor bump — E501 line-length overruns, ruff-format implicit-string-concat collapses, or unused-ignore mypy errors appear retroactively in files that previously passed CI, (7) a # type: ignore[tag] comment becomes an unused-ignore error after a mypy or ruff floor bump, (8) adding a new scripts/*.py to a repo with an auto-discovering smoke test, or adding a # noqa whose rule may not be in the ruff select list, (9) E501 or ruff format failures appear in newly-added TEST files on a large multi-file feature PR — running only the test suite before pushing misses these; CI fails on line-length or format in the new test files, (10) a CI validate job runs `ruff format --check` and fails with `Would reformat` even though local pytest, pre-push pytest, and `ruff check` passed."
category: tooling
date: 2026-06-26
version: "1.5.0"
user-invocable: false
verification: verified-ci
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
  - linter
  - policy-enforcement
  - root-cause
  - pre-commit
  - RUF022
  - I001
  - __all__
  - import-sort
  - isort
  - autofix
  - E501
  - line-length
  - type-ignore
  - unused-ignore
  - floor-bump
  - toolchain-upgrade
  - retroactive-violation
  - mypy
  - f-string
  - shell-continuation
  - RUF100
  - unused-noqa
  - select-list
  - scripts-smoke-test
  - help-contract
  - D103
  - test-files
  - feature-pr
  - parametrize
  - entry-points
  - add_version_arg
  - format-check
  - validate-ci
  - inference360
---

# Ruff Specific Rule Fixes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-26 |
| **Objective** | Fix specific Ruff rule violations (S101 assert-in-production, C901 cyclomatic complexity, RUF022 `__all__`-sort, I001 import-sort, RUF100 unused-noqa) and recognize when repeated policy violations mean the linter itself is the root cause; honor the auto-discovered scripts smoke `--help` contract; fix E501/ruff-format failures in newly-added test files on large feature PRs |
| **Outcome** | Verified — S101 guards converted across 20+ sites (PRs #1142, #1211), C901 extractions verified (PRs #1546, #1050), wrong-direction linter root-cause pattern verified-CI (PRs #863/#865/#866/#867), RUF022 + I001 fixes (issue #1189); RUF100 unused-noqa + scripts smoke `--help` contract verified-precommit (PR #1250); E501/format in new test files fixed (ProjectHephaestus PR #1035); CI `ruff format --check` failure after local tests/`ruff check` fixed and merged in Inference360 PR #282 |
| **Verification** | verified-ci |
| **History** | [changelog](./ruff-specific-rule-fixes.history) |

## When to Use

- Ruff reports **S101** (`use of assert`) in production code — `assert x is not None  # noqa: S101` precondition guards that must always run (Python's `-O` flag disables `assert`).
- Ruff or a custom hook reports **C901** (`<function> is too complex (N > 10)`) — adding conditional blocks pushed a function over the cyclomatic-complexity limit.
- Ruff reports **RUF022** (`__all__` is not sorted) or **I001** (import block is un-sorted) — both are marked `[*]` fixable by ruff itself.
- The **same policy violation** appears in 2+ independent files/configs — the linter that should enforce the policy is absent, misconfigured, or wrong-direction.
- You are deciding between a `# noqa` suppression, fixing the violation, or promoting the rule to error-level enforcement.
- You are tempted to open N parallel PRs to fix N violating files — pause and check the linter first.
- **main goes red after a ruff/mypy version-floor bump** (e.g., ruff 0.1.x to 0.15): E501 line-length overruns, ruff-format implicit-string-concat collapses, or `# type: ignore[tag]` comments become unused-ignore errors in files that previously passed CI.
- A `# type: ignore[tag]` comment fires mypy error `[unused-ignore]` after a mypy floor bump — the annotation was covering a type error that no longer exists in the new mypy version.
- You are **adding a new `scripts/*.py`** to a repo with an auto-discovering smoke test, or **adding a `# noqa: <RULE>` whose `<RULE>` may not be in the ruff `select` list** (RUF100 unused-noqa risk).
- You pushed a **large feature PR (40+ files)** after running only the test suite and CI fails on **E501 or `ruff format`** in newly-added test files — running tests does not invoke the linter; newly-added test files are subject to the same E501 line-length limit and `ruff format` rules as production code.
- A repository validate job runs `ruff format --check`, and CI fails with `Would reformat: <file>` even though local pytest, the pre-push pytest suite, and `ruff check <file>` all passed. `ruff check` and `ruff format --check` are separate gates; run both before pushing.

## Verified Workflow

### Quick Reference

```bash
# E501 / format on a large feature PR — lint AND format-check BOTH prod + tests
pixi run ruff check hephaestus/ tests/      # E501 line-length (limit = 100)
pixi run ruff format --check hephaestus/ tests/   # format wants some lines collapsed
# Newly-ADDED test files are just as subject to E501 + ruff format as production code.
```

```bash
# Focused PR / repo validate gate — pytest + ruff check is NOT enough
python3 -m pytest -q <affected-tests>
python3 -m ruff check <changed-python-files>
python3 -m ruff format --check <changed-python-files>
# If format-check fails:
python3 -m ruff format <changed-python-files>
python3 -m ruff format --check <changed-python-files>
```

```bash
# S101 — find assert guards in production code (exclude tests)
grep -rn "noqa: S101\|assert.*is not None" <src-path>/

# C901 — locally reproduce the complexity check
pre-commit run --all-files            # ruff C901 + custom CC hook

# RUF022 (__all__ not sorted) / I001 (import block un-sorted) — both [*]-fixable
# NEVER manually reorder: isort sorts by the 'as' alias name, not the original symbol
pixi run ruff check --fix <file1> <file2>
# Running --fix on just the affected files is safe and idempotent.
# Three errors were fixed in one pass across two files (issue #1189).

# Linter-as-root-cause — count distinct files violating the SAME rule
audit_output | grep "Rule: <rule-id>" | awk '{print $2}' | sort -u | wc -l
# >= 2 distinct files  ->  fix the LINTER first, not each file
```

```python
# S101: assert guard  ->  explicit RuntimeError
# BEFORE
assert self.experiment_dir is not None  # noqa: S101
return self.experiment_dir / "checkpoint.json"
# AFTER
if self.experiment_dir is None:
    raise RuntimeError("experiment_dir must be set before getting checkpoint path")
return self.experiment_dir / "checkpoint.json"
```

```python
# C901: inline branches  ->  extract helpers (each gets its own CC budget)
def _restore_run_context(ctx, state):
    if condition:
        _restore_judgment(ctx)        # CC counted in helper, not parent
    if condition:
        _restore_run_result(ctx)

def _restore_judgment(ctx): ...       # starts at CC=1
```

### Detailed Steps

#### Pattern A — Fix Ruff S101 (assert -> RuntimeError)

**Key insight**: `assert` is inappropriate in production code because Python's `-O` (optimize)
flag disables all `assert` statements. Legitimate runtime guards must use explicit `raise`.

1. **Find all violations** (current line numbers, not the stale ones in the issue):

   ```bash
   grep -rn "noqa: S101" <src-path>/          # production only
   grep -rn "noqa: S101" <src-path>/ <test-path>/   # full picture; tests may legitimately keep noqa
   ```

   The grep often finds MORE asserts than the issue lists (10 vs 6 reported in `runner.py`) — fix all of them if the deliverable is "no S101 in file X".

2. **Read context around each assert** to write a message describing *what operation is blocked*, not just restating the condition. Message format: `"<attribute> must be set before <operation>"`.

3. **Classify and replace**:

   | Assert pattern | Replacement |
   | --------------- | ----------- |
   | `assert x is not None  # noqa: S101` | `if x is None: raise RuntimeError("x must be set before <op>")` |
   | `assert x is not None, "msg"  # noqa: S101` | `if x is None: raise RuntimeError("msg")` (reuse the message verbatim) |
   | `assert condition  # noqa: S101` | `if not condition: raise RuntimeError("<condition description>")` |

   **For-else defensive guard** (e.g. retry loop in `llm_judge.py`): the `else` fires only if every attempt caught a `ValueError`, so `last_parse_error` is logically never `None`. Keep the guard — protect against future breakage — do not delete it:

   ```python
   else:
       if last_parse_error is None:
           raise RuntimeError("Judge retry loop exhausted but last_parse_error is None")
       raise last_parse_error
   ```

4. **Add regression tests** to the existing test class (no new files unless a guard has no home):

   ```python
   def test_method_raises_if_x_none(self, tmp_path: Path) -> None:
       obj = MyClass(attr=None, ...)
       with pytest.raises(RuntimeError, match="attr must be set before"):
           obj.method()
   ```

   For logically-unreachable guards (the for-else case), test the *observable adjacent behavior* — that the normal exhausted-retry path re-raises `ValueError` (not `RuntimeError`) — rather than contriving a path into the guard:

   ```python
   def test_raises_value_error_not_runtime_error_when_parse_fails(self, tmp_path: Path) -> None:
       bad = "Not valid JSON at all"
       with pytest.raises(ValueError):
           self._run_with_call_side_effects(tmp_path, [(bad, "", bad)] * 3)
   ```

   Coverage may stay flat — guard paths protect against impossible states and aren't exercised. That is expected.

5. **Verify and commit**:

   ```bash
   grep -rn "noqa: S101" <src-path>/    # must be empty
   pre-commit run --all-files           # run TWICE: ruff-format reflows long raise lines on pass 1
   pixi run python -m pytest <test-path>/ -q
   ```

#### Pattern B — Fix Ruff C901 (extract helpers)

1. **Identify the violation**: CI shows the function name and CC score, e.g. `_restore_run_context is too complex (11 > 10)`.

2. **Count branches**: each `if`/`elif`/`else`/`for`/`while`/`except`/`and`/`or` adds +1. The function starts at CC=1.

   | CC | Status | Action |
   | -- | ------ | ------ |
   | 1-7 | Safe | Can add 1-3 branches freely |
   | 8-9 | Warning | One more `if/else` hits the limit |
   | 10 | At limit | Any new branch fails CI |
   | 11+ | CI failure | Must extract helpers |

3. **Extract self-contained blocks** into module-level helpers or instance methods — blocks with their own imports, operating on a clear parameter subset, not sharing mutable state beyond `ctx`/`self`. Each helper gets its own CC budget starting at 1. Keep guard clauses in the parent:

   ```python
   if is_at_or_past_state(run_state, RunState.JUDGE_COMPLETE) and ctx.judgment is None:
       _restore_judgment(ctx)

   def _restore_judgment(ctx: Any) -> None:
       """Restore ctx.judgment from on-disk judge result."""
       from scylla.e2e.judge_runner import _has_valid_judge_result, _load_judge_result
       judge_dir = get_judge_dir(ctx.run_dir)
       if _has_valid_judge_result(ctx.run_dir):
           ctx.judgment = _load_judge_result(judge_dir)
   ```

4. **Multi-pass rendering — return-value threading**: when a method runs several sequential passes that each compute state feeding the next (workers -> separator -> logs), extract each pass as an instance method that takes and returns the running offset. No shared mutable state:

   ```python
   def _refresh_display(self, screen, height, width):
       start_row = 0
       start_row = self._draw_workers(start_row, height, width)
       start_row = self._draw_separator(start_row, height, width)
       start_row = self._draw_logs(start_row, height, width)

   def _draw_workers(self, start_row: int, height: int, width: int) -> int:
       ...
       return next_row   # next free row, threaded into the following pass
   ```

   Test each helper for return-value threading, boundary handling, and truncation independently.

5. **Verify**:

   ```bash
   pre-commit run --all-files                     # ruff C901 + custom "Check Cyclomatic Complexity" hook
   pixi run python -m pytest <test-path>/ -x -q
   ```

   Do NOT use `# noqa: C901` to suppress — extract-method is the correct fix. Many repos prohibit `--no-verify` and lint suppression.

#### Pattern C — Linter as root cause of repeated policy violations

When an audit flags the SAME rule violated in **2+ independent files**, the file count (not line
count) is the signal: two violations in one file are a localized bug; two in unrelated files are a
systemic one. The linter/validator that should enforce the policy is the FIRST suspect.

1. **Tally findings by rule ID**:

   ```bash
   jq -r '.findings[].rule' audit.json | sort | uniq -c | sort -rn   # JSON
   grep -oP 'Rule:\s*\K\S+' audit.md | sort | uniq -c | sort -rn      # text
   ```

2. **Locate the linter's rule definition** (read BOTH the good-pattern and bad-pattern sides):

   ```bash
   grep -rn "<rule-keyword>" <validation-module-path>/ <validation-tests-path>/ scripts/audit_*.py
   ```

3. **Locate the META source** the rule claims to enforce — `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, branch-protection rules. Read its statement verbatim.

4. **Diff linter assertion vs META source**:

   | Linter says | META says | Verdict |
   | ----------- | --------- | ------- |
   | Accept X, reject Y | Require X, prohibit Y | Linter correct — violations are real bugs; fix per-file |
   | Accept Y, reject X | Require X, prohibit Y | **Linter is WRONG-DIRECTION — fix linter FIRST** |
   | No assertion | Require X, prohibit Y | Linter has a gap — add the assertion, then fix files |

   If wrong-direction, the dependent files were written to COMPLY WITH the wrong linter — they are downstream consumers of a wrong contract, not independently buggy.

5. **Re-sequence PRs**: linter fix (validator + flipped test assertions, as ONE atomic PR) lands first; dependent file fixes land on top of main afterward. Opening per-file fixes first means CI rejects the correct pattern.

6. **Add pair-direction regression tests** so a future contributor with the same mental model can't flip the direction again:

   ```python
   def test_accepts_required_pattern(self):
       assert is_compliant("<required-pattern>")
   def test_rejects_prohibited_pattern(self):
       assert not is_compliant("<prohibited-pattern>")
   ```

7. **If META is also wrong** (e.g. CLAUDE.md says `--rebase` but branch protection disables rebase merge), the deployed config is ground truth — fix META first, then linter, then dependents. Confirm via `gh api repos/<owner>/<repo>/branches/<branch>/protection`.

#### Pattern D — Adding a new `scripts/*.py` (RUF100 unused-noqa + smoke `--help` contract)

> **Verification: verified-precommit** (ProjectHephaestus issue #1214 / PR #1250, 2026-06-12).
> Caught and fixed locally via `pixi run ruff check`, the auto-discovered smoke test,
> and `pre-commit run`; full CI not yet confirmed green at capture time.

Two tightly-coupled findings share the same search surface: *adding a new
`scripts/*.py` to a ProjectHephaestus-style repo*.

**Finding A — `# noqa: <RULE>` is RUF100 (unused-noqa) when `<RULE>` is NOT in ruff `select`.**

A `subprocess.run([...])` call written with `# noqa: S603` triggered
`RUF100 Unused noqa directive` because `S603` is absent from this repo's ruff
`select` list:

```toml
# pyproject.toml — only specific S-rules are enabled, NOT broad "S" or "S603"
select = ["E","F","W","I","N","D","UP","S101","S102","S105","S106","B","SIM","C4","C901","RUF"]
```

This is a concrete instance of dimension (5) — *deciding between adding a noqa,
fixing the violation, or promoting the rule*. **Decision rule: noqa only for
rules you actually `select`; otherwise the noqa is dead and itself RUF100-flagged.**
Before adding a `# noqa: X`, confirm `X` is in `select` (or covered by an enabled
broad family). For a static-literal `subprocess.run` arg list (no `shell=True`),
no enabled bandit rule fires, so **no noqa is needed at all** — remove it.

```python
# BAD — S603 is not selected, so the directive is dead -> RUF100 unused-noqa
subprocess.run(["git", "status"], check=True)  # noqa: S603
# GOOD — static literal args, no shell; nothing fires; no noqa
subprocess.run(["git", "status"], check=True)
```

**Finding B — every `scripts/*.py` is auto-discovered into a smoke test with a strict `--help` contract.**

In ProjectHephaestus, `tests/unit/scripts/conftest.py` auto-parametrizes EVERY
`scripts/*.py` into
`tests/unit/scripts/test_scripts_smoke.py::test_script_help_exits_zero`. That test
runs `python scripts/<name>.py --help` and asserts BOTH `returncode == 0` AND
`assert combined.strip()` (stdout+stderr non-empty) — UNLESS the basename is in the
`HELP_RUNS_REAL_WORK` allowlist.

Any new `scripts/*.py` MUST honor `--help`/`-h` by printing something AND have a
module docstring (so `print(__doc__)` is non-empty). Otherwise the auto-discovered
smoke test fails the moment the file lands — even for a one-liner guard script.
**Do NOT reach for `HELP_RUNS_REAL_WORK`; genuinely honor `--help`.**

```python
"""One-line module docstring — required so print(__doc__) is non-empty."""

def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return 0
    ...
```

Also: ruff **D103** (missing-docstring-in-public-function) is NOT ignored for
`tests/**` here — per-file-ignores only drops `S101,D102,D107` (`"tests/**" =
["S101","D102","D107"]`). New test functions therefore need one-line docstrings
or ruff fails.

#### Pattern E — Fix retroactive violations after a ruff/mypy floor bump

When a PR raises the ruff or mypy version floor (e.g., `ruff >= 0.15` from `0.1.x`), files
that passed CI when they were merged can suddenly violate rules the new toolchain enforces more
strictly. These violations are **not regressions in the file** — they are retroactive enforcement.

**Three common retroactive violation types:**

**D1 — ruff-format implicit string-concat collapse (two-literal to one-literal)**

ruff 0.15 auto-collapses adjacent implicit two-literal concatenations. Symptom: ruff-format
reports "would reformat" even after you run `ruff check --fix`.

```python
# BEFORE (implicit two-literal concat that ruff 0.15 collapses):
pyproject.write_text(
    "[project]\n"
    "name = 'foo'\n"
)

# AFTER (join into one literal — verify identical bytes, no missing \n):
pyproject.write_text(
    "[project]\nname = 'foo'\n"
)
```

Verify: the joined string produces identical bytes — check that `\n` separators between
fragments are preserved and that no content is lost.

**D2 — E501 line-length overruns**

E501 fires when a line exceeds `line-length` (commonly 100 chars). Two sub-patterns:

*Shell `printf` inside a Python f-string (use bash line continuation):*

```python
# BEFORE (110-char line inside triple-quoted f-string):
script = f"""
printf '%s\\t%s\\n' "$A" "$B_with_a_very_long_variable_name_that_pushes_past_100_chars_here"
"""

# AFTER (bash line continuation \<newline> inside the f-string):
script = f"""
printf '%s\\t%s\\n' "$A" \\
  "$B_with_a_very_long_variable_name_that_pushes_past_100_chars_here"
"""
```

Key insight: a backslash-newline inside a Python triple-quoted f-string is literal `\<newline>`;
bash interprets it as line continuation. The shell command is semantically identical.
Verify by running the generated script in a bash subshell after the change.

*One-line docstring exceeding the limit:*

```python
# BEFORE (106-char single-line docstring):
def foo():
    """Very long docstring that exceeds the 100-character line-length limit in pyproject.toml."""

# AFTER (two-line form):
def foo():
    """Very long docstring that exceeds the 100-character line-length
    limit in pyproject.toml."""
```

**D3 — mypy `[unused-ignore]` on a `# type: ignore[tag]` comment**

When mypy's type inference improves in a new version, it may solve a type error it previously
could not. The `# type: ignore[tag]` annotation is now unused and mypy fires `[unused-ignore]`.

```python
# BEFORE (mypy 1.x could not infer the generic, so [type-arg] was needed):
result: subprocess.CompletedProcess = subprocess.run(...)  # type: ignore[type-arg]

# AFTER (two-part fix):
#   1. Remove the stale comment
#   2. Add the correct generic parameter (text=True implies stdout/stderr are str)
result: subprocess.CompletedProcess[str] = subprocess.run(...)
```

Determining the correct type argument:

- `text=True` or `encoding=...` passed to `subprocess.run` means `[str]`
- `text=False` (the default) means `[bytes]`

Confirm with `pixi run mypy <file>` — must report zero errors including `[unused-ignore]`.

**D4 — Root cause pattern and discovery workflow**

These violations merged under the old floor and passed CI at the time. The floor-bump PR is
what makes them visible. All four violation types can appear together; fix them in one PR.

```bash
# Discover all retroactive violations after a floor bump:
pixi run ruff format --check .   # find format violations (D1)
pixi run ruff check .            # find lint violations including E501 (D2)
pixi run mypy                    # find unused-ignore errors (D3)

# Apply auto-fixable repairs:
pixi run ruff format .           # apply D1 format fixes
pixi run ruff check --fix .      # apply auto-fixable lint fixes

# Manually fix remaining E501 overruns and unused-ignore comments.
# Then verify clean:
pixi run ruff format --check .
pixi run ruff check .
pixi run mypy
```

Important: the `lint` job MUST be a required CI check. If it is advisory-only, retroactive
violations merge silently (as happened with PR #1308 when `lint` was not required).

#### Pattern F — E501 / ruff format failures in newly-added test files on a large feature PR

> **Verification: verified-ci** (ProjectHephaestus PR #1035, 2026-06-13).

On a large feature PR (40+ files), newly-added test files are just as subject to **E501
(line-length)** and **`ruff format`** as production code. Running only the test suite before
pushing does not invoke the linter or formatter — CI will fail on E501 or format in the new
test files even if all tests pass locally.

**Always run ruff check AND ruff format --check over BOTH source and test directories before
pushing a large PR:**

```bash
# E501 / format on a large feature PR — lint AND format-check BOTH prod + tests
pixi run ruff check hephaestus/ tests/      # E501 line-length (limit = 100)
pixi run ruff format --check hephaestus/ tests/   # format wants some lines collapsed
# Newly-ADDED test files are just as subject to E501 + ruff format as production code.
```

**Two opposite fix shapes for E501 violations:**

**(F1) Long literal that still overflows after wrapping the container — extract the literal:**

Hand-wrapping only the `for`-header or call-signature does not help if the literal itself
overflows 100 chars. Extract the literal to a variable first:

```python
# BAD — hand-wrapping the for-header still leaves the literal past col 100
for command, module_path, attr in [
    ("hephaestus", "hephaestus.__main__", "main"),
    ("hephaestus-cli-a-very-long-entry-point-name-that-overflows-the-100-char-limit", "hephaestus.cli", "cli_main"),
]:
    ...

# GOOD — extract the literal to a named constant
ENTRY_POINTS = [
    ("hephaestus", "hephaestus.__main__", "main"),
    (
        "hephaestus-cli-a-very-long-entry-point-name-that-overflows-the-100-char-limit",
        "hephaestus.cli",
        "cli_main",
    ),
]
for command, module_path, attr in ENTRY_POINTS:
    ...
```

**(F2) Hand-wrapped call that `ruff format` collapses — stop hand-wrapping it:**

If `ruff format` keeps rewriting a hand-wrapped call back onto one line, the call already
fits within the line-length limit and ruff's style is the single-line form. Stop fighting it:

```python
# BAD — hand-wrapping subprocess.run that fits on one line; ruff format undoes this every time
result = subprocess.run(
    ["git", "status"],
    check=True,
)

# GOOD — let ruff format collapse it; this is within the limit
result = subprocess.run(["git", "status"], check=True)
```

**Positive convention folded in from PR #1035:**

For cross-cutting CLI flag rollouts (e.g., `--version` across all entry points), use:

- A composable `add_version_arg(parser)` helper so the flag is added identically everywhere.
- A parametrized integration test:
  ```python
  @pytest.mark.parametrize("command,module_path,attr", ENTRY_POINTS)
  def test_version_flag(command: str, module_path: str, attr: str) -> None:
      """Each entry point exposes --version and exits zero."""
      result = subprocess.run([command, "--version"], capture_output=True, text=True)
      assert result.returncode == 0
  ```
  This pattern makes the ENTRY_POINTS list the single source of truth and forces the same
  line-length discipline on every parametrized row.

**F3) CI validate runs `ruff format --check` separately from `ruff check`:**

Some repos put format checking inside a higher-level validation target (e.g. `just validate`).
In that setup, the following local sequence is insufficient:

```bash
python3 -m pytest -q tests/test_setup_workflow.py
python3 -m pytest -q tests/test_governance_docs.py
python3 -m ruff check tests/test_setup_workflow.py
git diff --check
# pre-push hook runs pytest -q only
```

That exact sequence missed a formatter-only issue in Inference360 PR #282. GitHub CI
failed `validate` with:

```text
Would reformat: tests/test_setup_workflow.py
1 file would be reformatted, 51 files already formatted
```

Fix it by running `ruff format` on the reported file, committing the formatter-only diff,
and verifying both gates:

```bash
python3 -m ruff format tests/test_setup_workflow.py
python3 -m pytest -q tests/test_setup_workflow.py tests/test_governance_docs.py
python3 -m ruff check tests/test_setup_workflow.py
python3 -m ruff format --check tests/test_setup_workflow.py
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Suppress C901 with `# noqa: C901` | Considered suppressing the complexity warning instead of refactoring | Project prohibits `--no-verify` and lint-rule suppression | Extract-method is the correct fix, not suppression |
| Inline all restore logic in one function | Added judgment + run_result restore as new `if` blocks in a function already at CC~8 | CC went to 11, exceeding the C901 limit of 10 | Check the CC budget before adding branches to a function near the limit |
| Contrive a test into an unreachable guard | First S101 for-else test used a `StopIteration` trick to hit the logically-unreachable `RuntimeError` guard | The guard cannot fire in normal operation; the trick was brittle and abandoned | Test observable adjacent behavior (normal exhausted-retry path), not the unreachable guard path |
| Skip the second pre-commit run | Ran `pre-commit` once after converting asserts | ruff-format reflowed the longer `raise RuntimeError(...)` lines and reported "files were modified" | The `if ... raise` form is longer than the assert; run pre-commit twice (reflow, then confirm clean) |
| Open N parallel PRs to fix N violating files | 2 separate PRs to fix `--rebase`->`--squash` in two skill files | The validator enforced the WRONG direction (required `--rebase`, rejected `--squash`); the new PRs would fail CI on the correct pattern | When >=2 files violate the same rule, the linter is the first suspect — read its rule definition before per-file PRs |
| Fix linter and dependent files in one PR | Considered bundling validator + all doc fixes into one mega-PR | Linter and doc changes have different test surfaces; bundling makes CI feedback ambiguous | Keep the linter fix as its own atomic PR; dependent fixes land afterward |
| Flip only the validator, not its tests | Planned to update validator code but leave its test suite | Validator tests still asserted the wrong direction — the linter PR itself fails CI | Validator source + its tests are one atomic change; flip both together |
| Single-direction regression test | Wrote a test asserting only "accepts `--squash`" | A future agent with the same wrong-direction model could re-flip the assertion and ship it | Pair tests: assert correct accepted AND wrong rejected, to prevent silent drift |
| Manual reorder of `__all__` with `as` aliases | Tried to alphabetize `__all__` entries and import block by hand when ruff reported RUF022 + I001 | isort orders by the **alias** name (the `as <name>` part), not the original symbol — naive alphabetical order of original names produces a different sequence that ruff still rejects | Always use `pixi run ruff check --fix <files>` for RUF022 and I001; these are `[*]`-fixable and the sort order is non-obvious when `as` aliases are present |
| Only run `ruff check` after floor bump, missed ruff-format violations | Ran `pixi run ruff check .` and saw no output; assumed the repo was clean post-bump | `ruff check` (lint) and `ruff format --check` (formatter) are separate tools; a two-literal implicit concat collapse is a FORMAT violation, not a lint violation | Always run BOTH `ruff format --check .` AND `ruff check .` after a floor bump |
| Remove `# type: ignore[type-arg]` without adding the type parameter | Deleted the stale comment but left `subprocess.CompletedProcess` without a type argument | Bare `subprocess.CompletedProcess` without `[str]` still causes a mypy `type-arg` error in strict mode, creating a different failure | Always pair unused-ignore removal with the correct generic parameter; use `text=True` to `[str]`, `text=False` to `[bytes]` |
| Break the shell printf line with Python string continuation | Used Python line continuation (backslash at end of a string-literal line) inside an f-string | Python line continuation splits the Python source string, not the shell command; the resulting shell string is malformed | Use bash line continuation (backslash + newline as literal content inside the triple-quoted f-string); Python passes it through literally and bash interprets it as line continuation |
| Treat floor-bump violations as belonging to the bump PR | Tried to retroactively amend the original files that introduced violations | The violations pre-exist in files merged under the old floor; the bump PR is not the commit that introduced them | Create a new dedicated fix PR against main; do not rewrite the floor-bump PR history |
| Add `# noqa: S603` to silence a presumed bandit finding | Annotated a static-literal `subprocess.run([...])` with `# noqa: S603` | `S603` is not in the repo's ruff `select` list, so the directive is dead -> `RUF100 Unused noqa directive` | Remove the noqa — and it wasn't needed at all (static literal args, no `shell=True`); noqa only for rules you actually `select` |
| Ship a new `scripts/*.py` guard without a `--help` branch | Added a one-liner guard script with no `--help`/`-h` handling | The auto-discovered `test_script_help_exits_zero` runs `--help` and asserts exit 0 AND non-empty output — it failed the moment the file landed | Honor `--help`/`-h` -> `print(__doc__)`; add a module docstring; don't reach for `HELP_RUNS_REAL_WORK` |
| Omit docstrings on new pytest test functions | Wrote new test functions under `tests/` without docstrings | ruff `D103` (missing-docstring-in-public-function) is NOT ignored for `tests/**` (per-file-ignores drops only `S101,D102,D107`) | Add a one-line docstring to every new public test function |
| Pushed 44-file feature PR after only running the test suite | Ran `pixi run python -m pytest` locally; all tests passed; pushed to CI | CI failed on E501 in newly-added test files — the test runner does not invoke ruff check or ruff format | Always run `pixi run ruff check <src>/ tests/` AND `pixi run ruff format --check <src>/ tests/` before pushing any PR that adds new files |
| Ran pytest and `ruff check`, skipped `ruff format --check` | In Inference360 PR #282, ran focused pytest, `ruff check tests/test_setup_workflow.py`, `git diff --check`, and a pre-push full pytest suite | GitHub `validate` still failed because the repo's validation target ran `ruff format --check` and found `tests/test_setup_workflow.py` would be reformatted | Add `ruff format --check <changed-python-files>` to the local checklist whenever CI has a formatter gate; `ruff check` does not imply formatting is clean |
| Hand-wrapped a long `for`-header to fix E501 in a test file | Broke the `for command, module_path, attr in [...]` header onto multiple lines | The long string literal inside the list still overflowed col 100 — wrapping the header does not shorten the literal | Extract the literal list to a named constant (e.g., `ENTRY_POINTS`) so each row can be broken independently |
| Hand-wrapped `subprocess.run(...)` call across multiple lines | Split `subprocess.run(["git", "status"], check=True)` onto 3 lines to "look tidy" | `ruff format` kept collapsing it back to one line on every run — the call already fit within the line-length limit | Stop hand-wrapping calls that fit on one line; `ruff format` is the canonical style authority — let it collapse them |

## Results & Parameters

### S101 conversions (verified)

```text
Issue #1066 / PR #1142: 16 asserts replaced (10 in runner.py, 6 in stages.py),
                        16 noqa removed, 3185 tests pass, 78.09% coverage (>=75%)
Issue #1143 / PR #1211: 4 remaining sites converted (workspace_manager.py x2,
                        llm_judge.py for-else, runner.py _finalize_test_summary),
                        4 regression tests added, 3261 tests pass, 78.39% coverage,
                        zero S101 suppressions remain in scylla/
```

Representative replacement messages: `"experiment_dir must be set before getting checkpoint path"`,
`"agent_result must be set before finalize_run"`, `"commit must be set before calling _checkout_commit"`,
`"Judge retry loop exhausted but last_parse_error is None"`,
`"_state must be initialized before finalizing test summary"`.

### C901 configuration

- **Ruff C901**: `max-complexity = 10` (in `pyproject.toml` lint config).
- **Custom hook**: `Check Cyclomatic Complexity` — runs separately from ruff at the same threshold; both must pass for CI green.

### RUF100 unused-noqa + scripts smoke `--help` contract (verified-precommit)

- **ruff `select` (ProjectHephaestus `pyproject.toml`)** — a `# noqa: X` whose `X`
  is not here is dead and RUF100-flagged:

  ```toml
  select = ["E","F","W","I","N","D","UP","S101","S102","S105","S106","B","SIM","C4","C901","RUF"]
  ```

  Only specific S-rules (`S101/S102/S105/S106`) are enabled — NOT broad `S` or `S603`.

- **per-file-ignores** — `D103` is NOT dropped for tests, so new test functions
  still need docstrings:

  ```toml
  "tests/**" = ["S101","D102","D107"]
  ```

- **scripts smoke-test assertion** (`tests/unit/scripts/test_scripts_smoke.py::test_script_help_exits_zero`,
  auto-parametrized by `tests/unit/scripts/conftest.py` over every `scripts/*.py`):
  `returncode == 0` **AND** `combined.strip()` (stdout+stderr non-empty), unless the
  basename is in `HELP_RUNS_REAL_WORK`.

- **`--help` idiom** every new `scripts/*.py` must implement (plus a module docstring):

  ```python
  if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
      print(__doc__)
      return 0
  ```

### Linter-as-root-cause re-sequencing template

```text
WRONG ORDER (fails CI):           CORRECT ORDER:
  PR1: fix file_A   <- rejected     PR1: fix linter (validator + flipped tests)
  PR2: fix file_B   <- rejected     PR2: fix file_A (depends on PR1)
                                    PR3: fix file_B (depends on PR1)
                                    PR4: fix META source (only if META also wrong)
```

### Inference360 validate CI format gate

**Context:** Inference360 PR #282 (`Require setup installer checksums`) changed
`tests/test_setup_workflow.py`. Local focused pytest, `ruff check`, `git diff --check`,
and the pre-push full pytest suite all passed. GitHub `validate` failed anyway because the
repo's validation recipe included `ruff format --check`.

**CI failure signature:**

```text
Would reformat: tests/test_setup_workflow.py
1 file would be reformatted, 51 files already formatted
```

**Fix and verification:**

```bash
python3 -m ruff format tests/test_setup_workflow.py
python3 -m pytest -q tests/test_setup_workflow.py tests/test_governance_docs.py
python3 -m ruff check tests/test_setup_workflow.py
python3 -m ruff format --check tests/test_setup_workflow.py
git diff --check
```

**Outcome:** pushed a formatter-only follow-up commit to PR #282. GitHub `validate`,
`secrets`, `sast`, `python-sca`, and CodeQL all passed; auto-merge merged the PR.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | S101 bulk elimination — runner.py + stages.py (16 asserts) | PR #1142 (issue #1066) |
| ProjectScylla | S101 follow-up — 4 remaining production sites + regression tests | PR #1211 (issue #1143) |
| ProjectScylla | C901 — extracted `_restore_judgment()` / `_restore_run_result()` from `_restore_run_context()`, CC 11 -> ~7 | PR #1546 |
| ProjectHephaestus | C901 multi-pass — extracted `_draw_workers/_separator/_logs` from `_refresh_display()`, 69 lines -> 3 methods, 8 -> 23 tests, removed `# noqa: C901` | PR #1050 (issue #804) |
| ProjectHephaestus | Linter-as-root-cause — strict audit caught 2 skill files violating `--squash`-only merge policy; root cause was a wrong-direction validator | PRs #863, #865, #866, #867 |
| ProjectHephaestus | RUF022 + I001 — `__all__` sort and import-block sort in `hephaestus/validation/` after python-version-consistency DRY refactor; 3 errors fixed in one `ruff check --fix` pass across 2 files | Issue #1189 |
| ProjectHephaestus | Floor-bump retroactive violations (ruff 0.1.x to 0.15, PR #1294) — 4 violations across 3 test files: (D1) implicit two-literal concat collapse in `test_check_python_version_consistency.py:321-324`; (D2a) E501 in `test_choose_merge_flag_sh.py:60` fixed with bash `\<newline>` continuation inside f-string; (D2b) E501 in `test_planner_loop.py:681` one-line docstring expanded; (D3) unused `# type: ignore[type-arg]` in `test_choose_merge_flag_sh.py:30` removed and `[str]` generic added. Verified-local (pixi run mypy + ruff format --check + ruff check all clean). | Issue #1313 |
| ProjectHephaestus | RUF100 unused-noqa (`# noqa: S603` not in `select`) + scripts smoke `--help` contract (auto-discovered `test_script_help_exits_zero`), verified-precommit | issue #1214 / PR #1250 |
| ProjectHephaestus | E501 + `ruff format` failures in newly-added test files on 44-file feature PR; two opposite E501 fix shapes (extract literal vs. stop hand-wrapping); `add_version_arg` helper + parametrized `@pytest.mark.parametrize("command,module_path,attr", ENTRY_POINTS)` integration test pattern | PR #1035 |
| Inference360 | GitHub `validate` failed on `ruff format --check` after local pytest, `ruff check`, `git diff --check`, and pre-push pytest all passed; formatter-only follow-up fixed `tests/test_setup_workflow.py` | PR #282 |
