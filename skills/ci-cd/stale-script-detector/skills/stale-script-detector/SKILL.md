---
name: stale-script-detector
description: "Detect scripts/*.py files not referenced in CI workflows, justfile, or other scripts. Use when: adding automated stale-script checks, following up on manual audit rounds, or wiring orphaned scripts into CI."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Goal** | Surface `scripts/*.py` files with no references in `.github/`, `justfile`, `.pre-commit-config.yaml`, or other `scripts/*.py` files |
| **Output** | `WARNING: possibly stale: scripts/<name>` lines; always exits 0 (warning, not hard failure) |
| **Trigger** | Pre-commit hook fires on `^scripts/.*\.py$` changes |
| **Test coverage** | 20 pytest unit tests across 5 test classes |

## When to Use

- After multiple manual audit rounds that removed one-time scripts and you want to automate future detection
- When adding a pre-commit hook that flags orphaned automation scripts without blocking commits
- When a `scripts/` directory has grown organically and you need a lightweight CI check for drift

## Verified Workflow

### Quick Reference

```bash
# Run the check manually
python scripts/check_stale_scripts.py

# Run via pre-commit
pre-commit run check-stale-scripts --all-files

# Run tests
pixi run python -m pytest tests/unit/scripts/test_check_stale_scripts.py -v
```

### Step 1 — Design the detection logic

The script checks each `scripts/*.py` basename against a set of reference files:

- `.github/**/*.yml` — GitHub Actions workflows
- `justfile` — Just build recipes
- `.pre-commit-config.yaml` — hook entry points
- Other `scripts/*.py` files — cross-script references

Key design decisions:

1. **Always exit 0** — warning only, never blocks commits or CI
2. **Self-reference exclusion** — a script appearing in its own source file does not count as "referenced"
3. **`ALWAYS_ACTIVE` allowlist** — `common.py` and the detector script itself are never flagged (shared library modules are not invoked directly)
4. **Basename matching** — searches for the full filename (e.g., `audit_shared_links.py`), not the module name without extension, to avoid false-positive matches on imports

### Step 2 — Implement `scripts/check_stale_scripts.py`

```python
#!/usr/bin/env python3
"""Detect scripts/*.py files with no references in .github/, justfile, or other scripts/."""

import argparse
import sys
from pathlib import Path
from typing import List, Set

ALWAYS_ACTIVE: Set[str] = {"common.py", "check_stale_scripts.py"}


def get_all_scripts(scripts_dir: Path) -> List[str]:
    return sorted(p.name for p in scripts_dir.glob("*.py") if p.is_file())


def get_reference_targets(repo_root: Path) -> List[Path]:
    targets: List[Path] = []
    github_dir = repo_root / ".github"
    if github_dir.is_dir():
        targets.extend(github_dir.rglob("*.yml"))
    justfile = repo_root / "justfile"
    if justfile.is_file():
        targets.append(justfile)
    precommit = repo_root / ".pre-commit-config.yaml"
    if precommit.is_file():
        targets.append(precommit)
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        targets.extend(scripts_dir.glob("*.py"))
    return targets


def find_references(script_name: str, targets: List[Path], scripts_dir: Path) -> bool:
    own_path = scripts_dir / script_name
    for target in targets:
        if target.resolve() == own_path.resolve():
            continue
        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if script_name in content:
            return True
    return False


def find_stale_candidates(repo_root: Path) -> List[str]:
    scripts_dir = repo_root / "scripts"
    if not scripts_dir.is_dir():
        return []
    all_scripts = get_all_scripts(scripts_dir)
    targets = get_reference_targets(repo_root)
    return [s for s in all_scripts if s not in ALWAYS_ACTIVE and not find_references(s, targets, scripts_dir)]


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root if args.repo_root else Path(__file__).resolve().parent.parent
    candidates = find_stale_candidates(repo_root)
    for c in candidates:
        print(f"WARNING: possibly stale: scripts/{c}")
    if candidates:
        print(f"\n{len(candidates)} possibly stale script(s) found (warnings only, not a failure).")
    else:
        print("No stale script candidates found.")
    return 0
```

### Step 3 — Add pre-commit hook

Add to `.pre-commit-config.yaml` inside the existing `- repo: local` block:

```yaml
- id: check-stale-scripts
  name: Check for Stale Scripts
  description: Warn about scripts/*.py not referenced in .github/, justfile, or other scripts (Issue #3969)
  entry: python3 scripts/check_stale_scripts.py
  language: system
  files: ^scripts/.*\.py$
  pass_filenames: false
```

### Step 4 — Write unit tests

Test classes and coverage:

| Class | What it covers |
|-------|---------------|
| `TestGetAllScripts` | Only `.py` files returned, sorted, empty dir |
| `TestGetReferenceTargets` | justfile, `.pre-commit-config.yaml`, `.github/` workflows, missing files excluded |
| `TestFindReferences` | Found in justfile, not found, self-reference excluded, cross-script reference |
| `TestFindStaleCandidates` | All referenced → empty, unreferenced flagged, ALWAYS_ACTIVE excluded, self-only still stale, empty/missing dir |
| `TestMain` | Returns 0 with stale, without stale, and for empty repo |

Critical test — cross-script reference must use `.py` filename, not import name:

```python
def test_cross_script_reference(self, tmp_path: Path) -> None:
    scripts_dir = _make_scripts_dir(tmp_path, ["util.py", "caller.py"])
    (scripts_dir / "caller.py").write_text(
        "import subprocess\nsubprocess.run(['python', 'scripts/util.py'])\n", encoding="utf-8"
    )
    all_targets = list(scripts_dir.glob("*.py"))
    assert find_references("util.py", all_targets, scripts_dir) is True
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Match import names without `.py` | `from util import helper` → search for `"util.py"` | Import statement uses module name, not filename | Basename matching (with `.py`) is correct; cross-script references should use the full filename in subprocess calls or comments, not bare imports |
| Hard failure (exit 1) on stale candidates | Exit non-zero to force cleanup | Too aggressive — legitimate one-time scripts used during setup would block future commits | Always exit 0 for stale detection; this is discovery tooling, not enforcement |

## Results & Parameters

**Production run on a real repo:**

```
WARNING: possibly stale: scripts/analyze_issues.py
WARNING: possibly stale: scripts/analyze_warnings.py
... (22 total candidates)

22 possibly stale script(s) found (warnings only, not a failure).
Exit code: 0
```

**ALWAYS_ACTIVE set** (never flagged):

```python
ALWAYS_ACTIVE: Set[str] = {"common.py", "check_stale_scripts.py"}
```

Add to this set any shared library modules that are imported by other scripts but not invoked directly.

**Pre-commit trigger pattern:**

```yaml
files: ^scripts/.*\.py$
pass_filenames: false
```

The `pass_filenames: false` is intentional — the script performs a whole-repo scan, not per-file validation.
