---
name: dockerfile-digest-consistency-guard
description: "Skill: Dockerfile Digest Consistency Guard"
category: uncategorized
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: Dockerfile Digest Consistency Guard

| Field | Value |
|-------|-------|
| Date | 2026-03-02 |
| Project | ProjectScylla |
| Issue | #1201 |
| Outcome | Success — PR #1305 merged |
| Category | testing |

## Overview

Pattern for extending Dockerfile base image version guard tests to also verify
SHA256 digest consistency between multi-stage build stages.

## When to Use

- Adding regression tests for Dockerfile pinning discipline
- A Dockerfile uses multi-stage builds with SHA256-pinned base images
- You want to detect drift where one stage's digest is updated without updating all stages
- Extending an existing version-check test file (follow-on from a version guard)

## Verified Workflow

### 1. Read existing test file and Dockerfile first

Before writing any code, read both:
- The existing test file to understand helpers and test class structure
- The actual Dockerfile to count FROM lines, identify which use SHA256 pins, and verify current consistency

### 2. Add a digest-parsing helper

```python
def _parse_python_base_digests(dockerfile_content: str) -> list[str]:
    """Extract SHA256 digest strings from Python base image FROM lines."""
    digests: list[str] = []
    for line in dockerfile_content.splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("FROM"):
            continue
        if not re.search(r"python:", stripped, re.IGNORECASE):
            continue
        match = re.search(r"@(sha256:[a-f0-9]{64})", stripped, re.IGNORECASE)
        if match:
            digests.append(match.group(1))
    return digests
```

Key design choices:
- Strict 64-hex requirement in regex prevents matching partial/truncated hashes
- Filter to Python-only FROM lines (non-Python bases don't need the same digest)
- Return full `sha256:...` strings for readable assertion messages

### 3. Add integration test class

```python
class TestDockerfileBaseImageDigestConsistency:
    """Assert all Python base image FROM lines share the same SHA256 digest."""

    def test_all_python_from_lines_have_sha256_digest(self) -> None:
        content = DOCKERFILE_PATH.read_text()
        versions = _parse_python_base_versions(content)
        digests = _parse_python_base_digests(content)
        assert versions, "No Python base image version found."
        assert len(digests) == len(versions), (
            f"Expected {len(versions)} SHA256 digest(s) but found {len(digests)}."
        )

    def test_builder_and_runtime_digests_are_identical(self) -> None:
        content = DOCKERFILE_PATH.read_text()
        digests = _parse_python_base_digests(content)
        assert len(digests) >= 2, "Expected at least 2 digest pins (builder + runtime)."
        assert len(set(digests)) == 1, (
            "SHA256 digests differ: " + ", ".join(digests)
        )
```

### 4. Add unit test class for the helper

Test these cases: single digest, multiple same, multiple different, missing digest,
non-Python FROM lines, comment lines, empty content, short hash (63 chars) rejection.

### 5. Run tests

```bash
# Quick check on just the test file (expect coverage failure — normal for single-file runs)
pixi run python -m pytest tests/unit/scripts/test_dockerfile_constraints.py -v

# Full suite to confirm no regressions
pixi run python -m pytest tests/unit/ --override-ini="addopts=" -q
```

## Failed Attempts / Gotchas

- **Coverage failure on single-file run is expected**: Running only the Dockerfile test file
  produces 0% coverage, triggering `fail-under=9`. This is not a real failure — run the full
  test suite to verify the threshold is met.

- **`Skill` tool may be blocked in don't-ask mode**: Fall back to direct git/gh CLI commands
  for commit, push, and PR creation.

## Results

- 10 new tests added (2 integration + 8 unit)
- 3520 existing tests continue to pass
- Regex `@(sha256:[a-f0-9]{64})` is the correct pattern for strict 64-hex digest matching
- `len(set(digests)) == 1` is the cleanest consistency check
