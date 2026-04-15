---
name: latex-paper-parallel-assembly
description: "Assemble a large LaTeX research paper from parallel-agent-written parts. Use when: (1) a single agent cannot hold the full paper in context, (2) you have 20+ ideas/sections to write and want parallel speedup, (3) you need to merge N part files into one compilable .tex, (4) you need post-assembly error remediation (unicode, missing bib entries, tabular column drift, undefined commands), (5) removing inline arXiv hrefs from assembled paper body, (6) consolidating scattered verdict codes into a single Future Work section, (7) deduplicating bib entries introduced by parallel agents writing their own citation stubs."
category: documentation
date: 2026-04-14
version: "1.1.0"
user-invocable: false
verification: verified-local
tags: [latex, parallel, assembly, pdflatex, bibtex, cleanup, citations, verdicts]
---

# LaTeX Paper Assembly from Parallel Agent Parts

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-14 |
| **Objective** | Produce a single compilable LaTeX paper from parts written by N parallel agents |
| **Outcome** | Successful — 272 KB paper (3,320 lines, 102 pages, 0 errors) assembled from 4 parallel agent parts + cross-compiled with 395 BibTeX entries |
| **Verification** | verified-local |

## When to Use

- A single agent cannot write the full paper without hitting context limits (>50 ideas, >40 pages)
- You have independent parallel-writable sections (e.g., one idea per subsection, each self-contained)
- You need a reproducible farm-and-assemble pattern with explicit error-remediation steps
- Post-assembly compilation fails due to Unicode, missing bib keys, `\citeauthor`, or tabular column drift
- Removing all inline arXiv hrefs from a LaTeX paper body after a parallel assembly pass
- Consolidating scattered verdict codes (PURSUE/INVESTIGATE/DEPRIORITIZE) into a single Future Work section
- Deduplicating bib entries introduced by parallel agents writing their own citation stubs

## Verified Workflow

### Quick Reference

```bash
# Step 1: Farm to N part files
# Each agent writes part_N.tex with its assigned slice of subsections

# Step 2: Assemble
# head: keep lines 1..K from part1 (preamble + early sections)
head -717 part1.tex > paper.tex
# Append later part files, stripping their preambles (keep only from first \subsection)
awk '/^\\subsection/{found=1} found{print}' part2.tex >> paper.tex
awk '/^\\subsection/{found=1} found{print}' part3.tex >> paper.tex
cat part4.tex >> paper.tex   # part4 has only body content, no preamble

# Step 3: Unicode → math mode (must run before pdflatex)
python3 - <<'PY'
import pathlib, re
tex = pathlib.Path("paper.tex").read_text(encoding="utf-8")
replacements = {
    "\u00e9": r"\'{e}", "\u00e8": r"\`{e}", "\u00e0": r"\`{a}",
    "\u00e7": r"\c{c}", "\u00fc": r'\"u', "\u00f6": r'\"o',
    "\u00d7": r"$\times$", "\u2014": "---", "\u2013": "--",
    "\u03c1": r"$\rho$", "\u03c3": r"$\sigma$", "\u03b1": r"$\alpha$",
    "\u03bc": r"$\mu$", "\u0394": r"$\Delta$", "\u2264": r"$\leq$",
    "\u2265": r"$\geq$", "\u2248": r"$\approx$", "\u00b1": r"$\pm$",
}
for char, latex in replacements.items():
    tex = tex.replace(char, latex)
pathlib.Path("paper.tex").write_text(tex, encoding="utf-8")
print("Unicode replacement done")
PY

# Step 4: Compile (first pass — will show missing bib keys)
pdflatex -interaction=nonstopmode paper.tex 2>&1 | tail -5
bibtex paper
pdflatex -interaction=nonstopmode paper.tex 2>&1 | tail -5
pdflatex -interaction=nonstopmode paper.tex 2>&1 | tail -5

# Step 5: Extract missing bib keys and generate stubs
grep "^LaTeX Warning.*Citation.*undefined" paper.log | \
  grep -oP "(?<=Citation ')[^']+" | sort -u > missing_keys.txt
python3 - <<'PY'
keys = open("missing_keys.txt").read().splitlines()
with open("references.bib", "a") as f:
    for key in keys:
        f.write(f"\n@misc{{{key},\n  title={{STUB: {key}}},\n  author={{Unknown}},\n  year={{2024}},\n  note={{Auto-generated stub. Replace with real entry.}}\n}}\n")
print(f"Added {len(keys)} stub entries")
PY

# Step 6: Final compile (no undefined cite warnings)
pdflatex -interaction=nonstopmode paper.tex && bibtex paper && \
  pdflatex -interaction=nonstopmode paper.tex && \
  pdflatex -interaction=nonstopmode paper.tex

# Step 7: Verify
grep -c "^!" paper.log && echo "errors above (should be 0)"
grep "??" paper.log | grep -v pdfTeX
pdfinfo paper.pdf | grep Pages
```

### Detailed Steps

1. **Partition the paper into independent slices** — each part file should contain:
   - Part 1: full preamble (`\documentclass` through `\maketitle`), introduction, models section, and the first N ideas
   - Parts 2–N: only body content (subsections onward) for their assigned idea slices — NO `\documentclass`, NO `\begin{document}`, NO `\end{document}`

2. **Farm to parallel agents** — launch N agents in a single message (one Agent tool call per part). Each agent:
   - Gets the preamble template (lines 1–65 or equivalent) to understand column widths, package list, macros
   - Gets its assigned idea slice from the research corpus
   - Writes its part file to a known path (`part1.tex`, `part2.tex`, etc.)
   - Must NOT include `\documentclass` in parts 2..N

3. **Assemble** — use `head` to keep the preamble from part1 up to (but not including) any preamble-only content in later parts. Use `awk` to skip preamble lines in parts 2..N by looking for the first `\subsection` as the start marker.

4. **Unicode → math mode** — run the Python replacement dict BEFORE any pdflatex run. LaTeX will silently fail or produce garbled output on unescaped non-ASCII. Key characters: `×`, `—`, `–`, accented letters (é, è, à, ç, ü, ö), Greek letters (ρ, σ, α, μ, Δ), math symbols (≤, ≥, ≈, ±).

5. **First compile** — run `pdflatex + bibtex + pdflatex×2` once to discover all missing bib keys. Do NOT try to fix errors manually during this pass.

6. **Stub-bib generation** — extract missing keys from `paper.log` with grep, generate `@misc{}` stub entries, append to `references.bib`. This lets the paper compile while you (or an agent) fills in real entries later.

7. **Fix `\citeauthor{}` errors** — if plain BibTeX (not natbib) is used, `\citeauthor{}` is undefined. Replace with `\cite{}` using:
   ```python
   tex = re.sub(r'\\citeauthor\{([^}]+)\}(?:~\\cite\{\1\})?', r'\\cite{\1}', tex)
   ```

8. **Fix tabular column count drift** — if parallel agents produce tables with mismatched column specs (e.g., `{llp{7cm}}` for 3 columns but 4 cells in a row), grep for `Misplaced \noalign` or `Extra alignment tab` in the log. Fix by adding or removing column spec letters.

9. **Final compile** — `pdflatex + bibtex + pdflatex×2`. Verify: `grep "^!" paper.log` → 0, `grep "??" paper.log` → 0, `pdfinfo paper.pdf | grep Pages` → expected page count.

10. **Build script** — use the Scylla pattern: `pdflatex + bibtex + pdflatex + pdflatex` (4 runs total). Copy `~/ProjectScylla/docs/arxiv/haiku/build.sh` verbatim; it handles the exact sequencing. Required preamble directive: `\pdfoutput=1` for arXiv compatibility.

### Optional Phase: Post-Assembly Citation and Verdict Cleanup

Run after the assembly phase when the assembled paper contains inline arXiv hrefs, scattered verdict codes, unescaped underscores in `\texttt{}`, or duplicate bib entries from parallel agents.

**Step C1: Remove inline arXiv hrefs from paper body**

```python
import pathlib, re

tex = pathlib.Path("paper.tex").read_text(encoding="utf-8")

# Pattern 1 — Mixed \href{arxiv}{text\cite{key}}: strip \href wrapper, keep inner content
tex = re.sub(
    r'\\href\{https://arxiv\.org/abs/[^}]+\}\{([^}]*(?:\\cite\{[^}]+\}[^}]*)?)\}',
    r'\1',
    tex
)

# Pattern 2 — Bare arXiv ID list items: \href{https://arxiv.org/abs/NNNN.NNNNN}{arXiv:NNNN.NNNNN}
tex = re.sub(
    r'\\href\{https://arxiv\.org/abs/(\d{4}\.\d+)\}\{arXiv:\d{4}\.\d+\}',
    r'arXiv:\\texttt{\1}',
    tex
)

# Pattern 3 — Domain-only link: \href{https://arxiv.org}{arXiv} → arXiv
tex = tex.replace(r'\href{https://arxiv.org}{arXiv}', 'arXiv')

pathlib.Path("paper.tex").write_text(tex, encoding="utf-8")
print("arXiv href cleanup done")
```

Verification: `grep -c 'arxiv.org' paper.tex` → 0

**Step C2: Consolidate verdict codes into Future Work section**

- Grep for PURSUE/INVESTIGATE/DEPRIORITIZE in body text (not table cells):
  ```bash
  grep -n 'PURSUE\|INVESTIGATE\|DEPRIORITIZE' paper.tex
  ```
- In body paragraphs: replace with neutral prose (high-priority, candidate for investigation, lower-priority)
- In table rows: replace with `\textbf{P}`/`\textbf{I}`/`\textbf{D}` + footnote pointing to Future Work section
- Create new `\section{Future Work and Implementation Verdicts}` with:
  - `\description` list defining P/I/D
  - `longtable` per tier (PURSUE / INVESTIGATE / DEPRIORITIZE)
  - Recommended Implementation Sequence as `\enumerate`
- Remaining PURSUE/INVESTIGATE/DEPRIORITIZE count after cleanup = only Future Work section headings (intentional)
- **Package requirement:** Check `\usepackage{longtable}` and `\usepackage{booktabs}` in preamble before adding the Future Work section — `longtable` for the environment, `booktabs` for `\toprule`/`\midrule`/`\bottomrule`

**Step C3: Fix `\texttt{}` underscore escaping in research doc pointer lines**

Agents adding `\textit{Full analysis: \texttt{research_X_Y_*.md}}` produce unescaped `_` inside `\texttt{}`. LaTeX interprets `_` as subscript → "Missing $ inserted" errors.

```python
import pathlib, re

tex = pathlib.Path("paper.tex").read_text(encoding="utf-8")

# First, fix any double-escaping from previous agent passes (\\_  →  \_)
# Check: cat -A paper.tex | grep 'texttt' to see actual bytes
tex = tex.replace('\\\\_', '\\_')

# Then escape remaining bare underscores inside \texttt{} on research doc pointer lines
def escape_texttt_underscores(m):
    inner = m.group(1)
    # Only escape if not already escaped
    inner = re.sub(r'(?<!\\)_', r'\\_', inner)
    return r'\texttt{' + inner + '}'

tex = re.sub(r'\\texttt\{([^}]*research[^}]*)\}', escape_texttt_underscores, tex)
pathlib.Path("paper.tex").write_text(tex, encoding="utf-8")
print("texttt underscore escaping done")
```

**Critical:** `\verb|...|` does NOT work inside `\textit{}` — causes "\\verb ended by end of line" errors. Always use `\texttt{research\_X\_Y\_slug.md}` with explicitly escaped underscores.

**Step C4: Deduplicate bib entries introduced by parallel agents**

Parallel merge agents each add their own stubs with uppercase cite keys (e.g., `Banino2021PonderNet`). Original bib has lowercase versions (`banino2021pondernet`) — bibtex reports "Case mismatch" and "Repeated entry".

```bash
# Find duplicate keys (case-insensitive)
grep -i '^@' references.bib | grep -oP '(?<=\{)[^,]+' | sort -fi | uniq -di

# Remove uppercase duplicate entries from .bib (keep original lowercase entries)
# Also remove bare % comment lines at top of .bib that bibtex tries to parse as entries

# After editing .bib, ALWAYS clear intermediate files before rebuild:
rm -f paper.aux paper.bbl paper.blg
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
# Target: "Output written on paper.pdf (N pages, ...)" with zero ! errors
```

**Verification sequence after all cleanup steps:**

```bash
grep -c 'arxiv.org' paper.tex          # → 0 after href cleanup
grep -c '\\cite{' paper.tex            # should be unchanged (all cite keys preserved)
grep -c 'PURSUE\|INVESTIGATE\|DEPRIORITIZE' paper.tex  # → N (only Future Work section labels)
grep -n 'PURSUE\|INVESTIGATE\|DEPRIORITIZE' paper.tex  # verify all are in \section{Future Work}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single agent for full 38-idea paper | One agent writes the entire paper.tex | Context exhaustion mid-paper; agent loses track of earlier sections; inconsistent LaTeX macros between ideas | Partition into 4–6 parts; each agent handles a disjoint slice of 8–10 ideas |
| Including `\documentclass` in all part files | Each part file was a standalone compilable document | Assembly produced multiple `\documentclass` commands in paper.tex, which pdflatex rejects | Only part1 gets the full preamble; parts 2..N start from their first `\subsection` |
| Using `\citeauthor{}` without natbib | Agent wrote `\citeauthor{key}~\cite{key}` patterns | Plain BibTeX does not define `\citeauthor`; pdflatex errors on every citation of this form | Replace all `\citeauthor{X}~\cite{X}` patterns with `\cite{X}` using Python regex before compiling |
| Ignoring missing bib keys until final compile | Compiled twice before checking for undefined citations | With 342 missing keys, the paper generated 342 "citation undefined" warnings and suppressed all reference hyperlinks | After first compile, immediately extract missing keys and generate stubs; never let missing keys persist into final build |
| Manual Unicode → LaTeX replacement | Fixed Unicode chars one at a time when pdflatex reported them | Slow; new occurrences appear as new ideas are added; easy to miss low-frequency chars like ± or ≈ | Run the full Python replacement dict once before the first compile; maintain the dict as a canonical artifact |
| Trusting column spec across agents | Let each agent write its own table column spec | Agents independently chose `{llp{7cm}}` vs `{lll}` vs `{l l p{6.5cm}}` for equivalent tables; assembled paper had mismatched specs at row boundaries | Provide agents with a standard table macro or template column spec; add a post-assembly tabular audit step |
| Not anchoring awk at `\subsection` | Used `NR > 1` to skip the first line of each part file | Part files had multiple preamble lines before the first `\subsection` — all were included | Use `awk '/^\\subsection/{found=1} found{print}'` to skip everything before the first section marker |
| Trying to fix bib collisions by hand | Two agents independently invented the same cite key for different papers | Merged bib file had duplicate `@article{foo2024,...}` entries; BibTeX silently used first and dropped second | Each agent should use a namespaced cite-key prefix (e.g., part1_foo2024, part2_foo2024) or agree on cite keys from a shared reference list before writing |
| Using `\verb\|...\|` for research doc pointers | Replaced `\texttt{research_X_Y.md}` with `\verb\|research_X_Y.md\|` to avoid underscore escaping | `\verb` cannot be used inside `\textit{}` — "\\verb ended by end of line" error | Use `\texttt{research\_X\_Y.md}` with explicitly escaped underscores; Python `str.replace('_', '\\_')` works |
| Python str.replace with raw string double-escape | Used `r'\_'` in replace call to escape underscores, but multiple agent passes can double-escape to `\\_` | `\\_` renders as a literal backslash followed by underscore in LaTeX, not an escaped underscore | Check actual file bytes (`cat -A`) to distinguish `\_` from `\\_`; fix with `content.replace('\\\\_', '\\_')` |
| Fixing bib duplicates without clearing .aux | Removed duplicate uppercase entries from .bib then ran bibtex | .aux still referenced uppercase keys from previous pdflatex run → same "Case mismatch" errors | Always `rm paper.aux paper.bbl paper.blg` before the clean rebuild cycle after bib changes |
| Replacing verdict codes globally | Used sed to replace all `PURSUE` → `high-priority` across entire paper | Replaced the Future Work section headings too, making the section incoherent | Restrict verdict replacement to body text only; Future Work section headings/definition list must keep PURSUE/INVESTIGATE/DEPRIORITIZE as defined terms |

## Results & Parameters

### Verified Assembly (2026-04-14)

| Parameter | Value |
|-----------|-------|
| Source parts | 4 (part1.tex through part4.tex) |
| Total ideas | 38 (34 original + 4 new) |
| Final paper size | 3,320 lines, ~272 KB |
| Final page count | 102 pages |
| BibTeX entries | 395 (53 real + 342 stubs) |
| LaTeX errors | 0 |
| Unresolved references | 0 |
| Unicode chars replaced | ~40 distinct characters |
| Compile runs | 3 (pdflatex×1 + bibtex + pdflatex×2) |

### Verified Citation and Verdict Cleanup (2026-04-14)

| Parameter | Value |
|-----------|-------|
| arXiv hrefs removed | All (grep -c 'arxiv.org' paper.tex → 0) |
| Cite keys preserved | Unchanged count |
| Verdict codes consolidated | All body occurrences → Future Work section only |
| Bib duplicates removed | Uppercase agent-generated stubs removed; lowercase originals kept |
| Clean rebuild | rm paper.aux paper.bbl paper.blg → pdflatex → bibtex → pdflatex → pdflatex |
| Final LaTeX errors | 0 |

### Assembly Command (copy-paste)

```bash
# Given: part1.tex (lines 1-717 are preamble+section1-2), part2.tex, part3.tex, part4.tex
head -717 part1.tex > paper.tex
printf '\n\\section{Detailed Analyses of Candidate Mechanisms}\n\\label{sec:analyses}\n' >> paper.tex
awk '/^\\subsection/{found=1} found{print}' part2.tex >> paper.tex
awk '/^\\subsection/{found=1} found{print}' part3.tex >> paper.tex
cat part4.tex >> paper.tex
wc -l paper.tex  # sanity check
```

### Stub BibTeX Generator (copy-paste)

```python
import re, pathlib

log = pathlib.Path("paper.log").read_text()
bib = pathlib.Path("references.bib").read_text()
existing_keys = set(re.findall(r'@\w+\{([^,]+),', bib))
missing = set(re.findall(r"Citation '([^']+)' on page", log)) - existing_keys

stubs = []
for key in sorted(missing):
    stubs.append(f"@misc{{{key},\n  title={{STUB: {key}}},\n  author={{Unknown}},\n  year={{2024}},\n  note={{Auto-generated stub. Replace with real entry.}}\n}}\n")

with open("references.bib", "a") as f:
    f.write("\n" + "\n".join(stubs))
print(f"Added {len(stubs)} stub entries (total keys now {len(existing_keys)+len(stubs)})")
```

### Clean Bib Rebuild Sequence (copy-paste)

```bash
rm -f paper.aux paper.bbl paper.blg
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
# Target: "Output written on paper.pdf (N pages, ...)" with zero ! errors
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas | 38-idea AI architecture research paper | 4 parallel agents, head+awk assembly, 342 stubs, 3 compile passes, 102 pages final |
| ArchIdeas (post-assembly cleanup) | Same paper, post-assembly citation and verdict cleanup pass | Removed all arXiv hrefs, consolidated PURSUE/INVESTIGATE/DEPRIORITIZE into Future Work section, fixed \texttt{} underscore escaping, deduplicated bib entries — paper built cleanly with 0 errors after cleanup |
