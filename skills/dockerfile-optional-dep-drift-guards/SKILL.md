# Skill: Dockerfile Optional-Dependency Drift Guards

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-02 |
| Project | ProjectScylla |
| Objective | Add static-analysis regression tests to detect drift between `pyproject.toml` optional-dep groups and the Dockerfile's Layer 2 comment block |
| Outcome | Success — 3 new tests added (29 total in docker suite), 3587 passed full suite |
| Issue | HomericIntelligence/ProjectScylla#1174 |
| PR | HomericIntelligence/ProjectScylla#1294 |

## When to Use

Use this skill when:
- A Dockerfile uses `tomllib` (or `tomli`) to extract dependency lists from `pyproject.toml` at build time
- The Dockerfile supports optional-dependency groups via an `ARG EXTRAS` build argument
- You need to prevent silent drift between pyproject.toml group definitions and Dockerfile documentation/usage
- Adding a new `[project.optional-dependencies]` group and wanting a guard that forces Dockerfile comment updates

## Context: The Pattern Being Tested

`docker/Dockerfile` Layer 2 uses a tomllib one-liner to install deps dynamically:

```dockerfile
ARG EXTRAS=""
COPY pyproject.toml /opt/scylla/
RUN python3 -c "import tomllib, os; \
    data = tomllib.load(open('/opt/scylla/pyproject.toml', 'rb')); \
    project = data.get('project', {}); \
    deps = list(project.get('dependencies', [])); \
    opt = project.get('optional-dependencies', {}); \
    [deps.extend(opt.get(g.strip(), [])) for g in os.environ.get('EXTRAS', '').split(',') if g.strip()]; \
    open('/tmp/deps.txt', 'w').write(' '.join(deps))" EXTRAS="$EXTRAS" \
    && pip install --user --no-cache-dir $(cat /tmp/deps.txt) \
    && rm -f /tmp/deps.txt
```

This pattern:
1. Reads core deps from `[project.dependencies]`
2. Reads optional groups from `[project.optional-dependencies]` keyed by `EXTRAS` CSV
3. Documents available groups in a comment block above the `ARG EXTRAS` line

The risk is that new groups are added to `pyproject.toml` but not documented in the comment, or old group names in the comment become stale after renames.

## Verified Workflow

### 1. Locate the Test File

The tests live alongside other Dockerfile static-analysis tests:

```
tests/unit/docker/test_dockerfile_optional_deps.py
```

### 2. Add the tomllib Import Block at the Top

```python
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found, no-redef]

PYPROJECT = Path(__file__).parents[3] / "pyproject.toml"
```

Note: `parents[3]` navigates from `tests/unit/docker/` up to the repo root. Adjust depth for your project layout.

### 3. Add the pyproject_optional_groups Fixture

```python
@pytest.fixture(scope="module")
def pyproject_optional_groups() -> list[str]:
    """Return the list of [project.optional-dependencies] group names from pyproject.toml."""
    data = tomllib.loads(PYPROJECT.read_text())
    return list(data.get("project", {}).get("optional-dependencies", {}).keys())
```

**Key**: Use `tomllib.loads(path.read_text())` (text mode) not `tomllib.load(open(..., 'rb'))` (binary mode) — both work but `loads` is simpler for tests.

### 4. Test 1 — Comma-Splitting Guard

```python
def test_layer2_handles_comma_separated_extras(dockerfile_text: str) -> None:
    """The python3 snippet must split EXTRAS on commas to support multi-group input."""
    assert "split(',')" in dockerfile_text or 'split(",")' in dockerfile_text, (
        "The python3 -c snippet in Layer 2 must call .split(',') on the EXTRAS value "
        "so that comma-separated group names (e.g. 'analysis,dev') are handled correctly."
    )
```

### 5. Test 2 — All pyproject Groups Documented in Dockerfile

```python
def test_dockerfile_documents_all_optional_dep_groups(
    dockerfile_text: str,
    pyproject_optional_groups: list[str],
) -> None:
    """Every optional-dep group defined in pyproject.toml must appear in the Dockerfile comment."""
    missing = [g for g in pyproject_optional_groups if g not in dockerfile_text]
    assert not missing, (
        f"The following optional-dependency groups from pyproject.toml are not documented "
        f"in docker/Dockerfile: {missing}. Add them to the Layer 2 comment block."
    )
```

**Key**: This is a simple substring check — group names appear in the comment block (`#   analysis  — matplotlib, numpy...`), so `if g not in dockerfile_text` catches omissions.

### 6. Test 3 — No Stale Group Names in Dockerfile Comment

```python
def test_dockerfile_comment_groups_exist_in_pyproject(
    dockerfile_text: str,
    pyproject_optional_groups: list[str],
) -> None:
    """Every group name in the Dockerfile Layer 2 comment must exist in pyproject.toml."""
    # Extract group names from lines of the form: "#   <name>  —" or "#   <name>  -"
    comment_groups = re.findall(r"#\s{3,}(\w+)\s+[—-]", dockerfile_text)
    stale = [g for g in comment_groups if g not in pyproject_optional_groups]
    assert not stale, (
        f"The following group names appear in the Dockerfile Layer 2 comment but are not "
        f"defined in pyproject.toml [project.optional-dependencies]: {stale}. "
        f"Update the comment or pyproject.toml to keep them in sync."
    )
```

**Key regex**: `r"#\s{3,}(\w+)\s+[—-]"` matches comment lines where a group name is followed by an em-dash (—) or hyphen (-). Adjust the regex to match your actual Dockerfile comment format.

## Comment Format That the Regex Matches

The Dockerfile comment block must use this format for the regex to work:

```dockerfile
#   analysis  — matplotlib, numpy, pandas, scipy, seaborn, altair, vl-convert-python, krippendorff
#   dev       — pytest, pytest-cov, pre-commit, ruff, defusedxml
```

Pattern: `#` + 3+ spaces + `word` + spaces + em-dash or hyphen.

If your comment uses a different separator (e.g., `:`), update the character class `[—-]` accordingly.

## Failed Attempts

### 1. Binary Mode tomllib.load() in Tests

**Problem**: Using `tomllib.load(open(PYPROJECT, 'rb'))` directly in the fixture body works but makes it harder to close the file handle cleanly. The linter (ruff) may flag unclosed file handles.

**Fix**: Use `tomllib.loads(PYPROJECT.read_text())` — reads the text content first, then parses. Always closes the file.

### 2. Running Only the Docker Test Subset Shows 0% Coverage

**Problem**: Running `pixi run python -m pytest tests/unit/docker/ -v` reports:
```
FAIL Required test coverage of 9% not reached. Total coverage: 0.00%
```

**Why**: The Docker tests are pure static-analysis — they parse text files without importing any `scylla/` modules. The `addopts` coverage threshold applies globally. This is expected and NOT a bug.

**Fix**: Use `--override-ini="addopts="` to skip coverage when running only docker tests in development. The full CI suite (`tests/`) provides real coverage.

### 3. Regex Matching Too Broadly

**Problem**: An initial regex `r"#\s+(\w+)"` matched too many things — Python keywords, section headers, etc. — producing false positives for `stale` groups.

**Fix**: Anchor with `\s{3,}` (3+ spaces minimum) and require the trailing em-dash/hyphen: `r"#\s{3,}(\w+)\s+[—-]"`. This is specific to the comment format used in ProjectScylla's Dockerfile.

## Results & Parameters

### Test counts added
- `test_layer2_handles_comma_separated_extras` — 1 test
- `test_dockerfile_documents_all_optional_dep_groups` — 1 test (parametric via fixture)
- `test_dockerfile_comment_groups_exist_in_pyproject` — 1 test (parametric via fixture)
- **Total: 3 new tests (29 total in docker suite)**

### Full suite result
```
3587 passed, 1 skipped, 48 warnings
Coverage: 67.46% (threshold: 9%)
```

### pyproject.toml groups at time of writing
```
analysis  — matplotlib, numpy, pandas, scipy, seaborn, altair, vl-convert-python, krippendorff
dev       — pytest, pytest-cov, pre-commit, ruff, defusedxml
```

### When a new group is added to pyproject.toml
`test_dockerfile_documents_all_optional_dep_groups` will **fail** with:
```
AssertionError: The following optional-dependency groups from pyproject.toml are not documented
in docker/Dockerfile: ['new-group']. Add them to the Layer 2 comment block.
```

This is the intended behavior — it forces the developer to update the comment.
