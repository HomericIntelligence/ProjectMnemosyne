---
name: cli-json-report-format-implementation
description: "Implement JSON output format for CLI report commands using dataclasses.asdict() with NaN/Inf sanitization. Use when: (1) adding JSON output to a CLI that already has a dataclass-based report model, (2) serializing dataclasses containing IEEE 754 special floats to JSON."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
supersedes: []
tags: [json, cli, dataclasses, serialization, nan-sanitization, click]
---

# CLI JSON Report Format Implementation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add `--format json` to a Click CLI report command that already has a dataclass-based `ReportData` model and a working Markdown generator |
| **Outcome** | Successful — JSON report generator created, CLI wired, HTML stub removed, 20 new tests, PR merged |
| **Verification** | verified-local — all 46 targeted tests pass, pre-commit clean, CI pending |

## When to Use

- Adding a JSON output format to a CLI command that already has structured dataclass models
- Serializing Python dataclasses to JSON when fields may contain `float("inf")`, `float("-inf")`, or `float("nan")`
- Removing unimplemented CLI format stubs to avoid misleading `sys.exit(1)` on valid-looking options
- Following the "parallel generator class" pattern for multi-format report output

## Verified Workflow

### Quick Reference

```python
# 1. Sanitize special floats before json.dumps
import math
from dataclasses import asdict
from typing import Any

def _sanitize_for_json(obj: Any) -> Any:
    if isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(item) for item in obj]
    return obj

# 2. Generate JSON from dataclass
raw = asdict(report_data)
sanitized = _sanitize_for_json(raw)
json_str = json.dumps(sanitized, indent=2)

# 3. Wire into Click CLI (local import pattern)
elif output_format == "json":
    from module.json_report import JsonReportGenerator
    generator = JsonReportGenerator(report_dir)
    path = generator.write_report(data)
```

### Detailed Steps

1. **Create a parallel generator class** following the existing generator pattern (same `__init__(base_dir)`, same `write_report(data) -> Path` signature, same `get_report_dir(test_id)` helper)
2. **Add `_sanitize_for_json()` helper** — recursively walks `dataclasses.asdict()` output, replaces `float("inf")`, `float("-inf")`, `float("nan")` with `None`. Standard `json.dumps` raises `ValueError` on these values
3. **Wire into CLI dispatch** — add `elif output_format == "json":` branch with a local import (follows existing CLI pattern of importing inside branches)
4. **Remove unimplemented formats** from `click.Choice` — if a format raises `sys.exit(1)` with "not yet implemented", remove it from the choices so Click rejects it cleanly
5. **Update `__init__.py` exports** — add to imports and `__all__` (keep `__all__` sorted for ruff RUF022)
6. **Write tests** — sanitization helper tests (normal values, inf, -inf, nan, nested), generator tests (basic, with tiers, with sensitivity, with transitions, write to file, parametrized special floats), CLI integration tests (json with mock data, html rejection)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding comments to `__all__` | Added section comments (`# JSON`, `# Markdown`, etc.) between entries in `__all__` | ruff RUF022 requires isort-style sorting which doesn't support interleaved comments | Keep `__all__` as a flat sorted list without comments when RUF022 is enabled |
| N/A — direct approach worked | First implementation attempt succeeded | N/A | When the dataclass model is already structured for serialization, `dataclasses.asdict()` + sanitization is minimal work |

## Results & Parameters

**Key pattern**: `dataclasses.asdict()` + recursive sanitize + `json.dumps(indent=2)`

**NaN/Inf sanitization is required because**:
- `json.dumps(float("inf"))` raises `ValueError: Out of range float values are not JSON compliant`
- `json.dumps(float("nan"))` produces `NaN` which is not valid JSON per RFC 7159
- Using `json.dumps(allow_nan=True)` produces JavaScript-compatible but not JSON-standard output

**Test coverage**: 18 unit tests for the generator (100% module coverage) + 2 CLI integration tests

**Files created**:
- `scylla/reporting/json_report.py` — `JsonReportGenerator` class + `_sanitize_for_json` helper
- `tests/unit/reporting/test_json_report.py` — 18 tests

**Files modified**:
- `scylla/cli/main.py` — removed `"html"` from `click.Choice`, added `elif output_format == "json":` branch
- `scylla/reporting/__init__.py` — added `JsonReportGenerator` to imports and `__all__`
- `tests/unit/cli/test_cli.py` — added 2 new tests

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1510 — CLI report JSON format | PR #1553, all tests pass locally |
