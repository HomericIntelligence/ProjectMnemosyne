---
name: complex-agent-eval-task
description: "Create sophisticated E2E test cases for AI agents using real PRs as reference solutions"
category: evaluation
source: ProjectScylla
date: 2026-01-01
---

# Complex Agent Evaluation Task Design

Create sophisticated E2E test cases for AI agent evaluation using real-world PRs as both task source and reference solution.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-01-01 | Create T2+ test case using PR #3017 as reference for dtype migration task | Test case created with patchfile comparison, 50 turn limit, PR #107 merged |

## When to Use

- (1) Designing evaluation tasks for T2+ tiers (Skills, Tooling, Delegation, Hierarchy)
- (2) Need patchfile-based evaluation against a known reference solution
- (3) Testing agents on complex refactoring, migration, or multi-file changes
- (4) Want to constrain agents from accessing solution sources (git history, GitHub API)
- (5) Creating tasks that require >20 turns to complete

## Verified Workflow

### 1. Start with `/advise` to Find Related Skills

```bash
/advise <your task description>
```

Check for existing skills that document:
- The solution workflow (e.g., `dtype-native-migration` skill)
- Rubric design patterns (e.g., `e2e-judge-rubric-design` skill)

### 2. Create Test Directory Structure

```
tests/<id>-<name>/
├── test.yaml              # Test configuration
├── prompt.md              # Task prompt for agent
├── expected/
│   ├── criteria.md        # Human-readable success criteria
│   ├── rubric.yaml        # Weighted scoring rubric
│   └── reference/
│       ├── METADATA.yaml  # PR info, commit hash
│       └── reference.patch # git diff from reference PR
└── constraints/
    └── forbidden.md       # Explicitly forbidden actions
```

### 3. Configure test.yaml

```yaml
id: "002-dtype-native-migration"
name: "Migrate Custom DTypes to Mojo Native Types"
description: |
  Complex refactoring task description...

source:
  repo: "https://github.com/owner/repo"
  hash: "commit-before-pr"  # BEFORE the PR was merged

task:
  prompt_file: "prompt.md"
  timeout_seconds: 7200  # 2 hours for complex tasks
  max_turns: 50          # Generous limit for complex work

tiers:
  - T2
  - T3
  - T4
  - T5

runs_per_tier: 10

validation:
  criteria_file: "expected/criteria.md"
  rubric_file: "expected/rubric.yaml"
  reference_patch: "expected/reference/reference.patch"

evaluation:
  output_format: "patchfile_and_workspace"
  patchfile_command: "git diff HEAD"
```

### 4. Generate Reference Patch

```bash
gh pr diff <pr-number> --repo owner/repo > expected/reference/reference.patch
```

### 5. Create Forbidden Actions Document

Include in `constraints/forbidden.md`:
- NO git history access (git log, git show, git blame)
- NO GitHub API access (gh issue, gh pr, gh api)
- NO remote operations (git push, git fetch after clone)
- NO commit modification (git commit, git reset)
- NO web searches for the solution

### 6. Design Multi-Dimensional Rubric

```yaml
requirements:
  # Core Functionality (high weight)
  - id: "R001"
    description: "Primary deliverable created"
    weight: 3.0
    evaluation: "binary"

  # Patchfile Quality
  - id: "R005"
    description: "Changes are focused (no scope creep)"
    weight: 1.5
    evaluation: "scaled"

  # Code Quality
  - id: "R007"
    description: "Follows language idioms"
    weight: 1.0
    evaluation: "binary"

categories:
  functional_correctness:
    weight: 2.0
  semantic_alignment:
    weight: 2.0  # Match reference solution architecture
  completeness:
    weight: 1.5
  diff_quality:
    weight: 1.0

grading:
  pass_threshold: 0.70
  min_correctness: 0.80
```

### 7. Update LLM Judge for Patchfile Comparison

The judge should receive:
- Task prompt
- Agent output (stdout)
- Workspace state (files created/modified)
- Git diff (patchfile)
- Deleted files list
- Reference patch (for semantic comparison)

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| `max_turns` as test.yaml field only | Not threaded to Claude CLI | Add to ExperimentConfig, pass via adapter extra_args |
| 20 turn limit for complex task | Too restrictive for 15-file refactoring | Use 50+ turns for complex tasks |
| Full reference patch in judge prompt | 8211 lines too long for context | Truncate to 200 lines (100 first + 50 last) |
| Workspace state only (no patchfile) | Missing deleted files visibility | Add both patchfile AND deleted files list |

## Results & Parameters

### Recommended Parameters by Task Complexity

| Task Type | max_turns | timeout_seconds | Reference Patch Lines |
|-----------|-----------|-----------------|----------------------|
| Simple (1-3 files) | 20 | 1800 | 100 |
| Medium (3-10 files) | 30 | 3600 | 150 |
| Complex (10+ files) | 50 | 7200 | 200 |
| Very Complex (refactoring) | 100 | 10800 | 300 |

### Patchfile Truncation Settings

```python
# In judge prompt builder
max_lines = 500  # Agent's patchfile
if len(lines) > max_lines:
    half = max_lines // 2
    truncated = lines[:half] + ["... (truncated)"] + lines[-half:]

# Reference patch truncation
ref_max = 200
if len(ref_lines) > ref_max:
    ref_patch = ref_lines[:100] + ["... (truncated)"] + ref_lines[-50:]
```

### Judge System Prompt Additions

Add these criteria when reference provided:

```markdown
### Patchfile Quality Criteria (When Reference Provided)

11. **Semantic Alignment**: Same files created/modified/deleted?
12. **Change Minimality**: No unrelated modifications?
13. **Completeness vs Reference**: All key transformations implemented?

Note: Agent's solution does NOT need to be identical to reference.
Evaluate semantic equivalence, not exact match.
```

## References

- ProjectScylla PR #107 - Implementation of this pattern
- `/advise` skill - Search for related skills before starting
- `e2e-judge-rubric-design` skill - Rubric design patterns
- `dtype-native-migration` skill - Example reference solution documentation
