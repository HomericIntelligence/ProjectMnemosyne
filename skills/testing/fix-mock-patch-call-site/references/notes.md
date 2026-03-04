# References: Fix Mock Patch Call-Site Targets

## Session Context

- **Project**: ProjectScylla
- **Issue**: #1124 — Fix remaining mock patch call-site issues in test suite
- **PR**: #1344
- **Branch**: `1124-auto-impl`
- **Date**: 2026-03-03

## Raw Audit Findings

### Files With Wrong Patch Targets (before fix)

```
tests/unit/adapters/test_claude_code.py:336:  patch("subprocess.run", ...)
tests/unit/adapters/test_claude_code.py:370:  patch("subprocess.run", ...) as mock_run
tests/unit/adapters/test_claude_code.py:404:  patch("subprocess.run", side_effect=timeout_error)
tests/unit/adapters/test_claude_code.py:427:  patch("subprocess.run", side_effect=FileNotFoundError())
tests/unit/adapters/test_claude_code.py:451:  patch("subprocess.run", ...)
tests/unit/adapters/test_claude_code.py:478:  patch("subprocess.run", ...)
# Same pattern ×6 for test_cline.py, test_goose.py, test_openai_codex.py, test_opencode.py
```

### Verified Source Locations of `subprocess.run` Call

```python
# scylla/adapters/base_cli.py:10,88
import subprocess
...
result = subprocess.run(  # call-site for cline, goose, openai_codex, opencode

# scylla/adapters/claude_code.py:10,90
import subprocess
...
result = subprocess.run(  # call-site for claude_code
```

### Patterns NOT Fixed (confirmed correct)

- `time.sleep` patches: 16 instances, all `patch("time.sleep", ...)` — correct, no change
- `export_data.mann_whitney_power` / `export_data.kruskal_wallis_power` in `tests/unit/analysis/conftest.py` — correct call-site patches for sys.path-inserted modules

## Test Run Results

```
# Adapter tests only
160 passed, 1 warning in 0.25s

# Full unit suite
3696 passed, 1 skipped, 48 warnings in 102.70s

# Pre-push hook (full suite with coverage)
3799 passed, 1 skipped — coverage 67.96% > 9% threshold
```
