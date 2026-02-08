# Raw Session Notes: Adding Architecture Section to Paper

## Session Context

- **Date:** 2026-02-07
- **Branch:** skill/documentation/paper-final-review
- **Initial State:** Paper had no architecture section explaining how Scylla framework works as software
- **Publication Review:** Identified missing architecture section as major gap (CONDITIONAL GO rating)

## Detailed Implementation Log

### Phase 1: Initial Architecture Section Addition

**Plan Requirements:**
- Add ~250-300 lines of LaTeX
- Include 3 TikZ diagrams: system overview, execution pipeline, tier dependencies
- Insert between Methodology (Section 3) and Test Metrics (Section 4)
- Update cross-references

**Initial TikZ Code (BROKEN):**
```latex
\node[component, fill=blue!10, minimum width=8cm] (runner) at (0,0)
  {E2E Runner \\ \tiny (Experiment Orchestration)};
```

**Error Encountered:**
```
! LaTeX Error: Something's wrong--perhaps a missing \item.
l.577   {E2E Runner \\
```

**Root Cause:** Font size commands (`\tiny`, `\scriptsize`) after `\\` without braces cause LaTeX to interpret them as paragraph/item starts.

### Phase 2: TikZ Syntax Fixes

**Fix Applied:**
1. Wrapped all font commands in braces: `{\tiny ...}`
2. Added `align=center` to all node styles
3. Applied to all 3 TikZ diagrams

**Successful Compilation:**
- paper.pdf: 34 pages, 0 errors
- main.pdf (arxiv): 34 pages, 0 errors

### Phase 3: Removing Unimplemented Adapter References

**User Request:** Remove references to Cline, OpenAI Codex, OpenCode adapters (not yet implemented)

**Changes:**
1. Removed Table 10 (Concrete Adapter Implementations)
2. Simplified system architecture diagram: removed 3 subcomponents, kept only Claude Code
3. Updated text to say "enables future cross-vendor comparisons" instead of "implemented"
4. Updated figure caption to "(currently Claude Code)"

**Result:**
- Page count: 33 pages (down from 34)
- Cleaner, more accurate representation

### Phase 4: Diagram Redesign (DAG → Stacked Layers)

**User Request:** System architecture diagram rendering poorly, convert DAG to stacked blocks

**Original Design Issues:**
- Complex branching (E2E Runner → 3 managers → Adapter Layer)
- Different box widths (3cm, 4cm, 8cm)
- Diagonal arrows
- Misalignment

**New Design (Stacked):**
```latex
% 7 uniform layers, each 10cm wide, 0.4cm spacing
Layer 1: E2E Runner
Layer 2: Workspace Manager
Layer 3: Tier Manager
Layer 4: Checkpoint System
Layer 5: Adapter Layer
Layer 6: Judge Pipeline
Layer 7: Analysis Pipeline
```

**Benefits:**
- Perfect vertical alignment
- Simple top-to-bottom flow
- Uniform width (10cm)
- Professional appearance

### Phase 5: Table Cross-Reference Fixes

**Issues Found:**
- Section 3.2.1 (Agent Complexity): No reference to table
- Section 3.2.2 (Prompt Complexity): No reference to table
- Section 3.2.3 (Skill Complexity): No reference to table

**Fix Pattern:**
```latex
% Add to intro text
"as shown in Table~\ref{tab:table-name}"

% Add label to table
\label{tab:table-name}
```

### Phase 6: Figure Removal

**Figures Removed:**
1. **fig06_cop_by_tier.pdf** - Cost-of-Pass chart not rendering properly
2. **fig13_latency.pdf** - Latency bars growing outside bounding box

**Replacement Strategy:**
- CoP data: Kept enumerated list format (clearer for 7 data points)
- Latency data: Kept Table~\ref{tab:latency-breakdown} with all metrics

**Result:**
- Page count: 32 pages (down from 33)
- All remaining figures render correctly

### Phase 7: Long Path Overflow Fix

**Issue:** Long paths in Step 1 description running off page margin

**Original (Broken):**
```
...injects files (CLAUDE.md from config/tiers/TN/subtest-NN/CLAUDE.md,
skills from config/tiers/TN/subtest-NN/.claude-plugin/skills, agents
from config/tiers/TN/subtest-NN/.claude/agents), and generates...
```

**Fix (Bulleted List):**
```latex
...injects tier-specific configuration files via symlinks:

\begin{itemize}
\item CLAUDE.md from \texttt{config/tiers/TN/subtest-NN/CLAUDE.md}
\item Skills from \texttt{config/tiers/TN/subtest-NN/.claude-plugin/skills}
\item Agents from \texttt{config/tiers/TN/subtest-NN/.claude/agents}
\item Generates a \texttt{replay.sh} script for manual reproduction
\end{itemize}
```

## Build Process Notes

### Dual Build System

ProjectScylla uses two LaTeX files:
1. **paper.tex** - Source of truth (manually edited)
2. **main.tex** - Arxiv submission (generated from paper.tex)

**Build Script:** `scripts/build_arxiv_paper.py`

**Transformations Applied:**
- Adds `\pdfoutput=1` directive (arxiv requirement)
- Fixes relative paths (removes `docs/paper-dryrun/` prefixes)
- Fixes inline figure references
- Removes duplicate table includes

**Workflow:**
```bash
# 1. Edit paper.tex
# 2. Run transformation
python3 scripts/build_arxiv_paper.py
# 3. Compile both
cd docs && pdflatex paper.tex
cd docs/paper-dryrun-arxiv && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## TikZ Pattern Library

### Pattern 1: Stacked Layer Architecture

```latex
\begin{tikzpicture}[
  layer/.style={draw, rectangle, rounded corners, minimum width=10cm,
    minimum height=1.2cm, text centered, font=\small, align=center},
  arrow/.style={-Stealth, thick}
]

\node[layer, fill=blue!10] (layer1) at (0,0)
  {\textbf{Layer Title} \\ {\scriptsize Description}};

\node[layer, fill=blue!10, below=0.4cm of layer1] (layer2)
  {\textbf{Layer Title} \\ {\scriptsize Description}};

\draw[arrow] (layer1.south) -- (layer2.north);
```

**Use for:** System architecture, data pipelines, layered designs

### Pattern 2: Horizontal Flow Pipeline

```latex
\begin{tikzpicture}[
  block/.style={draw, rectangle, rounded corners, text width=2.5cm,
    minimum height=1.5cm, text centered, font=\small, align=center},
  arrow/.style={-Stealth, thick}
]

\node[block, fill=blue!10] (step1) at (0,0)
  {\textbf{Step 1} \\ \vspace{2mm} {\scriptsize Details \\ More details}};

\node[block, fill=green!10, right=1.2cm of step1] (step2)
  {\textbf{Step 2} \\ \vspace{2mm} {\scriptsize Details}};

\draw[arrow] (step1) -- (step2);
```

**Use for:** Process flows, pipelines, sequential workflows

### Pattern 3: Dependency Graph

```latex
\begin{tikzpicture}[
  tier/.style={draw, rectangle, rounded corners, minimum width=1.2cm,
    minimum height=0.8cm, text centered, font=\small},
  arrow/.style={-Stealth, thick},
  phase/.style={draw, dashed, rounded corners, inner sep=8pt, font=\scriptsize}
]

\node[tier, fill=blue!10] (t0) at (0,0) {T0};
\node[tier, fill=blue!10, below=0.3cm of t0] (t1) {T1};

\node[tier, fill=green!10] (t5) at (4,-0.5) {T5};

\draw[arrow] (t0.east) -- (t5.west);
\draw[arrow] (t1.east) -- (t5.west);

\node[phase, fit=(t0)(t1), label=above:\textbf{Phase 1}] {};
```

**Use for:** Dependencies, relationships, graph structures

## Compilation Verification Commands

```bash
# Check for errors
grep -E "(Error|Warning)" paper.log | head -20

# Check for unresolved references
grep "??" paper.log

# Verify sections count
grep -c "\\\\section" paper.tex

# Check page count
pdfinfo paper.pdf | grep Pages

# Verify tikz package loaded
grep -n "usepackage{tikz}" paper.tex
```

## Metrics

### Before Architecture Section
- Pages: 29
- Sections: 14
- Figures: 9
- Tables: 10

### After All Changes
- Pages: 32
- Sections: 15 (added Section 7: Framework Architecture)
- Figures: 7 (removed 2 problematic figures)
- Tables: 13 (removed 1 adapter table, all now properly cross-referenced)
- Subsections in Architecture: 5 (System Overview, Adapter Layer, Execution Pipeline, Tier Dependencies, Checkpoint)

### TikZ Diagrams Added
1. **System Overview** - 7-layer stacked architecture (10cm × 1.2cm each)
2. **Execution Pipeline** - 5-step horizontal flow (2.5cm width each)
3. **Tier Dependencies** - Dependency graph showing T0-T6 relationships

## Key Learnings

1. **TikZ font commands must be grouped** - `{\tiny ...}` not `\tiny ...`
2. **Simpler diagrams are better** - Stacked layers beat complex DAGs
3. **Tables beat broken figures** - Don't force visualizations that don't work
4. **Always cross-reference tables** - Professional academic writing standard
5. **Test both builds** - paper.tex and arxiv main.tex can have different issues
6. **Use lists for long paths** - Prevents margin overflow
7. **Remove unimplemented features** - Accuracy over aspiration in academic papers

## Tools Used

- LaTeX packages: `tikz`, `tabularx`, `booktabs`, `hyperref`
- TikZ libraries: `positioning`, `arrows.meta`, `shapes.geometric`, `fit`, `backgrounds`
- Build tools: `pdflatex`, `bibtex`, `pdfinfo`
- Python: `build_arxiv_paper.py` transformation script

## Follow-up Items

- [ ] Fix Python figure generation for CoP and Latency charts (user mentioned separately)
- [ ] Consider implementing Cline/Codex/OpenCode adapters to enable table re-insertion
- [ ] Add more architectural detail if reviewers request it
- [ ] Consider converting remaining PDF figures to TikZ for consistency
