---
name: create-swe-bench-tests
description: Create SWE-bench style benchmark test cases from repository PR history
category: evaluation
date: 2026-01-02
---

# Create SWE-Bench Tests

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Objective | Create benchmark test cases for AI agent evaluation from real PR history |
| Outcome | Generated 45 test cases across 9 categories following SWE-bench methodology |

## When to Use

Use this skill when:

1. **Setting up AI agent evaluation** - Need benchmark tasks based on real coding problems
2. **Creating test suites from PR history** - Want to use actual merged PRs as evaluation tasks
3. **Building ablation frameworks** - Need tier-based testing (prompts, skills, tools, delegation)
4. **Following SWE-bench methodology** - Want industry-standard benchmark patterns

## Verified Workflow

### Step 1: Analyze PR History

```bash
# Get merged PRs with metadata
gh pr list --state merged --limit 500 --json number,title,labels,additions,deletions

# Categorize by type and size:
# - Small: <100 LOC
# - Medium: 100-500 LOC
# - Large: 500-2000 LOC
```

### Step 2: Get Parent Commits

For each selected PR, get the pre-change state (what the agent will start from):

```bash
# Get merge commit
merge_commit=$(gh pr view <number> --json mergeCommit --jq '.mergeCommit.oid')

# Get parent commit (state before PR)
parent_commit=$(git rev-parse $merge_commit^)
```

### Step 3: Create Test Case Structure

Follow the fixtures pattern:

```text
tests/fixtures/tests/test-XXX/
├── test.yaml          # Test metadata
├── prompt.md          # Task prompt (from PR description)
├── config.yaml        # Timeout and cost limits
├── expected/
│   ├── criteria.md    # Evaluation criteria
│   └── rubric.yaml    # Grading rubric
├── t0/                # Tier 0: Prompt ablations
├── t1/                # Tier 1: Skills ablations
├── t2/                # Tier 2: Tooling ablations
├── t3/                # Tier 3: Delegation ablations
├── t4/                # Tier 4: Hierarchy ablations
├── t5/                # Tier 5: Hybrid ablations
└── t6/                # Tier 6: Super configuration
```

### Step 4: Generate test.yaml

```yaml
id: "test-XXX"
name: "Descriptive Task Name"
description: |
  Multi-line description of the test task.
source:
  repo: "https://github.com/org/repo"
  hash: "<parent-commit-hash>"  # State BEFORE the PR
task:
  prompt_file: "prompt.md"
  timeout_seconds: 3600
validation:
  criteria_file: "expected/criteria.md"
  rubric_file: "expected/rubric.yaml"
tiers:
  - T0
  - T1
  - T2
  - T3
  - T4
  - T5
  - T6
```

### Step 5: Copy Tier Directories

Copy tier configurations from an existing test case:

```bash
for tier in t0 t1 t2 t3 t4 t5 t6; do
  cp -r test-001/$tier test-XXX/
done
```

## Failed Attempts

| Attempt | What Failed | Why | Fix |
|---------|-------------|-----|-----|
| Using `$(seq)` in bash loop | Syntax error with special characters | Shell escaping issues in complex loops | Use explicit list: `for i in 001 002 003...` |
| Looking for marketplace.json in ProjectOdyssey | File not found | ProjectOdyssey has plugin.json, not marketplace.json | Check ProjectMnemosyne for marketplace.json |
| Using `tests/<category>/<id>/` structure | Wrong pattern | ProjectScylla uses fixtures pattern | Use `tests/fixtures/tests/test-XXX/` |
| Creating directories without tier subdirs | Incomplete structure | Forgot to copy t0-t6 directories | Copy from existing test case |

## Results & Parameters

### Recommended Categories

| Category | Description | Example PRs |
|----------|-------------|-------------|
| Build System | Build configs, Dockerfiles, pixi | Add dependency, fix build errors |
| CI/CD | GitHub Actions, workflows | Bump actions, add workflows |
| Bug Fixing | Code fixes, error resolution | Remove unused vars, fix threading |
| New Features | New functionality | Add modules, implement features |
| Refactoring | Code restructuring | Extract functions, migrate APIs |
| Optimization | Performance improvements | SIMD, inlining, fast paths |
| Documentation | Docs, comments, guides | Update versions, add guides |
| Testing | Test suites, fixtures | Enable tests, add coverage |
| Issue Planning | Implementation plans (markdown output) | Document issues, plan features |

### Timeout Guidelines

| Task Complexity | Timeout | Max Cost |
|-----------------|---------|----------|
| Simple (<100 LOC) | 600-1800s | $1-2 |
| Medium (100-500 LOC) | 1800-3600s | $2-5 |
| Large (500-2000 LOC) | 3600-7200s | $5-10 |

### Rubric Template

```yaml
requirements:
  - id: "R001"
    description: "Primary requirement"
    weight: 3.0
    evaluation: "binary"
  - id: "R002"
    description: "Secondary requirement"
    weight: 2.0
    evaluation: "binary"

grading:
  pass_threshold: 0.70
  grade_scale:
    A: 0.95
    B: 0.85
    C: 0.75
    D: 0.65
    F: 0.0
```

## Related Skills

- `gh-review-pr` - For analyzing PR content
- `analyze-ci-failure-logs` - For understanding test failures
- `doc-generate-adr` - For documenting evaluation methodology
