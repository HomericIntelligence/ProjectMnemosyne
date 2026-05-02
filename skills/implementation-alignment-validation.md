---
name: implementation-alignment-validation
description: Systematic workflow for validating implementation code against research
  documentation and fixing discrepancies
category: architecture
date: 2026-04-07
version: 1.1.0
---
# Implementation Alignment Validation

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2025-06-27 |
| Objective | Validate ProjectScylla implementation against docs/theory/research documentation |
| Outcome | SUCCESS - 14 items aligned, 5 gaps fixed, 892 tests passing |
| Duration | ~45 minutes |

## When to Use

Use this skill when:

- Starting work on a mature codebase with research/design documentation
- Before major releases to ensure implementation matches specifications
- After discovering a discrepancy between docs and code
- When metrics or formulas in code don't match documented definitions
- Auditing for technical debt related to doc-implementation drift
- Research/design docs exist but implementation status is unclear
- Onboarding to understand if docs match reality
- Reviewing code after major documentation updates

Trigger phrases:
- "validate implementation against docs"
- "check if code matches research"
- "audit implementation alignment"
- "verify metrics match documentation"
- "validate", "align", or "check" implementation against specs

## Verified Workflow

### Phase 1: Gather Documentation Sources

```bash
# Find all documentation files
docs/research.md           # Main research methodology
docs/summary.md            # Design decisions
docs/design/*.md          # Detailed specifications
.claude/shared/*.md        # Operational guidelines
CLAUDE.md                  # Project overview

# Also check:
glob docs/**/*.md
glob .claude/shared/*.md
```

### Phase 2: Map Implementation Files

```bash
# Find implementation files to validate
glob src/**/*.py           # Python implementation
glob src/**/*.mojo         # Mojo implementation
glob config/**/*.yaml      # Configuration files

# Key patterns:
# - src/metrics/*.py for metrics documentation
# - src/evaluation/*.py for evaluation protocols
# - src/config/*.py for configuration schemas
```

### Phase 3: Create Alignment Matrix

Build a comparison table with:

| Location | Theory/Docs | Implementation | Status |
| ---------- | ------------- | ---------------- | -------- |
| `file.py:line` | Documented behavior | Actual behavior | ✓/⚠️/❌ |

Status legend:
- ✓ = Aligned — implementation matches documentation
- ⚠️ = Partial/Different — implementation differs from documentation
- ❌ = Missing — documented feature not implemented

### Phase 4: Prioritize Gaps

Categorize by impact:
1. **Critical**: Core metrics/algorithms wrong (e.g. wrong formula)
2. **Important**: Missing documented features
3. **Minor**: Cosmetic differences, formula variations / documentation outdated but implementation correct

### Phase 5: Fix with Tests First

For each gap:
1. Write test validating documented behavior
2. Run test (should fail)
3. Fix implementation
4. Run test (should pass)
5. Run full test suite

### Phase 6: Update Documentation (if implementation is intentionally different)

If implementation differs from docs for good reason:
- Update docs to match implementation
- Add rationale for the change (inline code comments + updated docs)
- Document the fix in the PR

### Phase 7: Verify Full Suite

```bash
pixi run pytest tests/ -v --tb=short

# Check specific metric tests
pixi run pytest tests/unit/metrics/ -v

# Verify no regressions
pixi run pytest tests/integration/ -v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |

## Results & Parameters

### Alignment Categories Found

```yaml
aligned_items: 14
  - composite_score: "50/50 weights (orchestrator.py:158)"
  - cost_of_pass: "cost/pass_rate (grading.py:77)"
  - r_prog: "achieved/expected (process.py:92)"
  - strategic_drift: "1-alignment (process.py:145)"
  - cfp: "failed/total (process.py:199)"
  - token_tracking: "14 component types (token_tracking.py)"
  - runs_per_tier: "10 (orchestrator.py:24)"
  # ... plus 7 more

gaps_fixed: 5
  - tiers_t4_t6: "Added to tiers.yaml + prompt files"
  - frontier_cop: "Added to cross_tier.py"
  - consistency: "Added calculate_consistency() to statistics.py"
  - ablation_score: "New ablation.py module"
  - ttft_latency: "New latency.py module"
```

### Example Discrepancy Found

```yaml
# Composite Score Weights (from implementation-theory-alignment session)
location: src/scylla/orchestrator.py:158-159
documented: (pass_rate + impl_rate) / 2  # 50/50 weights
implemented: (impl_rate * 0.7) + (pass_rate * 0.3)  # 70/30 weights
fix: Update implementation to match documentation
```

### Files Created During Fix

```yaml
new_files:
  - config/tiers/t4-delegation.md
  - config/tiers/t5-hierarchy.md
  - config/tiers/t6-hybrid.md
  - src/scylla/metrics/ablation.py
  - src/scylla/metrics/latency.py
  - tests/unit/metrics/test_ablation.py
  - tests/unit/metrics/test_latency.py

modified_files:
  - config/tiers/tiers.yaml
  - src/scylla/metrics/cross_tier.py
  - src/scylla/metrics/statistics.py
  - src/scylla/metrics/__init__.py
  - src/scylla/executor/tier_config.py
  - tests/unit/metrics/test_statistics.py
  - tests/unit/metrics/test_cross_tier.py
  - tests/unit/executor/test_tier_config.py
```

### Test Results

```
892 passed in 0.90s
```

## Checklist Template

Use this checklist when performing alignment validation:

```markdown
## Documentation Review
- [ ] Read research.md
- [ ] Read design/*.md
- [ ] Read CLAUDE.md metrics section
- [ ] Identify key formulas and behaviors

## Implementation Mapping
- [ ] Locate all files implementing documented features
- [ ] Search for formula implementations
- [ ] Check for duplicate implementations

## Discrepancy Analysis
- [ ] Create alignment matrix
- [ ] Categorize by severity
- [ ] Identify root causes

## Fixes
- [ ] Write tests first
- [ ] Implement fixes
- [ ] Update related tests
- [ ] Run full test suite

## Documentation Updates
- [ ] Update metrics-formulas.md if needed
- [ ] Add inline code comments
- [ ] Create PR with summary
```
