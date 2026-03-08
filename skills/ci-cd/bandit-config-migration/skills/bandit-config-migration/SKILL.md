---
name: bandit-config-migration
description: "Move bandit skip flags from pre-commit hook CLI args to a .bandit INI config file so suppressions are visible when running bandit directly. Use when: bandit --skip flags live in .pre-commit-config.yaml making them invisible to developers, or pyproject.toml [tool.bandit] is desired but bandit doesn't natively read it."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

# Bandit Config Migration (CLI Flags → .bandit INI File)

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Objective** | Move bandit B310/B202 skip flags from pre-commit `--skip` CLI arg to a `.bandit` config file |
| **Outcome** | `.bandit` INI at repo root, `pixi run bandit` works for developers, pre-commit hook uses `--ini .bandit` |
| **Issue** | HomericIntelligence/ProjectOdyssey#3361 |
| **PR** | HomericIntelligence/ProjectOdyssey#4017 |

## When to Use

Invoke when:

- Bandit skip list is embedded in `.pre-commit-config.yaml` as `--skip B310,B202` CLI flags
- Developers running `bandit` directly get false positives that CI suppresses (skip rationale invisible)
- You want a `pixi run bandit` task that respects project-level suppressions without flags
- Skip rationale needs documentation with inline comments (impossible in CLI flags)
- Follow-up to adding a bandit pre-commit hook (see `bandit-precommit-security-scanner` skill)

## Verified Workflow

### Step 1 — Verify bandit version supports .bandit INI (not pyproject.toml)

```bash
bandit --version
# bandit 1.9.x does NOT natively read pyproject.toml [tool.bandit]
# It reads .bandit INI files via configparser with a [bandit] section
```

Key insight: Despite `[tool.bandit]` being a common expectation, bandit 1.9.x reads
suppressions only from `.bandit` INI files (via `--ini`) or via CLI flags.

### Step 2 — Create .bandit INI file at repo root

```ini
[bandit]
targets = scripts
recursive = true
skips = B310,B202
# B310: urllib.request.urlopen — all URLs are internal, non-user-supplied constants
#       (e.g., GHCR registry URLs in release scripts). No untrusted input reaches urlopen.
# B202: tarfile.extractall — archives are CI-produced artifacts from trusted pipelines,
#       not user-uploaded content. Path traversal risk does not apply here.
```

Key fields:
- `targets`: Comma-separated directories to scan (must also pass `-r` or set `recursive = true`)
- `recursive = true`: Required — bandit doesn't recurse without this even with targets set
- `skips`: Comma-separated test IDs to suppress
- Comments with `#` document rationale inline

### Step 3 — Update pre-commit hook to use --ini .bandit

Replace `--skip B310,B202` with `--ini .bandit`:

```yaml
# Before
entry: pixi run bandit -ll --skip B310,B202

# After
entry: pixi run bandit -ll --ini .bandit
```

Update the description too:

```yaml
- id: bandit
  name: Bandit Security Scan
  description: Scan Python files for security vulnerabilities using bandit (suppressions in .bandit)
  entry: pixi run bandit -ll --ini .bandit
  language: system
  files: ^(scripts|tests)/.*\.py$
  types: [python]
  pass_filenames: true
```

### Step 4 — Add pixi task for developers

```toml
[tasks]
bandit = "bandit --ini .bandit"
```

This lets developers run `pixi run bandit` and get the same suppressions as CI/pre-commit.

### Step 5 — Verify skips are applied

```bash
bandit --ini .bandit --verbose 2>&1 | grep "cli exclude"
# Expected: [main]  INFO  cli exclude tests: B310,B202
```

Verify no B310/B202 issues remain:

```bash
bandit --ini .bandit 2>&1 | grep -E "B310|B202"
# Expected: no output
```

### Step 6 — Verify pre-commit hook passes

```bash
pixi run pre-commit run --all-files bandit
# Expected: Bandit Security Scan.....Passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `[tool.bandit]` in pyproject.toml | Added `[tool.bandit]` with `targets` and `skips` arrays | Bandit 1.9.x does not read `pyproject.toml`; it only reads `.bandit` INI files via `--ini` or auto-discovery within target dirs | Always verify with `bandit --version` and check source — `[tool.bandit]` is a community expectation, not reality for 1.9.x |
| `pixi run bandit -r scripts/` as task | Set pixi task to `bandit -r scripts/` then tried `pixi run bandit -ll -r scripts/` | Pixi tasks append extra args after the task command, causing `bandit -r scripts/ -ll -r scripts/` which bandit rejects as duplicate args | Pixi task args are appended, not replaced — keep pixi tasks minimal (`bandit --ini .bandit`) with no positional args |
| `bandit --ini .bandit` without `recursive = true` | Set targets in `.bandit` but no recursive flag | Bandit skipped the directory with warning "Skipping directory (scripts), use -r flag to scan contents" | The `.bandit` INI `recursive = true` is required; `targets` alone doesn't enable recursion |
| Auto-discovery of .bandit at repo root | Expected bandit to find `.bandit` automatically when scanning `scripts/` | Bandit only searches for `.bandit` files *within* the passed target directories, not at repo root | For repo-root `.bandit`, always pass `--ini .bandit` explicitly in both pre-commit hook and pixi task |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Bandit version | 1.9.4 |
| Config file format | INI (configparser), `[bandit]` section |
| `pyproject.toml [tool.bandit]` support | Not supported in 1.9.x |
| Auto-discovery scope | Only within passed target directories (not repo root) |
| Pre-commit entry | `pixi run bandit -ll --ini .bandit` |
| Pixi task | `bandit --ini .bandit` |
| Skipped tests | `B310,B202` |
| Medium/High issues after migration | 0 |
| Pre-commit result | Passed |

## Key Takeaways

1. **bandit 1.9.x ignores `[tool.bandit]` in pyproject.toml** — use `.bandit` INI with `[bandit]`
   section and pass `--ini .bandit` explicitly.

2. **`recursive = true` is required in `.bandit`** — `targets = scripts` alone causes bandit to
   skip the directory without recursing into it.

3. **Pixi tasks append extra args** — keep pixi task definitions minimal (no positional targets)
   to avoid duplication when users pass extra args.

4. **`.bandit` at repo root is not auto-discovered** — it's only found when inside a passed
   target directory. Always use `--ini .bandit` explicitly.

5. **Inline comments in `.bandit` document skip rationale** — this is the key developer
   experience win: devs can read *why* B310/B202 are skipped directly in the config file.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3361, PR #4017 | [notes.md](../references/notes.md) |
