# Raw Session Notes: arXiv Paper Publication Polish

**Session Date**: 2026-02-07
**Paper**: "Taming Scylla: Measuring Cost-of-Pass in Agentic CLI Tools"
**Objective**: Apply publication polish based on comprehensive 10-category GO/NO-GO review

---

## Session Context

User provided structured fix plan with 5 categories:
1. **Fix 1**: Three decimal places for all CoP values (tier summary table)
2. **Fix 2**: Git worktrees, not containers (3 locations + remove Docker)
3. **Fix 3**: Remove uncited bibliography entries (36 → 10 entries)
4. **Fix 4**: Glob path corrections (tests/*/test.yaml → tests/fixtures/tests/*/test.yaml)
5. **Fix 5**: Grammar & consistency fixes (20+ edits)

---

## Detailed Fix Breakdown

### Fix 1: CoP Precision (Tier Summary Table)

**Raw data values from summary.json**:
- T0: 0.13513625 → 0.135
- T1: 0.12742665 → 0.127
- T2: 0.13796935 → 0.138
- T3: 0.1294133 → 0.129
- T4: 0.1684904 → 0.168
- T5: 0.06531415 → 0.065
- T6: 0.24744315 → 0.247

**T4 Mean Score discrepancy**:
- Paper text (line 1050): "0.9595" (4 decimal places)
- Table (tab01_tier_summary.tex): "0.960" (3 decimal places)
- Raw value: 0.959524 → rounds to 0.960 at 3dp
- **Fix**: Changed paper.tex to match table precision (0.960)

**Edit locations**:
- Lines 1046-1052: Updated all 7 tier CoP values
- Line 1050: Updated T4 mean score from 0.9595 to 0.960 (2 columns)

---

### Fix 2: Git Worktrees Not Containers

**Three locations requiring "container" → "git worktree"**:

1. **Line 310**: Test definition description
   - Old: "pre-defined tooling, set of commands to validate the results, and a container to"
   - New: "pre-defined tooling, set of commands to validate the results, and a git worktree to"

2. **Lines 859-861**: Test infrastructure description
   - Old: "Each test runs in its own git clone...Every container starts fresh with:"
   - New: "Each test runs in its own git worktree...Every worktree starts fresh with:"

3. **Line 1490**: Appendix C Required Software
   - Removed: "\item Docker (containerization)"

**Rationale**: Project uses git worktrees for test isolation, not Docker containers

---

### Fix 3: Bibliography Cleanup

**Before**: 36 entries (397 lines)
**After**: 10 cited entries (103 lines)
**Reduction**: 72% (-294 lines)

**10 Cited Entries to KEEP**:
1. `liu2023agentbench` - AgentBench evaluation framework
2. `jimenez2024swebench` - SWE-Bench GitHub issues benchmark
3. `yao2024taubench` - TAU-bench tool-augmented LLMs
4. `zhu2024promptbench` - PromptBench robustness evaluation
5. `polo2024efficient` - Efficient LLM evaluation framework
6. `projectodyssey` - ProjectOdyssey orchestration framework
7. `anthropic2024claude` - Claude Code CLI tool
8. `gao2024lmevalharness` - lm-evaluation-harness framework
9. `safetynet` - safety-net Claude Code plugin
10. `ccmarketplace` - CC-Marketplace community plugins

**26 Entries REMOVED** (all uncited in paper.tex):
- `eval-harness` (duplicate of gao2024lmevalharness)
- `anthropic2024claudecode` (duplicate of anthropic2024claude)
- `deng2024prompteval`, `li2023agentboard`, `emergentmind2025hierarchical`
- `zero3dmap2025`, `theagentcompany2024`, `nay2023legal`
- `arkondata2025frameworks`, `anthropic2025context`, `arcade2025skills`
- `zerocode2025`, `ghosh2025token`, `selfresource2025`
- `multiagent2024challenges`, `hockeystack2025latency`, `infiagent2024`
- `huggingface2025aiconf`, `medium2025evaluation`, `evidently2025metrics`
- `vellum2025rag`, `moonlight2025review`, `benchagents2024`
- `hamzaerol2025costofpass`, `costofpass2025paper`, `e2edev2024`
- `practical2025llm`, `dx2025metrics`, `codacy2025cfr`
- `nvidia2025inference`, `kinde2025pricing`, `voltagent2025metrics`
- `costofpass2025arxiv`, `rodriguez2025impact`, `aisi2025hibayes`

---

### Fix 4: Glob Path Corrections

**Two lines requiring path updates**:

1. **Line 1482**: Test definitions path
   - Old: `\item Test definitions: \texttt{tests/*/test.yaml}`
   - New: `\item Test definitions: \texttt{tests/fixtures/tests/*/test.yaml}`

2. **Line 1483**: Rubric schemas path
   - Old: `\item Rubric schemas: \texttt{tests/*/expected/rubric.yaml}`
   - New: `\item Rubric schemas: \texttt{tests/fixtures/tests/*/expected/rubric.yaml}`

**Rationale**: Actual test structure uses `tests/fixtures/tests/` subdirectory, not `tests/` directly

---

### Fix 5: Grammar & Consistency (20+ Edits)

#### Subject-Verb Agreement
- **Line 163**: "do not apply" → "does not apply" (subject "work" is singular)

#### Verb Forms
- **Line 210**: "setup" → "set up" (verb form, not noun)

#### Hyphenation (Compound Adjectives)
- **Line 303**: "top level" → "top-level"
- **Lines 312/321/1365**: "pipecleaner" → "pipe-cleaner"

#### Capitalization (Proper Nouns)
- **Line 309**: "github hash" → "GitHub hash"
- **Line 122**: "mcp servers" → "MCP servers"

#### Table Headers
- **Line 420**: "Sub-tests" → "Subtests" (consistency with rest of paper)

#### Sentence Fragments
- **Line 438**: Merged "Token-efficient." fragment with previous sentence
  - Old: "T1 uses skills, domain knowledge baked into prompts. Token-efficient."
  - New: "T1 uses skills, domain knowledge baked into prompts which is token-efficient."

#### Informal Tone → Formal Academic
- **Line 762**: "super useful" → "particularly useful"
- **Line 802**: "figuring out" → "identifying"
- **Line 1078**: "kitchen sink approach" → "maximalist approach"
- **Line 1290**: "hands out S grades easily" → "awards S grades more frequently"
- **Line 1355**: "spit out" → "produced"
- **Line 755**: "if you have 30+ runs" → "when sample sizes exceed 30"

#### Self-Reference Issues
- **Line 1116**: Removed circular reference
  - Old: "as discussed in the Token Analysis section" (this IS the Token Analysis section)
  - New: "The Token Efficiency Chasm mentioned in Section~\ref{sec:tiered-ablation} is supported by this data."

#### Abstract Precision
- **Line 72**: "exponential rate" → "rapid pace" (more accurate, less hyperbolic)
- **Line 82**: "human-driven rubrics" → "human-designed, LLM-evaluated rubrics" (more precise description)

---

## Compilation Pipeline

### Full LaTeX Build Cycle

```bash
cd /home/mvillmow/ProjectScylla/docs/arxiv/dryrun

# Step 1: Initial compilation
pdflatex -interaction=nonstopmode paper.tex

# Step 2: Process bibliography
bibtex paper

# Step 3: Update references (first pass)
pdflatex -interaction=nonstopmode paper.tex

# Step 4: Finalize references (second pass)
pdflatex -interaction=nonstopmode paper.tex
```

**Why 4 steps?**
- First `pdflatex`: Generate `.aux` file with citation keys
- `bibtex`: Process `.bib` → create `.bbl` with formatted references
- Second `pdflatex`: Include `.bbl` references, update citation numbers
- Third `pdflatex`: Resolve all cross-references and page numbers

---

## Verification Results

### Compilation Success Metrics

```
LaTeX Errors: 0 (grep -c "^!" paper.log)
Unresolved References: 0 (grep "??" paper.log | grep -v pdfTeX)
PDF Generated: ✓ (494KB, 32 pages)
Build Time: ~8 seconds (full 4-step cycle)
```

### Fix Verification

```bash
# Container references removed
grep -n "container" paper.tex
# Result: 0 matches ✓

# 2-decimal CoP values removed
grep -n "& 0\.1[34] \\\\\|& 0\.07 \\\\\|& 0\.25 \\\\\|& 0\.17 \\\\" paper.tex
# Result: 0 matches ✓

# Old glob paths removed
grep -n "tests/\*/test.yaml" paper.tex
# Result: 0 matches ✓

# Bibliography reduced
grep -c "@" references.bib
# Result: 10 entries ✓

# Grammar fixes applied
grep -n "do not apply\|setup the\|top level\|github hash\|Sub-tests" paper.tex
# Result: 0 matches except line 208 (GitHub hash in text) ✓
```

### Warnings (Non-Critical)

1. **PDF version warnings** (4 instances): Figures generated as PDF 1.7 but pdflatex expects ≤1.5
   - Cosmetic only, does not affect output

2. **Hfootnote.1 warning**: `\thanks{}` footnote in title generates hyperref warning
   - Known LaTeX/hyperref issue, does not break functionality

3. **Overfull/underfull hbox warnings**: Typographic warnings
   - Common in LaTeX, not errors

---

## Git Workflow

### Branch & Commit

```bash
# Changes on main branch (not typical skill workflow)
Branch: main
Files modified: 3
- docs/arxiv/dryrun/paper.tex (66 changes)
- docs/arxiv/dryrun/references.bib (-307 lines)
- docs/arxiv/dryrun/paper.pdf (regenerated)

Commit: 989a0c7
Message: "fix(paper): polish 'Taming Scylla' for publication readiness"
Pre-commit hooks: PASSED
```

### File Statistics

```
Before:
- paper.tex: 1600+ lines
- references.bib: 397 lines (36 entries)
- paper.pdf: 505KB

After:
- paper.tex: 1600+ lines (66 edits)
- references.bib: 103 lines (10 entries)
- paper.pdf: 494KB
```

---

## Lessons Learned

### Critical Success Factors

1. **Structured fix categories** prevent omissions and enable systematic verification
2. **Full compilation cycle** is mandatory after bibliography changes (4-step process)
3. **Independent verification** per category catches regression errors
4. **Include regenerated PDF** in commit to reflect all changes

### Common Pitfalls

1. **Line number editing**: Line numbers shift after each edit, causing mismatches
   - **Solution**: Use unique text strings for `old_string` parameter

2. **Skipping bibtex step**: Bibliography changes require full 4-step cycle
   - **Solution**: Always run pdflatex → bibtex → pdflatex × 2

3. **Over-aggressive replace_all**: Some terms have multiple contexts
   - **Solution**: Default to `replace_all=false` with sufficient context

4. **Cascading terminology changes**: Changing "container" requires removing Docker
   - **Solution**: Identify related terms in installation/requirements sections

### arXiv Submission Gotchas

1. **.bbl file gitignore**: The `paper.bbl` file is required for arXiv but may be gitignored
   - **Check**: `.gitignore` has `docs/arxiv/dryrun/*.bbl` pattern
   - **Solution**: Force-add `.bbl` for arXiv submissions or adjust gitignore

2. **Figure PDF versions**: arXiv may reject PDF 1.7 figures (expects ≤1.5)
   - **Check**: PDF version warnings in log
   - **Solution**: Regenerate figures with PDF 1.5 compatibility

---

## Related Files

**Modified**:
- `/home/mvillmow/ProjectScylla/docs/arxiv/dryrun/paper.tex`
- `/home/mvillmow/ProjectScylla/docs/arxiv/dryrun/references.bib`
- `/home/mvillmow/ProjectScylla/docs/arxiv/dryrun/paper.pdf`

**Referenced**:
- Plan transcript: `/home/mvillmow/.claude/projects/-home-mvillmow-ProjectScylla/32adcebf-b662-4e11-9617-b93b77fa0eeb.jsonl`
- Compilation log: `/home/mvillmow/ProjectScylla/docs/arxiv/dryrun/paper.log`

---

## Timeline

```
18:05 - Plan approved, begin implementation
18:06 - Read paper sections (5 parallel reads)
18:07 - Apply Fix 1 (CoP precision) - tier summary table
18:08 - Apply Fix 2 (git worktrees) - 3 locations + Docker removal
18:09 - Apply Fix 4 (glob paths) - 2 lines
18:10 - Apply Fix 5 (grammar) - 20+ edits across 15 sections
18:11 - Apply Fix 3 (bibliography) - rewrite to 10 entries
18:11 - Full compilation verification (4-step cycle)
18:12 - Verification checks (all passed)
18:12 - Commit (989a0c7)
18:12 - Session complete
```

**Total time**: ~7 minutes for 30+ edits across 3 files
