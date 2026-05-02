---
name: config-env-double-underscore-nesting
description: "Fix ambiguous env var to config key mapping by using __ as nesting delimiter. Use when: (1) env var names collide with underscore-containing config keys, (2) implementing env var config override with nested keys."
category: architecture
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [config, environment-variables, nesting, convention]
---

# Config Env Double Underscore Nesting

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Fix ambiguous `_` → `.` mapping in `merge_with_env()` so config keys with underscores can be set via env vars |
| **Outcome** | Success — `__` adopted as nesting delimiter, single `_` preserved as literal |
| **Verification** | verified-local |
| **Issue** | HomericIntelligence/ProjectHephaestus#29 |
| **PR** | HomericIntelligence/ProjectHephaestus#67 |

## When to Use

- An env var config override function uses `_` as both a nesting delimiter and a literal character, creating ambiguity
- Config keys containing underscores (e.g., `database.max_connections`) cannot be set via environment variables
- Implementing a new env var → config key mapping and need a convention for nesting

## Verified Workflow

### Quick Reference

```python
# Double underscore (__) = nesting delimiter
# Single underscore (_) = literal underscore in key segment
config_key = key[len(prefix):].lower()
segments = config_key.split("__")
# HEPHAESTUS_DATABASE__MAX_CONNECTIONS → database.max_connections
# HEPHAESTUS_LOG_LEVEL → log_level
```

### Detailed Steps

1. Replace `.replace("_", ".")` with `.split("__")` on the stripped, lowercased env var name
2. Each segment from the split becomes a nesting level; single underscores within segments are preserved
3. Update docstrings with the new convention and examples showing `__` for nesting
4. Update existing tests that relied on single `_` for nesting (e.g., `HEPHAESTUS_DATABASE_HOST` → `HEPHAESTUS_DATABASE__HOST`)
5. Add edge case tests: single underscore preserved, mixed nesting+underscore, deep nesting, triple underscore (`___` splits as `__` + `_`)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Original impl | `replace("_", ".")` — single underscore as nesting delimiter | Cannot represent config keys with underscores (e.g., `max_connections` becomes `max.connections`) | Need distinct characters for nesting vs. literal underscore |
| Configurable separator param | Considered adding a `separator` kwarg to `merge_with_env` | YAGNI — `__` convention is well-established (Django, Flask) and sufficient | Don't add parameters for hypothetical flexibility when a convention solves the problem |

## Results & Parameters

```python
# Before (ambiguous):
config_key = key[len(prefix):].lower().replace("_", ".")
# HEPHAESTUS_DATABASE_MAX_CONNECTIONS → database.max.connections (WRONG)

# After (unambiguous):
raw_key = key[len(prefix):].lower()
segments = raw_key.split("__")
# HEPHAESTUS_DATABASE__MAX_CONNECTIONS → database.max_connections (CORRECT)
# HEPHAESTUS_LOG_LEVEL → log_level (CORRECT)
# HEPHAESTUS_A__B__C → a.b.c (CORRECT)
# HEPHAESTUS_A___B → a._b (edge case, CORRECT)
```

**Convention reference**: Django uses `__` for nesting in `django-environ`, Flask-based projects use similar patterns.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #29 — merge_with_env ambiguity fix | All 389 unit tests pass locally |
