---
name: "Skill: Adding Architecture Sections to LaTeX Academic Papers"
description: "Add architecture sections to academic LaTeX papers with TikZ diagrams, including fixing common TikZ syntax errors and managing arxiv builds"
category: documentation
date: 2026-02-07
user-invocable: false
---
# Skill: Adding Architecture Sections to LaTeX Academic Papers

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-07 |
| **Project** | ProjectScylla |
| **Objective** | Add comprehensive Architecture section to academic paper with TikZ diagrams and fix LaTeX formatting issues |
| **Outcome** | ✅ Success - 32-page paper with clean architecture section and 7 working figures |

## When to Use This Skill

Use this skill when:
- Adding an Architecture section to an academic LaTeX paper
- Creating TikZ diagrams for system architecture visualization
- Fixing TikZ compilation errors (especially "missing \item" errors)
- Converting complex DAG diagrams to simpler stacked layouts
- Managing dual builds (paper.tex and arxiv main.tex)
- Adding cross-references to tables and figures in LaTeX
- Fixing long path/text overflow issues in LaTeX

## Verified Workflow

### 1. Add TikZ Package Imports

Add to preamble after hyperref package:

```latex
% ===== Diagrams =====
\usepackage{tikz}
\usetikzlibrary{positioning, arrows.meta, shapes.geometric, fit, backgrounds}
```

### 2. Create TikZ Diagrams with Correct Syntax

**CRITICAL:** When using font size commands in multi-line nodes, wrap them in braces:

```latex
% WRONG - causes "missing \item" error
\node[component] (runner) at (0,0)
  {E2E Runner \\ \tiny (Experiment Orchestration)};

% CORRECT - wraps font command in braces
\node[component, align=center] (runner) at (0,0)
  {E2E Runner \\ {\tiny (Experiment Orchestration)}};
```

**Always add `align=center` to node styles** when using multi-line text:

```latex
component/.style={draw, rectangle, rounded corners, minimum width=3cm,
  minimum height=1cm, text centered, font=\small, align=center}
```

### 3. Prefer Stacked Block Diagrams Over DAG Layouts

For system architecture, use vertical stacks instead of complex DAGs:

```latex
\begin{tikzpicture}[
  layer/.style={draw, rectangle, rounded corners, minimum width=10cm,
    minimum height=1.2cm, text centered, font=\small, align=center},
  arrow/.style={-Stealth, thick}
]

% Layer 1
\node[layer, fill=blue!10] (runner) at (0,0)
  {\textbf{E2E Runner} \\ {\scriptsize Experiment Orchestration}};

% Layer 2
\node[layer, fill=blue!10, below=0.4cm of runner] (workspace)
  {\textbf{Workspace Manager} \\ {\scriptsize Git Worktrees}};

% Arrows showing data flow
\draw[arrow] (runner.south) -- (workspace.north);
```

**Benefits:**
- All blocks same width → perfect alignment
- Simple top-to-bottom flow → easier to read
- No diagonal arrows → cleaner layout

### 4. Add Proper Cross-References

For every table, add:
1. Label in table: `\label{tab:table-name}`
2. Reference in text: "as shown in Table~\ref{tab:table-name}"

```latex
\subsubsection{Agent Complexity Axis}

The agent complexity axis spans from simple single-agent configurations
to hierarchical multi-agent systems, as shown in Table~\ref{tab:agent-complexity}.

\begin{table}[htbp]
\centering
\caption{Agent Complexity Axis}
\label{tab:agent-complexity}
...
```

### 5. Fix Long Path Overflow with Lists

When paths overflow page margins, convert to bulleted lists:

```latex
% BEFORE (overflows)
...injects files (CLAUDE.md from config/tiers/TN/subtest-NN/CLAUDE.md,
skills from config/tiers/TN/subtest-NN/.claude-plugin/skills, ...)

% AFTER (clean list)
...injects tier-specific configuration files via symlinks:

\begin{itemize}
\item CLAUDE.md from \texttt{config/tiers/TN/subtest-NN/CLAUDE.md}
\item Skills from \texttt{config/tiers/TN/subtest-NN/.claude-plugin/skills}
\item Agents from \texttt{config/tiers/TN/subtest-NN/.claude/agents}
\end{itemize}
```

### 6. Manage Dual Build System

For projects with both `paper.tex` (source) and `main.tex` (arxiv):

```bash
# 1. Edit paper.tex (source of truth)

# 2. Transform to arxiv version
python3 scripts/build_arxiv_paper.py

# 3. Compile both versions
cd docs && pdflatex -interaction=nonstopmode paper.tex
cd docs/paper-dryrun-arxiv && pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

### 7. Verify Compilation

```bash
# Check for errors
grep -E "(Error|Warning)" paper.log

# Verify page count
pdfinfo paper.pdf | grep Pages

# Check cross-references resolved (should return nothing)
grep "??" paper.log
```

## Failed Attempts (Lessons Learned)
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Failed: TikZ Font Commands Without Braces

**What we tried:** Direct use of `\tiny`, `\scriptsize` after `\\` in node text

```latex
\node[component] (runner) at (0,0)
  {E2E Runner \\ \tiny (Experiment Orchestration)};
```

**Error:**
```
! LaTeX Error: Something's wrong--perhaps a missing \item.
l.577   {E2E Runner \\
```

**Why it failed:** LaTeX interprets `\tiny` as starting a new paragraph/item when following `\\` without grouping.

**Solution:** Wrap font commands in braces: `{\tiny ...}`

### ❌ Failed: Complex DAG Architecture Diagram

**What we tried:** Multi-column DAG with branching arrows and different box widths

```latex
% Workspace, Tier, Checkpoint at different positions
\node[component, below left=1.5cm and 2cm of runner] (workspace) ...
\node[component, below=1.5cm of runner] (tier) ...
\node[component, below right=1.5cm and 2cm of runner] (checkpoint) ...

% Multiple arrows converging
\draw[arrow] (workspace.south) -- (adapter_group.north);
\draw[arrow] (tier.south) -- (adapter_group.north);
```

**Why it failed:**
- Boxes misaligned (different widths: 3cm, 4cm, 8cm)
- Diagonal arrows looked messy
- Hard to follow data flow

**Solution:** Convert to vertical stack with uniform 10cm width and simple top-to-bottom arrows.

### ❌ Failed: Keeping All Figures

**What we tried:** Including Cost-of-Pass and Latency breakdown figures

**Why it failed:**
- CoP figure: Not rendering properly
- Latency figure: Bars growing outside bounding box (scale issue)

**Solution:** Remove problematic figures, keep data in tables or enumerated lists instead. Tables are often clearer for small datasets anyway.

## Results & Parameters

### Architecture Section Structure

```
Section 7: Framework Architecture
├── 7.1 System Overview (stacked block diagram)
├── 7.2 Adapter Layer (text description, removed table)
├── 7.3 Execution Pipeline (horizontal flow diagram)
├── 7.4 Tier Dependencies and Parallelism (dependency graph)
└── 7.5 Checkpoint and Reproducibility (text only)
```

### TikZ Style Templates

**Stacked Layer Diagram:**
```latex
layer/.style={draw, rectangle, rounded corners, minimum width=10cm,
  minimum height=1.2cm, text centered, font=\small, align=center}
```

**Horizontal Flow Diagram:**
```latex
block/.style={draw, rectangle, rounded corners, text width=2.5cm,
  minimum height=1.5cm, text centered, font=\small, align=center}
```

**Dependency Graph:**
```latex
tier/.style={draw, rectangle, rounded corners, minimum width=1.2cm,
  minimum height=0.8cm, text centered, font=\small}
```

### Final Metrics

- **Page count:** 32 pages (down from 34 after removing 2 figures)
- **Figures:** 7 total (3 TikZ diagrams + 4 imported PDFs)
- **Tables:** 13 total (all properly cross-referenced)
- **Compilation:** Clean (0 errors, only font warnings)

## Common Pitfalls to Avoid

1. **Never use bare `\tiny`, `\scriptsize`, etc. after `\\`** in TikZ nodes - always wrap in `{}`
2. **Always add `align=center`** to node styles when using multi-line text
3. **Test compilation after each major change** - don't wait until the end
4. **Keep diagram complexity low** - simpler layouts are more readable
5. **Remove figures that don't render well** - tables are often better for small datasets
6. **Always run both builds** (paper.tex and main.tex) to catch arxiv-specific issues
7. **Add labels and cross-references immediately** when creating tables/figures

## References

- TikZ documentation: https://tikz.net/
- LaTeX cross-referencing: `\label{}` and `\ref{}`
- Arxiv submission guide: https://arxiv.org/help/submit_tex

## Files Modified

- `/home/mvillmow/ProjectScylla/docs/paper.tex` (source file)
- `/home/mvillmow/ProjectScylla/docs/paper-dryrun-arxiv/main.tex` (generated via build script)
- Build script: `/home/mvillmow/ProjectScylla/scripts/build_arxiv_paper.py`

## Related Skills

- `tikz-diagrams` - General TikZ diagram creation
- `academic-writing` - Academic paper formatting best practices
- `latex-debugging` - Debugging LaTeX compilation errors
