---
name: code-quality-enforcement-gates
description: "Canonical guide to code-quality enforcement THRESHOLDS and decisions: when to fail builds on complexity, when to enable mypy strict modes, when to promote warnings to errors, how to scope override subsets, deprecation removal policy. Use when: (1) deciding fix-vs-suppress for a new lint rule, (2) enabling mypy check-untyped-defs or new ruff rules, (3) promoting CI warnings to exit-1, (4) tuning markdownlint MD024 / ruff C901 thresholds, (5) narrowing mypy module override globs to specific paths."
category: ci-cd
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: code-quality-enforcement-gates.history
tags: [merged, code-quality, quality-gate, mypy, ruff, complexity-budget, deprecation]
---

# Code-Quality Enforcement Gates

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Canonical reference for when and how to turn lint warnings into hard build failures |
| **Outcome** | Merged from 8 skills — covers complexity thresholds, mypy strictness, deprecation enforcement, markdown rule tuning, override narrowing, and regression-guard tests |
| **Scope** | ci-cd quality gates only — for hook wiring / pre-commit-config surface area see M1 (pre-commit-linting-hooks-config) |

## When to Use

1. Deciding whether to **fix or suppress** a newly enabled lint rule (ruff C901, mypy strict, etc.)
2. Enabling **mypy `check_untyped_defs`** or `disallow_untyped_defs` and fixing surfaced errors
3. **Promoting a CI `::warning::`** grep step to `::error::` + `exit 1` enforcement
4. Tuning **markdownlint MD024** (`siblings_only`) or ruff **C901** (mccabe `max-complexity`) thresholds
5. **Narrowing mypy module glob overrides** to exclude a fully-annotated subdir
6. Coordinating **batch fixes** across 5+ files in a single PR
7. Fixing **placeholder code / type-migration assertion** CI failures
8. **Fixing regression-guard tests** that pin to suppression syntax before an ecosystem sweep

---

## Verified Workflow

### Quick Reference

| Gate Decision | Tool / Config | Key Threshold |
| --- | --- | --- |
| McCabe complexity | `ruff C901` + `max-complexity` in `pyproject.toml` | Accept ≤12; suppress >12 with rationale |
| Mypy function bodies | `check_untyped_defs = true` in `[tool.mypy]` | Triage first: run flag manually, fix errors, then commit config |
| Mypy strictness scope | `[[tool.mypy.overrides]]` module list | Replace broad glob with explicit list when subdir is clean |
| Deprecation warning → error | CI grep chain + `exit 1` | Count must be 0 before switching `::warning::` → `::error::` |
| Markdown duplicate headings | `.markdownlint.yaml` `MD024.siblings_only: true` | Config-only; never rename Keep-a-Changelog headings |
| Batch fix PR scope | 5–12 low-complexity issues, one PR | Read all files before editing; use Python scripts for 10+ bulk replacements |
| Placeholder code CI | Comment out ALL code using a placeholder variable | Fix type-migration assertions to match new native types |
| Regression-guard tests | Assert property, not literal suppression syntax | Run meta-test grep BEFORE a sweep; fix in a predecessor PR |

---

### 1. Ruff C901 McCabe Complexity Gate

**Decision rule:** Accept complexity 11–12 for orchestration/CLI code. Suppress >12 with documented rationale. Default threshold (10) is too strict for non-trivial orchestration.

**Step 1 — Audit violations at candidate threshold:**

```bash
# Count violations at default complexity=10
pixi run ruff check <source-dirs>/ --select C901 2>&1 | grep "C901"

# Get file:line locations
pixi run ruff check <source-dirs>/ --select C901 2>&1 | grep -E "C901|-->" | paste - -
```

**Step 2 — Update `pyproject.toml`:**

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]

[tool.ruff.lint.mccabe]
max-complexity = 12
```

**Step 3 — Add annotated suppressions (noqa MUST be on the `def` line):**

```python
# CORRECT — noqa on the def line
def run_subtest(  # noqa: C901  # orchestration with many retry/outcome paths
    self,
    tier_id: TierID,
) -> SubTestResult:

# WRONG — noqa on return type line (ruff ignores it)
def run_subtest(
    self,
) -> SubTestResult:  # noqa: C901  # does NOT suppress
```

**Standard rationale categories:**

| Rationale | Function archetypes |
| --- | --- |
| `orchestration with many retry/outcome paths` | `run`, `run_subtest`, `_implement_all` |
| `pipeline with sequential conditional stages` | `_run_mojo_pipeline`, `_run_python_pipeline` |
| `CLI dispatch with many command branches` | `main`, `cmd_run`, `cmd_visualize` |
| `validation with many independent rule checks` | `validate_frontmatter`, `check_configs` |
| `config loader with many format/version branches` | `load`, `load_run`, `load_rubric_weights` |
| `AST traversal with many node type branches` | `detect_shadowing` |

**Step 4 — Verify:**

```bash
pixi run ruff check <source-dirs>/ --select C901
pixi run ruff check <source-dirs>/
pixi run python -m pytest tests/ -v
```

---

### 2. Mypy Strictness Gates

#### 2a. Enable `check_untyped_defs`

**Always triage before committing config changes:**

```bash
# Run flag manually; fix ALL surfaced errors before touching config
pixi run mypy <source-dir>/ --check-untyped-defs --exclude <excluded-dir>/
```

**Common errors and fixes:**

```python
# defaultdict missing annotation (var-annotated error)
file_counts: defaultdict[str, int] = defaultdict(int)  # add explicit type

# Empty list missing annotation
optional: list[str] = []  # add explicit type

# Pillow 10+ deprecated aliases
img = img.resize((28, 28), Image.Resampling.LANCZOS)        # was Image.LANCZOS
img = img.transpose(Image.Transpose.TRANSPOSE)               # was Image.TRANSPOSE
```

**Update `pyproject.toml`:**

```toml
[tool.mypy]
disallow_untyped_defs = true
check_untyped_defs = true
```

**Update `.pre-commit-config.yaml`:**

```yaml
- id: mypy
  args: [--ignore-missing-imports, --no-strict-optional,
         --explicit-package-bases, --check-untyped-defs,
         --python-version, "3.10"]
```

#### 2b. Narrow Mypy Override Glob

**Use when one subdir becomes fully annotated.** Triage first — the work may already be done:

```bash
pixi run mypy tests/unit/<subdir>/ --disallow-untyped-defs
# "Success: no issues found" → skip to pyproject.toml edit; no test files needed
```

**Find remaining subdirs that still need suppression:**

```bash
# Temporarily remove the override, then:
pixi run mypy tests/unit/ --disallow-untyped-defs --no-error-summary 2>&1 \
  | grep "error:" | sed 's|tests/unit/||;s|/.*||' | sort -u
```

**Replace broad glob with explicit list in `pyproject.toml`:**

```toml
# Before — broad glob suppresses everything
[[tool.mypy.overrides]]
module = "tests.unit.*"
disable_error_code = ["no-untyped-def"]

# After — explicit list excluding the newly-clean subdir
# tests/unit/scripts/ is fully annotated. Remaining subdirs still need suppression.
[[tool.mypy.overrides]]
module = [
    "tests.unit.adapters.*",
    "tests.unit.analysis.*",
    "tests.unit.automation.*",
    # ... list every remaining subdir explicitly
]
disable_error_code = ["no-untyped-def"]
```

Note: mypy `[[tool.mypy.overrides]]` accepts a `module` array as of mypy 0.930+.

---

### 3. Deprecation CI Gate: Warning → Error Promotion

**Step 1 — Confirm count is zero before adding `exit 1`:**

```bash
count=$(grep -rn "SomeDeprecatedSymbol" . \
  --include="*.py" \
  --exclude-dir=".pixi" \
  | grep -v "definition_file.py" \
  | grep -v "# deprecated" \
  | grep -v "test_file.py" \
  | wc -l)
echo "$count"
# Must be 0 before proceeding
```

**Step 2 — Classify any count > 0 hits:**
- **Legitimate caller** → must be removed first
- **Re-export** (`__init__.py`) → add `grep -v "path/to/__init__.py"`
- **Docstring "See also"** mention → add `grep -v "(deprecated)"` (distinct from `grep -v "# deprecated"`)

**Step 3 — Update the CI step:**

```yaml
- name: Enforce no new deprecated <Symbol> usage
  run: |
    count=$(grep -rn "<Symbol>" . \
      --include="*.py" \
      --exclude-dir=".pixi" \
      | grep -v "definition_file.py" \
      | grep -v "path/to/__init__.py" \
      | grep -v "# deprecated" \
      | grep -v "(deprecated)" \
      | grep -v "test_file.py" \
      | wc -l)
    echo "<Symbol> usage count: $count"
    if [ "$count" -gt "0" ]; then
      echo "::error::Found $count usages of deprecated <Symbol> — remove before merging"
      grep -rn "<Symbol>" . --include="*.py" --exclude-dir=".pixi" \
        | grep -v "definition_file.py" \
        | grep -v "path/to/__init__.py" \
        | grep -v "# deprecated" \
        | grep -v "(deprecated)" \
        | grep -v "test_file.py"
      exit 1
    fi
```

Key changes from warning step: `::warning::` → `::error::`, add `exit 1`, mirror all new exclusions into the diagnostics grep block.

**Deprecation gate promotion checklist:**

- [ ] Run grep chain locally — confirm count is 0
- [ ] Classify count > 0 hits as caller (remove) or safe reference (exclude)
- [ ] Add `grep -v` exclusions for re-exports and docstring annotations
- [ ] Update step name "Track..." → "Enforce..."
- [ ] Change `::warning::` → `::error::`
- [ ] Add `exit 1` inside the `if` block
- [ ] Mirror all new exclusions into the diagnostic grep block
- [ ] Run full test suite to confirm no regressions

---

### 4. Markdownlint MD024 Threshold Tuning

**Problem:** `MD024/no-duplicate-heading` false positives on Keep-a-Changelog `CHANGELOG.md` where `### Added`, `### Fixed`, `### Changed`, `### Removed` legitimately repeat under each `## [x.y.z]` version block.

**Fix — config-only, zero edits to CHANGELOG.md:**

```yaml
# .markdownlint.yaml
MD024:
  siblings_only: true
```

```json
// .markdownlint.json — equivalent JSON
{ "MD024": { "siblings_only": true } }
```

**Confirm the right failure mode before applying** — the CI error must show headings under *different* parent sections:

```text
CHANGELOG.md:42 MD024/no-duplicate-heading Multiple headings with the same content [Context: "### Added"]
CHANGELOG.md:58 MD024/no-duplicate-heading Multiple headings with the same content [Context: "### Fixed"]
```

**Verify locally:**

```bash
npx markdownlint-cli2 "**/*.md"
pre-commit run markdownlint-cli2 --all-files
```

**Companion rules for changelog-heavy repos:**

| Rule | Setting | Why |
| --- | --- | --- |
| `MD013` | `false` (or `line_length: 120`) | Long PR titles / URLs in changelogs |
| `MD033` | `{ allowed_elements: [br, details, summary] }` | Collapsible release notes |
| `MD034` | `false` | Bare URLs common in changelogs |
| `MD041` | `false` | If CHANGELOG.md doesn't lead with H1 |

---

### 5. Regression-Guard Tests — Assert Property, Not Syntax

**Run this grep BEFORE any ecosystem sweep that changes suppression syntax:**

```bash
grep -rn "continue-on-error\|or-true\|::warning::" tests/ .github/ \
  --include="*.py" --include="*.sh" --include="*.bats" \
  --include="*.yml" --include="*.yaml"
```

Any hits must be fixed in a **predecessor PR** before the sweep.

**Anti-pattern (pinned to literal):**

```python
def test_npm_audit_is_non_blocking():
    assert "continue-on-error: true" in step_text
```

**Broadened (accepts either syntax form):**

```python
def test_npm_audit_is_non_blocking():
    """Property: the npm-audit step must NOT fail the workflow on audit findings."""
    legacy = "continue-on-error: true" in step_text
    in_script_capture = (
        "|| AUDIT_EXIT=$?" in step_text
        and "AUDIT_EXIT:-0" in step_text
    )
    assert legacy or in_script_capture, "audit step must be non-blocking"
```

**Strict fail-fast form (Bucket F policy — no suppression allowed):**

```python
def test_npm_audit_is_fail_fast():
    """Property (Bucket F): no suppression mechanism allowed in the audit step."""
    forbidden = ["continue-on-error: true", "|| true", "::warning::",
                 "--exit-code 0", "--exit-zero"]
    for pat in forbidden:
        assert pat not in step_text, f"audit step contains forbidden pattern: {pat}"
```

**Workflow-level smoke tests** — replace grep-for-literal with structural yq check:

```yaml
- name: smoke-test step is fail-fast
  run: |
    step=$(yq '.jobs.lint.steps[] | select(.name == "Run <step>")' .github/workflows/<workflow>.yml)
    for pat in 'continue-on-error: true' '|| true' '::warning::' '--exit-code 0'; do
      if echo "$step" | grep -qF "$pat"; then
        echo "::error::step contains forbidden pattern: $pat"
        exit 1
      fi
    done
```

**Warning:** If the smoke-test's own error message contains `::warning::`, the `forbid-advisory-warnings` hook fires on the test file. Self-exempt via `exclude:` in `.pre-commit-config.yaml` or construct the literal at runtime.

---

### 6. Batch Fix Coordination (5–12 files per PR)

**When to use:** Multiple low-complexity issues (text, comments, docstrings, trivial one-liners) that can be fixed independently in a single PR.

**Step 1 — Plan & read all files first:**

```bash
# Read ALL files before making any edits
# Note any import requirements or dependencies
# Identify pre-existing lint issues that are OUT OF SCOPE
```

**Step 2 — Apply edits sequentially; use Python for 10+ bulk replacements:**

```python
import re
with open('file.md', 'r') as f:
    content = f.read()
content = re.sub(r'^```text\s*$', '```', content, flags=re.MULTILINE)
with open('file.md', 'w') as f:
    f.write(content)
```

**Step 3 — Validate with pre-commit before committing:**

```bash
# Check pre-existing issues (ignore errors from before your changes)
git diff <file> | grep -E "^[+-]" | head -20

# Validate specific files
npx markdownlint-cli2 docs/file1.md
<package-manager> run mojo format <changed-files>
```

**Step 4 — Commit with all issues in description; enable auto-merge.**

---

### 7. Placeholder Code and Type-Migration CI Failures

**Placeholder code pattern (comment ALL dependent code, not just the declaration):**

```mojo
# BAD — declaration commented but dependent code is not
# var parts = split(a, 3)
if len(parts) != 3:  # ERROR: 'parts' undeclared

# GOOD — comment out all code that uses the placeholder
# TODO(<issue>): Implement split()
# var parts = split(a, 3)
# if len(parts) != 3:
#     raise Error("...")
_ = a  # Suppress unused variable warning
```

**Type-migration assertion updates:**

```mojo
# Before (old aliased behavior)
assert_equal(tensor.dtype(), DType.float16, "BF16 tensor dtype")

# After (native type after migration)
assert_equal(tensor.dtype(), DType.bfloat16, "BF16 tensor dtype")
```

**Triage CI failures:**

```bash
gh run view <run_id> --repo <owner>/<repo> --log-failed 2>&1 | head -200
gh run view <run_id> --repo <owner>/<repo> --log-failed 2>&1 | grep -A 50 "error:\|FAILED"
```

Always rebase before pushing when merge conflicts exist — never wait for CI with unresolved conflicts.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Bash `sed`/`awk` for multi-file edits | `sed -i 's/old/new/g'` across files | Pattern too broad, missed context-specific nuances | Use Edit tool for code; Python `re.sub` for bulk markdown |
| Bulk replace without reading file state first | Started editing based on assumptions | Missed existing imports / misunderstood context | Always read files first before editing |
| Adding noqa on return-type line | `def f(...) -> T:  # noqa: C901` on closing line | Ruff ignores noqa on any line other than the `def` line | noqa MUST be on the first `def` line |
| Setting ruff `max-complexity = 10` (default) | Left the default threshold in place | Produced 65 violations — too many to fix at once | 12 is the pragmatic threshold for orchestration codebases |
| Renaming Keep-a-Changelog headings to be unique | `### Added in 0.2.0`, `### Fixed in 0.2.0` | Breaks release-drafter / auto-changelog tooling expecting literal `### Added` | Fix the linter config (`siblings_only: true`), not the doc |
| Disabling MD024 globally | `MD024: false` | Too permissive — real same-section duplicates silently pass | Use `siblings_only: true`: keeps rule active for real duplicates |
| Inline `<!-- markdownlint-disable MD024 -->` | Per-release-block disable comments | Must be added for every new release; clutters changelog | Config-level `siblings_only` is one line and applies globally |
| Switching deprecation CI to `exit 1` before count = 0 | Changed `::warning::` → `::error::` + `exit 1` while hits remain | CI fails on every PR for legitimate usages | Count MUST be 0; classify every hit before promoting gate |
| Ignoring `(deprecated)` inline annotation in grep filter | Only had `grep -v "# deprecated"` | Missed annotations like `# - BaseClass (deprecated)` in docstrings | Both `grep -v "# deprecated"` and `grep -v "(deprecated)"` needed |
| Running sweep first, fixing meta-tests after CI broke | Changed suppression syntax; updated tests reactively | Every sweep PR's CI failed; reviewers confused real regression with test brittleness | Fix meta-tests in a predecessor PR BEFORE the sweep |
| Replacing pinned literal with new mechanism's literal | Broadened test to only accept the new syntax | Broke again on the next sweep iteration | Assert the property (fail-fast / non-blocking), not the syntax |
| Testing for step property via `gh workflow run` | Live runtime check of step behavior | Too slow for pre-merge unit tests | Use static analysis: parse YAML structurally and check step text |
| Enabling `check_untyped_defs` in config before triaging | Added flag to `pyproject.toml` first | Surprise failures in CI; no chance to fix before push | Always run the flag manually first, fix all errors, then commit config |
| Broad `tests.unit.*` glob override as permanent state | One glob suppresses all unannotated test subdirs forever | Suppresses already-annotated subdirs; masks progress | Narrow to explicit list whenever a subdir is confirmed clean |

---

## Results & Parameters

### Ruff C901 Summary

| Complexity range | Action |
| --- | --- |
| ≤ 10 (default) | No suppression needed |
| 11–12 (accepted) | No change needed at `max-complexity = 12` |
| > 12 | `# noqa: C901  # <rationale>` on the `def` line |

### Mypy Config Reference

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
check_untyped_defs = true
explicit_package_bases = true
mypy_path = "."
exclude = "<excluded-dir>/"

# Narrow override — replace broad glob with explicit list
[[tool.mypy.overrides]]
module = [
    "tests.unit.adapters.*",
    "tests.unit.analysis.*",
    # ... one entry per unannotated subdir
]
disable_error_code = ["no-untyped-def"]
```

### Markdownlint Config Reference

```yaml
# .markdownlint.yaml
default: true

MD024:
  siblings_only: true

# Optional companions for changelog-heavy repos:
MD013: false
MD033:
  allowed_elements: [br, details, summary]
MD034: false
```

### Batch Fix Parameters

```yaml
issues_per_batch: 8          # Sweet spot: 5–12
files_affected: 9            # Typically 8–12
complexity_level: low        # Text/comment/docstring only — no refactoring
read_before_edit: true       # Always
use_python_script: true      # For 10+ bulk replacements
validate_with_git_diff: true # Check only changed lines
```

### Deprecation Gate Verification Commands

```bash
# Confirm count is 0 before promoting to exit 1
count=$(grep -rn "<DeprecatedSymbol>" . --include="*.py" --exclude-dir=".pixi" \
  | grep -v "<definition_file>" | grep -v "# deprecated" | grep -v "(deprecated)" \
  | wc -l); echo "$count"

# Run tests after CI step change
<package-manager> run python -m pytest tests/ -v
```

## Verified On

| Project | Context |
| --- | --- |
| ProjectScylla | narrow-mypy-override-subset (PR #1316); testing-regression-guard (PR #1968) |
| ProjectOdyssey | enable-mypy-check-untyped-defs (PR #4036); batch-fix-implementation; fix-placeholder-code-ci (PR #3017); ruff-c901-mccabe-complexity |
| ProjectAgamemnon | markdownlint-md024-siblings-only-for-changelogs (PR #404) |
| HomericIntelligence (ecosystem) | ci-deprecation-enforcement (PR #834); testing-regression-guard sweep (PR #5385, #5387) |
