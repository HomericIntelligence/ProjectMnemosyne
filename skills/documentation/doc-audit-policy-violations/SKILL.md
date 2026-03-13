# Skill: Audit Documentation Examples for Policy Violations

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| Issue | #878 |
| PR | #925 |
| Category | documentation |
| Objective | Systematically audit all markdown documentation for command examples that contradict CLAUDE.md policies |
| Outcome | Success — audit script created, no violations found in primary docs (previous fix by #758 had already cleaned up the only known violation) |

## When to Use

Trigger this skill when:

- A policy violation is discovered in documentation examples and you want to check whether similar violations exist elsewhere
- A new policy rule is added to CLAUDE.md and you need to verify no existing docs contradict it
- You want to catch doc policy drift proactively (e.g., before a major release or after a policy change)
- Running as a CI gate to prevent future violations from being introduced

## Verified Workflow

### 1. Scope the audit

The canonical policies to check are defined in `CLAUDE.md`. The four enforced rules:

| Rule ID | Violation | Policy |
|---------|-----------|--------|
| `no-label-in-pr-create` | `gh pr create --label` | Labels are prohibited |
| `no-verify-in-commit` | `git commit --no-verify` | Absolutely prohibited |
| `wrong-merge-strategy` | `gh pr merge --merge` or `--squash` | Must use `--auto --rebase` |
| `push-direct-to-main` | `git push origin main/master` | Must use PRs |

### 2. Run the audit script

```bash
# Report all violations with file:line references
pixi run python scripts/audit_doc_examples.py

# Verbose mode (shows violating line content)
pixi run python scripts/audit_doc_examples.py --verbose

# JSON output (for programmatic consumption)
pixi run python scripts/audit_doc_examples.py --json
```

Exit code: `0` = no violations, `1` = violations found.

### 3. Interpret findings

The script scans only **fenced shell code blocks** (bash/sh/shell/zsh/console or untagged), never prose text, to avoid false positives from prohibition text like "Never use --no-verify".

Excluded paths (archived/test-fixture content):

- `docs/arxiv/`
- `tests/claude-code/`
- `.pixi/`
- `build/`
- `node_modules/`

### 4. Fix any violations found

For each violation:

1. Read the file at the reported `file:line`
2. Determine whether it's a real violation or a false positive (see False Positives section)
3. If real: make the minimal fix — remove or replace the offending flag/command
4. Re-run audit to confirm clean

### 5. Add a regression test

If a new violation pattern is discovered, add a test case to `tests/unit/scripts/test_audit_doc_examples.py`:

```python
def test_detects_new_violation_type(self, tmp_path: Path) -> None:
    """Should flag <description>."""
    md = make_md(tmp_path, "bad.md", """\
        ```bash
        <violating command here>
        ```
        """)
    findings = scan_file(md, tmp_path)
    assert any(f.rule == "new-rule-id" for f in findings)
```

### 6. Commit and PR

```bash
git add scripts/audit_doc_examples.py tests/unit/scripts/test_audit_doc_examples.py
git commit -m "feat(scripts): Add doc audit script for policy violation detection

Closes #<issue>"
git push -u origin <branch>
gh pr create --title "feat(scripts): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## False Positives

### Pattern 1: Prohibited examples annotated with `# BLOCKED` or `# PROHIBITED`

**Trigger**: `git push origin main  # BLOCKED - Will be rejected by GitHub` in CLAUDE.md

**Why**: CLAUDE.md's "ABSOLUTELY PROHIBITED" section intentionally shows the wrong pattern with a comment explaining it's blocked. The `push-direct-to-main` rule excludes lines containing `#` (any inline comment).

**Resolution**: Already handled — the pattern excludes comment-annotated lines via `(?![^#]*#)` negative lookahead.

### Pattern 2: Prose inside commit message bodies

**Trigger**: `CONTRIBUTING.md which included --label in the gh pr create example.` inside a multi-line `git commit -m "..."` block

**Why**: A git commit message body containing the words `--label` and `gh pr create` matched the original broad regex.

**Resolution**: Already handled — the `no-label-in-pr-create` rule anchors to lines that start with `gh` (possibly with leading whitespace), requiring it to look like a real command invocation.

### Pattern 3: `gh issue list --label` (legitimate flag use)

**Why**: `--label` is only prohibited for `gh pr create`. Using it with `gh issue list` is valid.

**Resolution**: Already handled — the pattern specifically requires `gh pr create` before `--label`, not just any `gh` subcommand.

## Results & Parameters

### Script location

`scripts/audit_doc_examples.py` — uses `scylla.automation.git_utils.get_repo_root` (NOT `from common import get_repo_root` which breaks under pytest's import path).

### Test suite

`tests/unit/scripts/test_audit_doc_examples.py` — 36 tests, all passing.

Test classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestExtractCodeBlocks` | 7 | Code block extraction |
| `TestScanFileDetectsViolations` | 6 | All 4 rules triggered |
| `TestScanFilePassesCleanExamples` | 7 | Compliant examples pass |
| `TestFindingMetadata` | 4 | Severity, path, line, content |
| `TestScanRepositoryExclusions` | 6 | Path exclusion (parametrized) |
| `TestFormatTextReport` | 4 | Report formatting |
| `TestFormatJsonReport` | 2 | JSON serialization |

### Audit result on this repo (2026-02-21)

```
No policy violations found.
```

The only historical violation (`--label` in `CONTRIBUTING.md`) was already fixed by PR #871 (issue #758).

## Failed Attempts

### Import pattern: `from common import get_repo_root` fails under pytest

**What happened**: `scripts/common.py` re-exports `get_repo_root` with `from common import get_repo_root`. This works when running scripts directly (CWD = `scripts/`), but fails under pytest because `scripts/` is on `sys.path` as a package (`pythonpath = ["."]` in `pyproject.toml`), so `import common` resolves to the module but `from common import get_repo_root` inside `audit_doc_examples.py` fails at collection time.

**Fix**: Import directly from `scylla.automation.git_utils`:

```python
# WRONG — fails under pytest
from common import get_repo_root

# CORRECT — works everywhere
from scylla.automation.git_utils import get_repo_root
```

**Note**: `scripts/check_model_config_consistency.py` avoids this because it doesn't use `common.py` at all.

### First regex for `push-direct-to-main` was too broad

**What happened**: The initial pattern `r"git\s+push\b(?!.*--delete\b).*\b(?:origin\s+main|...)\b"` flagged `git push origin main  # BLOCKED - Will be rejected by GitHub` in CLAUDE.md.

**Fix**: Added `(?![^#]*#)` negative lookahead to exclude lines with inline comments:

```python
r"git\s+push\b(?!.*--delete\b)(?![^#]*#).*\b(?:origin\s+main|origin\s+master|...)\b"
```

### First regex for `no-label-in-pr-create` was too broad

**What happened**: The initial bidirectional pattern `r"gh\s+pr\s+create\b.*--label\b|--label\b.*gh\s+pr\s+create\b"` matched a prose line inside a commit message body: `CONTRIBUTING.md which included --label in the gh pr create example.`

**Fix**: Anchored the pattern to command-like lines starting with `gh` (with optional leading whitespace):

```python
r"^\s*(?:gh|\$\s*gh|\\)\s*(?:pr\s+create\b.*--label\b|.*--label\b.*gh\s+pr\s+create\b)"
```

### Ruff D102: missing docstrings in test methods

**What happened**: First version of test file had test methods without docstrings. Ruff enforces D102 (missing docstring in public method) including for test methods.

**Fix**: Add a one-line docstring to every test method. These can be concise (e.g., `"""Should flag gh pr create that includes --label."""`).
