---
name: latex-table-underscore-escape-missing-dollar
description: "Use when: (1) a LaTeX build fails with '! Missing $ inserted' and the error context shows an underscore character, (2) table cells in .tex files contain identifier-style text with underscores (e.g., code_quality, build_pipeline), (3) pdflatex or tectonic reports subscript-related errors in plain text mode"
category: documentation
date: 2026-05-01
version: "1.0.0"
user-invocable: false
tags: [latex, pdflatex, underscore, tables, paper]
---

# LaTeX Table Underscore Escape — Missing Dollar Error

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-01 |
| **Objective** | Fix `! Missing $ inserted` compile errors caused by unescaped underscores in LaTeX table cells |
| **Outcome** | Successful — paper compiled to 56 pages after escaping underscores in table file |

## When to Use

- LaTeX build fails with `! Missing $ inserted` or `! Missing $ inserted. <inserted text> $` and the error log line contains an underscore character
- Table `.tex` files contain snake\_case identifiers, metric names, or code-style strings in plain text mode
- pdflatex or tectonic exits non-zero and the offending line is inside a tabular environment

## Verified Workflow

### Quick Reference

```bash
# 1. Find unescaped underscores in .tex table files
grep -n "_" docs/arxiv/<paper>/tables/*.tex | grep -v "\\\_"

# 2. Replace unescaped underscores (in plain-text cells only, not math mode)
# Before: code_quality
# After:  code\_quality

# 3. Rebuild
cd docs/arxiv/<paper> && bash build.sh
```

### Detailed Steps

1. Run the build and capture the error output: `bash build.sh 2>&1 | grep -A3 "Missing"`
2. The error message reads `! Missing $ inserted` — LaTeX thinks the `_` starts a math subscript.
3. Look at the line reference in the log (e.g., `l.42 code_quality`) to find the offending file and line.
4. Open the table `.tex` file and escape every underscore that is in plain text mode: change `_` to `\_`.
5. Do NOT escape underscores inside `$...$` or `\(...\)` math environments — those are intentional.
6. Re-run the build and confirm it completes cleanly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Rely on error message alone | Read `! Missing $ inserted` without checking line context | Error message does not mention underscores; the word "subscript" or "_" does not appear in the error header | Always inspect the line context (`l.NN ...`) printed after the error — it shows the actual character causing the problem |

## Results & Parameters

### Configuration

No special build configuration needed. Standard pdflatex 4-pass cycle:

```bash
# Typical build.sh sequence
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Or using tectonic (single command, auto-resolves passes):

```bash
tectonic main.tex
```

### Expected Output

After escaping all underscores in plain text table cells:

- `bash build.sh` exits 0
- PDF generated (e.g., 56 pages)
- No `Missing $` errors in the pdflatex log

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey (haiku paper) | Local paper build — `docs/arxiv/haiku/tables/tab04_criteria_performance.tex` | Fixed `code_quality`, `build_pipeline`, `overall_quality` column headers |

## References

- [LaTeX special characters reference](https://en.wikibooks.org/wiki/LaTeX/Special_Characters)
- [Related skill: pixi-tectonic-latex-build](pixi-tectonic-latex-build.md)
