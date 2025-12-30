# Troubleshooting Guide Template

Use this for error-solution mappings.

## Common Issues

### Category: [e.g., Training Errors]

#### Issue 1: [Error Name]

**Symptom**: [Observable behavior]
**Cause**: [Why it happens]
**Solution**: [How to fix]
**Prevention**: [How to avoid]

#### Issue 2: [Error Name]

[Same structure...]

### Category: [e.g., Infrastructure]

[More issues...]

## Debugging Checklist

Before filing issues, check:
- [ ] Environment matches documented versions
- [ ] Dataset is correct format
- [ ] Hardware has sufficient resources
- [ ] Configuration file is valid
- [ ] Dependencies are installed

## Quick Reference

| Error Pattern | Likely Cause | Quick Fix |
|--------------|--------------|-----------|
| OOM errors | Batch too large | Reduce batch_size by 50% |
| NaN loss | Learning rate too high | Reduce LR by 10x |
| Slow convergence | LR too low | Increase by 2-5x |
