---
name: ci-gitleaks-toml-allowlist-slice-vs-map
description: "Fix gitleaks config crash: 'Rules[0].AllowList expected a map, got slice'. Use when: (1) gitleaks fails with this error on startup, (2) .gitleaks.toml uses [[rules.allowlist]] (TOML array-of-tables syntax), (3) upgrading gitleaks from v7 to v8 and config suddenly breaks."
category: ci-cd
date: 2026-04-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [gitleaks, toml, allowlist, config, secrets-scan, pre-commit]
---

# Gitleaks TOML Allowlist: Slice vs Map Config Error

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-28 |
| **Objective** | Fix gitleaks crash when loading `.gitleaks.toml` with `[[rules.allowlist]]` section |
| **Outcome** | Successful — changed `[[rules.allowlist]]` (array-of-tables) to `[allowlist]` (top-level map) |
| **Verification** | verified-local |

## When to Use

- gitleaks fails with: `Failed to load config error="1 error(s) decoding:\n\n* 'Rules[0].AllowList' expected a map, got 'slice'"`
- `.gitleaks.toml` uses `[[rules.allowlist]]` double-bracket syntax
- Upgrading gitleaks from v7 to v8 and config suddenly breaks
- pre-commit gitleaks hook crashes at startup (not a secret detection failure)

## Verified Workflow

### Quick Reference

```toml
# WRONG — [[double brackets]] = TOML array-of-tables = slice
[[rules.allowlist]]
description = "Test fixtures"
regexes = ["fake-api-key"]

# CORRECT — [single brackets] at top level = map
[allowlist]
description = "Test fixtures"
regexes = ["fake-api-key"]
paths = ["tests/.*"]
```

### Detailed Steps

1. Open `.gitleaks.toml`
2. Find `[[rules.allowlist]]` — the double bracket is TOML array-of-tables syntax, which produces a slice (list of maps), but gitleaks v8 expects a single map
3. Replace `[[rules.allowlist]]` with `[allowlist]` (top-level, single brackets)
4. Remove any blank lines or separator comments between allowlist entries — with the map syntax there is only one `[allowlist]` block; all regexes and paths are within it
5. Validate: `gitleaks detect --source . --no-git -v` — should load config and scan without crashing

**Full working example**:

```toml
title = "Myrmidons gitleaks configuration"

[extend]
useDefault = true

[allowlist]
description = "Test fixtures and documentation examples"
regexes = [
  '''your-token-here''',
  '''fake-api-key''',
  '''test-token''',
]
paths = [
  '''tests/.*''',
  '''README\.md''',
  '''CLAUDE\.md''',
]
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `[[rules.allowlist]]` double-bracket syntax | TOML array-of-tables — produces a slice/list | gitleaks v8.24.3 AllowList field expects a map, not a slice; error: `'Rules[0].AllowList' expected a map, got 'slice'` | Use `[allowlist]` (top-level map) not `[[rules.allowlist]]` (nested array-of-tables) |
| Multiple `[[rules.allowlist]]` blocks | Adding a second `[[rules.allowlist]]` for different path patterns | Same error — still produces a slice even with one block | There is exactly one `[allowlist]` block; all patterns go inside it |

## Results & Parameters

**Error message** (exact — use to identify this bug):
```
Failed to load config error="1 error(s) decoding:

* 'Rules[0].AllowList' expected a map, got 'slice'"
```

**TOML semantics**:
- `[[table]]` — TOML array of tables; each occurrence appends to a slice → produces `[]AllowList`
- `[table]` — TOML table (map); exactly one occurrence → produces `AllowList{}` (what gitleaks expects)

**gitleaks version**: v8.24.3 (confirmed broken with `[[rules.allowlist]]`; `[allowlist]` works)

**Validate locally**:
```bash
gitleaks detect --source . --no-git -v
# Should print: "X leaks found" or "No leaks detected" — NOT a config decode error
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Myrmidons | fix/ci-precommit-parity PR — gitleaks pre-commit hook crashing on config load | 2026-04-28 |
