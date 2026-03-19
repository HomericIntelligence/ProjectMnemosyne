---
name: bare-mojo-call-lint-guard
description: 'Add a pre-commit hook and CI step to prevent bare ''pixi run mojo test/run''
  calls in workflow YAMLs without retry wrappers. Use when: (1) bare mojo calls were
  patched with retry but no guardrail prevents regression, (2) enforcing retry discipline
  in GitHub Actions workflow lint.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# bare-mojo-call-lint-guard

Implement a dual-layer guardrail (pre-commit hook + CI lint step) that prevents
new GitHub Actions workflow files from introducing bare `pixi run mojo test|run`
calls without retry wrappers. Per-line suppression via comment annotation
lets existing legitimate calls (inside retry loops) pass without changes to logic.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-15 |
| Mojo Version | 0.26.1 |
| Objective | Prevent regression of bare pixi run mojo calls after retry was applied |
| Outcome | Success — pre-commit hook + CI step + 23 tests |
| Repository | ProjectOdyssey |
| Issue | #3956 (follow-up to #3329) |
| PR | #4840 |

## When to Use

- You just patched all existing bare `pixi run mojo` calls with retry logic
  (e.g., after #3329) and want to prevent future regression
- A CI lint step needs to enforce that workflow YAMLs never introduce new
  unprotected `pixi run mojo test|run` calls
- You want a suppressible lint rule (not a hard ban) so existing retry-wrapped
  calls can be annotated rather than restructured

## Verified Workflow

### Quick Reference

| File | What it does |
|------|-------------|
| `scripts/check_bare_mojo_calls.py` | Grep-based detector script |
| `.pre-commit-config.yaml` | `no-bare-pixi-mojo-calls` hook |
| `.github/workflows/validate-workflows.yml` | CI lint step |
| Existing workflow violations | Add `# no-bare-mojo-lint: inside retry loop` |

### Step 1 — Write the detector script

Create `scripts/check_bare_mojo_calls.py`:

```python
import re, sys
from pathlib import Path
from typing import List, Tuple

BARE_PATTERN = re.compile(r"pixi run mojo\s+(test|run)\b")
SUPPRESSION = "# no-bare-mojo-lint"

def check_file(path: Path) -> List[Tuple[int, str]]:
    violations = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if SUPPRESSION in line:
            continue
        if BARE_PATTERN.search(line):
            violations.append((lineno, line.rstrip()))
    return violations

def main(argv):
    files = [Path(f) for f in argv] if argv else []
    all_violations = []
    for f in files:
        if not f.exists():
            continue
        for lineno, line in check_file(f):
            all_violations.append((f, lineno, line))
    if all_violations:
        for path, lineno, line in all_violations:
            print(f"{path}:{lineno}: bare pixi run mojo call — wrap with just test-group or add retry, "
                  f"or suppress with '# no-bare-mojo-lint: <reason>'")
            print(f"  {line}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Key design decisions:
- Pattern matches `mojo test` and `mojo run` only — not `--version`, `build`, `package`, `format`
- Suppression is per-line via comment annotation, not per-file
- Non-existent files are silently skipped (safe for pre-commit pass_filenames mode)

### Step 2 — Suppress existing legitimate calls

All existing bare calls are already inside retry loops (from #3329). Annotate them:

```yaml
if pixi run mojo test -I . "$paper_dir/tests" --verbose; then  # no-bare-mojo-lint: inside retry loop
```

Do this for every file that already has retry wrappers — do NOT restructure the logic.

Verify zero violations after annotating:

```bash
python3 scripts/check_bare_mojo_calls.py .github/workflows/*.yml
# Should print nothing and exit 0
```

Watch out: the CI echo line itself can trigger the pattern if it contains the literal string
`pixi run mojo test|run`. Rephrase echo messages to avoid matching:

```yaml
# WRONG — triggers the linter:
echo "Checking for bare 'pixi run mojo test|run' calls..."

# CORRECT:
echo "Checking workflow files for bare pixi run mojo calls..."
```

### Step 3 — Add pre-commit hook

In `.pre-commit-config.yaml`, add a new `repo: local` block:

```yaml
- repo: local
  hooks:
    - id: no-bare-pixi-mojo-calls
      name: No bare pixi run mojo test/run calls
      description: >
        Prevent bare 'pixi run mojo test|run' in workflow YAMLs without retry
        wrapper or just test-group routing. Ref #3956. Suppress with
        '# no-bare-mojo-lint: <reason>' on the same line.
      entry: python3 scripts/check_bare_mojo_calls.py
      language: system
      files: ^\.github/workflows/.*\.ya?ml$
      pass_filenames: true
```

Place it near other workflow lint hooks for discoverability.

### Step 4 — Add CI lint step

In `.github/workflows/validate-workflows.yml`, add a new step after the existing
checkout-order check:

```yaml
- name: Check for bare pixi run mojo calls
  run: |
    echo "Checking workflow files for bare pixi run mojo calls without retry (ref #3956)..."
    python3 scripts/check_bare_mojo_calls.py .github/workflows/*.yml
```

Also expand the `paths:` trigger to include `scripts/check_bare_mojo_calls.py` so the
CI job re-runs when the script itself changes.

### Step 5 — Write unit tests

Create `tests/scripts/test_check_bare_mojo_calls.py` with three test classes:

1. `TestBarePattern` — verify pattern and suppression constants
2. `TestCheckFile` — positive cases (mojo test, mojo run), negative cases
   (--version, build, package, format, hyphenated mojo-format), suppression,
   line number accuracy, multiple violations
3. `TestMain` — exit codes, output format, multiple files, all-suppressed case

Run with:

```bash
pixi run python -m pytest tests/scripts/test_check_bare_mojo_calls.py -v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Context-aware retry detection | Detect retry loop context by scanning surrounding lines | Too complex and fragile; `while [ $attempt -lt 3 ]` above `pixi run mojo` is inconsistently formatted | Per-line suppression comments are simpler and self-documenting |
| Broad pattern `pixi run mojo [^-]` | Match any pixi run mojo call not starting with `-` | Would flag `pixi run mojo build`, `mojo package`, etc. which are fine without retry | Scope pattern to `test` and `run` subcommands only |
| Echo message containing literal pattern | CI step's echo included `'pixi run mojo test\|run'` | The linter matched its own echo line, causing false positive | Rephrase echo messages to avoid containing the exact pattern string |
| Pygrep hook | Use pre-commit `language: pygrep` to match the pattern | `pygrep` has no suppression mechanism; can't skip annotated lines | Use `language: system` with a Python script that handles suppression |

## Results & Parameters

### Pattern configuration

```python
# Matches mojo test and mojo run — nothing else
BARE_PATTERN = re.compile(r"pixi run mojo\s+(test|run)\b")

# Per-line suppression comment
SUPPRESSION = "# no-bare-mojo-lint"
```

### Suppression annotation format

```yaml
# Template:
<command>  # no-bare-mojo-lint: <reason>

# Examples used in practice:
if pixi run mojo test -I . tests/ --verbose; then  # no-bare-mojo-lint: inside retry loop
pixi run mojo test tests/smoke/ || echo "failed"  # no-bare-mojo-lint: smoke test; failure is non-fatal (|| echo)
if pixi run mojo run -I . bench.mojo | tee out.txt; then  # no-bare-mojo-lint: inside retry loop
```

### Test count

23 unit tests covering: positive detection, negative detection (6 non-flagged patterns),
suppression, line number accuracy, multiple violations, exit codes, output format.
