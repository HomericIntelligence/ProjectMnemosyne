---
name: implementation-alignment-validation
description: Systematic workflow for validating implementation code against research documentation and fixing discrepancies
category: architecture
date: 2025-06-27
---

# Implementation Alignment Validation

## Overview

| Field | Value |
|-------|-------|
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

Trigger phrases:
- "validate implementation against docs"
- "check if code matches research"
- "audit implementation alignment"
- "verify metrics match documentation"

## Verified Workflow

### Phase 1: Gather Documentation Sources

```bash
# Find all documentation files
docs/research.md           # Main research methodology
docs/summary.md            # Design decisions
docs/design/*.md          # Detailed specifications
.claude/shared/*.md        # Operational guidelines
CLAUDE.md                  # Project overview
```

### Phase 2: Map Implementation Files

```bash
# Find implementation files to validate
glob src/**/*.py           # Python implementation
glob src/**/*.mojo         # Mojo implementation
glob config/**/*.yaml      # Configuration files
```

### Phase 3: Create Alignment Matrix

Build a comparison table with:

| Location | Theory/Docs | Implementation | Status |
|----------|-------------|----------------|--------|
| `file.py:line` | Documented behavior | Actual behavior | ✓/⚠️/❌ |

Status legend:
- ✓ = Aligned
- ⚠️ = Partial/Different
- ❌ = Missing

### Phase 4: Prioritize Gaps

Categorize by impact:
1. **Critical**: Core metrics/algorithms wrong
2. **Important**: Missing documented features
3. **Minor**: Cosmetic differences, formula variations

### Phase 5: Fix with Tests First

For each gap:
1. Write test validating documented behavior
2. Run test (should fail)
3. Fix implementation
4. Run test (should pass)
5. Run full test suite

### Phase 6: Verify Full Suite

```bash
pixi run pytest tests/ -v --tb=short
```

## Failed Attempts

| Attempt | Why It Failed | Lesson Learned |
|---------|---------------|----------------|
| Updating config without updating test fixtures | Tests failed because fixtures only had T0-T3 but validator now required T4-T6 | Always search for test fixtures when changing validators |
| Using exact float comparisons in tests | `0.2 != 0.20000000000000007` due to floating point | Always use `pytest.approx()` for float comparisons |
| Trusting code comments over docs | Comment said 70/30 weights, docs said 50/50 | Docs are authoritative; verify comments against docs |

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
## Pre-Validation
- [ ] Identified all documentation sources
- [ ] Located all implementation files
- [ ] Created blank alignment matrix

## During Validation
- [ ] Compared each documented feature to implementation
- [ ] Used file:line references for precision
- [ ] Categorized gaps by priority

## Fixing Gaps
- [ ] Wrote tests for each gap BEFORE fixing
- [ ] Fixed one gap at a time
- [ ] Ran tests after each fix
- [ ] Updated test fixtures if validators changed

## Post-Validation
- [ ] Full test suite passes
- [ ] All gaps resolved or documented as intentional
- [ ] Created PR with summary
```

## Related Skills

- `implementation-theory-alignment`: Initial skill for finding gaps (predecessor)
- `test-implementation-gap-analysis`: For test coverage gaps
