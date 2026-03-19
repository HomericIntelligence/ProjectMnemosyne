---
name: workflow-smoke-tests
description: 'Write pytest smoke tests and pre-commit hooks to prevent GitHub Actions
  security workflow regressions. Use when: (1) security workflow gaps were fixed and
  need regression protection, (2) CI properties like triggers/flags need continuous
  verification, (3) a pygrep pre-commit hook should catch bad patterns in workflow
  files.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Workflow Smoke Tests

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Add regression tests preventing recurrence of security workflow gaps |
| Outcome | Operational — applied in ProjectOdyssey PR #3945 (issue #3318) |

After fixing security workflow gaps (see `fix-security-scan-gaps` skill), the next
step is continuous verification. This skill covers writing pytest smoke tests, a
dedicated CI workflow, and a pygrep pre-commit hook to enforce the fixed properties.

## When to Use

- Security workflow gaps were fixed (missing trigger, silenced failures, wrong flags)
- Need automated tests to prevent those gaps from being re-introduced
- A workflow property must be enforced on every PR touching that workflow file
- Want a fast-fail pre-commit gate before heavy CI setup runs

## Verified Workflow

### Step 1: Create pytest smoke tests

Place in `tests/smoke/test_<workflow>_properties.py`. Use a `scope="module"` fixture
to read the workflow file once, then group assertions by concern:

```python
import re
from pathlib import Path
import pytest

WORKFLOW = Path(__file__).parent.parent.parent / ".github" / "workflows" / "security.yml"

@pytest.fixture(scope="module")
def workflow_content() -> str:
    assert WORKFLOW.exists(), f"Workflow not found at {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")

class TestTriggers:
    def test_pull_request_trigger(self, workflow_content: str) -> None:
        assert re.search(r"^\s+pull_request\b", workflow_content, re.MULTILINE), (
            "security.yml is missing pull_request trigger. "
            "Add 'pull_request:' under the 'on:' block."
        )

class TestSemgrepStep:
    def test_no_continue_on_error(self, workflow_content: str) -> None:
        semgrep_block_match = re.search(
            r"(returntocorp/semgrep-action|semgrep/semgrep-action).*?(?=\n\s*-\s+name:|\Z)",
            workflow_content, re.DOTALL
        )
        assert semgrep_block_match is not None, "No Semgrep action found"
        assert "continue-on-error: true" not in semgrep_block_match.group(0), (
            "Semgrep step has continue-on-error: true — remove it."
        )

class TestGitleaksStep:
    def test_no_no_git_flag(self, workflow_content: str) -> None:
        assert "--no-git" not in workflow_content, (
            "Gitleaks uses --no-git — remove it to scan full git history."
        )
```

**Key pattern**: Use `re.DOTALL` when extracting multi-line step blocks to avoid
matching the wrong section. Scope the search with a lookahead that stops at the
next `- name:` step header.

### Step 2: Add pygrep pre-commit hook for the most critical property

For properties that can be expressed as "this pattern must NOT appear", use pygrep:

```yaml
- repo: local
  hooks:
    - id: check-security-workflow-no-git
      name: Check Gitleaks has no --no-git flag
      description: Prevent regression of security scan gaps
      entry: 'gitleaks detect.*\-\-no\-git'
      language: pygrep
      files: ^\.github/workflows/security\.yml$
```

**Critical**: Do NOT use `--no-git` as the `entry` value directly — pre-commit
treats it as a CLI flag for the pygrep runner, causing `unrecognized arguments` error.
Anchor the pattern with context: `gitleaks detect.*\-\-no\-git`.

**For positive assertions** (pattern MUST be present): pygrep cannot do this natively.
Use a dedicated CI workflow step instead (see Step 3).

### Step 3: Create a CI workflow for smoke tests

```yaml
name: Workflow Smoke Tests
on:
  pull_request:
  push:
    branches: [main]
    paths:
      - '.github/workflows/security.yml'
      - 'tests/smoke/test_security_workflow_properties.py'

jobs:
  smoke-test-security-workflows:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@...

      # Fast grep checks BEFORE pixi/conda setup (saves 2-3 min on failure)
      - name: Check pull_request trigger present
        run: |
          grep -qP '^\s+pull_request\b' .github/workflows/security.yml || {
            echo "ERROR: missing pull_request trigger"; exit 1; }

      - name: Check Semgrep has no continue-on-error
        run: |
          grep -A20 'semgrep-action' .github/workflows/security.yml \
            | grep -q 'continue-on-error: true' && {
              echo "ERROR: Semgrep has continue-on-error: true"; exit 1; } || true

      - name: Check Gitleaks has no --no-git
        run: |
          grep -q -- '--no-git' .github/workflows/security.yml && {
            echo "ERROR: Gitleaks uses --no-git"; exit 1; } || true

      # Full pytest run for comprehensive assertions
      - name: Set up environment
        uses: ./.github/actions/setup-pixi

      - name: Run smoke tests
        run: pixi run python -m pytest tests/smoke/test_security_workflow_properties.py -v
```

**Design principle**: Put cheap grep checks before expensive environment setup.
If the workflow has a regression, fail fast in 30s instead of 3 minutes.

### Step 4: Fix the actual workflow before writing tests (TDD order matters)

1. First fix the gaps in the target workflow file
2. Then write the tests — they should pass immediately
3. Then add the pre-commit hook

Do NOT write tests for the broken state. Tests should document the correct state.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `entry: '--no-git'` in pygrep hook | Used `--no-git` directly as the pygrep entry pattern | pre-commit passes `entry` as program args; `--no-git` becomes a CLI flag, causing `unrecognized arguments` error | Prefix pattern with anchoring context: `gitleaks detect.*\-\-no\-git` |
| `pixi run pytest` pre-commit hook | Used `pixi run python -m pytest tests/smoke/...` as hook entry | pytest creates/modifies `__pycache__/*.pyc` files; pre-commit detects "files modified by hook" and fails commit even though tests pass | For pre-commit, use pygrep (no side effects) for negative assertions; reserve pytest for CI |
| `negate: true` on pygrep hook | Added `negate: true` to flip "pattern found = fail" to "pattern absent = fail" | `negate` is not a valid key for pygrep hooks in pre-commit; causes `Unexpected key` warning and hook is skipped | pygrep has no `negate` field — use `--negate` flag in a shell hook instead, or just flip the pattern logic |
| Calling pytest as pre-commit entry for positive assertions | Wanted pre-commit to enforce pull_request trigger presence | Same `__pycache__` modification problem; also slow (pixi startup ~30s per commit) | Use CI workflow for positive assertions; reserve pre-commit for fast negative pattern checks |

## Results & Parameters

Applied to ProjectOdyssey issue #3318, PR #3945:

- `tests/smoke/test_security_workflow_properties.py`: 7 assertions in 3 test classes
- `.github/workflows/workflow-smoke-test.yml`: Fast grep gate + pytest
- `.pre-commit-config.yaml`: pygrep hook for `gitleaks detect.*\-\-no\-git`
- All 7 tests pass in ~0.02s (no pixi startup after initial load)

**Test run command**:

```bash
pixi run python -m pytest tests/smoke/test_security_workflow_properties.py -v
```

**Pre-commit hook test** (verify it catches regressions):

```bash
# Temporarily add --no-git to security.yml, then run:
git add .github/workflows/security.yml
pixi run pre-commit run check-security-workflow-no-git --files .github/workflows/security.yml
# Should fail; restore the file and it should pass
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3945, issue #3318 | [notes.md](../references/notes.md) |
