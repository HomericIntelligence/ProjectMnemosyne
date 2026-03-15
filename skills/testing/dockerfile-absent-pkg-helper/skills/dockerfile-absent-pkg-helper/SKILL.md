---
name: dockerfile-absent-pkg-helper
description: "Extract a shared assert_pkg_absent helper into conftest.py to DRY up Dockerfile absence regression tests. Use when: (1) multiple test methods repeat apt-get/install regex checks, (2) adding a new removed-dependency regression test, (3) refactoring Dockerfile test suites."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| Category | testing |
| Pattern | Extract shared helper to conftest.py |
| Language | Python / pytest |
| Test framework | pytest parametrize + class |

Extracts duplicated Dockerfile absence regex logic into a single `assert_pkg_absent(dockerfile, pkg)` helper in `conftest.py`, making it trivial to add regression tests for any removed dependency.

## When to Use

- Two or more test methods contain the same `re.search(r"apt-get install.*\bpkg\b", ...)` pattern
- Adding a new test for a removed apt/cargo/rustc dependency
- Refactoring `TestXxxAbsent` classes to reduce duplication
- Following up on a PR that introduced the first instance of the pattern (DRY follow-up issue)

## Verified Workflow

### Quick Reference

```python
# In tests/foundation/conftest.py
def assert_pkg_absent(dockerfile: Path, pkg: str) -> None:
    content = dockerfile.read_text()
    apt_match = re.search(rf"apt-get install[^\n]*\b{re.escape(pkg)}\b", content)
    assert apt_match is None, f"Found {pkg!r} in apt-get install in {dockerfile.name}: {apt_match.group()!r}"
    install_match = re.search(rf"\b{re.escape(pkg)}\s+install\b", content)
    assert install_match is None, f"Found '{pkg} install' in {dockerfile.name}: {install_match.group()!r}"
```

### Step 1 — Add helper to conftest.py

Add `import re` at the top, then add the plain function (not a fixture) before the first `@pytest.fixture`:

```python
import re

def assert_pkg_absent(dockerfile: Path, pkg: str) -> None:
    """Assert that a package does not appear as an apt-get dependency or standalone install.

    Checks two patterns:
    - ``apt-get install ... <pkg>`` (package listed as an apt dependency)
    - ``<pkg> install`` (package used as its own installer, e.g. ``cargo install``)

    Args:
        dockerfile: Path to the Dockerfile to inspect.
        pkg: Package name to assert is absent (e.g. ``"cargo"``, ``"rustc"``).

    Raises:
        AssertionError: If either forbidden pattern is found, with a message
            identifying the matched line and the Dockerfile name.
    """
    content = dockerfile.read_text()

    apt_match = re.search(rf"apt-get install[^\n]*\b{re.escape(pkg)}\b", content)
    assert apt_match is None, (
        f"Found {pkg!r} in apt-get install in {dockerfile.name}: {apt_match.group()!r}"
    )

    install_match = re.search(rf"\b{re.escape(pkg)}\s+install\b", content)
    assert install_match is None, (
        f"Found '{pkg} install' in {dockerfile.name}: {install_match.group()!r}"
    )
```

### Step 2 — Refactor test class

Replace duplicated test methods with a single call:

```python
from tests.foundation.conftest import assert_pkg_absent

@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=["Dockerfile", "Dockerfile.ci"])
class TestCargoAbsent:
    """Assert cargo does not appear in apt-get install or as cargo install."""

    def test_cargo_absent(self, dockerfile: Path) -> None:
        """Assert cargo does not appear as an apt-get dependency or as 'cargo install'."""
        assert_pkg_absent(dockerfile, "cargo")
```

### Step 3 — Verify tests pass

```bash
pixi run python -m pytest tests/foundation/test_dockerfile_cargo_free.py -v
# Expected: all tests PASSED
```

### Step 4 — Reuse for other packages

When adding a regression test for a new removed dependency (e.g. `rustc`, `gcc`):

```python
def test_rustc_absent(self, dockerfile: Path) -> None:
    assert_pkg_absent(dockerfile, "rustc")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Separate helpers.py | Creating a dedicated `tests/foundation/helpers.py` file | conftest.py is already the shared utilities file for the suite; a second file adds unnecessary indirection | Put plain helper functions directly in conftest.py — no separate helpers module needed |
| pytest fixture for the helper | Making `assert_pkg_absent` a pytest fixture | Fixtures are injected by pytest; assertion helpers are plain functions and more flexible | Use plain functions for assertion helpers, fixtures for test data/setup |
| Comma-separated Closes in commit | Using `Closes #3994, #3995` in one line | Project convention requires separate `Closes #N` lines per issue | Always use separate lines per issue per feedback_pr_closes_format.md |

## Results & Parameters

- **Before**: 2 test methods per Dockerfile × 2 Dockerfiles = 4 regex checks duplicated
- **After**: 1 test method per Dockerfile, regex in one place
- **Test count**: unchanged (5 tests, same parametrization)
- **Python**: 3.14, pytest 7.4.4
- **Import path**: `from tests.foundation.conftest import assert_pkg_absent`
- **Regex patterns**:
  - apt: `rf"apt-get install[^\n]*\b{re.escape(pkg)}\b"`
  - install: `rf"\b{re.escape(pkg)}\s+install\b"`
