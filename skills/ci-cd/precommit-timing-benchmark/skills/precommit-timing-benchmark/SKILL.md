---
name: precommit-timing-benchmark
description: "Add pre-commit hook runtime measurement to CI to catch performance regressions. Use when: (1) regressions in hook speed are suspected, (2) a hook config change may affect performance, (3) you want to document before/after timing improvements."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Goal** | Measure pre-commit hook wall-clock runtime in CI and emit a warning annotation if it exceeds a threshold |
| **Trigger issue** | Hook config changes (e.g. `pass_filenames: true` on ruff) that should speed up partial-change commits |
| **Language** | Python helper script + GitHub Actions YAML + justfile recipe |
| **Exit policy** | Always exits 0 — timing regressions are informational, not blocking |
| **Annotation** | `::warning::` annotation when elapsed > threshold (default 120 s) |

## When to Use

- A pre-commit hook was changed and you want to document the before/after timing improvement
- You suspect a hook config change introduced a slowdown
- You want a reproducible local timing recipe (`just bench-precommit`) that mirrors CI
- You need `$GITHUB_STEP_SUMMARY` output for a timing dashboard

## Verified Workflow

### 1. Create the Python helper script (`scripts/bench_precommit.py`)

Key design decisions:

- **Always exits 0** — timing regressions should never break CI
- `check_threshold(elapsed, threshold=120)` returns `True` when `elapsed > threshold`
- `emit_warning(msg)` writes `::warning::<msg>` to stdout (GitHub Actions annotation)
- `write_step_summary(content, path)` appends Markdown to `$GITHUB_STEP_SUMMARY`
- `format_summary_table(elapsed, files, status)` returns a pipe-delimited Markdown table

```python
def check_threshold(elapsed_s: int, threshold_s: int = 120) -> bool:
    return elapsed_s > threshold_s

def emit_warning(message: str) -> None:
    print(f"::warning::{message}")
```

### 2. Write unit tests (24 tests, all passing)

Cover every public function; include a subprocess test to verify the script's exit code:

```python
def test_subprocess_exits_zero(self) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/bench_precommit.py",
         "--elapsed", "200", "--status", "passed"],
        capture_output=True,
    )
    assert result.returncode == 0
```

### 3. Add the CI workflow (`.github/workflows/precommit-benchmark.yml`)

Trigger on `.pre-commit-config.yaml` / `pyproject.toml` changes and `workflow_dispatch`.
Use `$SECONDS` bash built-in for integer-second timing:

```yaml
- name: Time pre-commit hooks
  id: time-hooks
  run: |
    START=$SECONDS
    pixi run pre-commit run --all-files --show-diff-on-failure
    HOOK_EXIT=$?
    ELAPSED=$((SECONDS - START))
    echo "elapsed=$ELAPSED" >> "$GITHUB_OUTPUT"
    if [ "$HOOK_EXIT" -eq 0 ]; then
      echo "status=passed" >> "$GITHUB_OUTPUT"
    else
      echo "status=failed" >> "$GITHUB_OUTPUT"
    fi
```

### 4. Add the justfile recipe

```just
bench-precommit:
    #!/usr/bin/env bash
    set -e
    START=$SECONDS
    pixi run pre-commit run --all-files
    ELAPSED=$((SECONDS - START))
    echo ""
    echo "Hook runtime: ${ELAPSED}s"
    python3 scripts/bench_precommit.py --elapsed "$ELAPSED" --status passed
```

### 5. Validate and commit

```bash
pixi run python -m pytest tests/scripts/test_bench_precommit.py -v   # 24 passed
git add scripts/bench_precommit.py tests/scripts/test_bench_precommit.py \
        .github/workflows/precommit-benchmark.yml justfile
git commit -m "feat(ci): add pre-commit hook performance benchmark"
gh pr create --title "feat(ci): add pre-commit hook performance benchmark" \
             --body "Closes #3353"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `date +%s` for timing | Shell `date +%s` subtraction in YAML | Fragile across platforms; requires subshell | Use `$SECONDS` bash built-in — always integer seconds, no subshell needed |
| Failing CI on slow hooks | Exit 1 from helper when threshold exceeded | Blocked legitimate CI runs on slow runners | Timing benchmarks must be non-blocking; use `::warning::` annotation instead |
| Attaching `if: failure()` to summary step | Wrote summary only on failure | Miss timing data for passing slow runs | Use `if: always()` so summary is always written |

## Results & Parameters

### Thresholds

| Parameter | Default | Override |
|-----------|---------|----------|
| `--threshold` | 120 s | `--threshold 60` |
| Warning annotation | `::warning::` | Not configurable |
| Exit code | Always 0 | Not configurable |

### Copy-paste: CI workflow trigger block

```yaml
on:
  workflow_dispatch:
  push:
    paths:
      - .pre-commit-config.yaml
      - pyproject.toml
  pull_request:
    paths:
      - .pre-commit-config.yaml
      - pyproject.toml
```

### Copy-paste: summary step

```yaml
- name: Write benchmark summary
  if: always()
  env:
    ELAPSED: ${{ steps.time-hooks.outputs.elapsed }}
    FILE_COUNT: ${{ steps.count-files.outputs.file_count }}
    HOOK_STATUS: ${{ steps.time-hooks.outputs.status }}
  run: |
    python3 scripts/bench_precommit.py \
      --elapsed "${ELAPSED:-0}" \
      --files "${FILE_COUNT:-0}" \
      --status "${HOOK_STATUS:-unknown}"
```
