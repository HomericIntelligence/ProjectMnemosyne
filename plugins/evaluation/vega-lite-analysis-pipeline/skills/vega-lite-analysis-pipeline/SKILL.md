---
name: "Skill: Vega-Lite Analysis Pipeline"
description: "Build comprehensive analysis pipelines with text-based Vega-Lite figures and statistical tables for research papers"
category: evaluation
date: 2026-01-30
user-invocable: false
---
# Skill: Vega-Lite Analysis Pipeline

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-30 |
| **Project** | ProjectScylla |
| **Objective** | Build a complete analysis pipeline for experiment results with text-based figures and statistical tables |
| **Outcome** | ✅ Success - 15 figures + 7 tables, all outputs text-based and version-controllable |
| **PR** | #213 (merged) |
| **LOC Added** | 6,229 lines |

---

## When to Use This Skill

Use this approach when you need to:

1. **Generate publication-quality figures** for research papers
   - Figures must be version-controllable (text, not binary)
   - Need both interactive viewing and paper rendering (PNG/PDF/SVG)
   - Want consistent styling across all visualizations

2. **Create statistical analysis pipelines** for experiment data
   - Multiple data formats (runs, judges, criteria, subtests)
   - Complex hierarchical data structures (experiments → tiers → subtests → runs)
   - Need comprehensive statistical tests (bootstrap CI, Mann-Whitney U, etc.)

3. **Avoid gitignore conflicts with generated outputs**
   - Figures and tables are generated at runtime, not committed
   - Raw data stays portable (CSV format)
   - Specs are text (JSON), not images

4. **Support multiple output consumers**
   - Paper authors (need LaTeX tables, PDF figures)
   - Data analysts (need CSV exports)
   - Web viewers (need interactive Vega-Lite specs)
   - Automation (need consistent APIs)

---

## Verified Workflow

### 1. Architecture: Text-Based Outputs Strategy

**Key Decision**: Use **Vega-Lite JSON specifications** as the primary figure format.

**Rationale**:
- ✅ Text-based (JSON) → version-controllable
- ✅ Portable → works in Vega Editor, Python, R, web browsers
- ✅ Self-contained → data can be inlined or separate CSV
- ✅ Multi-format rendering → PNG/PDF/SVG via `vl-convert`
- ✅ Interactive → tooltips, zoom, pan in web viewers

**Implementation**:
```python
# Use altair (Python Vega-Lite API) to build specs programmatically
import altair as alt

chart = alt.Chart(data).mark_bar().encode(
    x='tier:O',
    y='pass_rate:Q',
    color='model:N'
)

# Save as JSON spec
chart.save("figure.vl.json")

# Also save data separately
data.to_csv("figure.csv")

# Optional: render to PNG/PDF
chart.save("figure.png", scale_factor=2.0)  # 300 DPI
chart.save("figure.pdf")
```

**Result**: All 15 figures saved as `.vl.json` + `.csv`, with optional PNG/PDF rendering.

---

### 2. Data Loading: Handle Corrupted/Incomplete Runs Gracefully

**Challenge**: Real experiment data has failures (missing files, corrupted JSON, incomplete judges).

**Solution**: Try-except with informative warnings, skip bad runs, continue processing.

```python
def load_run(run_dir: Path, experiment: str, tier: str, subtest: str) -> RunData:
    try:
        # Load run_result.json
        with (run_dir / "run_result.json").open() as f:
            result = json.load(f)

        # Load per-judge evaluations
        judges = []
        judge_dir = run_dir / "judge"
        if judge_dir.exists():
            for judge_num in [1, 2, 3]:
                judge_path = judge_dir / f"judge_0{judge_num}" / "judgment.json"
                if judge_path.exists():
                    judges.append(load_judgment(judge_path, judge_num))

        return RunData(...)
    except Exception as e:
        print(f"Warning: Failed to load {run_dir}: {e}")
        # Return None or raise to skip this run
```

**Result**: 97.4% load success rate (2,238 of 2,298 runs loaded), graceful degradation.

---

### 3. DataFrame Architecture: Four Core DataFrames

**Pattern**: Build hierarchical views of the same data for different analysis levels.

```python
# 1. Runs DataFrame (one row per run)
runs_df = build_runs_df(experiments)  # 2,238 rows
# Columns: experiment, agent_model, tier, subtest, run_number, score, passed, cost, tokens, etc.

# 2. Judges DataFrame (one row per judge evaluation)
judges_df = build_judges_df(experiments)  # 6,216 rows (3 judges × 2,238 runs)
# Columns: (all run columns) + judge_model, judge_number, judge_score, judge_passed, etc.

# 3. Criteria DataFrame (one row per criterion score)
criteria_df = build_criteria_df(experiments)  # 30,929 rows (5 criteria × 6,216 judges)
# Columns: (all judge columns) + criterion, criterion_score, criterion_achieved, etc.

# 4. Subtests DataFrame (pre-aggregated)
subtests_df = build_subtests_df(runs_df)  # 226 rows
# Columns: experiment, tier, subtest, pass_rate, mean_score, consistency, cop, etc.
```

**Why This Works**:
- ✅ Different levels of granularity for different analyses
- ✅ Easy filtering: `runs_df[runs_df['tier'] == 'T0']`
- ✅ Aggregation helpers reuse the same base data
- ✅ CSV export gives analysts full flexibility

---

### 4. Statistical Functions: Non-Parametric by Default

**Observation**: Scores are bounded [0, 1] and often bimodal → parametric tests inappropriate.

**Solution**: Use non-parametric tests throughout.

```python
# Bootstrap 95% CI (no distribution assumptions)
mean, ci_low, ci_high = bootstrap_ci(data, n_resamples=10000)

# Mann-Whitney U (non-parametric significance test)
u_stat, pvalue = mann_whitney_u(group1, group2)

# Cliff's delta (non-parametric effect size)
delta = cliffs_delta(group1, group2)
# Interpretation: |δ| < 0.147 negligible, < 0.33 small, < 0.474 medium, ≥0.474 large

# Krippendorff's alpha (inter-rater reliability, ordinal scale)
alpha = krippendorff_alpha(ratings_matrix, level="ordinal")
```

**Result**: Robust statistics appropriate for bounded, potentially non-normal data.

---

### 5. Table Generation: Markdown + LaTeX Dual Output

**Pattern**: Generate both formats from the same data, single source of truth.

```python
def table01_tier_summary(runs_df: pd.DataFrame) -> tuple[str, str]:
    # Compute statistics
    stats = compute_tier_stats(runs_df)

    # Generate Markdown
    md_lines = ["# Table 1: Tier Summary", ""]
    md_lines.append("| Model | Tier | Pass Rate | ... |")
    md_lines.append("|-------|------|-----------|-----|")
    for _, row in stats.iterrows():
        md_lines.append(f"| {row['Model']} | {row['Tier']} | {row['Pass Rate']:.3f} | ... |")
    markdown = "\n".join(md_lines)

    # Generate LaTeX
    latex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Tier Summary Statistics}",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Model & Tier & Pass Rate & ... \\",
        r"\midrule",
    ]
    for _, row in stats.iterrows():
        latex_lines.append(f"{row['Model']} & {row['Tier']} & {row['Pass Rate']:.3f} & ... \\\\")
    latex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    latex = "\n".join(latex_lines)

    return markdown, latex
```

**Result**: 7 tables × 2 formats = 14 files, all generated from same data.

---

### 6. Master Orchestrator Script Pattern

**Structure**: Separate scripts for each step, master script calls them all.

```
scripts/
├── export_data.py          # Step 1: Export CSVs
├── generate_figures.py     # Step 2: Generate 15 figures
├── generate_tables.py      # Step 3: Generate 7 tables
└── generate_all_results.py # Master: Runs 1→2→3 in sequence
```

**Master script pattern**:
```python
def run_script(script_name: str, args: list[str], description: str) -> bool:
    cmd = ["pixi", "run", "-e", "analysis", "python", script_name, *args]
    result = subprocess.run(cmd, check=True)
    return result.returncode == 0

# Run in sequence
success = True
if not args.skip_data:
    success = run_script("scripts/export_data.py", [...], "Step 1/3: Export data")
if not args.skip_figures and success:
    success = run_script("scripts/generate_figures.py", [...], "Step 2/3: Figures")
if not args.skip_tables and success:
    success = run_script("scripts/generate_tables.py", [...], "Step 3/3: Tables")
```

**Benefits**:
- ✅ Can run individual steps for debugging
- ✅ Can skip steps (e.g., `--skip-data` if CSVs already exported)
- ✅ Fail-fast: stops on first error
- ✅ Clear progress reporting

---

### 7. Gitignore Strategy: Exclude All Generated Outputs

**Pattern**: Generated files (CSV, JSON, images, tables) go in `.gitignore`.

```gitignore
# Analysis pipeline outputs (generated at runtime)
docs/data/*.csv
docs/data/*.json
docs/figures/*.vl.json
docs/figures/*.csv
docs/figures/*.png
docs/figures/*.pdf
docs/figures/*.svg
docs/tables/*.md
docs/tables/*.tex
```

**Rationale**:
- ✅ Generated files are runtime artifacts, not source code
- ✅ Avoids git bloat (2,238 rows of CSV would be huge)
- ✅ Forces reproducibility (can't commit stale outputs)
- ✅ Users generate fresh outputs from latest data

**Important**: Remove any previously committed generated files:
```bash
git rm --cached -r docs/data/ docs/figures/ docs/tables/
```

---

### 8. Color Palette: Consistent Across All Figures

**Pattern**: Define color palette once, reuse everywhere.

```python
# figures/__init__.py
COLORS = {
    "models": {
        "Sonnet 4.5": "#4C78A8",  # Blue
        "Haiku 4.5": "#E45756",   # Red
    },
    "tiers": {
        "T0": "#66c2a5", "T1": "#fc8d62", "T2": "#8da0cb",
        "T3": "#e78ac3", "T4": "#a6d854", "T5": "#ffd92f", "T6": "#e5c494"
    },
    "grades": {
        "S": "#FFD700", "A": "#2ecc71", "B": "#3498db",
        "C": "#f39c12", "D": "#e67e22", "F": "#e74c3c"
    },
}

# Usage in figures
alt.Color("model:N", scale=alt.Scale(
    domain=list(COLORS["models"].keys()),
    range=list(COLORS["models"].values())
))
```

**Result**: All 15 figures use the same colors for the same entities → visual consistency.

---

### 9. Publication Theme: Serif Fonts, Clean Axes

**Pattern**: Register a custom Altair theme once, applies to all charts.

```python
def apply_publication_theme() -> None:
    theme = {
        "config": {
            "font": "serif",
            "axis": {
                "labelFontSize": 11,
                "titleFontSize": 13,
                "gridColor": "#e0e0e0",
            },
            "legend": {
                "labelFontSize": 11,
                "titleFontSize": 12,
            },
            "title": {
                "fontSize": 14,
                "anchor": "start",
            },
            "view": {"stroke": None},
        }
    }
    alt.themes.register("publication", lambda: theme)
    alt.themes.enable("publication")

# Call once in spec_builder.py
apply_publication_theme()
```

**Result**: All figures have serif fonts (academic papers), clean axes, no border.

---

## Failed Attempts

### ❌ Attempt 1: Matplotlib as Primary Figure Format

**What We Tried**: Generate PNG images directly using matplotlib, commit to git.

**Why It Failed**:
- ❌ Binary PNG files in git → huge repository bloat
- ❌ Not version-controllable (can't see diffs)
- ❌ Hard to iterate (need to regenerate all images after small change)
- ❌ Not interactive (static images only)

**Lesson**: Use text-based formats (Vega-Lite JSON) as primary, render to images optionally.

---

### ❌ Attempt 2: Inline Data in Vega-Lite Specs (Too Large)

**What We Tried**: Put all data directly inside `.vl.json` files.

**Why It Failed**:
- ❌ Some figures have 2,238 rows → 500KB+ JSON files
- ❌ Hard to inspect data separately from spec
- ❌ Can't easily use data in other tools (R, Excel)

**Solution**: Save data as separate `.csv` files, reference from spec OR inline for small datasets.

```python
# For small data: inline
chart = alt.Chart(data)  # Data goes inside .vl.json

# For large data: separate CSV
chart = alt.Chart("figure.csv")  # Reference external file
data.to_csv(output_dir / f"{name}.csv")
```

**Result**: Each figure has both `.vl.json` (spec) and `.csv` (data) for flexibility.

---

### ❌ Attempt 3: f-string Escaping for Special Characters

**What We Tried**: Use `f"... {row['Cliff\\'s δ']} ..."` in f-strings.

**Why It Failed**:
```python
# SyntaxError: invalid syntax
f"{row['Cliff\\'s δ']:+.3f}"
```

**Solution**: Extract value to variable first.
```python
cliffs_delta_val = row["Cliff's δ"]
f"{cliffs_delta_val:+.3f}"
```

**Lesson**: Don't escape quotes in f-string dictionary keys → extract to variable.

---

### ❌ Attempt 4: Ruff Linting - Docstring Imperative Mood

**What We Tried**: Use "Main entry point." for `main()` docstrings.

**Why It Failed**:
```
D401 First line of docstring should be in imperative mood: "Main entry point."
```

**Solution**: Use imperative mood.
```python
# Bad
def main() -> None:
    """Main entry point."""

# Good
def main() -> None:
    """Run the script to generate results."""
```

**Lesson**: Ruff enforces imperative mood for docstrings (command, not statement).

---

### ❌ Attempt 5: Variable Names - Uppercase Grade Variables

**What We Tried**: Use `grade_S`, `grade_A`, etc. for clarity.

**Why It Failed**:
```
N806 Variable `grade_S` in function should be lowercase
```

**Solution**: Use lowercase with underscores.
```python
# Bad
grade_S = grade_counts.get("S", 0)

# Good
grade_s = grade_counts.get("S", 0)
```

**Lesson**: Ruff enforces snake_case for all variables, even when uppercase seems clearer.

---

### ❌ Attempt 6: Long LaTeX Lines in Tables

**What We Tried**: Single-line LaTeX table headers for readability.

**Why It Failed**:
```
E501 Line too long (121 > 100)
```

**Solution**: Split across multiple lines.
```python
# Bad (121 chars)
r"Model & Tier & Subtests & Pass Rate (95\% CI) & Mean Score ($\pm\sigma$) & Median & Consistency & CoP (\$) \\"

# Good (split)
r"Model & Tier & Subtests & Pass Rate (95\% CI) & "
r"Mean Score ($\pm\sigma$) & Median & Consistency & CoP (\$) \\"
```

**Lesson**: Ruff enforces 100-char line limit even for LaTeX strings.

---

### ❌ Attempt 7: Layer + Facet in Altair (Not Allowed)

**What We Tried**: Combine layered charts (scatter + line) with faceting.

```python
# Failed
chart = (scatter + line).facet(row="judge_y:N", column="judge_x:N")
# Error: Facet charts require data to be specified at the top level
```

**Why It Failed**: Altair doesn't allow faceting on layered charts directly.

**Solution**: Use faceting without layers, or use `repeat` instead of `facet`.

```python
# Good
chart = scatter.facet(row="judge_y:N", column="judge_x:N")
# Skip the diagonal line, or add it in post-processing
```

**Lesson**: Altair has restrictions on combining layers with facets.

---

## Results & Parameters

### Final Output Counts

| Category | Count | Formats |
|----------|-------|---------|
| **Data Files** | 5 | CSV, JSON |
| **Figures** | 15 | `.vl.json` + `.csv` per figure |
| **Tables** | 7 | `.md` + `.tex` per table |
| **Scripts** | 4 | Python executable |
| **Modules** | 13 | Python source |

### Data Statistics

From 2,238 loaded runs:

| Metric | Overall | Sonnet 4.5 | Haiku 4.5 |
|--------|---------|------------|-----------|
| Pass Rate | 83.9% | 94.2% | 73.4% |
| Mean Score | 0.786 | 0.908 | 0.662 |
| Mean Cost/Run | $0.060 | $0.077 | $0.043 |
| Load Success | 97.4% | — | — |

### Dependencies (pyproject.toml)

```toml
[project.optional-dependencies]
analysis = [
    "matplotlib>=3.8",
    "numpy>=1.24",
    "pandas>=2.0",
    "seaborn>=0.13",
    "scipy>=1.11",
    "altair>=5.0",
    "vl-convert-python>=1.0",
]
```

### Pixi Environment

```toml
[feature.analysis.pypi-dependencies]
matplotlib = ">=3.8"
numpy = ">=1.24"
pandas = ">=2.0"
seaborn = ">=0.13"
scipy = ">=1.11"
altair = ">=5.0"
vl-convert-python = ">=1.0"

[environments]
analysis = { features = ["dev", "analysis"], solve-group = "default" }
```

### Usage Commands

```bash
# Install environment
pixi install

# Generate everything
pixi run python scripts/generate_all_results.py

# Generate with PNG/PDF rendering
pixi run python scripts/generate_all_results.py --no-render=false

# Generate specific components
pixi run python scripts/export_data.py       # Data only
pixi run python scripts/generate_figures.py  # Figures only
pixi run python scripts/generate_tables.py   # Tables only

# View outputs
# - Data: docs/data/*.csv (Excel, Python, R)
# - Figures: docs/figures/*.vl.json (Vega Editor: https://vega.github.io/editor/)
# - Tables: docs/tables/*.{md,tex}
```

---

## Key Takeaways

### Architecture Decisions

1. **Text-Based Outputs First**: Use Vega-Lite JSON as primary format, render to images optionally
2. **Four DataFrame Hierarchy**: runs → judges → criteria, plus pre-aggregated subtests
3. **Non-Parametric Statistics**: Bootstrap CI, Mann-Whitney U, Cliff's delta for bounded data
4. **Dual Table Formats**: Generate Markdown + LaTeX from same data
5. **Modular Scripts**: Separate scripts per step, master orchestrator

### Code Quality

1. **Graceful Degradation**: Try-except on data loading, 97.4% success rate
2. **Consistent Styling**: Single color palette, publication theme applied once
3. **Version Control**: Exclude generated files, commit only source code
4. **Linting**: Imperative docstrings, lowercase variables, 100-char lines

### Performance

1. **Load Time**: ~30s to load 2,238 runs with 13,560 JSON files
2. **Figure Generation**: ~60s for all 15 figures (Vega-Lite is fast)
3. **Table Generation**: ~10s for all 7 tables
4. **Total Pipeline**: ~2 minutes for complete analysis

---

## Future Improvements

1. **Parallel Figure Generation**: Use multiprocessing to generate figures in parallel
2. **Incremental Updates**: Only regenerate changed figures/tables
3. **Interactive Dashboard**: Streamlit/Plotly Dash web interface
4. **Automated Narrative**: Generate text snippets for paper sections
5. **Cross-Experiment Comparison**: Load multiple experiment sets, compare

---

## Related Skills

- `experiment-recovery-tools`: Handles failed runs and judge retries
- `parallel-io-executor`: Optimizes parallel I/O operations
- `statistical-analysis`: Comprehensive statistical test library (if exists)

---

## Questions This Skill Answers

1. How do I create version-controllable figures for papers? → Use Vega-Lite JSON
2. How do I handle corrupted experiment data? → Try-except with graceful degradation
3. How do I generate both Markdown and LaTeX tables? → Single function, dual output
4. How do I avoid git bloat from generated files? → Gitignore + separate data/specs
5. How do I ensure visual consistency across figures? → Single color palette + theme
6. How do I support multiple output consumers? → CSV data + Vega-Lite specs + LaTeX tables
7. How do I structure complex analysis pipelines? → Modular scripts + master orchestrator
8. What statistical tests for bounded [0,1] data? → Non-parametric (Mann-Whitney U, bootstrap CI)

---

**Created**: 2026-01-30
**Project**: ProjectScylla
**PR**: #213 (merged)
**Success Rate**: 100% (all outputs generated, linting passed, PR merged)
