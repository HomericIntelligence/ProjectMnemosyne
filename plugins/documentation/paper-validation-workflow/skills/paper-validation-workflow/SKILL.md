---
name: "Paper Validation Workflow"
description: "Paper Validation Workflow"
category: documentation
date: 2026-02-07
user-invocable: false
---
# Paper Validation Workflow

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-07 |
| Objective | | Attribute | Value | |-----------|-------| | **Date** | 2026-02-07 | | **Objective** | Validate and correct LaTeX academic paper against raw exper... |
| Outcome | Operational |


## Session Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-07 |
| **Objective** | Validate and correct LaTeX academic paper against raw experimental data |
| **Outcome** | ✅ Success - 7 categories of fixes applied, verified, and committed |
| **Skill Type** | Documentation quality assurance and cross-validation |

---

## When to Use This Skill

Use this workflow when:

- ✅ You have an academic paper with numerical claims that must match raw data
- ✅ You need to verify methodology descriptions match actual implementation
- ✅ You're doing a final review before publication/submission
- ✅ You've received feedback about inconsistencies or errors
- ✅ You need to fix typos, grammar, and formatting issues systematically

**Do NOT use** for:
- ❌ Initial paper drafting (use during review phase only)
- ❌ Simple proofreading without data validation
- ❌ Papers without quantitative claims to verify

---

## Verified Workflow

### Phase 1: Cross-Validation Against Raw Data

**Objective**: Ensure every numerical claim in the paper matches source data

**Steps**:

1. **Identify all numerical claims** in the paper:
   ```bash
   # Extract numbers, percentages, ratios from paper
   grep -E '[0-9]+\.[0-9]+|[0-9]+%|[0-9]+x' docs/paper.tex
   ```

2. **Locate source data files**:
   - Experiment results: `~/fullruns/test001-dryrun/summary.json`
   - Run-level data: `~/fullruns/test001-dryrun/runs.csv`
   - Judge scores: `~/fullruns/test001-dryrun/judges.csv`
   - Criteria scores: `~/fullruns/test001-dryrun/criteria.csv`

3. **Cross-validate systematically**:
   - Tier scores (T0-T6)
   - Token counts (input, output, cache create, cache read)
   - Timing values (agent time, judge time)
   - Ratios and derived metrics (CoP, percentages)
   - Statistical claims (correlations, agreements)

4. **Document verification status**:
   - Create checklist of all claims
   - Mark each as ✅ verified or ❌ needs correction
   - Track line numbers for corrections

**Tools Used**:
- `jq` for JSON data extraction
- `grep` for pattern matching in LaTeX
- Text editor for manual verification

**Result**: 50+ numerical claims verified as accurate in this session

---

### Phase 2: Identify Systematic Issues

**Objective**: Find patterns of errors that affect multiple locations

**Steps**:

1. **Check methodology consistency**:
   ```bash
   # Find all mentions of statistical methods
   grep -i "median\|mean\|average" docs/paper.tex
   ```
   - Verify implementation matches description
   - Common issue: Paper claims "median" but code uses "mean"

2. **Verify terminology consistency**:
   ```bash
   # Check for mismatches in category lists
   grep -i "categories\|criteria" docs/paper.tex
   ```
   - Ensure lists match actual rubric/schema
   - Watch for outdated terminology from earlier drafts

3. **Find typos and grammar issues**:
   - Systematic typos (e.g., "iers" instead of "tiers")
   - Grammar patterns (e.g., "is more of X than Y" vs "is more X than Y")
   - Subject-verb agreement (e.g., "test themselves" vs "tests themselves")

4. **Check cross-references**:
   ```bash
   # Find broken LaTeX references
   grep '\\ref{' docs/paper.tex
   ```
   - Verify section references point to correct sections
   - Check label consistency

**Result**: Identified 7 categories of fixes in this session

---

### Phase 3: Implement Fixes Systematically

**Objective**: Apply corrections with verification at each step

**Steps**:

1. **Read the file first** (CRITICAL):
   ```python
   # Always use Read tool before Edit tool
   Read(file_path="/path/to/paper.tex")
   ```

2. **Apply edits with exact string matching**:
   ```python
   Edit(
       file_path="/path/to/paper.tex",
       old_string="exact text from Read output",  # Copy-paste exactly
       new_string="corrected text"
   )
   ```

3. **Handle multi-location fixes**:
   - Apply each fix individually
   - Verify each change before moving to next
   - Use `replace_all=True` only for simple find-replace

4. **Verify compilation after each major change**:
   ```bash
   cd docs && pdflatex -interaction=nonstopmode paper.tex
   ```

5. **Use grep to confirm all instances fixed**:
   ```bash
   # Example: Verify all "median" changed to "mean"
   grep -n "median" docs/paper.tex
   ```

**Tools Used**:
- `Read` tool for exact text extraction
- `Edit` tool for surgical changes
- `pdflatex` for compilation verification
- `grep` for post-change verification

**Result**: 11 successful edits applied (7 categories of fixes)

---

### Phase 4: Final Verification & Commit

**Objective**: Confirm all changes correct and commit cleanly

**Steps**:

1. **Final compilation check**:
   ```bash
   cd docs
   pdflatex paper.tex
   bibtex paper
   pdflatex paper.tex
   pdflatex paper.tex
   ```
   - Should complete with no errors
   - Check page count unchanged (unless expected)
   - Review PDF visually

2. **Verify no regressions**:
   ```bash
   # Check for remaining issues
   grep -i "TODO\|FIXME\|XXX" docs/paper.tex
   grep "??" docs/paper.pdf  # Unresolved references
   ```

3. **Review git diff**:
   ```bash
   git diff docs/paper.tex | less
   ```
   - Verify only intended changes present
   - Check line counts reasonable

4. **Commit with detailed message**:
   ```bash
   git add docs/paper.tex
   git commit -m "fix(paper): correct methodology and fix typos/grammar

   - Fix median → mean for judge consensus scoring (7 locations)
   - Correct evaluation categories list to match actual rubric
   - Fix typo: iers → tiers
   - Fix grammar: more of black magic → more black magic
   - Fix grammar: test themselves → tests themselves
   - Fix section reference to Section 10
   - Update Haiku model ID to claude-haiku-4-5-20251001

   All changes verified against implementation data.
   Paper compiles successfully with no errors.

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

**Result**: Clean commit with 15 insertions, 16 deletions

---

## Failed Attempts & Lessons Learned
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Failed: Batch Editing Without Reading File First

**What happened**: Early attempts to apply multiple edits in parallel failed when the exact string didn't match the file.

**Why it failed**:
- String matching is exact (including whitespace, line breaks)
- Can't rely on memory of file contents
- LaTeX has subtle formatting variations

**Lesson**: Always use `Read` tool immediately before `Edit` tool to get exact text.

---

### ❌ Failed: Using Generic Search Patterns

**What happened**: Initially tried to find "median" references without checking context.

**Why it failed**:
- Some "median" uses are legitimate (e.g., "median_score" column names)
- Need to distinguish methodology claims from data references

**Lesson**: Read surrounding context before deciding if a match needs fixing.

---

### ⚠️ Partial Success: Parallel Edit Calls

**What happened**: Attempted to make multiple edits in a single message with multiple tool calls.

**Why it partially failed**:
- Works when strings are unique and file hasn't changed
- Fails when earlier edits affect later string matches
- Error cascades cause all subsequent edits to fail

**Lesson**: For dependent edits, apply sequentially. For truly independent edits (different files, completely different sections), parallel calls work.

---

## Results & Parameters

### Fixes Applied (7 Categories)

1. **Median → Mean** (7 locations)
   - Lines: 592, 733, 845, 1020-1022, 1060, 1133-1134
   - Reason: Implementation uses `mean()` not `median()`

2. **Evaluation Categories Mismatch** (1 location)
   - Line: 216-218
   - Changed: 6 categories → 5 categories (removed "security and safety", "patchfile correctness")
   - Reason: Actual rubric only has 5 categories

3. **Typo: "iers" → "tiers"** (1 location)
   - Line: 442

4. **Grammar: "more of black magic"** (1 location)
   - Line: 93
   - Fixed to: "more black magic"

5. **Grammar: "test themselves" → "tests themselves"** (1 location)
   - Line: 303
   - Also fixed: "The test are" → "The tests are"

6. **Section Reference** (1 location)
   - Line: 821
   - Changed: `Section~\ref{sec:discussion}` → "Section 10"
   - Reason: Reference pointed to wrong section

7. **Model ID Consistency** (1 location)
   - Line: 723
   - Changed: `claude-haiku-4-5-20250929` → `claude-haiku-4-5-20251001`
   - Reason: Actual experiment used dated model ID

### Verification Results

- ✅ LaTeX compilation: Success (29 pages, 0 errors)
- ✅ All "median" references changed: Confirmed with grep
- ✅ Git diff clean: 15 insertions, 16 deletions
- ✅ Pre-commit hooks: All passed

### Key Configuration

```yaml
Paper: docs/paper.tex
Source Data: ~/fullruns/test001-dryrun/
Verification Method: Manual cross-validation with jq/grep
Tools: Read, Edit, Bash (pdflatex, grep, git)
```

---

## Copy-Paste Checklist for Future Use

When validating a paper, use this checklist:

```markdown
## Paper Validation Checklist

### Phase 1: Data Cross-Validation
- [ ] Extract all numerical claims from paper
- [ ] Locate source data files (JSON, CSV, logs)
- [ ] Verify tier scores match summary.json
- [ ] Verify token counts match run data
- [ ] Verify timing values match logs
- [ ] Verify derived metrics (ratios, percentages)
- [ ] Verify statistical claims (correlations, p-values)

### Phase 2: Methodology Consistency
- [ ] Check statistical method descriptions (median vs mean)
- [ ] Verify terminology matches implementation
- [ ] Check category/criteria lists match rubrics
- [ ] Verify model IDs and version numbers
- [ ] Check cross-references (Section/Figure/Table refs)

### Phase 3: Grammar & Formatting
- [ ] Run spell check
- [ ] Check subject-verb agreement
- [ ] Verify article usage (a/an/the)
- [ ] Check for typos in technical terms
- [ ] Verify LaTeX syntax correct

### Phase 4: Final Verification
- [ ] Compile LaTeX (pdflatex + bibtex + pdflatex x2)
- [ ] Check for unresolved references (??)
- [ ] Review PDF page count
- [ ] Git diff review
- [ ] Pre-commit hooks pass
- [ ] Commit with detailed message
```

---

## Success Metrics

This workflow achieved:

- ✅ **100% numerical accuracy** - All 50+ claims verified
- ✅ **7 categories of fixes** - Systematic issues resolved
- ✅ **Zero compilation errors** - Clean LaTeX build
- ✅ **Clean commit** - No auxiliary files, clear message
- ✅ **~2 hours total time** - From plan to committed fix

---

## Related Skills

- `latex-workflow` - General LaTeX editing and compilation
- `data-validation` - Verifying experimental data integrity
- `academic-writing` - Research paper writing best practices
- `git-workflow` - Commit message formatting and PR creation

---

## Notes

- This workflow is **read-heavy, write-light** - most time spent verifying, not editing
- **Cross-validation is critical** - don't assume paper matches implementation
- **Systematic approach wins** - categorize issues before fixing
- **Verification after each phase** - don't wait until end to check compilation

---

**Skill Created**: 2026-02-07
**Last Updated**: 2026-02-07
**Times Used**: 1
**Success Rate**: 100%
