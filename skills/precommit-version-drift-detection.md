---
name: precommit-version-drift-detection
description: 'Automate detection of version drift between .pre-commit-config.yaml
  revs and pixi.toml package versions using a validation script and local hook. Use
  when: auditing external hooks for drift, or enforcing version consistency automatically
  at commit time.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | precommit-version-drift-detection |
| **Category** | ci-cd |
| **Complexity** | Medium |
| **Time** | ~30 minutes (script + tests + hook registration) |
| **Risk** | Low — adds enforcement, no behavior change to existing hooks |

Implements automated enforcement to catch version drift between `.pre-commit-config.yaml`
`rev:` fields and the corresponding `pixi.toml` lower-bound versions. The key artifacts are:

1. A `check_precommit_versions.py` script that compares hook revs against pixi constraints
2. A local pre-commit hook that runs the script on changes to either config file
3. pixi.toml entries for tracked packages (as the single source of truth)

This complements the manual `pre-commit-version-alignment` skill by making drift
impossible to accidentally commit.

## When to Use

- After fixing a version drift manually and wanting to prevent recurrence
- Auditing all external hooks in `.pre-commit-config.yaml` for potential drift
- Implementing the "automation" follow-up from a version alignment issue
- Any project where multiple external hook repos have pixi/conda counterparts

## Verified Workflow

### Quick Reference

```bash
# Run the check manually
pixi run python scripts/check_precommit_versions.py

# Run all tests
pixi run python -m pytest tests/scripts/test_check_precommit_versions.py -v
```

### Step 1 — Audit which external repos have pixi counterparts

For each external repo in `.pre-commit-config.yaml`, check if the package exists on conda-forge:

```bash
pixi search <package-name>
```

**Critical decision**: only include repos where conda-forge versions are comparable to the
pre-commit `rev:`. JS tools (like `markdownlint-cli2`) publish on npm with different version
series than conda-forge — exclude them to avoid false positives.

### Step 2 — Add pixi.toml entries for tracked packages

For each tracked external hook, add a constraint matching the pre-commit rev:

```toml
# pixi.toml [dependencies]
nbstripout = ">=0.7.1"            # tracked to keep in sync with .pre-commit-config.yaml
pre-commit-hooks = ">=4.5.0,<4.6"  # pinned to match .pre-commit-config.yaml rev
```

Verify the constraints are satisfiable:

```bash
pixi install  # must succeed — will fail immediately if no matching conda-forge package
```

### Step 3 — Write the validation script

The script needs to:

1. Parse `.pre-commit-config.yaml` for external repo URLs and `rev:` values
2. Parse `pixi.toml` for package versions (use `tomllib` with fallback for Python <3.11)
3. Map repo URL → pixi package name via a static dict
4. Normalize versions (strip leading `v` from git tags)
5. Report `DRIFT` (version mismatch) or `MISSING` (package not in pixi.toml)

```python
# HOOK_TO_PIXI_MAP — only include repos with comparable conda-forge versioning
HOOK_TO_PIXI_MAP: Dict[str, str] = {
    "https://github.com/pre-commit/mirrors-mypy": "mypy",
    "https://github.com/kynan/nbstripout": "nbstripout",
    "https://github.com/pre-commit/pre-commit-hooks": "pre-commit-hooks",
    # markdownlint-cli2 excluded: conda-forge version series differs from npm
}
```

**tomllib fallback pattern** (needed since `tomllib` is Python 3.11+ only):

```python
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        return _parse_pixi_dependencies_fallback(pixi_path)  # manual parser
```

The fallback manual parser scans lines, stops at the next `[section]` header:

```python
def _parse_pixi_dependencies_fallback(pixi_path: Path) -> Dict[str, str]:
    in_deps = False
    for line in pixi_path.read_text().splitlines():
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True; continue
        if stripped.startswith("[") and stripped != "[dependencies]":
            in_deps = False; continue
        if in_deps and "=" in stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            ...
```

### Step 4 — Register a local pre-commit hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-precommit-versions
      name: Check Pre-commit Version Consistency
      description: Ensure .pre-commit-config.yaml revs match pixi.toml versions
      entry: python scripts/check_precommit_versions.py
      language: system
      files: ^(\.pre-commit-config\.yaml|pixi\.toml)$
      pass_filenames: false
```

The `files:` pattern ensures the hook only runs when either config file is staged, making it
fast in normal development.

### Step 5 — Write tests

Test coverage should include:

- `normalize_version()` — strips leading `v`, handles bare versions
- `parse_pixi_constraint()` — parses `>=X.Y.Z,<N`, `==X.Y.Z`, bare versions
- `extract_external_hooks()` — skips `local` repos and repos without `rev:`
- `_parse_pixi_dependencies_fallback()` — stops at next `[section]`, skips comments
- `check_version_drift()` — `DRIFT`, `MISSING`, unmapped repos ignored, all-consistent
- `check_version_consistency()` — integration tests with temp files
- `main()` — exit codes 0/1, output messages

```bash
pixi run python -m pytest tests/scripts/test_check_precommit_versions.py -v
# 52 tests, all pass
```

### Step 6 — Verify end-to-end

```bash
# Script reports OK on current repo state
pixi run python scripts/check_precommit_versions.py
# → OK: all pre-commit hook versions are consistent with pixi.toml

# Hook triggers only on relevant file changes (fast)
git add .pre-commit-config.yaml && pixi run pre-commit run check-precommit-versions
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Include `markdownlint-cli2` in `HOOK_TO_PIXI_MAP` | Added it to the map with `>=0.12.1,<0.13` in pixi.toml | conda-forge only has `markdownlint-cli2 >=0.13`; the npm package `v0.12.1` is a different versioning series | JS tools published on npm and conda-forge use incomparable version numbers — exclude them from drift tracking |
| Add `markdownlint-cli2 = ">=0.12.1,<0.13"` to pixi.toml | Tried to install it | `pixi install` failed immediately with "No candidates" — conda-forge has no 0.12.x build | Always verify conda-forge availability with `pixi search <pkg>` before adding constraints |
| Require exact version match for all packages | Used `version_tuple(hook) == version_tuple(pixi)` where pixi is lower bound | For `>=0.7.1` (no upper bound), the lower bound is `0.7.1` and hook rev is also `0.7.1` — they match exactly by accident | The exact-match approach works when pixi lower bound equals the hook rev; consider range checking for future robustness |

## Results & Parameters

### Files Created/Modified

```text
scripts/check_precommit_versions.py          # new — 332 lines, full validation logic
tests/scripts/test_check_precommit_versions.py  # new — 494 lines, 52 tests
.pre-commit-config.yaml                      # +11 lines — local hook registration
pixi.toml                                    # +2 lines — nbstripout, pre-commit-hooks
```

### pixi.toml Constraints (copy-paste)

```toml
nbstripout = ">=0.7.1"            # tracked to keep in sync with .pre-commit-config.yaml
pre-commit-hooks = ">=4.5.0,<4.6"  # pinned to match .pre-commit-config.yaml rev
```

### Script Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| `0` | All tracked hooks consistent with pixi.toml |
| `1` | Drift detected, missing entry, or file not found |

### HOOK_TO_PIXI_MAP — Which Repos to Track

| Repo URL | Pixi Package | Include? | Reason |
|----------|-------------|---------|--------|
| `mirrors-mypy` | `mypy` | ✅ Yes | Pure Python, same versioning |
| `nbstripout` | `nbstripout` | ✅ Yes | Pure Python, same versioning |
| `pre-commit-hooks` | `pre-commit-hooks` | ✅ Yes | Pure Python, same versioning |
| `markdownlint-cli2` | `markdownlint-cli2` | ❌ No | JS/npm; conda-forge version series differs |
