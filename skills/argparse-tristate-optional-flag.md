---
name: argparse-tristate-optional-flag
description: "Python argparse pattern for tri-state CLI flags (absent / present-with-no-arg / present-with-value) using nargs='?' + const=<sentinel>. Use when: (1) designing CLI flags like --org that need three behaviors, (2) want argparse to do parsing rather than custom post-processing."
category: tooling
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [python, argparse, cli]
---

# Argparse Tri-State Optional Flag

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-26 |
| **Objective** | Document the argparse pattern for a flag that needs three states: absent / present-with-no-arg / present-with-value |
| **Outcome** | Pattern shipped in hephaestus-automation-loop CLI; 16 unit tests verify all three branches |
| **Verification** | verified-local (PR #591 unit tests + smoke tests pass; CI still running) |

## When to Use

- Designing a CLI flag that needs three states: absent / present-with-no-arg / present-with-value
- Examples: `--org` (no flag -> cwd default; `--org` alone -> auto-detect; `--org NAME` -> explicit)
- Want argparse to do the parsing rather than custom post-processing

## Verified Workflow

### Quick Reference

```python
_SENTINEL = object()
p.add_argument("--flag", nargs="?", const=_SENTINEL, default=None)
# args.flag is None | _SENTINEL | str
```

### Detailed Steps

The pattern:

```python
_AUTODETECT_SENTINEL = object()  # module-level singleton

p.add_argument(
    "--org",
    nargs="?",                    # makes the value optional
    const=_AUTODETECT_SENTINEL,   # value used when flag is present with no arg
    default=None,                 # value used when flag is absent
    help="Pass --org NAME for explicit; --org alone to auto-detect.",
)
```

Then in main():

```python
if args.org is None:
    # flag was not passed at all -> default behavior
    ...
elif args.org is _AUTODETECT_SENTINEL:
    # flag was passed with no argument -> auto-detect
    org = detect_from_env() or error_out()
else:
    # flag was passed with a string -> explicit value
    org = args.org
```

Why a sentinel `object()` and not a string like `"AUTODETECT"`? Because a string collides with a legitimate user-supplied value (`--org AUTODETECT` would be ambiguous). `object()` produces a unique singleton that can never collide with a CLI string.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `default="AUTODETECT"` string sentinel | Use a magic string instead of object() | A user passing `--org AUTODETECT` collides with the sentinel | Use a module-level `object()` instance; identity comparison via `is` cannot collide |
| `action="store_true"` + separate `--org-name` arg | Two flags for one concept | Surprising UX (POLA violation); operator must remember which one to use | A single flag with `nargs="?"` captures both modes intuitively |
| `nargs="*"` | Allow zero-or-more values | Returns `[]` when flag has no value; also greedily consumes following positionals | `nargs="?"` is the precise tool for "0 or 1 value" |

## Results & Parameters

Tested in `hephaestus/automation/loop_runner.py` -- see PR HomericIntelligence/ProjectHephaestus#591. All three branches (no flag / `--org` / `--org NAME`) verified end-to-end via 16 unit tests in `tests/unit/automation/test_loop_runner.py` and live smoke tests.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | hephaestus-automation-loop CLI (PR #591) | --org tri-state flag for org enumeration vs cwd auto-detect vs explicit name |
