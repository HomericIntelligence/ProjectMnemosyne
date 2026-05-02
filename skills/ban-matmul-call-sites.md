---
name: ban-matmul-call-sites
description: 'Add a system-language pre-commit hook and belt-and-suspenders CI step
  to ban dunder method call sites (e.g. .__matmul__()) in Mojo files while excluding
  function definition lines. Use when: (1) codebase has been standardized on a free-function
  form and you need to prevent dunder-call-site regression, (2) pygrep cannot express
  the exclusion you need, (3) you need both pre-commit and CI enforcement.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Ban Dunder Call Sites via Pre-commit Hook and CI Step

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-03-07 |
| **Objective** | Prevent `.__matmul__(` call sites from being reintroduced after codebase was standardized on `matmul(A, B)` |
| **Outcome** | Hook + CI step implemented, zero violations on current codebase, all pre-commit hooks passed |
| **PR** | HomericIntelligence/ProjectOdyssey#3733 |
| **Closes** | HomericIntelligence/ProjectOdyssey#3215 |

## When to Use

Invoke when:

- A codebase has been migrated from dunder call sites (`a.__matmul__(b)`) to a free-function form (`matmul(a, b)`) and you need to lock in the change
- The banned pattern requires an **exclusion** (e.g., exclude `fn __matmul__(` definition lines) — `pygrep` cannot do this
- You want both local pre-commit enforcement **and** a redundant CI step
- The project targets Mojo `.mojo` files (same pattern works for Python with minor tweaks)

## Verified Workflow

### Step 1 — Choose `language: system` over `language: pygrep`

`pygrep` matches the `entry` pattern against file contents but cannot **exclude** lines. When the banned
pattern appears on both call sites (`a.__matmul__(b)`) and definition lines (`fn __matmul__(`),
use `language: system` with a `bash -c` entry so you can pipe through `grep -v` exclusions.

### Step 2 — Add the hook to `.pre-commit-config.yaml`

Place it in the same `local` repo block as related Mojo lint hooks:

```yaml
- id: no-matmul-call-sites
  name: Enforce no .__matmul__() call sites
  description: Ban .__matmul__( call sites in Mojo files (use matmul(A, B) instead). Ref #3215
  entry: bash -c 'violations=$(grep -rn "\.__matmul__(" . --include="*.mojo" --exclude-dir=".pixi" --exclude-dir=".git" | grep -v "fn __matmul__(" | grep -v "# __matmul__" | grep -v "__matmul__.*deprecated"); if [ -n "$violations" ]; then echo "Found .__matmul__() call sites (use matmul(A, B) instead):"; echo "$violations"; exit 1; fi'
  language: system
  pass_filenames: false
  always_run: true
```

Key fields:

- `language: system` — runs entry as a shell command, no script file needed
- `pass_filenames: false` — the hook greps the whole repo itself
- `always_run: true` — runs even when no `.mojo` files are staged (important for a repository-wide guard)
- `grep -v` chain — excludes definition lines, comments, and deprecation notes

### Step 3 — Add a belt-and-suspenders CI step

In the pre-commit workflow (`.github/workflows/pre-commit.yml`), add a dedicated step with a GitHub
Actions error annotation:

```yaml
- name: Enforce no .__matmul__() call sites
  run: |
    violations=$(grep -rn "\.__matmul__(" . --include="*.mojo" --exclude-dir=".pixi" --exclude-dir=".git" | grep -v "fn __matmul__(" | grep -v "# __matmul__" | grep -v "__matmul__.*deprecated")
    if [ -n "$violations" ]; then
      echo "::error::Found .__matmul__() call site(s). Use matmul(A, B) instead."
      echo "$violations"
      exit 1
    fi
    echo "No .__matmul__() call sites found."
```

The `::error::` prefix produces a GitHub Actions annotation visible in the PR diff view.

### Step 4 — Verify baseline is clean before enabling enforcement

```bash
violations=$(grep -rn "\.__matmul__(" . --include="*.mojo" --exclude-dir=".pixi" --exclude-dir=".git" \
  | grep -v "fn __matmul__(" | grep -v "# __matmul__" | grep -v "__matmul__.*deprecated")
if [ -n "$violations" ]; then echo "VIOLATIONS: $violations"; else echo "Clean baseline"; fi
```

Zero violations is required before committing the hook, or the hook will fail immediately.

### Step 5 — Test exclusion logic with synthetic files

```bash
# Should catch: real call site
echo "result = a.__matmul__(b)" > /tmp/test_call.mojo
grep -n "\.__matmul__(" /tmp/test_call.mojo | grep -v "fn __matmul__("
# expected: 1:result = a.__matmul__(b)

# Should exclude: function definition
echo "fn __matmul__(self, rhs: Self) -> Self:" > /tmp/test_def.mojo
grep -n "\.__matmul__(" /tmp/test_def.mojo | grep -v "fn __matmul__("
# expected: (empty)

rm /tmp/test_call.mojo /tmp/test_def.mojo
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `language: pygrep` | Pattern `\.__matmul__\(` with `negate: false` | Cannot exclude lines matching `fn __matmul__(` — would false-positive on definition lines | Use `language: system` when exclusions are needed |
| Separate script file | Considered writing a Python script for the hook | Unnecessary complexity for a single-pattern grep-based guard | `bash -c` inline entry keeps it zero-dependency |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| Hook language | `system` |
| Entry style | `bash -c '...'` inline (no script file) |
| `pass_filenames` | `false` (hook greps entire repo) |
| `always_run` | `true` |
| Baseline violations | 0 (verified before enabling) |
| CI annotation | `::error::` prefix for GitHub PR diff view |
| Exclusion filters | `grep -v "fn __matmul__("` · `grep -v "# __matmul__"` · `grep -v "__matmul__.*deprecated"` |

## Key Takeaways

1. **`pygrep` cannot exclude lines** — use `language: system` with `grep -v` when you need exclusions.
2. **`always_run: true`** ensures the guard fires even when no `.mojo` files are staged (repo-wide grep).
3. **Verify baseline is clean first** — enabling enforcement on a codebase with existing violations will immediately block all commits.
4. **Belt-and-suspenders CI step** catches violations if the pre-commit hook is bypassed or missing locally.
5. **`::error::` annotation** surfaces the violation clearly in the GitHub PR diff view.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3215, PR #3733 | [notes.md](../references/notes.md) |
