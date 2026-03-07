---
name: dockerfile-cargo-free-regression
description: "Add static regression tests and pre-commit hooks to assert a forbidden shell pattern is absent from Dockerfiles. Use when: a dep was removed from Dockerfiles and you want to prevent re-introduction, or when adding absent-pattern guards."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Objective** | Prevent re-introduction of a removed Dockerfile dependency via pytest regression tests and a pygrep pre-commit hook |
| **Trigger** | Dependency removed from Dockerfile; need automated guard against regression |
| **Output** | `tests/foundation/test_dockerfile_<name>.py` + pre-commit hook in `.pre-commit-config.yaml` |
| **Language** | Python (pytest) |
| **Project** | ProjectOdyssey / any repo with Dockerfiles and pytest |

## When to Use

- A `cargo`, `rustc`, or other heavy build-time dependency was removed from Dockerfiles in favor of a pre-built binary
- You want to block future contributors from re-adding the dependency without noticing
- An issue requests "add a static regression test for X-free build" as a follow-up
- You need both a pytest test (for visibility in test reports) and a commit-time guard (pre-commit hook)

## Verified Workflow

### 1. Identify the forbidden patterns

Two patterns to guard (example: `cargo`):

- `apt-get install[^\n]*\bcargo\b` — catches cargo as an apt dependency
- `\bcargo\s+install\b` — catches `cargo install` anywhere in the file

### 2. Scan existing Dockerfiles for false positives

```bash
grep -n 'cargo' Dockerfile Dockerfile.ci
```

**Critical**: comments containing the forbidden phrase will trigger the test.
Update any comments that contain the pattern before or immediately after writing the tests.

For example, `# much faster than cargo install` must become `# avoids cargo build-from-source`.

### 3. Write the pytest test

```python
"""Static regression tests asserting cargo is absent from Dockerfiles."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
DOCKERFILES = [REPO_ROOT / "Dockerfile", REPO_ROOT / "Dockerfile.ci"]


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=["Dockerfile", "Dockerfile.ci"])
class TestCargoAbsent:
    """Assert cargo does not appear in apt-get install or as cargo install."""

    def test_cargo_not_in_apt_get_install(self, dockerfile: Path) -> None:
        """Assert cargo is not listed as an apt-get install dependency."""
        content = dockerfile.read_text()
        match = re.search(r"apt-get install[^\n]*\bcargo\b", content)
        assert match is None, f"Found 'cargo' in apt-get install in {dockerfile.name}: {match.group()!r}"

    def test_cargo_install_not_present(self, dockerfile: Path) -> None:
        """Assert 'cargo install' does not appear anywhere in the Dockerfile."""
        content = dockerfile.read_text()
        match = re.search(r"\bcargo\s+install\b", content)
        assert match is None, f"Found 'cargo install' in {dockerfile.name}: {match.group()!r}"
```

### 4. Add the pygrep pre-commit hook

In `.pre-commit-config.yaml`, add inside the existing `local` repo block:

```yaml
      - id: no-cargo-in-dockerfile
        name: No cargo in Dockerfile
        description: Prevent re-introduction of cargo apt dependency or cargo install
        entry: '(cargo\s+install|apt-get install[^\n]*cargo)'
        language: pygrep
        files: ^Dockerfile(\.ci)?$
        types: [text]
```

### 5. Run tests and verify

```bash
pixi run python -m pytest tests/foundation/test_dockerfile_cargo_free.py -v
```

All 4 parametrized tests (2 patterns × 2 Dockerfiles) should pass.

### 6. Commit, push, and open PR

```bash
git add .pre-commit-config.yaml Dockerfile tests/foundation/test_dockerfile_cargo_free.py
git commit -m "test(foundation): add static regression tests for cargo-free Dockerfiles"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Initial regex `\bcargo\s+install\b` against Dockerfile | Ran tests immediately after writing | Matched `# Install just tool (pre-built binary, much faster than cargo install)` — a comment line | Scan target files for false positives **before** writing the test; update comments that contain the forbidden phrase |
| Keeping original Dockerfile comment | Left comment as-is, expected test to pass | The regex matches inside comments too — there is no Dockerfile "comment-aware" mode in Python `re` | Either strip comment lines before matching, or (simpler) reword the comment to avoid the forbidden phrase |

## Results & Parameters

### Pytest parametrize pattern

```python
DOCKERFILES = [REPO_ROOT / "Dockerfile", REPO_ROOT / "Dockerfile.ci"]

@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=["Dockerfile", "Dockerfile.ci"])
```

- One class, two test methods, two Dockerfiles → 4 test cases total
- `ids=` gives clean names in test output: `[Dockerfile]` / `[Dockerfile.ci]`

### pygrep hook pattern for Dockerfiles

```yaml
entry: '(cargo\s+install|apt-get install[^\n]*cargo)'
files: ^Dockerfile(\.ci)?$
types: [text]
```

- `pygrep` hooks run the regex against each matched file
- `files: ^Dockerfile(\.ci)?$` matches both `Dockerfile` and `Dockerfile.ci` only
- No `pass_filenames: true` needed — pygrep handles it automatically

### Generalization for other patterns

Replace `cargo` with any package name (e.g. `rustc`, `gcc`, `nodejs`):

```python
match = re.search(r"apt-get install[^\n]*\b<pkg>\b", content)
match = re.search(r"\b<pkg>\s+install\b", content)
```

```yaml
entry: '(<pkg>\s+install|apt-get install[^\n]*<pkg>)'
```
