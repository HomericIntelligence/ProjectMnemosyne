---
name: code-quality-enforcement-gates
description: "Canonical guide to code-quality enforcement THRESHOLDS, remediation workflow, and post-audit verification: when to fail builds on complexity, when to enable mypy strict modes, when to promote warnings to errors, how to scope override subsets, deprecation removal policy, how to fix production asserts/hardcoded paths, how to run a post-remediation audit, how to verify audit/PR-reviewer findings against ground truth before acting, and how to verify a TRACKING/REMEDIATION DOC's checkbox state against live `gh issue view` before editing it. Use when: (1) deciding fix-vs-suppress for a new lint rule, (2) enabling mypy check-untyped-defs or new ruff rules, (3) promoting CI warnings to exit-1, (4) tuning markdownlint MD024 / ruff C901 thresholds, (5) narrowing mypy module override globs to specific paths, (6) replacing production assert input-validation or hardcoded /tmp paths with safe equivalents, (7) executing a post-remediation audit to close remaining CI/classifier/release/docs gaps after an initial cleanup, (8) strict-mode repo audits or PR-reviewer sub-agents produce hallucinated findings (nonexistent files, phantom CI checks, red-on-main checks cited as PR blockers) — verify against live state before acting, (9) the task is 'fix stale checkboxes in a tracking/remediation markdown doc' — verify EVERY box against live `gh issue view` (the doc AND the bug report's own stale-list are not authoritative) before editing, and guard re-drift with a PROPERTY-based regression test."
category: ci-cd
date: 2026-06-20
version: "1.2.0"
user-invocable: false
verification: verified-local
history: code-quality-enforcement-gates.history
tags: [merged, code-quality, quality-gate, mypy, ruff, complexity-budget, deprecation, post-remediation-audit, audit-verification, fact-checking, production-code-fixes, tracking-doc, remediation-plan, checkbox-drift]
---

# Code-Quality Enforcement Gates

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Canonical reference for when and how to turn lint warnings into hard build failures, fix production code-quality issues, run a post-remediation audit, and verify audit/reviewer findings before acting |
| **Outcome** | Merged from 11 skills — covers complexity thresholds, mypy strictness, deprecation enforcement, markdown rule tuning, override narrowing, regression-guard tests, production assert/path fixes, post-remediation auditing, and ground-truth verification of hallucinated findings |
| **Scope** | ci-cd quality gates, remediation workflow, and audit verification — for hook wiring / pre-commit-config surface area see M1 (pre-commit-linting-hooks-config) |

## When to Use

1. Deciding whether to **fix or suppress** a newly enabled lint rule (ruff C901, mypy strict, etc.)
2. Enabling **mypy `check_untyped_defs`** or `disallow_untyped_defs` and fixing surfaced errors
3. **Promoting a CI `::warning::`** grep step to `::error::` + `exit 1` enforcement
4. Tuning **markdownlint MD024** (`siblings_only`) or ruff **C901** (mccabe `max-complexity`) thresholds
5. **Narrowing mypy module glob overrides** to exclude a fully-annotated subdir
6. Coordinating **batch fixes** across 5+ files in a single PR
7. Fixing **placeholder code / type-migration assertion** CI failures
8. **Fixing regression-guard tests** that pin to suppression syntax before an ecosystem sweep
9. Replacing **production `assert` input validation** (stripped by `python -O`) with explicit `ValueError`, or **hardcoded `/tmp` paths** with `tempfile`
10. Running a **post-remediation audit** to close residual CI/classifier/release-gate/docs gaps before ecosystem integration
11. **Verifying audit or PR-reviewer findings against ground truth** before writing a remediation plan, filing issues, or posting a REQUEST_CHANGES verdict (strict-mode audits and reviewer sub-agents hallucinate ~10–30% of findings)
12. **Planning a tracking/remediation-doc checkbox correction** — the task is "fix stale `- [ ]` / `- [x]` state in a remediation-plan / roadmap / status markdown doc": verify EVERY checkbox against live `gh issue view <n> --json state` before editing, then guard re-drift with a property-based regression test (see §11)

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
| Production assert / `/tmp` | Replace with `raise ValueError` / `tempfile.gettempdir()` | `python -O` strips asserts; grep `tests/` for `AssertionError` after |
| Post-remediation audit | Read state in parallel → fix classifier/release/docs gaps | Classifiers reflect what CI tests; release needs `needs: test` gate |
| Verify audit/reviewer findings | `ls` / `grep` / `git ls-files` / `gh run list --branch main` | 10–30% of strict-audit & reviewer findings are hallucinated; verify before acting |
| Verify tracking-doc checkboxes (PLANNING) | `gh issue view <n> --json state` per box; property regression test | Doc + bug-report list are NOT authoritative; box ticked ⟺ ALL issues on line CLOSED. Planning-stage; test shape unverified until PR lands |

---

### 1. Ruff C901 McCabe Complexity Gate

**Decision rule:** Accept complexity 11–12 for orchestration/CLI code. Suppress >12 with documented rationale. Default threshold (10) is too strict for non-trivial orchestration.

**Step 1 — Audit violations**, then set `max-complexity = 12`:

```bash
pixi run ruff check <source-dirs>/ --select C901 2>&1 | grep -E "C901|-->" | paste - -
```

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]
[tool.ruff.lint.mccabe]
max-complexity = 12
```

**Step 2 — Add annotated suppressions — noqa MUST be on the `def` line** (ruff ignores it on the
return-type / closing line of a multi-line signature):

```python
def run_subtest(  # noqa: C901  # orchestration with many retry/outcome paths
    self, tier_id: TierID,
) -> SubTestResult:
```

Standard rationale categories: `orchestration with many retry/outcome paths` (`run`, `_implement_all`);
`pipeline with sequential conditional stages` (`_run_mojo_pipeline`); `CLI dispatch with many command
branches` (`main`, `cmd_run`); `validation with many independent rule checks` (`validate_frontmatter`);
`config loader with many format/version branches` (`load_rubric_weights`); `AST traversal with many node
type branches` (`detect_shadowing`).

**Step 3 — Verify:** `pixi run ruff check <source-dirs>/ --select C901` then full `ruff check` + tests.

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

**Promotion checklist:** confirm count is 0 → classify any hit as caller (remove) or safe reference
(exclude) → add `grep -v` for re-exports and docstring annotations → rename step "Track..." →
"Enforce..." → `::warning::` → `::error::` → add `exit 1` → mirror exclusions into the diagnostic grep
block → run the full test suite.

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

Any hits must be fixed in a **predecessor PR** before the sweep. The anti-pattern is pinning to a
literal (`assert "continue-on-error: true" in step_text`) — assert the property instead.

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

### 8. Production Code Quality Fixes (assert / hardcoded path)

**Production `assert` for input validation is unsafe** — `python -O` (optimized mode) strips all
`assert` statements at compile time, leaving a silent validation gap. Replace with an explicit raise.

**Step 1 — Locate asserts outside test files:**

```bash
grep -rn "^    assert\|^assert" <source-dir>/ --include="*.py"
```

**Step 2 — Replace assert → `ValueError`:**

```python
# Before — stripped by python -O
assert 0.0 <= score <= 1.0, f"Score {score} is outside valid range [0.0, 1.0]"

# After — always enforced
if not (0.0 <= score <= 1.0):
    raise ValueError(f"score must be in [0.0, 1.0], got {score}")
```

**Step 3 — Locate and replace hardcoded `/tmp` paths:**

```bash
grep -rn '"/tmp/' <source-dir>/ --include="*.py"
```

```python
# Before — not cross-platform; collides under parallel runs
env["PYTHONPYCACHEPREFIX"] = "/tmp/scylla_pycache"

# After — portable
import tempfile
env["PYTHONPYCACHEPREFIX"] = str(Path(tempfile.gettempdir()) / "scylla_pycache")
```

Check existing imports first — `tempfile` and `Path` are often already imported.

**Step 4 — CRITICAL: update tests that expected `AssertionError`:**

```bash
grep -rn "AssertionError" tests/ --include="*.py"
```

```python
# Before
with pytest.raises(AssertionError, match="outside valid range"):
    assign_letter_grade(1.1)
# After
with pytest.raises(ValueError, match="score must be in"):
    assign_letter_grade(1.1)
```

Add a parametrized boundary test for the new `ValueError`, then run affected tests + pre-commit on
the changed files only.

---

### 9. Post-Remediation Audit (close residual gaps)

**When to use:** after a first-pass cleanup, before ecosystem integration — verifies CI/classifier
alignment, release-gate safety, undocumented CLI tools, and residual code smells.

**Step 1 — Read current state in parallel** (single batch): `pyproject.toml` (classifiers, pytest
version, console_scripts), `.github/workflows/release.yml` (test gate), `README.md` (CLI docs), and
the source files flagged for bare-except / redundant-import smells.

| Issue Type | File | Fix |
| --- | --- | --- |
| Classifier/CI mismatch | `pyproject.toml` classifiers | Remove classifiers for untested Python versions |
| pytest version skew | `pyproject.toml` dev deps | Align to range tested in `pixi.toml` |
| Release without test gate | `.github/workflows/release.yml` | Add `test` job + `needs: test` on publish job |
| Undocumented CLI | `README.md` | Add CLI Commands section with table + examples |
| Bare `except Exception: pass` | Source file | Add inline comment justifying the broad catch |
| Redundant local import | Source file | Remove — use module-level import directly |
| Empty placeholder dirs | `scripts/` | `rmdir` the empty directories |

**Step 2 — Classifiers reflect what CI tests, not aspiration:**

```toml
# pyproject.toml — REMOVE untested versions (CI only tests 3.12)
classifiers = ["Programming Language :: Python :: 3",
               "Programming Language :: Python :: 3.12"]
```

**Step 3 — Gate the release workflow on tests** — add a `test` job and `needs: test` on the
`build-and-publish` job so a failed test blocks the PyPI publish.

**Step 4 — Fix residual smells:**

```python
except Exception:  # /etc/os-release parsing is best-effort; any failure is non-fatal
    pass
```

Remove redundant local imports (e.g. `import re as _re` inside a method when `re` is module-level)
and `rmdir` empty placeholder directories.

**Step 5 — Verify all green** before committing:

```bash
pixi run ruff check <pkg>/ tests/
pixi run mypy <pkg>/
pixi run pytest tests/unit -q
pre-commit run --all-files
```

Commit with a structured conventional message listing every audit item. Outcome reference: 82% → 86%
grade across 15 dimensions, coverage above the threshold, all hooks green.

**Audit checklist (copy-paste):**

```markdown
- [ ] CI matrix Python versions match pyproject.toml classifiers
- [ ] pytest version range in dev deps matches pixi.toml lower bound
- [ ] Release workflow has `needs: test` before publish job
- [ ] All `console_scripts` documented in README with examples
- [ ] No unjustified `except Exception: pass` (add comment or narrow exception)
- [ ] No redundant local imports (check `__init__` methods especially)
- [ ] No empty placeholder directories in scripts/
- [ ] Coverage threshold consistent across pyproject.toml, pytest addopts, and CI
```

---

### 10. Verify Audit & Reviewer Findings Against Ground Truth Before Acting

Strict-mode repo audits AND PR-reviewer sub-agents routinely **hallucinate** findings (references to
nonexistent files, "missing CI checks" that already exist, a red-on-the-PR check that is ALSO red on
`main`) and **miss** real ones (linters present but enforcing the wrong rule). Observed false-positive
rate: **10–30% across multiple sessions.** Verify each finding against live state BEFORE writing a
remediation plan, filing issues, or posting a REQUEST_CHANGES verdict.

**Per-finding 30-second verify:**

```bash
ls <path-the-audit-claimed-is-missing>   # is the file really absent?
grep -rn <symbol-or-config> <path>        # is the integration really missing?
git ls-files <path>                       # is the file really tracked? (empty = not tracked)
git log --all -- <path>                   # was it ever there?
```

| Finding type | Verify with |
| --- | --- |
| "Reference to missing file X" | `ls X && grep -rln 'pattern' <dir>` — absent file AND no reference → hallucinated |
| "No SAST/secrets-scan/dep-audit in CI" | `grep -rniE 'gitleaks\|trufflehog\|detect-secrets\|pip-audit\|bandit\|codeql\|semgrep' .github/` — controls often live in an aggregator / `_required.yml`, not the file named after them |
| "File X tracked despite .gitignore" | `git ls-files X` — empty output means not tracked → already-fixed-state hallucination |
| "File A duplicates file B" | Read BOTH files — do not trust prose summaries of structural overlap |
| "Function X has wrong return type" | `grep -nE '^def X' <file>` + read every `return` |

**Run Phase 1 verification BEFORE drafting the remediation plan** — not before issue filing. Drafting
against unverified findings produces PRs that fix non-issues AND leaves the real root causes untouched.
Dispatch ONE Explore agent with the full findings list; it returns a STATUS table
(CONFIRMED / REFUTED / PARTIAL with evidence).

**Search the inverse hypothesis space (Phase 1.5):** for every "X is MISSING" finding, also ask "is X
PRESENT but WRONG?" (e.g. "linter MISSING" → "linter present but enforcing the WRONG rule"; "no CI gate
for Y" → "gate exists but `continue-on-error: true` makes it a no-op"). This is the most common audit
blind spot and often the actual root cause. Worked example: an audit flagged skills mandating `--rebase`
despite squash-only policy; the inverse check found `validation/doc_policy.py` was REJECTING `--squash` —
the linter was the ROOT CAUSE. Sequencing PR1 = fix linter, PR2+ = fix skills made all 10 PRs pass CI.

**Every audit-driven remediation plan MUST contain an `## AUDIT CORRECTIONS` section** listing what
Phase 1 refuted (with evidence) and an `## AUDIT-MISSED FINDINGS (NEW)` section listing inverse-search
discoveries — this bridges the audit's finding count to the plan's PR count for reviewers.

**PR-reviewer REQUEST_CHANGES verdict — check `main` before blocking on a red check:**

```bash
# 1. Get the failing check names on the PR
gh pr view N --repo OWNER/REPO --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.conclusion=="FAILURE") | .name'
# 2. Check the same names on latest main
gh run list --repo OWNER/REPO --branch main --limit 5 \
  --json name,conclusion,headSha --jq '.[] | "\(.headSha[0:8]) \(.name) \(.conclusion)"'
# 3. If a failure appears on BOTH the PR and latest main for the same job name,
#    it's pre-existing -> mention it but do NOT block on it.
```

A `feature-dev:code-reviewer` sub-agent sees only the PR's `statusCheckRollup` and has no visibility
into `main`'s independent CI state. Trusting its label without checking `main` produces false
REQUEST_CHANGES verdicts that unfairly block clean dependency bumps.

**Triage rule:** if verification refutes a finding, log it but do NOT file an issue or open a PR. If
the stale-finding rate exceeds 20%, question the audit methodology, not the codebase. Verification is
"cheaply confirm each," not "distrust everything" — verified MAJOR findings still hold up.

---

### 11. Verify a Tracking/Remediation Doc's Checkboxes Before Editing (planning-stage sub-pattern of §10)

> **Planning-stage pattern — the NEW additions in this section are `unverified`.** They come from a
> PLANNING session for a ProjectProteus tracking-doc correction; the regression-test *shape* below was
> NOT implemented or CI-run. Treat the test as a hypothesis until the PR lands. The §10 ground-truth
> principle it extends is `verified-local`; this concrete sub-pattern is not.

When the task is "fix stale state in a tracking/remediation doc" (a `docs/.../remediation-plan.md`
with `- [ ]` / `- [x]` checkboxes that claim issue/PR state), the **doc's own claims are NOT
authoritative — and neither is the bug report that asked you to fix it.** In the originating session,
the triggering issue body listed which entries were stale; verifying every box against live `gh`
surfaced **two additional stale entries (#92, #100) the issue body never mentioned.** Apply §10's
ground-truth rule per checkbox:

```bash
# For EVERY checkbox in the doc — not just the ones the bug report names — verify live state.
gh issue view <n> --repo OWNER/REPO --json state --jq .state   # OPEN | CLOSED
```

**Checkbox semantics (the load-bearing nuance):** Wave-3 lines in this doc are **PR-GROUP scoped, not
per-issue.** A group box may be ticked ONLY when **EVERY** issue on the line is CLOSED. Ticking a group
(e.g. PR-C / PR-E) that still has an open child (#98 / #101 / #103) falsely marks work done. The rule:
`box ticked ⟺ ALL issue numbers on the line are CLOSED`.

**Then guard re-drift with a PROPERTY-based regression test, not a literal-text assertion** (this is
§5 applied to a doc): assert the invariant `all referenced issues CLOSED ⇒ box ticked`, wired into the
repo's existing CI test job, skipping gracefully when `gh` is unauthenticated. The property only fires
when ALL issues on a line are closed, so it correctly does NOT trip on partial PR groups.

**Risks to record in the plan (do not gloss over these):**

- **Silent false-green from skip-on-unauth.** A `gh`-dependent CI test that skips when unauthenticated
  becomes a **no-op** if the CI `GITHUB_TOKEN` lacks issue-read scope — the guard passes while
  protecting nothing. Either ensure CI provides an authenticated token, or **fail loudly when
  unauthenticated in a CI context** rather than skipping. (A self-contained committed-fixture invariant
  table avoids the network/auth dependency entirely — see the dedicated
  `tracking-doc-checkbox-sync-regression-guard` skill, which supersedes the live-`gh` design.)
- **Network / rate-limit dependency.** The test calls `gh` on every CI run.
- **Point-in-time snapshot.** Issue state read at planning time can change (an issue may reopen) before
  implementation; a live re-checking test self-heals, but the static edits do not.
- **Stale line/coordinate refs.** Line numbers in `remediation-plan.md` (e.g. line 21/25) and
  `_required.yml:158-159` job name `dispatch-contract-test` were relied on WITHOUT re-verification at
  implement time — re-grep at edit time; line refs go stale even when the finding is true (§10).

**For the full, executed (verified-local) regression-guard design** — committed-fixture invariant table,
stable per-line keys, bidirectional SEEN-set coverage, and why a live-`gh` guard is the wrong design —
see the dedicated `tracking-doc-checkbox-sync-regression-guard` skill.

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
| Replacing production assert without updating tests | Swapped `assert` → `raise ValueError` and committed | A pre-existing test expecting `AssertionError` failed CI | After replacing asserts, `grep tests/ -rn AssertionError` and update each to `ValueError` |
| `noqa: BLE001` on bare except | Added `# noqa: BLE001` to suppress the broad-except warning | `BLE001` was not in the project's ruff `select` → "unused noqa directive" error | Check `[tool.ruff.lint] select` before adding noqa codes; use a plain justifying comment when the rule isn't selected |
| Relative `cd build/$$/...` in Bash | Used a relative path with shell PID `$$` | `$$` expanded to empty string in the tool invocation context | Always use absolute paths; capture `$$` into a variable first |
| File all audit findings as issues, then triage in PRs | Trusted the audit; assumed the backlog would sort itself | 3 of 11 majors were stale → 3 PRs would have "fixed" non-issues (e.g. adding gitleaks when already present) | Triage during audit-consume, not after issue filing |
| Re-run the audit to "verify itself" | Hoped a second pass would catch the hallucinations | Identical output — strict-mode prompt + same model = same hallucinations | Audits cannot fact-check themselves; verify against the filesystem |
| Believe "CRITICAL" severity tags | Deferred to the audit's own ranking | A hallucinated "CRITICAL: missing hook" — severity tag does not correlate with accuracy | Severity is a model's prediction, not a filesystem fact |
| Trust "missing control" from the obviously-named file | Read only `security.yml`, declared "no secrets-scanning in CI" | Gitleaks was a REQUIRED check in `_required.yml` — a file the agent never grepped | For any "missing X" claim, grep the WHOLE `.github/`/repo — controls live in aggregator/required workflows |
| File/fix at the audit's cited file:line without re-checking | Opened the issue/PR at the exact reported line | Line refs were stale even in TRUE findings (line 18 vs 19; already-fixed `timeout=10`) | Re-verify exact file:line at fix time; a finding can be real while its location is stale |
| Draft remediation plan from raw audit output | Started planning before Phase 1 verification | 10.3% of findings refuted on disk → PRs that fix non-issues, root causes left untouched | Run Phase 1 verification BEFORE drafting the plan, not before issue filing |
| Skip the inverse-hypothesis check | Treated the audit's hypothesis space as complete | Missed a `doc_policy.py` linter REJECTING `--squash` — the actual root cause | For every "X is missing", also ask "is X present but wrong?" |
| Omit the AUDIT CORRECTIONS section | Handed the plan to reviewers without explaining the count gap | Reviewers confused; downstream agents re-introduced refuted findings | Every audit-driven plan needs an AUDIT CORRECTIONS section with refutation evidence |
| Post REQUEST_CHANGES citing a red CI check | Reviewer agent said CI was red, so drafted REQUEST_CHANGES | The same check was ALSO red on `main` — failure was pre-existing, not PR-introduced | `gh run list --branch main --limit 5` before treating a red check as PR-introduced |
| Trusted the issue body's list of stale entries | Took the triggering issue's "these boxes are stale" list as complete | It omitted #92 and #100 — both actually stale | Enumerate EVERY checkbox and verify each against `gh issue view`; the bug report's own list is a self-report, not ground truth |
| Treated Wave-3 PR-group lines as per-issue checkboxes | Would tick a group box because one child issue closed | PR-C / PR-E still had open issues (#98/#101/#103) — group would falsely read "done" | Tick a group line only when ALL its issue numbers are CLOSED; the property test fires only on all-closed |
| Regression test asserting literal line text | `assert "- [x] #84 ..." in doc` style positional/wording check | Breaks on any legitimate wording change → false regression noise | Assert the PROPERTY (`all referenced issues CLOSED ⇒ box ticked`), not the literal line |
| `gh`-dependent CI test with silent skip-on-unauth | Test SKIPs (exit 0) when `gh` is unauthenticated | A missing/under-scoped CI token turns the guard into a no-op false-green — zero protection in exactly the env CI runs in | Provide an authenticated token, or fail loudly when unauth in CI; prefer an offline committed-fixture invariant table (see tracking-doc-checkbox-sync-regression-guard) |

---

## Results & Parameters

### Ruff C901 Summary

| Complexity range | Action |
| --- | --- |
| ≤ 10 (default) | No suppression needed |
| 11–12 (accepted) | No change needed at `max-complexity = 12` |
| > 12 | `# noqa: C901  # <rationale>` on the `def` line |

### Key Config & Parameter Reference

```toml
# pyproject.toml — quality-gate anchors
[tool.mypy]
disallow_untyped_defs = true
check_untyped_defs = true
[[tool.mypy.overrides]]                 # narrow override: explicit list, not broad glob
module = ["tests.unit.adapters.*", "tests.unit.analysis.*"]  # one entry per unannotated subdir
disable_error_code = ["no-untyped-def"]

[tool.ruff.lint.mccabe]
max-complexity = 12                      # pragmatic threshold for orchestration code
```

```yaml
# .markdownlint.yaml — MD024 fix + changelog companions
MD024: { siblings_only: true }
MD013: false
MD033: { allowed_elements: [br, details, summary] }
MD034: false
```

**Batch fix:** 5–12 low-complexity issues per PR; read all files before editing; Python `re.sub` for
10+ bulk replacements; validate changed lines via `git diff`.

**Deprecation gate / post-fix verification:**

```bash
# Deprecation: count MUST be 0 before promoting ::warning:: → ::error:: + exit 1
count=$(grep -rn "<DeprecatedSymbol>" . --include="*.py" --exclude-dir=".pixi" \
  | grep -v "<definition_file>" | grep -v "# deprecated" | grep -v "(deprecated)" | wc -l); echo "$count"
# After any production-code or migration fix, run tests + pre-commit on changed files
<package-manager> run python -m pytest tests/ -v
```

**Audit verification metrics:** 10–30% of strict-audit/reviewer findings are hallucinated
(3/11, ~3/16, 3/29 refuted across three sessions); ~30s verify per finding vs ~30 min per
false-positive PR; post-remediation audit moved a repo 82% → 86% across 15 dimensions.

## Verified On

| Project | Context |
| --- | --- |
| ProjectScylla | narrow-mypy-override-subset (PR #1316); testing-regression-guard (PR #1968); production-code-quality-fixes (issue #757, PR #891) |
| ProjectOdyssey | enable-mypy-check-untyped-defs (PR #4036); batch-fix-implementation; fix-placeholder-code-ci (PR #3017); ruff-c901-mccabe-complexity |
| ProjectAgamemnon | markdownlint-md024-siblings-only-for-changelogs (PR #404) |
| ProjectHephaestus | post-remediation-audit (82% → 86%, 358 tests); verify-audit-findings-before-acting (strict-full audits 2026-05-26/27/31, 10–30% findings refuted) |
| AchaeanFleet | verify-audit-findings-before-acting (Dependabot review session — 2 reviewer agents cited pre-existing main-branch CI failures as PR blockers; PR #688 flipped to APPROVE) |
| HomericIntelligence (ecosystem) | ci-deprecation-enforcement (PR #834); testing-regression-guard sweep (PR #5385, #5387) |
| ProjectProteus | verify-tracking-doc-checkboxes (§11, PLANNING-stage, unverified): remediation-plan checkbox correction — per-box `gh issue view` surfaced 2 extra stale entries (#92, #100) the issue body omitted; PR-group line semantics + property-regression-test plan. Test shape not yet implemented/CI-run |
