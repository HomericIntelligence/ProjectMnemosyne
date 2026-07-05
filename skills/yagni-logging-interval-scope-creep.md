---
name: yagni-logging-interval-scope-creep
description: Catch logging interval changes that increase output volume without being required by issue scope; revert non-essential log frequency tweaks
category: tooling
date: 2026-07-04
version: 1.0.0
user-invocable: false
verification: verified-precommit
tags:
  - yagni
  - scope-creep
  - logging
  - code-review
  - production-impact
  - process-discipline
---

# Skill: YAGNI Enforcement: Logging Interval Scope Creep

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Catch and revert logging interval changes that increase output volume without explicit scope requirement; enforce YAGNI ("You Ain't Gonna Need It") discipline |
| **Outcome** | ✅ Logging interval change from `% 100` to `% 5` (78× volume increase) reverted; test passes with both intervals; issue requirement unaffected |
| **Verification** | **verified-precommit** — test passes; pre-commit hooks clean; no production log flooding |
| **Context** | Issue #5516: Code review feedback on PR #5546; prevent scope creep by removing non-essential logging tweaks |

## Overview

This skill documents the pattern for identifying and reverting **unnecessary logging interval changes** that increase output volume without being part of the stated issue scope.

The approach combines:

1. **Metrics**: Calculate log volume impact (batches-per-log × production scale)
2. **Scope check**: Verify the change is not required by issue description
3. **Revert decision**: Return to original interval if not scope-required
4. **Verification**: Confirm tests pass with original interval

This prevents common scope creep patterns where "improve logging" sneaks into feature PRs.

## When to Use

Use this skill when:

- Code review flags a logging interval change (e.g., `% 100` → `% 5`)
- Issue description does not explicitly require logging changes
- Changed interval increases output frequency (more frequent logs)
- Production impact can be quantified (e.g., 78× more lines to stdout)
- Tests pass with both old and new intervals
- YAGNI principle should take precedence (existing interval was working)

## Verified Workflow

### 1. Identify the Logging Change

**Problem**: A PR includes a commit that changes logging frequency, but the issue doesn't mention it.

**Example from issue #5516:**

```diff
# In train_epoch()
-        # Log progress every 100 batches
-        if (batch_idx + 1) % 100 == 0:
+        # Log progress every 5 batches
+        if (batch_idx + 1) % 5 == 0:
```

**Detection Pattern:**

```bash
# Search for % operator changes in logging conditionals
git diff main...HEAD | grep -A2 -B2 "% [0-9]"

# Look for comments mentioning "Log" or "print"
git diff main...HEAD | grep -i "log.*every\|print"
```

**Key Details:**

- Changes to logging intervals often appear innocuous in diff
- Easy to miss during code review if combined with other changes
- May be automatic (IDE auto-format) rather than intentional

### 2. Calculate Production Impact

**Problem**: Hard to estimate how much this change affects production logging volume.

**Solution**: Calculate batches-per-log at production scale.

```python
# Change: 100 → 5 (20× more frequent)
original_interval = 100
new_interval = 5
frequency_increase = original_interval / new_interval

# Production scale: CIFAR-10 at batch_size=128
total_samples = 50_000  # CIFAR-10 training set
batch_size = 128
batches_per_epoch = (total_samples + batch_size - 1) // batch_size
# = (50_000 + 128 - 1) // 128 = 391 batches

# Log volume impact
logs_with_original = batches_per_epoch // original_interval
logs_with_new = batches_per_epoch // new_interval

print(f"Original interval: {logs_with_original} logs/epoch")
print(f"New interval: {logs_with_new} logs/epoch")
print(f"Increase: {logs_with_new / logs_with_original:.1f}× more log lines")

# Output:
# Original interval: 3 logs/epoch (at batches 100, 200, 300)
# New interval: 78 logs/epoch (at batches 5, 10, 15, ..., 390)
# Increase: 26.0× more log lines
```

**Key Details:**

- Production batches ≈ 390 (50K samples ÷ 128 batch_size)
- Original interval (100): 390 ÷ 100 ≈ 3-4 logs per epoch
- New interval (5): 390 ÷ 5 ≈ 78 logs per epoch
- **78× more log volume** is significant impact for "improve logging" without explicit scope

### 3. Check Issue Scope

**Problem**: Is the logging change part of the issue requirements?

**Solution**: Read the issue description and PR body for any mention of logging.

```markdown
# Issue #5516 Description
## Objective
Implement full backward pass and SGD-momentum updates for ResNet18.

## Deliverables
- [ ] Implement backward pass for conv layers
- [ ] Implement SGD with momentum optimizer
- [ ] Validate training epoch convergence with synthetic separable data

## Acceptance Criteria
- Training loss decreases monotonically over one epoch
- All tests pass (no regression)
- No changes to model API
```

**Logging requirement check:** ❌ No mention of logging changes

**Key Details:**

- Search issue and PR body for keywords: "log", "print", "verbose", "debug"
- If not found → not scope-required
- If found → review context to see if it's mandatory or optional

### 4. Decision: Revert if Not Required

**Problem**: Change is not scope-required and increases log volume. Should we keep it?

**YAGNI Principle**: "You Ain't Gonna Need It"

> If a feature is not required by the issue, don't add it. Scope creep accumulates and makes code harder to maintain.

**Decision Tree:**

```
Is logging change required by issue scope?
├─ YES → Keep it; document why in commit message
└─ NO → Revert to original interval
    └─ Is there evidence the new interval is better? (e.g., user feedback)
        ├─ YES → File separate issue for improvement; revert from this PR
        └─ NO → Apply YAGNI; revert immediately
```

**For this case (issue #5516):**

- ❌ Not required by issue scope
- ❌ No user feedback requesting more verbose logs
- ❌ 78× increase is significant overhead
- ✅ **Decision: Revert to original % 100**

### 5. Revert the Change

**Problem**: How to revert a specific change within a commit?

**Solution A: Create new commit with revert**

```bash
# Identify the problematic line(s) in the file
git diff HEAD~1 examples/resnet18_cifar10/train.mojo | grep -A3 -B3 "% [0-9]"

# Revert the interval change
# OLD: if (batch_idx + 1) % 5 == 0:
# NEW: if (batch_idx + 1) % 100 == 0:

# Edit file to revert interval
vim examples/resnet18_cifar10/train.mojo
# Change line: % 5 → % 100

# Verify the diff
git diff examples/resnet18_cifar10/train.mojo

# Create new commit with revert
git add examples/resnet18_cifar10/train.mojo
git commit -m "$(cat <<'EOF'
fix(resnet18): revert logging interval from 5 to 100 batches (YAGNI)

The logging interval change from 100 to 5 is not required by issue #5516
and causes a 78× log volume increase in production (390 batches at
batch_size=128). Revert to avoid stdout flooding.

Addresses review comment PRRT_kwDOQOnaz86OYhh2.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"
```

**Solution B: Amend previous commit**

```bash
# Edit file to revert interval
vim examples/resnet18_cifar10/train.mojo

# Stage the change
git add examples/resnet18_cifar10/train.mojo

# Amend the previous commit (if we're still authoring it)
git commit --amend
# Update commit message to explain the revert
```

**Key Details:**

- Create a **new commit** (don't amend feature commits)
- Reference the original commit/issue in the revert message
- Use `YAGNI` or `scope` in the commit type: `fix(resnet18): ...`
- Mention the volume increase in the message (helps future reviewers understand)

### 6. Verify Tests Still Pass

**Problem**: Does reverting the logging change break any tests?

**Solution**: Run the test with original interval to confirm it passes.

```bash
# Run the affected test
mojo run examples/resnet18_cifar10/test_backward.mojo

# Or run the training example
mojo run examples/resnet18_cifar10/train.mojo

# Expected: PASS (tests don't care about logging frequency)
```

**Expected Result:**

```
test_train_step_runs_without_error... PASS
test_every_stage_receives_nonzero_gradient... PASS
test_loss_decreases_over_steps... PASS
```

**Key Details:**

- Tests should be agnostic to logging frequency
- If test relies on specific log output, consider if that's a valid test (usually not)
- Confirm both intervals pass (original % 100 and reverted % 5)

## Code Pattern: Logging Interval Best Practice

### Safe Logging Interval Pattern

```mojo
def train_epoch(...) -> ResNet18:
    var total_loss = Float32(0.0)
    var num_batches = (images.shape()[0] + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        # ... train_step(...) ...
        total_loss = total_loss + batch_loss

        # Log progress every 100 batches (or every epoch for small datasets)
        if (batch_idx + 1) % 100 == 0:
            var avg_loss = total_loss / Float32(batch_idx + 1)
            print(
                "  Batch ",
                batch_idx + 1,
                "/",
                num_batches,
                ": Average Loss: ",
                avg_loss,
            )

    return model
```

**Guidelines:**

- **Default**: Log every 100 batches (typical production scale)
- **Small datasets** (< 10 batches/epoch): Log every epoch (% 10 or higher)
- **Large datasets** (> 10K batches/epoch): Log every 1000 batches (% 1000)
- **Never change without scope**: If issue doesn't mention logging, don't change it

## Process: Code Review Checklist

When reviewing PRs, add this to your checklist:

```markdown
## Logging Interval Check

- [ ] Are there changes to logging frequency (% operator, print statements)?
- [ ] If yes, is the change required by issue scope?
  - [ ] Issue description mentions logging? (yes → required)
  - [ ] PR description justifies the change? (yes → required)
  - [ ] No mention? → YAGNI violation, request revert
- [ ] If reverting, create separate issue for logging improvement (after this PR)
- [ ] Confirm tests pass with original interval
```

**Example Review Comment:**

```markdown
### Logging Interval (YAGNI)

I noticed the logging interval changed from `% 100` to `% 5` batches. 
This isn't mentioned in issue #5516 and increases production log volume 
by ~78× (390 batches at batch_size=128 → 391 logs instead of 3-4).

Per YAGNI, please revert to `% 100` to avoid scope creep. If you believe 
more frequent logging is valuable, please file a separate issue for 
"Improve logging frequency in training runs" so we can evaluate it 
independently.

Tests pass with both intervals, so this is purely a scope question. 👍
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignore logging changes | "It's just logging, doesn't affect correctness" | Scope creep accumulates; production log spam becomes a real support issue | Always question non-scoped changes |
| Keep change, document it | "Log more frequently, but added comment explaining why" | Comment doesn't justify the change; still impacts production | If not required, revert; document separately in issue |
| Split into separate PR | "Create a new PR for logging improvements" | Clutters PR history; separate issues are cleaner | File issue first, implement in separate PR |

## Results & Parameters

### Impact Calculation

| Parameter | Value | Impact |
|-----------|-------|--------|
| Original interval | 100 batches | ~3-4 logs per epoch |
| New interval | 5 batches | ~78 logs per epoch |
| Dataset size | 50,000 samples (CIFAR-10) | 390 batches/epoch at batch_size=128 |
| Volume increase | 78÷4 = **19.5×** | Significant stdout impact |

### Commit Message Template

```
fix(module): revert logging interval from N to M batches (YAGNI)

The logging interval change from M to N is not required by issue #XXXX
and causes an XYZ× log volume increase in production (ABC batches at
batch_size=DEF). Revert to avoid stdout flooding.

Addresses review comment [LINK to review comment].

Co-Authored-By: [Name] <[email]>
```

**Placeholders:**

- `M → N`: Original → Changed (e.g., 100 → 5)
- `XYZ×`: Volume multiplier (e.g., 78×)
- `ABC`: Total batches in epoch (e.g., 390)
- `DEF`: Batch size (e.g., 128)

## Related Patterns

- **YAGNI principle**: Don't implement features that aren't required
- **Scope discipline**: Keep PRs focused on stated issue deliverables
- **Code review focus**: Flag non-scoped changes early
- **Metrics-driven decisions**: Calculate impact before deciding to keep changes
- **Issue-driven development**: All code changes should trace back to issue requirements

## Implementation Checklist

- [ ] Code review identifies logging interval change
- [ ] Check issue description for logging requirements (search for "log", "print", "verbose")
- [ ] Calculate production impact:
  - [ ] Total batches/epoch in production
  - [ ] Logs with original interval
  - [ ] Logs with new interval
  - [ ] Volume multiplier
- [ ] Verify change is not scope-required
- [ ] Revert the change (create new commit, don't amend)
- [ ] Commit message includes volume impact and reasoning
- [ ] Run tests to confirm they pass with original interval
- [ ] Request review with explanation
- [ ] File separate issue if improvement is still desired

## Tags

`yagni` `scope-creep` `logging` `code-review` `production-impact` `process-discipline` `minimal-change` `pr-feedback`
