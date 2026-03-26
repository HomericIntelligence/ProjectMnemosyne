# Experiment Log Template

Use this for detailed experiment tracking.

## Experiment: [Name]

**Date**: YYYY-MM-DD
**Objective**: [What you're trying to learn]
**Hypothesis**: [What you predict will happen]

### Environment

| Item | Details |
|------|---------|
| Hardware | [GPU model, RAM, CPU] |
| Software | [Framework versions, OS] |
| Dataset | [Name, size, splits] |
| Baseline | [Reference performance] |

### Parameters

```yaml
# Copy-paste ready configuration
param1: value1
param2: value2
```

### Results

| Run | Config | Metric | Notes |
|-----|--------|--------|-------|
| 1 | baseline | 85.3% | [Observations] |
| 2 | +changes | 87.1% | [Observations] |

### Failed Runs

| Run | Config | Error | Root Cause | Fix |
|-----|--------|-------|------------|-----|
| 3 | x=10 | OOM | Batch too large | Reduce to x=5 |

### Conclusions

**What Worked**:
- [List successful approaches]

**What Failed**:
- [List failed approaches with reasons]

**Next Steps**:
- [What to try next]
