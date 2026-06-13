---
name: github-api-label-parsing-splitlines-not-split
description: "Use .splitlines() not .split() when parsing gh api label output in Python.
  Use when: (1) calling `gh api .../labels --jq '.[].name'` and splitting the output
  into a Python list, (2) any `gh api` call whose newline-delimited output is processed
  with `.split()`, (3) a label-reconciliation function checks `if name.startswith('prefix:')`
  and needs to avoid tokenizing multi-word labels like `good first issue`."
category: tooling
date: 2026-06-13
version: 1.0.0
user-invocable: false
verification: verified-ci
tags:
  - gh-api
  - labels
  - splitlines
  - split
  - whitespace
  - label-parsing
  - ruff-e741
  - github-labels
  - python
---
# Skill: github-api-label-parsing-splitlines-not-split

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-06-13 |
| Project | ProjectHephaestus |
| Objective | Parse `gh api .../labels --jq '.[].name'` output into a Python list without tokenizing multi-word label names |
| Outcome | Fixed latent bug in `hephaestus/github/severity_label.py`; 293 unit tests pass; CI green |
| PR | HomericIntelligence/ProjectHephaestus#1298 |
| Verification | verified-ci (commit `13ff0bbf`, branch `1210-auto-impl`) |

## When to Use

Use this skill when:
- Calling `gh api repos/{owner}/{repo}/issues/{n}/labels --jq '.[].name'` and splitting the result into a Python list
- Any `gh api` endpoint that returns newline-delimited strings and the Python caller uses `.split()` to tokenize
- A label-reconciliation function filters labels with `if name.startswith("prefix:")` — multi-word labels with spaces will be silently mis-tokenized by `.split()`
- You see a loop variable named `l` (lowercase L) in a list comprehension — ruff E741 flags this as ambiguous

**Trigger symptom (latent, no immediate error):**

```python
# This looks harmless — no crash today
current = _gh("api", f"repos/{repo}/issues/{n}/labels", "--jq", ".[].name").split()
```

If the issue has a label like `good first issue`, `.split()` produces `["good", "first", "issue"]` — three tokens, none matching `severity:`. The reconciler silently skips the delete that should have fired.

## Verified Workflow

Replace every `.split()` on `gh api` label output with `.splitlines()` + blank-line filter:

```python
current = [
    name
    for name in _gh(
        "api",
        f"repos/{repo}/issues/{n}/labels",
        "--jq",
        ".[].name",
    ).splitlines()
    if name
]
```

**Why `.splitlines()` works:**
- `gh api --jq '.[].name'` emits one label name per line. `.splitlines()` splits only on line boundaries — a label like `good first issue` stays as one element.
- The trailing newline that `gh` often appends produces an empty string; `if name` filters it out.

**Why `.split()` is wrong:**
- `.split()` with no arguments splits on ALL whitespace (spaces, tabs, newlines). A label `good first issue` becomes `["good", "first", "issue"]` — three tokens instead of one.

**Also: avoid single-letter loop variables in list comprehensions:**

```python
# BAD — ruff E741 flags `l` as ambiguous (looks like 1 or I)
current = [l for l in lines if l]

# GOOD
current = [name for name in lines if name]
```

### Quick Reference

```
gh api endpoint → one label per line → trailing newline possible
.split()      → tokenizes on ALL whitespace → WRONG for multi-word labels
.splitlines() → splits on line boundaries → correct
if name       → filters blank lines from trailing newline
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | `.split()` on `gh api --jq '.[].name'` output | Tokenizes on ALL whitespace; a label like `good first issue` becomes `["good", "first", "issue"]` — three tokens instead of one | Use `.splitlines()` which splits only on line boundaries |
| 2 | Loop variable `l` in list comprehension | Ruff E741 flags `l` as ambiguous (looks like `1` or `I`) | Use descriptive names: `name`, `label`, `line` |

## Results & Parameters

### gh api label endpoint summary

| Parameter | Value |
| ----------- | ------- |
| Endpoint | `/repos/{owner}/{repo}/issues/{n}/labels` |
| JQ filter | `.[].name` |
| Output format | One label name per line, possible trailing newline |
| Correct Python split | `.splitlines()` + `if name` filter |
| Wrong Python split | `.split()` (splits on all whitespace) |

### When the `.split()` bug is harmless vs. dangerous

| Scenario | Safe? | Why |
| --------- | ------- | ----- |
| All labels are single-word (`severity:high`, `bug`) | Apparently safe (latent) | No spaces to mis-tokenize — but if a multi-word label is added later, the bug activates silently |
| Any label contains a space (`good first issue`, `help wanted`) | Broken | Multi-word label is split into separate tokens; prefix-filter misses the correct label; reconciler deletes or adds incorrectly |

### File changed in ProjectHephaestus

`hephaestus/github/severity_label.py` — `apply_severity_label()` function, line fetching current labels.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #1298 — severity label auto-triage (issue #1210) | 293 unit tests pass locally and in CI; commit `13ff0bbf` |
