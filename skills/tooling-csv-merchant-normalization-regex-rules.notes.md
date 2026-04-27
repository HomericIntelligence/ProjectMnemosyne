# tooling-csv-merchant-normalization-regex-rules — Session Notes

## Session Context

- **Date**: 2026-04-26
- **File**: `/home/mvillmow/Downloads/combined_transactions.csv`
- **Rows**: 2,261 (header + 2,260 data rows)
- **Original unique descriptions**: 1,039
- **Final unique merchant names**: 559
- **Script**: `/home/mvillmow/Downloads/normalize_descriptions.py`

## CSV Column Layout (after normalization)

| Column | Name | Example |
|--------|------|---------|
| A | (account/type) | CHECKING |
| B | description | `SQ* VERVE COFFEE ROASTERS SAN JOSE CA` |
| C | merchant | `Verve Coffee` |
| D | date | 2025-03-15 |
| E | amount | -4.75 |

## Key Regex Patterns Used

### Namespace prefixes
- `SQ\s*\*\s*` — Square payment terminal
- `SP\s*\*\s*` — SumUp / generic prefix
- `TST\s*\*\s*` — Toast POS
- `CTLP\s*\*\s*` — Contactless payment
- `EBAY\s*\*` — eBay marketplace

### Cross-namespace exceptions documented
1. **The Plex** (climbing gym): appears as both `CTLP* THE PLEX ...` and `TST* THE PLEX ...` and standalone `THE PLEX ...` — all merged to `"The Plex"`
2. **Sports Basement**: appears as `SP* SPORTS BASEMENT ...` and standalone `SPORTS BASEMENT ...` — both merged to `"Sports Basement"`

### Debit Card Purchase pattern
Raw description format: `Debit Card Purchase - <merchant> <CITY> <ST> US`

Strip with:
```python
DCP_RE = re.compile(
    r"^Debit Card Purchase\s*-\s*(.+?)(?:\s+\w{2,3}\s+\w{2}\s+US)?\s*$",
    re.IGNORECASE,
)
```
Then pass inner text back through the normalizer recursively.

### Store-number prefixes
Some merchants embed a store number at the start:
- `5223 GREAT CLIPS OF MO` — needs rule `r"\d+\s+GREAT\s+CLIPS.*"` BEFORE `r"GREAT\s+CLIPS.*"`
- `580 BOWLMOR 8003425263` — needs rule `r"\d+\s+BOWLMOR.*"`

## Debugging Workflow

```python
# Find all descriptions that still pass through unchanged (no rule matched):
import csv
with open('combined_transactions.csv') as f:
    rows = list(csv.DictReader(f))
unchanged = [(r['description'], r['merchant']) for r in rows if r['merchant'] == r['description']]
# Sort by frequency
from collections import Counter
freq = Counter(r['description'] for r in rows if r['merchant'] == r['description'])
for desc, count in freq.most_common(30):
    print(count, desc)
```

## LibreOffice Calc Tips

1. Open the CSV with Import dialog — set delimiter to comma, encoding to UTF-8
2. After UNIQUE formula generates merchant list, copy-paste as values to freeze it
3. Add a "Total" row: `=SUM(H2:H<last_row>)` — should equal sum of all transaction amounts
4. For year-over-year: add a `year` helper column with `=YEAR(D2)`, then use `SUMIFS` with both merchant and year criteria

## Files Created

| File | Purpose |
|------|---------|
| `/home/mvillmow/Downloads/normalize_descriptions.py` | Normalization script (idempotent, re-runs from .bak) |
| `/home/mvillmow/Downloads/combined_transactions.csv` | Enriched CSV with `merchant` column added |
| `/home/mvillmow/Downloads/combined_transactions.csv.bak` | Backup of original CSV before modification |
