---
name: tooling-csv-merchant-normalization-regex-rules
description: "Normalize raw bank/CC transaction descriptions in a CSV so variants of the same merchant collapse to a single canonical name, enabling clean per-merchant aggregation. Use when: (1) you have a CSV of transactions with messy raw descriptions, (2) you want SUMIF/pivot-table rollups by merchant in a spreadsheet, (3) multiple description variants (location suffixes, namespace prefixes like SQ*/SP*/TST*) represent one real merchant."
category: tooling
date: 2026-04-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [csv, python, regex, financial, transactions, merchant, normalization, libreoffice, spreadsheet]
---

# CSV Merchant Normalization with Ordered Regex Rules

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-26 |
| **Objective** | Normalize 1,039 unique raw transaction descriptions in a bank/CC export CSV down to a manageable set of canonical merchant names for spreadsheet aggregation |
| **Outcome** | Successful — 1,039 unique descriptions collapsed to 559 unique merchant names; 87% of rows normalized; row count unchanged |
| **Verification** | verified-local |

## When to Use

- You have a CSV bank or credit-card export with a "description" column containing raw, messy transaction strings (location suffixes, store numbers, payment namespace prefixes)
- You want a `merchant` column for clean SUMIF / UNIQUE / pivot-table rollups in LibreOffice Calc or Excel
- Multiple description variants for the same merchant appear: `AMAZON.COM*AB1CD2345`, `AMAZON MKTPLACE PMTS`, `AMAZON WEB SERVICES` — all Amazon, but with different prefixes
- Namespace prefixes like `SQ*`, `SP*`, `TST*`, `CTLP*`, `eBay` are present, and you want per-vendor control (collapse within a vendor, but NOT wholesale across the namespace)
- You need an idempotent, re-runnable script that is safe to iterate on as you add more rules

## Verified Workflow

### Quick Reference

```bash
# Script lives at normalize_descriptions.py
# Run once (backs up CSV, adds merchant column, writes in-place):
python3 normalize_descriptions.py

# Re-run safely (always re-reads from .bak):
python3 normalize_descriptions.py

# Count unique merchants after normalization:
python3 -c "
import csv
with open('combined_transactions.csv') as f:
    rows = list(csv.DictReader(f))
print('Rows:', len(rows))
print('Unique merchants:', len(set(r['merchant'] for r in rows)))
print('Unchanged (passthrough):', sum(1 for r in rows if r['merchant'] == r['description']))
"
```

### Detailed Steps

1. **Identify the CSV structure** — locate the `description` column name (exact case matters for `csv.DictReader`). Note which columns exist and where to insert the `merchant` column.

2. **Back up the original CSV** — copy to `<file>.bak` before any modification. This is the idempotency anchor: subsequent runs re-read from `.bak`, so re-running never double-normalizes.

3. **Build an ordered `(compiled_regex, canonical_name)` rule list** — order matters: first match wins.
   - Put more-specific rules BEFORE broader ones (e.g., a Plex cross-namespace rule before generic `CTLP*`/`TST*` carve-outs)
   - Use `re.IGNORECASE` on all rules
   - Use `re.match()` for prefix/anchored patterns; use `re.fullmatch()` only when you need exact matching
   - `re.match()` is anchored at the start but NOT at the end — add `.*` at the end to consume the rest

4. **Handle payment namespace prefixes** (`SQ*`, `SP*`, `TST*`, `CTLP*`, `EBAY*`):
   - Do NOT collapse entire namespaces to one merchant — each underlying vendor should stay separate
   - Rule per vendor within a namespace: `r"SQ\s*\*\s*VERVE\s+COFFEE.*"` → `"Verve Coffee"`
   - Document cross-namespace exceptions explicitly (e.g., "The Plex" appears under both `CTLP*` and `TST*` → single canonical)

5. **Handle "Debit Card Purchase - \<inner text\>"** rows** — strip the prefix AND trailing location noise (`CITY ST US` suffix), then re-run the inner text through the normalizer recursively:

   ```python
   DCP_RE = re.compile(r"^Debit Card Purchase\s*-\s*(.+?)(?:\s+\w{2,3}\s+\w{2}\s+US)?\s*$", re.IGNORECASE)

   def normalize(desc: str) -> str:
       m = DCP_RE.match(desc)
       if m:
           inner = m.group(1).strip()
           # re-run inner text through the rule list
           return normalize(inner)
       for pattern, canonical in RULES:
           if pattern.match(desc):
               return canonical
       return desc  # pass-through
   ```

6. **Handle descriptions that start with store-number prefixes** — some merchants prepend a store number: `5223 GREAT CLIPS OF MO`, `580 BOWLMOR 8003425263`. `re.match()` won't find `GREAT\s+CLIPS` if the string starts with digits. Add explicit rules:
   - `r"\d+\s+GREAT\s+CLIPS.*"` → `"Great Clips"` (before the general `r"GREAT\s+CLIPS.*"` rule)
   - `r"\d+\s+BOWLMOR.*"` → `"Bowlmor"`

7. **Insert `merchant` column** between `description` and `date` in the output CSV using `csv.DictWriter`. Reorder fieldnames explicitly — `DictWriter` preserves insertion order.

8. **Spot-check results** — for each tricky rule, verify with a one-liner:

   ```python
   python3 -c "
   import csv
   with open('combined_transactions.csv') as f:
       rows = list(csv.DictReader(f))
   for r in rows:
       if '7-ELEVEN' in r['description'].upper() or '7ELEVEN' in r['description'].upper():
           print(r['description'], '->', r['merchant'])
   "
   ```

9. **LibreOffice Calc formulas** — once `merchant` column is present (column C if CSV has description/merchant/date/amount order):
   - Sum by merchant: `=SUMIF($C:$C, G2, $E:$E)` (adjust column letters to match your layout)
   - Extract unique merchant list to summary sheet: `=UNIQUE(Sheet1.$C$2:$C$2262)`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `SMART AND FINAL` regex used `&` | Rule: `r"SMART\s*&\s*FINAL.*"` | Bank description used `AND` not `&` (`SMART AND FINAL`) | Use `(?:AND\|&)` to cover both ampersand and spelled-out "and" in merchant names |
| Debit Card Purchase inner-text extraction | Extracted inner text with `(.+)` then ran through normalizer | Inner text `7-ELEVEN 12345 SAN JOSE CA` still had trailing location suffix; only the `7` character was captured by a short rule | Strip trailing location noise (`CITY ST US`) before re-normalizing; use a greedy group + optional trailing suffix in the DCP regex |
| `re.match()` on digit-prefixed descriptions | Rule `r"GREAT\s+CLIPS.*"` via `re.match()` | String starts with `5223 GREAT CLIPS OF MO` — `re.match()` requires match at position 0 | When store-number prefixes are present, add `r"\d+\s+<MERCHANT_NAME>.*"` rule BEFORE the general rule |
| Treating all "unchanged" entries as failures | 161 descriptions had `merchant == description` | Most were single-occurrence merchants (Japanese restaurant names from a trip) that correctly pass through unchanged | Distinguish true normalization failures from legitimate single-occurrence pass-throughs; audit only the high-frequency "unchanged" rows |
| Collapsing entire SQ*/SP*/TST*/CTLP* namespaces to one merchant | Considered writing `r"SQ\s*\*.*"` → `"Square Vendor"` | Multiple unrelated vendors share the same namespace prefix | Keep per-vendor rules within each namespace; only merge cross-namespace when you can confirm it's the same real merchant |

## Results & Parameters

### Normalization Summary (this session)

| Metric | Value |
| -------- | ------- |
| Input rows | 2,261 |
| Unique raw descriptions | 1,039 |
| Unique canonical merchants | 559 |
| Rows normalized (non-passthrough) | ~87% |
| Rules applied | ~200 regex rules |

### Script Structure (copy-paste template)

```python
#!/usr/bin/env python3
"""
normalize_descriptions.py
Adds a `merchant` column to combined_transactions.csv.
Idempotent: re-reads from .bak on every run.
"""
import csv, re, shutil
from pathlib import Path

CSV_FILE = Path("combined_transactions.csv")
BAK_FILE = CSV_FILE.with_suffix(".csv.bak")

# ── Rule list: (compiled_pattern, canonical_name) ──────────────────────────
# First match wins. More-specific rules MUST come before broader ones.
RULES: list[tuple[re.Pattern, str]] = [
    # Cross-namespace exceptions first
    (re.compile(r"(?:CTLP|TST)\s*\*\s*THE\s*PLEX.*", re.I),       "The Plex"),
    (re.compile(r"THE\s+PLEX.*",                        re.I),       "The Plex"),
    # Namespace-prefixed vendors (SQ*, SP*, TST*, CTLP*, EBAY*)
    (re.compile(r"SQ\s*\*\s*VERVE\s+COFFEE.*",          re.I),       "Verve Coffee"),
    # ... add more rules here ...
    # Store-number prefixed merchants (before their general equivalents)
    (re.compile(r"\d+\s+GREAT\s+CLIPS.*",               re.I),       "Great Clips"),
    (re.compile(r"GREAT\s+CLIPS.*",                     re.I),       "Great Clips"),
    (re.compile(r"\d+\s+BOWLMOR.*",                     re.I),       "Bowlmor"),
    # Generic merchants
    (re.compile(r"AMAZON(?:\.COM|MKTPLACE|\.COM\s*PMTS)?.*", re.I),  "Amazon"),
    (re.compile(r"SMART\s+(?:AND|&)\s*FINAL.*",         re.I),       "Smart & Final"),
]

# Debit Card Purchase prefix stripper
DCP_RE = re.compile(
    r"^Debit Card Purchase\s*-\s*(.+?)(?:\s+\w{2,3}\s+\w{2}\s+US)?\s*$",
    re.IGNORECASE,
)

def normalize(desc: str) -> str:
    m = DCP_RE.match(desc)
    if m:
        return normalize(m.group(1).strip())
    for pattern, canonical in RULES:
        if pattern.match(desc):
            return canonical
    return desc  # pass-through

def main():
    if not BAK_FILE.exists():
        shutil.copy(CSV_FILE, BAK_FILE)
    with BAK_FILE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        original_fields = list(reader.fieldnames)
        rows = list(reader)

    # Insert merchant column after description
    desc_idx = original_fields.index("description")
    new_fields = original_fields[:desc_idx+1] + ["merchant"] + original_fields[desc_idx+1:]

    for row in rows:
        row["merchant"] = normalize(row["description"])

    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {len(rows)} rows written.")

if __name__ == "__main__":
    main()
```

### LibreOffice Calc Formulas

```
# Sum amounts for each merchant (merchant list in column G, amounts in column E):
=SUMIF($C:$C, G2, $E:$E)

# Extract unique merchant names to a summary sheet (all merchants in C2:C2262):
=UNIQUE(Sheet1.$C$2:$C$2262)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Personal finance CSV | 2,261-row bank/CC export, 1,039 unique raw descriptions | [notes.md](./tooling-csv-merchant-normalization-regex-rules.notes.md) |
