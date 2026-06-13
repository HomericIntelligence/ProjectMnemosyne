---
name: cli-validator-cross-section-blind-spot
description: "Markdown-section validators that break on the first non-matching H2 silently miss duplicate sections later in the document. Use when: (1) a tier/table validator parses a markdown section and stops early, (2) a CI gate passes despite a doc contradiction, (3) a 'break' at a section-end guard is the only early-exit in a line-by-line parser."
category: debugging
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [validation, markdown-parser, state-machine, cli-tier-docs, duplicate-section, break-vs-continue]
---

# CLI Validator Cross-Section Blind Spot

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Detect contradictory CLI tier documentation across two `## Console-Script Stability Tiers` sections in COMPATIBILITY.md |
| **Outcome** | Plan produced; implementation pending CI verification |
| **Verification** | unverified — plan not yet executed |
| **Issue** | ProjectHephaestus #1257 |
| **See also** | `validation-cli-tier-docs-duplicate-section-detection` (issue #1255) — detailed step-by-step fix workflow |

## When to Use

- A markdown-section validator uses `break` to exit parsing when it sees any non-matching H2
- A doc with two same-name H2 sections passes a validator that should have flagged them
- `find_duplicate_tiers()` returns empty despite a CLI appearing with different tiers in two separate table sections
- A PR reviewer manually deleted a duplicate section that the validator never caught

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```python
# Before: break exits on first non-matching H2, missing second tier section
if in_section and line.startswith("## ") and not _SECTION_HEADER_RE.match(line):
    break  # BUG: second ## Console-Script Stability Tiers is never seen

# After: continue scanning; re-enter section if a second matching H2 appears
if in_section and line.startswith("## ") and not _SECTION_HEADER_RE.match(line):
    in_section = False
    in_table = False
    continue  # keep scanning for another tier section

# Track how many times the section header appeared
if _SECTION_HEADER_RE.match(line):
    in_section = True
    in_table = False
    section_count += 1
    continue
```

```python
# Return section_count as 3rd element of the tuple
return tiers, occurrences, section_count

# In main(): emit duplicate-section finding when section_count > 1
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
```

### Detailed Steps

1. In `load_documented_tiers` (`hephaestus/validation/cli_tier_docs.py:89-90`): replace `break` with `in_section = False; in_table = False; continue`
2. Add `section_count = 0` before the loop; increment when `_SECTION_HEADER_RE.match(line)` is true; reset `in_table = False` on re-entry
3. Change return type annotation: `tuple[dict[str, str], dict[str, list[str]]]` → `tuple[dict[str, str], dict[str, list[str]], int]`
4. In `main()`: unpack 3-tuple; if `section_count > 1`, append a `duplicate-section` TierDocFinding to `duplicates` before calling `find_violations`
5. Update existing test unpacking: `tiers, _ =` → `tiers, _, _ =`; `tiers, occ =` → `tiers, occ, _ =` (4 test sites)
6. Add `TestCrossSectionDetection` class with 4 new tests covering: two-section contradiction, single-section count, main() exit code, non-tier H2 still ends section

## Key Uncertainties (Planning-Phase Risks)

### 1. 3-tuple return is a clean API extension

`load_documented_tiers` currently returns a 2-tuple; the plan changes it to a 3-tuple `(tiers, occurrences, section_count)`. This is a public function, so if any callers outside the main module exist (e.g., external code, other tests), they will break silently.

**The plan only verified the four call sites in the existing test file and `main()`.** Always run before implementing:

```bash
grep -rn "load_documented_tiers" hephaestus/ tests/ scripts/
```

### 2. `section_count > 1` emitted in `main`, not in `find_violations`

The `duplicate-section` finding is placed in `main()` rather than in `find_duplicate_tiers()` or `find_violations()`, since those functions do not have access to `section_count`. This is a clean design but means the finding does not appear if callers invoke `find_violations` directly without going through `main()`.

### 3. `test_load_tiers_stops_at_next_section` contract preserved

The existing test verifies that rows under `## Other Section` are NOT accumulated. The `break` → `continue` change preserves this: `in_section = False` is set when the non-matching H2 is seen, so content under it is still excluded. The test still passes — but the test name implies a hard stop (`break`), which is semantically wrong after the fix. Consider renaming to `test_load_tiers_excludes_content_under_other_sections`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Original `break` guard (PR #1248) | Added within-section duplicate detection; `break` on first non-matching H2 | Second `## Console-Script Stability Tiers` after an intervening H2 is never parsed | `break` in a section parser is a single-section assumption; use `continue` to keep scanning |
| Dedup within single section only | `occurrences` dict accumulated rows within one section | Cross-section contradiction (Stable in section 1, Internal in section 2) produces no `occurrences` conflict since both sections are never read together | Parser must accumulate all matching sections into a single `occurrences` dict |

## Results & Parameters

**Root cause**: `cli_tier_docs.py:89-90` — `break` on non-matching H2 means:
- Section 1 parsed: `hephaestus-foo → Stable`
- `## Public API` H2 triggers `break`
- Section 2 (`hephaestus-foo → Internal`) never reached
- `find_duplicate_tiers({"hephaestus-foo": ["Stable"]}) == []` → validator reports OK

**Risk**: `load_documented_tiers` 3-tuple API change may break undiscovered callers outside `main()` and the test file. Run `grep -r "load_documented_tiers" hephaestus/ scripts/` before implementing.

**Risk**: `test_duplicate_section_finding_emitted_by_main` uses a minimal pyproject without `[build-system]` — verify tomllib parses it without error.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1257 planning — plan only, not yet implemented | Plan review pending |
