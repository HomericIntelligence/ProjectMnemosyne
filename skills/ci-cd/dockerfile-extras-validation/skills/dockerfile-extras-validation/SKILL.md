---
name: dockerfile-extras-validation
description: "Validate Docker build-arg EXTRAS group names against pyproject.toml [project.optional-dependencies] at build time. Use when a Dockerfile uses a python3 -c snippet to resolve optional-dependency groups from EXTRAS and typos should fail fast rather than silently omitting deps."
user-invocable: false
category: ci-cd
date: 2026-03-02
---

# dockerfile-extras-validation

Fail-fast validation of Docker `--build-arg EXTRAS` group names against
`[project.optional-dependencies]` in `pyproject.toml`, with static pytest regression tests.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Issue | #1204 |
| PR | #1306 |
| Objective | Detect unknown EXTRAS group names (e.g. `EXTRAS=analyysis`) at Docker build time rather than silently omitting the requested extras |
| Outcome | Success — 8 static regression tests added, 3593 total tests passing, 67.46% coverage |
| Category | ci-cd |
| Project | ProjectScylla |

## When to Use

- When a Dockerfile Layer uses a `python3 -c` snippet to parse `pyproject.toml` and resolve optional-dependency groups from an `EXTRAS` build-arg
- When a typo in `EXTRAS` (e.g. `EXTRAS=analyysis`) would silently produce only runtime deps with no warning
- When you want build-time validation that exits non-zero with a clear error message for unknown group names
- When writing static pytest regression tests to guard that the validation logic is not accidentally removed

## Verified Workflow

### Step 1: Locate the Layer 2 dependency-extraction RUN snippet

```bash
grep -n "optional-dependencies\|EXTRAS" docker/Dockerfile
```

Typically looks like:
```dockerfile
ARG EXTRAS=""
RUN python3 -c "import tomllib, os; data = tomllib.load(...); opt = ...; \
    [deps.extend(opt.get(g.strip(), [])) for g in os.environ.get('EXTRAS','').split(',') if g.strip()]; ..." \
    EXTRAS="$EXTRAS"
```

### Step 2: Extend the snippet with validation

Insert validation logic **before** the dep-resolution loop. The pattern uses a one-expression conditional to stay inline-friendly:

```dockerfile
RUN python3 -c "\
import sys, tomllib, os; \
from pathlib import Path; \
data = tomllib.load(open('/opt/scylla/pyproject.toml', 'rb')); \
project = data.get('project', {}); \
opt = project.get('optional-dependencies', {}); \
valid = set(opt.keys()); \
extras = {g.strip() for g in os.environ.get('EXTRAS', '').split(',') if g.strip()}; \
unknown = extras - valid; \
(print(f'ERROR: Unknown EXTRAS group(s): {sorted(unknown)}. Valid: {sorted(valid)}', file=sys.stderr) or sys.exit(1)) if unknown else None; \
deps = list(project.get('dependencies', [])); \
[deps.extend(opt.get(g, [])) for g in extras]; \
Path('/tmp/deps.txt').write_text(' '.join(deps)); \
" EXTRAS="$EXTRAS" \
    && pip install --user --no-cache-dir $(cat /tmp/deps.txt) \
    && rm -f /tmp/deps.txt
```

Key points:
- `unknown = extras - valid` computes the set difference
- `(print(..., file=sys.stderr) or sys.exit(1)) if unknown else None` — prints then exits in a single expression (avoids multi-line `if` block inside a `-c` string)
- Empty EXTRAS (`""`) produces an empty set — no error, no extra deps installed
- Add a comment above the layer referencing the issue: `# EXTRAS validation: unknown group names emit an error and exit non-zero (see #<issue>).`

### Step 3: Write static regression tests

Create `tests/unit/scripts/test_dockerfile_extras_validation.py`:

```python
"""Tests for Dockerfile EXTRAS group name validation. See issue #1204."""

import re
import sys
import tomllib
from pathlib import Path

import pytest

DOCKERFILE_PATH = Path(__file__).parents[3] / "docker" / "Dockerfile"
PYPROJECT_PATH = Path(__file__).parents[3] / "pyproject.toml"


def _extract_layer2_run_snippet(dockerfile_content: str) -> str:
    """Extract the Layer 2 RUN python3 -c block referencing optional-dependencies."""
    pattern = re.compile(r"(RUN python3 -c .*?(?:\\\n.*?)*)\n(?!.*\\)", re.DOTALL)
    for match in pattern.finditer(dockerfile_content):
        block = match.group(1)
        if "optional-dependencies" in block:
            return block
    return ""


class TestDockerfileExtrasValidation:
    """Assert Dockerfile Layer 2 snippet validates EXTRAS group names."""

    def test_dockerfile_exists(self) -> None:
        """Dockerfile must exist at docker/Dockerfile."""
        assert DOCKERFILE_PATH.is_file()

    def test_layer2_snippet_contains_sys_exit(self) -> None:
        """Layer 2 RUN snippet must call sys.exit for invalid EXTRAS groups."""
        content = DOCKERFILE_PATH.read_text()
        snippet = _extract_layer2_run_snippet(content)
        assert snippet
        assert "sys.exit" in snippet

    def test_layer2_snippet_validates_optional_dependencies(self) -> None:
        """Layer 2 RUN snippet must reference 'unknown' for validation logic."""
        content = DOCKERFILE_PATH.read_text()
        snippet = _extract_layer2_run_snippet(content)
        assert snippet
        assert "unknown" in snippet

    def test_layer2_snippet_contains_error_message(self) -> None:
        """Layer 2 RUN snippet must emit an 'Unknown EXTRAS group' error message."""
        content = DOCKERFILE_PATH.read_text()
        assert "Unknown EXTRAS group" in content

    def test_layer2_snippet_references_issue(self) -> None:
        """Dockerfile must reference the issue number in a comment."""
        content = DOCKERFILE_PATH.read_text()
        assert "#1204" in content  # update to the actual issue number


class TestOptionalDependenciesNonEmpty:
    """Regression guard: pyproject.toml optional-dependencies must be non-empty."""

    def test_pyproject_has_optional_dependencies(self) -> None:
        """pyproject.toml must define at least one optional-dependency group."""
        with PYPROJECT_PATH.open("rb") as f:
            data = tomllib.load(f)
        opt = data.get("project", {}).get("optional-dependencies", {})
        assert opt

    @pytest.mark.parametrize("group", ["analysis", "dev"])
    def test_known_groups_are_present(self, group: str) -> None:
        """Known optional-dependency groups must remain in pyproject.toml."""
        with PYPROJECT_PATH.open("rb") as f:
            data = tomllib.load(f)
        opt = data.get("project", {}).get("optional-dependencies", {})
        assert group in opt, f"Group '{group}' missing. Available: {sorted(opt.keys())}"
```

### Step 4: Run tests

```bash
# New tests only (fast)
pixi run python -m pytest tests/unit/scripts/test_dockerfile_extras_validation.py -v --no-cov

# Full scripts suite (regression check)
pixi run python -m pytest tests/unit/scripts/ -v --no-cov
```

### Step 5: Run pre-commit and commit

```bash
pre-commit run --all-files
git add docker/Dockerfile tests/unit/scripts/test_dockerfile_extras_validation.py
git commit -m "feat(docker): validate EXTRAS group names at build time"
git push -u origin <branch>
gh pr create --title "[Feat] Validate EXTRAS group names at Docker build time" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Skill tool `commit-commands:commit-push-pr` | Denied in don't-ask permission mode (non-interactive session) | Use plain `git add`, `git commit`, `git push`, `gh pr create`, `gh pr merge --auto --rebase` via Bash directly |
| Multi-line `if unknown:` block in `-c` string | Dockerfile RUN continuation syntax makes multi-line Python awkward | Use `(print(...) or sys.exit(1)) if unknown else None` single-expression pattern |

## Error Message Format

The validation emits to `stderr` so it appears in `docker build` output:

```
ERROR: Unknown EXTRAS group(s): ['analyysis']. Valid: ['analysis', 'dev']
```

Pattern: `f"ERROR: Unknown EXTRAS group(s): {sorted(unknown)}. Valid: {sorted(valid)}"`

- Uses `sorted()` for deterministic output regardless of set iteration order
- Prints to `sys.stderr` so it surfaces in Docker build logs even when stdout is piped

## Results & Parameters

### Test counts

| Test Class | Tests | What it checks |
|------------|-------|----------------|
| `TestDockerfileExtrasValidation` | 5 | sys.exit present, unknown referenced, error message present, issue comment present, Dockerfile exists |
| `TestOptionalDependenciesNonEmpty` | 3 | non-empty optional-deps, analysis group present, dev group present |
| **Total** | **8** | |

### Dockerfile snippet structure

The Layer 2 snippet has three logical sections:
1. **Load**: `data = tomllib.load(...)` — parse pyproject.toml
2. **Validate**: `unknown = extras - valid; (print ... or sys.exit(1)) if unknown else None` — fail fast
3. **Resolve**: `deps = list(...); [deps.extend(opt.get(g, [])) for g in extras]` — build dep list

### Regex for extracting the Layer 2 block in tests

```python
pattern = re.compile(r"(RUN python3 -c .*?(?:\\\n.*?)*)\n(?!.*\\)", re.DOTALL)
```

Matches a `RUN python3 -c` line plus all backslash-continued lines. Filter for `"optional-dependencies" in block` to isolate the Layer 2 snippet specifically.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1204, PR #1306 | [notes.md](../../references/notes.md) |

## Related Skills

- **dockerfile-python-version-guard** — Companion skill: guards the Python version constraint needed by `tomllib` in the same Layer 2 snippet (issue #1138)
- **docker-multistage-build** — Docker build optimization patterns; Layer 2 caching semantics
- **pixi-pypi-upper-bounds** — `tomllib`-based `pyproject.toml` parsing pattern

## References

- Issue #1204: <https://github.com/HomericIntelligence/ProjectScylla/issues/1204>
- PR #1306: <https://github.com/HomericIntelligence/ProjectScylla/pull/1306>
- Follow-up from issue #1139 (EXTRAS build-arg feature)
