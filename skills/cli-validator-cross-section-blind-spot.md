---
name: cli-validator-cross-section-blind-spot
description: "Fix markdown-section validators that silently miss duplicate or contradictory sections because a section parser breaks on the first non-matching H2. Use when a CLI/doc validator parses only the first matching section, a duplicate section later in the document passes CI, or a parser return shape must expose section_count without losing per-item duplicate checks."
category: debugging
date: 2026-06-13
version: "3.0.0"
user-invocable: false
verification: verified-local
history: cli-validator-cross-section-blind-spot.history
tags: [validation, markdown-parser, state-machine, cli-tier-docs, duplicate-section, cross-section, break-vs-continue, return-shape]
---

# CLI Validator Cross-Section Blind Spot

## Overview

Markdown section parsers often carry a hidden single-section assumption: once they enter the target section, a later unrelated H2 triggers `break`, so the parser never sees a second matching section. That makes validators pass duplicate sections and cross-section contradictions.

This skill consolidates three CLI tier-doc validator memories. The general fix is to reset parser state and continue scanning, count matching sections, and surface section-level findings alongside per-item duplicate/conflict findings.

| Field | Value |
|-------|-------|
| Date | 2026-07-04 |
| Objective | Generalize duplicate-section validator repair while preserving ProjectHephaestus issue-specific implementation details. |
| Outcome | Canonical v3 replaces two duplicate memories and keeps exact source snapshots in history. |
| Verification | verified-local for this consolidation; source examples preserve their original verified-ci status in history. |

## When to Use

- A markdown validator parses a named H2 section and stops at the first non-matching H2.
- A document can contain two same-name sections, but the validator only sees the first.
- A cross-section contradiction is possible, such as the same CLI documented with different tiers.
- A parser currently returns per-item data but not section metadata.
- You need to add a document-level finding such as `duplicate-section` without corrupting per-item duplicate logic.
- A test name still says "stops at next section" after behavior changes to "exits this section but keeps scanning".

## Verified Workflow

### Quick Reference

```python
# Old: exits the whole parser on the first unrelated H2.
if in_section and line.startswith("## ") and not SECTION_RE.match(line):
    break

# New: exits this section, resets table state, and keeps scanning.
if in_section and line.startswith("## ") and not SECTION_RE.match(line):
    in_section = False
    in_table = False
    continue

# Re-enter and count every matching section.
if SECTION_RE.match(line):
    in_section = True
    in_table = False
    section_count += 1
    continue
```

```python
# Return section metadata with the existing parsed data.
return tiers, occurrences, section_count

# Aggregate section-level and per-item findings together.
findings = (
    find_duplicate_sections(section_count)
    + find_duplicate_tiers(occurrences)
    + find_violations(tiers, registered)
)
```

1. Grep all callers before changing a parser return shape: `grep -rn "load_documented_tiers" hephaestus/ tests/ scripts/`.
2. Replace parser-wide `break` with a section-exit reset plus `continue`.
3. Reset all state-machine flags on both exit and re-entry. At minimum, reset `in_section` and `in_table`; reset `header_seen` or equivalent if the parser tracks table headers.
4. Add `section_count` or equivalent metadata at the parser boundary.
5. Emit document-level findings outside per-item duplicate functions unless those functions already receive section metadata.
6. Add tests for: zero sections, one section, duplicate section, cross-section conflict, same item/same value across sections, and unrelated H2 content exclusion.
7. Rename tests whose names encode the old hard-stop behavior.

### Worked Example

| ProjectHephaestus Issue | Failure | Fix | Verification |
|---|---|---|---|
| #1255 / PR #1301 | `break` skipped a second `## Console-Script Stability Tiers` section, hiding duplicate/conflicting tiers. | Added `section_count`, `find_duplicate_sections`, 3-tuple return, and six duplicate-section tests. | 22 tests passed; CI green. |
| #1257 / PR #1302 | Follow-up variant needed the same duplicate-section detection with a sentinel finding. | Reset parser state on section exit/re-entry and emitted `cli="<section>"` duplicate-section finding. | 20 tests passed; CI green. |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| `break` on first non-matching H2 | Treated the first unrelated H2 as the end of all relevant parsing. | A later matching H2 was never reached. | Use state reset plus `continue` for section-scoped parsers. |
| Replace `break` without resetting table state | Continued scanning but left `in_table` true from the previous section. | The new section's table header could be skipped or misclassified. | Reset every state flag needed for fresh re-entry. |
| Only fix within-section duplicates | Improved duplicate detection inside one parsed section. | Cross-section contradictions still never reached the duplicate checker. | Parser reachability must be fixed before duplicate logic can work. |
| Change return shape without caller audit | Assumed only one caller unpacked the parser return. | Any un-audited unpack would break at runtime. | Grep all callers and update unpack sites atomically. |
| Put section finding inside per-item duplicate logic | Tried to thread document-level metadata through item keyed helpers. | It coupled orthogonal concerns and complicated API shape. | Emit document-level findings at the aggregation layer. |

## Results & Parameters

Use these implementation parameters for similar validators:

```yaml
parser_state:
  section_count: int
  in_section: bool
  in_table: bool
  header_seen: bool
finding_kinds:
  document_level: duplicate-section
  item_level: [duplicate-tier, conflicting-tier]
sentinel_values:
  section: "<section>"
  table: "<table>"
validation_tests:
  - zero target sections
  - one target section
  - two target sections same item same value
  - two target sections same item conflicting value
  - unrelated h2 content excluded
  - main exits nonzero when duplicate-section is emitted
```

Commands:

```bash
grep -rn "load_documented_tiers" hephaestus/ tests/ scripts/ 2>/dev/null
grep -c '^## Console-Script Stability Tiers' COMPATIBILITY.md
pixi run pytest tests/unit/validation/test_cli_tier_docs.py -v
```
