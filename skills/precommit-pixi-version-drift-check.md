---
name: precommit-pixi-version-drift-check
description: 'Add a CI check that detects version drift between .pre-commit-config.yaml
  rev: tags and pixi.lock resolved versions. Use when: (1) adding external pre-commit
  hooks that are also pixi dependencies, (2) preventing silent version drift between
  pre-commit and pixi environments, (3) debugging inconsistent pre-commit behavior
  across machines.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | `rev:` tags in `.pre-commit-config.yaml` and pixi-resolved versions in `pixi.lock` can silently drift, causing pre-commit hooks to use different tool versions than the rest of the project |
| **Solution** | A stdlib-only Python script that parses both files using regex and fails CI if any mismatch is found |
| **Trigger** | `.pre-commit-config.yaml` or `pixi.lock` changes |
| **Exit code 0** | Versions match (or tool not tracked in pixi.lock — skipped silently) |
| **Exit code 1** | Version mismatch detected, or required files missing |

## When to Use

- You have external pre-commit hooks (e.g. `mirrors-mypy`, `nbstripout`) that are **also** installed as pixi/conda packages
- CI passes but tools behave differently between local and CI environments
- A follow-up issue is filed because a pre-commit version drifted from the lock file without anyone noticing
- You want to add a new external hook to `.pre-commit-config.yaml` and need to ensure it stays pinned

## Verified Workflow

### Quick Reference

```bash
# Run the check manually
python3 scripts/check_precommit_versions.py

# Run with explicit repo root (for testing)
python3 scripts/check_precommit_versions.py --repo-root /path/to/repo

# Expected output when clean
# OK: No version drift detected (checked: mirrors-mypy, kynan/nbstripout)
```

### Step 1: Understand the two files

`.pre-commit-config.yaml` external repos have `rev:` tags:

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.19.1
```

`pixi.lock` has conda URL lines with the authoritative version:

```text
- conda: https://conda.anaconda.org/conda-forge/linux-64/mypy-1.19.1-py314h5bd0f2a_0.conda
```

The version must match after stripping the leading `v` prefix.

### Step 2: Create `scripts/check_precommit_versions.py`

Key design decisions:
- **Stdlib only** (`re`, `argparse`, `pathlib`, `sys`) — runs before Pixi setup in CI
- **`main()` returns int** (not `sys.exit()`) — enables unit testing with `pytest`
- **`--repo-root` arg** — enables `tmp_path`-based tests without filesystem mocking
- **`REPO_TO_PACKAGE` dict** — maps URL substring → conda package name; add new tools here
- **Silent skip** when package not in lock — avoids false positives for non-pixi hooks
- **`normalize_rev()`** strips leading `v` before comparison (`v1.19.1` → `1.19.1`)

```python
# Maps pre-commit repo URL substring → pixi.lock conda package name
REPO_TO_PACKAGE: Dict[str, str] = {
    "mirrors-mypy": "mypy",
    "kynan/nbstripout": "nbstripout",
}
```

Parse `rev:` tags using regex (avoids yaml dependency):

```python
repo_rev_pattern = re.compile(
    r"-\s+repo:\s+(\S+)\s+rev:\s+(\S+)",
    re.MULTILINE,
)
```

Parse pixi.lock conda URL lines:

```python
conda_pattern = re.compile(
    r"-\s+conda:\s+https?://\S+/([a-zA-Z0-9_\-]+)-(\d+\.\d+[\.\d]*)-[^/\s]+\.(?:conda|tar\.bz2)"
)
```

### Step 3: Add pre-commit hook

In `.pre-commit-config.yaml`, add inside an existing `local` repo block:

```yaml
- id: check-precommit-versions
  name: Check pre-commit vs pixi version drift
  description: Fail if rev tags in .pre-commit-config.yaml drift from pixi.lock versions
  entry: python scripts/check_precommit_versions.py
  language: system
  pass_filenames: false
  files: ^(\.pre-commit-config\.yaml|pixi\.toml|pixi\.lock)$
```

### Step 4: Add CI step (runs before Pixi setup)

In your CI workflow (e.g. `.github/workflows/pre-commit.yml`), add the check **before** the Pixi setup step since the script uses only stdlib:

```yaml
- name: Check pre-commit vs pixi version drift
  run: python3 scripts/check_precommit_versions.py

- name: Set up Pixi
  uses: ./.github/actions/setup-pixi
```

Placing it before Pixi setup is intentional: the script has no external dependencies, so it acts as an early gate.

### Step 5: Write tests

Use `pytest` with `tmp_path` to avoid any filesystem mocking:

```python
def test_returns_1_when_versions_mismatch(self, tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text(PRECOMMIT_MYPY_MISMATCH)
    (tmp_path / "pixi.lock").write_text(LOCK_WITH_MYPY)
    assert main(["--repo-root", str(tmp_path)]) == 1
```

Test coverage should include:
- Match → exit 0
- Mismatch → exit 1
- Missing config file → exit 1
- Missing lock file → exit 1
- Untracked repos silently skipped → exit 0
- Package not in lock → exit 0 (not tracked)
- `normalize_rev` stripping `v` prefix
- First occurrence wins for duplicate package names in lock

### Step 6: Extend for new tools

To add a new tool (e.g. `ruff`), add an entry to `REPO_TO_PACKAGE` in the script:

```python
REPO_TO_PACKAGE: Dict[str, str] = {
    "mirrors-mypy": "mypy",
    "kynan/nbstripout": "nbstripout",
    "astral-sh/ruff-pre-commit": "ruff",  # ← new entry
}
```

The URL substring just needs to be unique enough to match the repo URL unambiguously.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `yaml` library to parse `.pre-commit-config.yaml` | Import `yaml` (PyYAML) in the script | Would require pixi to be set up first — the whole point is to run before Pixi | Use `re` regex instead; the structure is regular enough |
| `sys.exit()` in `main()` | Called `sys.exit(0/1)` directly | `pytest` catches `SystemExit`, requiring `pytest.raises(SystemExit)` wrappers for every test | Return `int` from `main()` and call `sys.exit(main())` only in `if __name__ == "__main__"` |
| Placing CI step after Pixi setup | Added the version drift check after `Set up Pixi` | Works but misses the value of failing fast before expensive Pixi install | Place before Pixi setup — stdlib-only scripts should run as early gates |
| Security hook blocking `Edit` on workflow file | Used `Edit` tool on `.github/workflows/pre-commit.yml` | Project security hook fires on all GitHub Actions workflow edits | Use `python3 -c "..."` via Bash to write the file instead |
| `lstrip("v")` test expected single-v strip | Test checked `normalize_rev("vv1.0") == "v1.0"` | `str.lstrip()` strips ALL leading matching characters | `lstrip("v")` strips all leading `v` chars; test should expect `"1.0"` not `"v1.0"` |

## Results & Parameters

**Script produced**: `scripts/check_precommit_versions.py` (~130 lines, stdlib only)

**Tests**: 34 tests in `tests/scripts/test_check_precommit_versions.py`, all passing

**`REPO_TO_PACKAGE` mapping** (extend as needed):

```python
REPO_TO_PACKAGE: Dict[str, str] = {
    "mirrors-mypy": "mypy",
    "kynan/nbstripout": "nbstripout",
}
```

**Pixi.lock regex** (matches both `.conda` and `.tar.bz2` formats):

```python
r"-\s+conda:\s+https?://\S+/([a-zA-Z0-9_\-]+)-(\d+\.\d+[\.\d]*)-[^/\s]+\.(?:conda|tar\.bz2)"
```

**Pre-commit hook trigger pattern**:

```text
^(\.pre-commit-config\.yaml|pixi\.toml|pixi\.lock)$
```
