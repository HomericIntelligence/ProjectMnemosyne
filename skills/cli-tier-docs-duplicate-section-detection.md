---
name: cli-tier-docs-duplicate-section-detection
description: "Fix cli-tier-docs validator blindness to duplicate '## Console-Script Stability Tiers' H2 sections. Use when: (1) load_documented_tiers uses break to exit at the first non-matching H2, silently ignoring a second tier section; (2) cross-section contradictions (same CLI with different tiers in two sections) are not detected by find_duplicate_tiers(); (3) extending a section-scoped parser to accumulate across all matching H2 sections; (4) adding a duplicate-section TierDocFinding sentinel when section_count > 1; (5) updating callers that unpack a 2-tuple return from load_documented_tiers to a 3-tuple."
category: tooling
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: ["cli-tier-docs", "validation", "markdown-parser", "duplicate-section", "hephaestus", "COMPATIBILITY.md"]
---

# CLI Tier Docs Duplicate Section Detection

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Issue** | #1257 (follow-up from #1213 / PR #1248) |
| **PR** | #1302 |
| **Objective** | Detect a second `## Console-Script Stability Tiers` section in COMPATIBILITY.md so cross-section contradictions are caught |
| **Outcome** | 20 tests pass; `duplicate-section` finding emitted correctly |
| **Verification** | verified-ci |

> **See also**: `validation-cli-tier-docs-duplicate-section-detection` (v2.0.0) — more comprehensive coverage of the same root fix from issue #1255/PR #1301 with 22 tests and a `find_duplicate_sections` helper; `cli-validator-cross-section-blind-spot` for the general pattern.

## When to Use

- A section-scoped Markdown parser uses `break` to stop at the first non-matching H2 and you need it to accumulate across ALL matching sections instead.
- `load_documented_tiers` returns `find_duplicate_tiers()==[]` for a doc with two `## Console-Script Stability Tiers` sections and contradictory rows.
- A CLI appears with `hephaestus-foo|Stable` in section 1 and `hephaestus-foo|Internal` in section 2 — validator reports OK despite the contradiction.
- Extending a 2-tuple return value to a 3-tuple to surface section-level metadata without breaking the `occurrences`-keyed downstream logic.
- Adding a `duplicate-section` `TierDocFinding` using a sentinel `cli="<section>"` (consistent with existing `cli="<table>"` sentinel for `parser-found-no-rows`).

## Verified Workflow

### Quick Reference

```python
# In load_documented_tiers: replace break with reset + continue
# OLD (breaks on any non-tier H2, misses second tier section):
if in_section and line.startswith("## ") and not _SECTION_HEADER_RE.match(line):
    break  # next H2 ends the section

# NEW (resets state, keeps scanning for another tier section):
if in_section and line.startswith("## ") and not _SECTION_HEADER_RE.match(line):
    in_section = False
    in_table = False
    continue

# Also: re-enter on a second matching H2
if _SECTION_HEADER_RE.match(line):
    in_section = True
    in_table = False   # reset table state for the new section
    section_count += 1
    continue

# Return 3-tuple
return tiers, occurrences, section_count

# In main(): emit duplicate-section when section_count > 1
tiers, occurrences, section_count = load_documented_tiers(repo_root / "COMPATIBILITY.md")
duplicates = find_duplicate_tiers(occurrences)
if section_count > 1:
    duplicates.append(
        TierDocFinding(
            cli="<section>",
            kind="duplicate-section",
            detail=(
                f"COMPATIBILITY.md contains {section_count} "
                "'## Console-Script Stability Tiers' sections; "
                "merge them into one to prevent cross-section contradictions"
            ),
        )
    )
findings = find_violations(scripts, tiers, duplicates)
```

### Detailed Steps

1. **Replace `break` with reset**: In the non-tier H2 branch, set `in_section = False; in_table = False; continue` instead of `break`. This keeps the scanner reading the rest of the file.

2. **Reset `in_table` on re-entry**: When `_SECTION_HEADER_RE.match(line)` fires a second time, set `in_table = False` so the table header detection works fresh for the new section.

3. **Add `section_count` counter**: Initialize to `0` before the loop; increment inside the `_SECTION_HEADER_RE.match(line)` branch. Each distinct tier section header increments it.

4. **Return 3-tuple**: Change signature to `-> tuple[dict[str, str], dict[str, list[str]], int]`. Update docstring to document `section_count`.

5. **Update `main()` to emit `duplicate-section`**: After `find_duplicate_tiers(occurrences)`, check `section_count > 1` and append a `TierDocFinding(cli="<section>", kind="duplicate-section", ...)`. The sentinel `cli="<section>"` mirrors the existing `cli="<table>"` for `parser-found-no-rows`.

6. **Update all callers of `load_documented_tiers`**: Search for `tiers, _ =` and `tiers, occ =` unpackings and update to `tiers, _, _ =` and `tiers, occ, _ =`. In this codebase there were 4 sites in `tests/unit/validation/test_cli_tier_docs.py`.

7. **Add `TestCrossSectionDetection` tests**:
   - `test_two_tier_sections_same_cli_conflict_flagged`: exact issue repro (two sections, contradictory tiers, asserts `section_count==2` and `conflicting-tier` finding)
   - `test_section_count_one_for_normal_doc`: normal single-section doc asserts `section_count==1`
   - `test_duplicate_section_finding_emitted_by_main`: integration test calling `main()` with `--repo-root tmp_path`, asserts `result==1`
   - `test_non_tier_h2_still_ends_section`: regression canary asserting non-tier H2 rows are still excluded (`section_count==1`)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Only replace `break` without resetting `in_table` | Changed `break` to `continue` but left `in_table = True` from the previous section | The new section's table header was matched inside an already-active `in_table` context, causing rows before the header to be skipped silently | Always reset `in_table = False` when re-entering a section via the `_SECTION_HEADER_RE` branch |
| Thread `section_count` through `find_violations` | Considered adding `section_count: int = 0` parameter to `find_violations` | No current consumer of `find_violations` passes section metadata; adds a parameter with no caller (YAGNI) | Emit `duplicate-section` in `main()` at the aggregation layer, not inside `find_violations` |
| Thread `section_count` through `find_duplicate_tiers` | Considered making `find_duplicate_tiers` accept `section_count` | `find_duplicate_tiers` is keyed on CLI names from `occurrences`; section metadata is orthogonal to per-CLI dedup logic | Keep `find_duplicate_tiers` pure (occurrences-only); emit section-level findings in `main()` |
| Only fix within-section duplication | Left the `break` and only added dedup logic within a single section | A second matching section later in the file was never reached; cross-section contradictions still undetected | Must BOTH remove the `break` (continue scanning) AND accumulate all matching sections into the same `occurrences` dict |

## Results & Parameters

### Production Change

**File**: `hephaestus/validation/cli_tier_docs.py`

```python
# Signature change:
def load_documented_tiers(
    compatibility_path: Path,
) -> tuple[dict[str, str], dict[str, list[str]], int]:   # was 2-tuple

# Loop body: replace break branch with reset
if _SECTION_HEADER_RE.match(line):
    in_section = True
    in_table = False    # reset for new section
    section_count += 1  # new
    continue
if in_section and line.startswith("## ") and not _SECTION_HEADER_RE.match(line):
    in_section = False  # was: break
    in_table = False
    continue

# main(): emit finding
tiers, occurrences, section_count = load_documented_tiers(...)
duplicates = find_duplicate_tiers(occurrences)
if section_count > 1:
    duplicates.append(TierDocFinding(cli="<section>", kind="duplicate-section", detail=...))
```

### TierDocFinding `kind` docstring addendum

```python
# kind values: "missing-from-docs" | "missing-from-pyproject"
#              | "invalid-tier" | "parser-found-no-rows"
#              | "duplicate-tier" | "conflicting-tier"
#              | "duplicate-section"
```

### Test Results

- 20 tests pass (16 existing + 4 new `TestCrossSectionDetection`)
- `TestRealRepo::test_repo_has_no_tier_doc_violations` still passes (real COMPATIBILITY.md has exactly one tier section)
- Commit: signed, `Good signature`
- PR #1302 merged

### Sentinel Convention

`cli="<section>"` mirrors the existing `cli="<table>"` sentinel (used for `parser-found-no-rows`). Both use angle-bracket sentinels for findings that are document-level, not CLI-specific.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1257, PR #1302 | 20 tests pass, CI green, verified-ci |
