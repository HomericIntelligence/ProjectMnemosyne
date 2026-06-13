---
name: testing-notice-cross-check-value-scoping
description: "Scope NOTICE/registry value assertions to per-key lines, not full-file text. Use when: (1) writing a test that validates a value (e.g. SPDX license ID) is associated with a specific package in NOTICE, (2) any test asserting a value appears in a structured free-text file (changelogs, allowlists, SECURITY.md), (3) reviewing cross-check tests for potential false-pass conditions."
category: testing
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: ["testing", "notice", "spdx", "cross-check", "value-scoping", "false-pass", "license", "assertion-pattern"]
---

# Scope NOTICE Value Assertions to Per-Package Lines

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Prevent false-pass conditions when cross-checking SPDX values (or any values) against a human-readable file like NOTICE |
| **Outcome** | Per-package line filtering pattern documented; `test_static_values_match_notice` scoped to lines mentioning the package name |
| **Verification** | verified-ci — PR #1304 commit d9dcde04, test `test_static_values_match_notice` passes |

## When to Use

- Writing a test that validates a value (e.g. SPDX license ID) is associated with a specific package or key in NOTICE
- Any test asserting a value appears in a structured free-text file (NOTICE, CHANGELOG, allowlists, SECURITY.md) where the same value could appear on multiple different entries' lines
- Reviewing an existing cross-check test for potential false-pass conditions when two keys share the same value
- Adding staleness-mitigation tests for a static mapping (e.g. `STATIC_FALLBACK_LICENSES`) whose values are sourced from an authoritative human-readable file

## Verified Workflow

### The Bug Pattern

When validating that value `V` is associated with key `K` in a structured free-text file, `assert V in full_file_text` is **too loose**: the same value `V` can legitimately appear on a different key's line, so the assertion passes even when `K`'s entry is wrong or missing.

**Concrete example**: `tzdata`'s static license fallback is `Apache-2.0`. `packaging` also carries `Apache-2.0` and appears earlier in NOTICE. The naive check `assert "Apache-2.0" in notice_text` passes even if tzdata's NOTICE entry is changed to `MIT` or deleted — because `packaging`'s line still satisfies it.

### Quick Reference

```python
# WRONG — too loose: value from a different key satisfies the check
assert spdx_id in notice_text

# RIGHT — scope to lines mentioning the package
pkg_lines = [line for line in notice_text.splitlines() if pkg.lower() in line.lower()]
assert any(spdx_id in line for line in pkg_lines), (
    f"STATIC_FALLBACK_LICENSES[{pkg!r}] = {spdx_ids!r} but SPDX id "
    f"{spdx_id!r} not found on any NOTICE line mentioning {pkg!r} — "
    "update one to match the other."
)
```

### Detailed Steps

1. **Identify the key-value relationship**: Determine what key (e.g. package name) owns the value (e.g. SPDX ID) in the authoritative file. The assertion must check that the value appears on a line associated with *that specific key*.

2. **Extract key-relevant lines**: Split the file on newlines and filter to lines where the key appears (case-insensitive):
   ```python
   key_lines = [line for line in file_text.splitlines() if key.lower() in line.lower()]
   ```

3. **Assert key presence first**: Before asserting the value, assert that any key-relevant lines exist at all:
   ```python
   assert key_lines, f"{key!r} not found in NOTICE — add it or remove from the static map."
   ```

4. **Assert value on key lines**: Use `any(value in line for line in key_lines)` rather than `value in file_text`:
   ```python
   assert any(value in line for line in key_lines), (
       f"Value {value!r} not found on any NOTICE line mentioning {key!r}. "
       "Either update NOTICE or update the static map to match."
   )
   ```

5. **Write a clear error message**: The failure message must identify both the key and the value so the developer knows which static map entry to fix and which NOTICE line to check.

### Full test implementation

```python
def test_static_values_match_notice(self):
    """Unconditional cross-check: each fallback key + SPDX value must appear together in NOTICE.

    NOTE: We scope the value assertion to lines mentioning the package name.
    A full-file `assert spdx_id in notice_text` is too loose: the same SPDX ID
    can appear on a *different* package's NOTICE line (e.g. Apache-2.0 appears
    on both `packaging` and `tzdata`), causing a false pass if tzdata's entry
    is wrong or deleted.
    """
    notice_path = Path(__file__).parent.parent.parent / "NOTICE"
    notice_text = notice_path.read_text(encoding="utf-8")
    for pkg, spdx_ids in STATIC_FALLBACK_LICENSES.items():
        pkg_lines = [line for line in notice_text.splitlines() if pkg.lower() in line.lower()]
        assert pkg_lines, (
            f"STATIC_FALLBACK_LICENSES key {pkg!r} not found in NOTICE — "
            "add the package to NOTICE or remove it from the fallback map."
        )
        for spdx_id in spdx_ids:
            assert any(spdx_id in line for line in pkg_lines), (
                f"STATIC_FALLBACK_LICENSES[{pkg!r}] = {spdx_ids!r} but SPDX id "
                f"{spdx_id!r} not found on any NOTICE line mentioning {pkg!r} — "
                "update one to match the other."
            )
```

### General reusable helper

```python
def assert_value_on_key_lines(file_text: str, key: str, value: str, file_name: str = "file") -> None:
    """Assert that `value` appears on a line mentioning `key` in `file_text`.

    Never use `assert value in file_text` — that assertion passes if the value
    appears anywhere in the file, even on a different key's line.
    """
    key_lines = [line for line in file_text.splitlines() if key.lower() in line.lower()]
    assert key_lines, f"{key!r} not found in {file_name}"
    assert any(value in line for line in key_lines), (
        f"{value!r} not found on any {file_name} line mentioning {key!r}. "
        f"Lines for {key!r}: {key_lines}"
    )
```

### Files where this pattern commonly matters

- `NOTICE` — multiple packages share the same SPDX license (Apache-2.0 is very common)
- `CHANGELOG.md` / `RELEASING.md` — version numbers repeat across entries
- `SECURITY.md` allowlists — CVE IDs can appear in both "known-safe" and "affected" sections
- Any `.txt` or `.md` registry with repeated values across multiple entries

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `assert spdx_id in notice_text` | Full-file text search in `test_static_values_match_notice` | `packaging`'s `Apache-2.0` in NOTICE satisfied `tzdata`'s SPDX check — false pass; caught during PR review | Full-file `in` check decouples the value from the key; always filter to key-relevant lines first |

## Results & Parameters

### Decision matrix: when to use line-scoped vs full-file assertion

| Condition | Assertion Style | Rationale |
|-----------|----------------|-----------|
| Values are unique across all entries in the file | `assert value in full_text` | Safe; no ambiguity |
| Values can repeat across different entries (e.g. SPDX IDs, version strings) | Line-scoped: `any(value in line for line in key_lines)` | Required; full-file check creates false passes |
| File has no concept of "entries" (e.g. prose docs) | `assert value in full_text` | No key-value structure to scope to |
| Asserting presence of the key itself | `assert key.lower() in full_text.lower()` | Key is the entity being searched; full-file is correct |

### Key invariant

```
For every (key, value) pair validated against a structured free-text file:
  assert any(value in line for line in [l for l in file.splitlines() if key in l])
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1258, PR #1304 | Reviewer caught that `assert spdx_id in notice_text` let tzdata pass via packaging's Apache-2.0 line. Fixed in commit d9dcde04 by scoping to per-package lines. All tests pass. |
