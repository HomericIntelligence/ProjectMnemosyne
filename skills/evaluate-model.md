---
name: evaluate-model
description: Measure model performance on test datasets. Use when assessing accuracy,
  precision, recall, and other metrics.
category: tooling
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Evaluate Model

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | Measure machine learning model performance using appropriate metrics for the task (classification, regression, etc.). |
| Outcome | Operational |

Measure machine learning model performance using appropriate metrics for the task (classification, regression, etc.).

## When to Use

- Comparing different model architectures
- Assessing performance on test/validation datasets
- Detecting overfitting or underfitting
- Reporting model accuracy for papers and documentation

### Quick Reference

```mojo
# Mojo model evaluation pattern
struct ModelEvaluator:
    fn evaluate_classification(
        mut self,
        predictions: ExTensor,
        ground_truth: ExTensor
    ) -> Tuple[Float32, Float32, Float32]:
        # Returns accuracy, precision, recall
        ...

    fn evaluate_regression(
        mut self,
        predictions: ExTensor,
        ground_truth: ExTensor
    ) -> Tuple[Float32, Float32]:
        # Returns MSE, MAE
        ...
```

## Verified Workflow

1. **Load test data**: Prepare test/validation dataset
2. **Generate predictions**: Run model inference on test set
3. **Select metrics**: Choose appropriate metrics (accuracy, precision, recall, F1, AUC, MSE, etc.)
4. **Calculate metrics**: Compute performance metrics
5. **Analyze results**: Compare to baseline and identify strengths/weaknesses

## Output Format

Evaluation report:

- Task type (classification, regression, etc.)
- Metrics (accuracy, precision, recall, F1, AUC, etc.)
- Per-class breakdown (if applicable)
- Comparison to baseline model
- Confusion matrix (classification)
- Error analysis

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See CLAUDE.md > Language Preference (Mojo for ML models)
- See `train-model` skill for model training
- See `/notes/review/mojo-ml-patterns.md` for Mojo tensor operations
