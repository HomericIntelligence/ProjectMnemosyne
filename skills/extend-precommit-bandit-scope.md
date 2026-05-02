---
name: extend-precommit-bandit-scope
description: 'Extend bandit pre-commit hook file scope to additional directories.
  Use when: adding new Python-containing dirs, broadening security scanning coverage
  in .pre-commit-config.yaml.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Goal** | Extend bandit pre-commit hook to cover additional Python directories |
| **Trigger** | New dirs added to project, or existing dirs not covered by bandit hook |
| **Outcome** | All Python files scanned for security issues before commit |
| **Risk** | Existing violations in newly-scanned dirs will break CI until addressed |

## When to Use

- A project adds `tools/`, `examples/`, or other directories containing Python files
- A pre-commit bandit hook only covers a subset of directories (e.g., `scripts/` and `tests/`)
- Security scanning needs to be extended without changing the hook's severity thresholds

## Verified Workflow

1. **Identify current scope** — read `files:` regex in the bandit hook entry in `.pre-commit-config.yaml`

2. **Pre-scan new directories** before extending scope:
   ```bash
   python -m bandit -ll --skip <existing_skips> -r new_dir1/ new_dir2/
   ```
   This reveals violations that would break CI once the hook covers those dirs.

3. **Triage findings**:
   - If findings are true positives → fix the code with `# nosec B<id>` or code changes
   - If findings are expected/acceptable patterns → add the rule ID to `--skip`
   - Document rationale in a comment above the hook (e.g., "B301: pickle used for trusted dataset files")

4. **Edit `.pre-commit-config.yaml`** — update two fields in the bandit hook:
   ```yaml
   entry: pixi run bandit -ll --skip B310,B202,B301   # add new skip IDs if needed
   files: ^(scripts|tests|tools|examples)/.*\.py$      # extend regex
   ```

5. **Verify** the updated skip list passes on all directories:
   ```bash
   python -m bandit -ll --skip B310,B202,B301 -r scripts/ tests/ tools/ examples/
   ```
   Expect zero medium/high issues.

6. **Commit and PR** — pre-commit hooks skip on YAML-only changes (no Python files staged),
   so the bandit hook itself won't run on the config change commit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Extend scope without pre-scanning | Extended `files:` pattern directly and committed | B301 (pickle) violations in `examples/` would have broken CI | Always pre-scan new directories before extending hook scope |
| Adding `# nosec` to all pickle calls | Considered adding `# nosec B301` to every `pickle.load()` call | More invasive than needed; 5 identical files would each need annotation | Prefer adding to `--skip` when the pattern is project-wide and intentional |

## Results & Parameters

### Bandit hook config (after extension)

```yaml
- id: bandit
  name: Bandit Security Scan
  description: Scan Python files for security vulnerabilities using bandit
  entry: pixi run bandit -ll --skip B310,B202,B301
  language: system
  files: ^(scripts|tests|tools|examples)/.*\.py$
  types: [python]
  pass_filenames: true
```

### Skip ID reference

| ID | Rule | When to skip |
| ---- | ------ | ------------- |
| B310 | `urllib` urlopen | Controlled/hardcoded URLs only |
| B202 | `tarfile` extraction | Download scripts with known-safe archives |
| B301 | `pickle.load` | Loading trusted local dataset files (e.g., CIFAR-10) |

### Key flags

- `-ll` = medium severity and above (Low issues ignored)
- `--skip` = comma-separated rule IDs to suppress
- `pass_filenames: true` = bandit receives individual file paths from pre-commit
