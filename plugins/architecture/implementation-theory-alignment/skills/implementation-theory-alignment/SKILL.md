---
name: implementation-theory-alignment
description: Systematic workflow for validating implementation against research/theory documentation and fixing discrepancies
category: architecture
date: 2025-12-31
---

# Implementation-Theory Alignment

## Overview

| Field | Value |
|-------|-------|
| Date | 2025-12-31 |
| Objective | Validate implementation aligns with research documentation and fix discrepancies |
| Outcome | Successfully identified and fixed 5 alignment issues, added 2 new modules |

## When to Use

Use this skill when:
- Starting work on a mature codebase with existing documentation
- Research/design docs exist but implementation status is unclear
- User asks to "validate", "align", or "check" implementation against specs
- Reviewing code after major documentation updates
- Onboarding to understand if docs match reality

## Verified Workflow

### Step 1: Gather Documentation Sources
```bash
# Find all research and design documentation
glob docs/**/*.md
glob .claude/shared/*.md

# Key files to read:
# - docs/research.md (research methodology)
# - docs/summary.md (design decisions)
# - docs/design/*.md (detailed specifications)
# - CLAUDE.md (project overview with metric definitions)
```

### Step 2: Map Implementation Files
```bash
# Find implementation files matching documentation topics
glob src/**/*.py  # or *.mojo, *.ts, etc.

# Key patterns:
# - src/metrics/*.py for metrics documentation
# - src/evaluation/*.py for evaluation protocols
# - src/config/*.py for configuration schemas
```

### Step 3: Create Alignment Matrix

Build a table comparing:
| Location | Theory/Docs | Implementation | Status |
|----------|-------------|----------------|--------|
| File:line | Expected behavior | Actual behavior | ✓/⚠️/❌ |

Status codes:
- ✓ Aligned - implementation matches documentation
- ⚠️ Mismatch - implementation differs from documentation
- ❌ Missing - documented feature not implemented

### Step 4: Prioritize Discrepancies

Order by:
1. **Critical** - Core functionality differs (e.g., wrong formula)
2. **Important** - Missing features documented in research
3. **Minor** - Documentation outdated but implementation correct

### Step 5: Fix with Tests First

For each discrepancy:
1. Write test that validates documented behavior
2. Fix implementation to pass test
3. Update integration tests if needed
4. Document the fix

### Step 6: Update Documentation

If implementation is intentionally different:
- Update docs to match implementation
- Add rationale for the change

## Failed Attempts

| Attempt | What Failed | Why |
|---------|-------------|-----|
| Trusting comments | Comment said 70/30 weights | Docs said 50/50; always verify against authoritative source |
| Partial search | Searched one file for formula | Same formula existed in multiple files with different implementations |

## Results & Parameters

### Key Discrepancies Found

```yaml
# Example: Composite Score Weights
location: src/scylla/orchestrator.py:158-159
documented: (pass_rate + impl_rate) / 2  # 50/50 weights
implemented: (impl_rate * 0.7) + (pass_rate * 0.3)  # 70/30 weights
fix: Update implementation to match documentation
```

### Missing Features Implemented

```yaml
# Process Metrics (from research.md)
r_prog:
  formula: achieved_steps / expected_steps
  module: src/scylla/metrics/process.py

strategic_drift:
  formula: 1 - (goal_aligned_actions / total_actions)
  module: src/scylla/metrics/process.py

cfp:
  formula: failed_changes / total_changes
  module: src/scylla/metrics/process.py

# Token Tracking (from research.md Section 2.2)
token_efficiency_ratio:
  formula: schema_tokens / skill_tokens
  module: src/scylla/metrics/token_tracking.py
```

### Verification Commands

```bash
# Run all tests to verify alignment
pixi run pytest tests/ -v

# Check specific metric tests
pixi run pytest tests/unit/metrics/ -v

# Verify no regressions
pixi run pytest tests/integration/ -v
```

## Checklist Template

```markdown
## Implementation-Theory Alignment Checklist

### Documentation Review
- [ ] Read research.md
- [ ] Read design/*.md
- [ ] Read CLAUDE.md metrics section
- [ ] Identify key formulas and behaviors

### Implementation Mapping
- [ ] Locate all files implementing documented features
- [ ] Search for formula implementations
- [ ] Check for duplicate implementations

### Discrepancy Analysis
- [ ] Create alignment matrix
- [ ] Categorize by severity
- [ ] Identify root causes

### Fixes
- [ ] Write tests first
- [ ] Implement fixes
- [ ] Update related tests
- [ ] Run full test suite

### Documentation Updates
- [ ] Update metrics-formulas.md if needed
- [ ] Add inline code comments
- [ ] Create PR with summary
```
