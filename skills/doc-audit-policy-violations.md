---
name: doc-audit-policy-violations
description: "Skill: Audit Documentation Examples for Policy Violations"
category: documentation
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
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

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |