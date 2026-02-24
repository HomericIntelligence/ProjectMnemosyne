# Mojo Test Fixture Creation

Create comprehensive E2E test fixtures for evaluating AI agents on Mojo development tasks.

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Objective | Create test-002 for Mojo hello world task targeting Modular repo |
| Outcome | Successfully created 14-requirement test with 116 sub-tests |
| PR | https://github.com/HomericIntelligence/ProjectScylla/pull/110 |

## When to Use

- Creating new E2E test cases targeting Mojo repositories
- Designing rubrics aligned with Mojo v0.26.1 best practices
- Integrating ProjectOdyssey Mojo skills and agents into test tiers
- Building ablation tests across prompt/skill/tool/agent configurations

## Verified Workflow

### 1. Start with /advise

Search the skills marketplace for relevant Mojo skills before designing:

```bash
/advise I want to create a Mojo test fixture
```

Key skills to review:
- `mojo-lint-syntax` - v0.26.1 syntax validation
- `validate-mojo-patterns` - Constructor/method patterns
- `check-memory-safety` - Ownership validation

### 2. Define Test Structure

Create required files:

```
tests/fixtures/tests/test-XXX/
├── test.yaml           # Main definition (repo, commit, tiers)
├── prompt.md           # Task prompt for agent
├── config.yaml         # Timeout, cost limits
├── expected/
│   ├── criteria.md     # Detailed requirement descriptions
│   └── rubric.yaml     # Weighted scoring rubric
└── t0-t6/              # Tier sub-test directories
```

### 3. Design Mojo-Specific Requirements

Align requirements with judge system prompt weights:

| Category | Weight | Requirements |
|----------|--------|--------------|
| Functional (50%) | 7.5 pts | File creation, syntax, output |
| Build/Compile (22%) | 3.5 pts | mojo build, bazel, mojo format |
| Documentation (16%) | 2.5 pts | Docstrings, comments, README |
| Safety/Patterns (16%) | 2.5 pts | Memory safety, ownership, no deprecated |

### 4. Include Mojo v0.26.1 Criteria

Essential requirements for Mojo code:

```yaml
# R003: Mojo Syntax Compliance
criteria:
  - "fn main() entry point"
  - "print() function used"
  - "out self in constructors (not mut self)"
  - "mut self in mutating methods"
  - "No deprecated patterns (inout, @value, DynamicVector)"
  - "List literals [1, 2, 3] not List[Int](1, 2, 3)"
  - "Tuple return syntax -> Tuple[T1, T2]"

# R014: Code Formatting
criteria:
  - "mojo format --check passes"
```

### 5. Integrate ProjectOdyssey Skills

Add Mojo skills tier sub-test:

```yaml
# t1/11-mojo-skills/config.yaml
name: "Mojo Skills Bundle"
skills:
  - mojo-lint-syntax
  - validate-mojo-patterns
  - check-memory-safety
  - mojo-build-package
  - mojo-format
  - mojo-type-safety
  - mojo-test-runner
skills_source: "https://github.com/mvillmow/ProjectOdyssey/.claude/skills"
```

### 6. Add Mojo Agent Delegations

Add specialist agents to T3:

```yaml
# t3/42-mojo-syntax-validator/config.yaml
agent: mojo-syntax-validator
agent_source: "https://github.com/mvillmow/ProjectOdyssey/.claude/agents"

# t3/43-mojo-language-review/config.yaml
agent: mojo-language-review-specialist
```

### 7. Copy Tier Structure

Reuse existing tiers from reference test:

```bash
cp -r tests/fixtures/tests/test-001/t0 tests/fixtures/tests/test-XXX/
cp -r tests/fixtures/tests/test-001/t1 tests/fixtures/tests/test-XXX/
# ... t2 through t6
```

## Failed Attempts

| Attempt | Why It Failed | Solution |
|---------|---------------|----------|
| Initial plan without ProjectOdyssey | Missing external skill/agent integration | User reminded to add skills_source references |
| No mojo format requirement | Incomplete build validation | Added R014 after user feedback |

## Results & Parameters

### test.yaml Template

```yaml
id: "test-XXX"
name: "Mojo Task Name"
description: |
  Description of what agent must accomplish.

source:
  repo: "https://github.com/modular/modular"
  hash: "COMMIT_HASH"

task:
  prompt_file: "prompt.md"
  timeout_seconds: 7200

validation:
  criteria_file: "expected/criteria.md"
  rubric_file: "expected/rubric.yaml"

tiers:
  - T0  # Prompts (24 sub-tests)
  - T1  # Skills (11 sub-tests with Mojo bundle)
  - T2  # Tooling (15 sub-tests)
  - T3  # Delegation (43 sub-tests with Mojo agents)
  - T4  # Hierarchy (7 sub-tests)
  - T5  # Hybrid (15 sub-tests)
  - T6  # Super (1 sub-test)
```

### Rubric Weight Distribution

```yaml
grading:
  pass_threshold: 0.70
  grade_scale:
    A: 0.95
    B: 0.85
    C: 0.75
    D: 0.65
    F: 0.0

# Total: 16.0 points for 14 requirements
```

### Required Mojo Evaluation Skills

| Skill | Purpose | Source |
|-------|---------|--------|
| mojo-lint-syntax | v0.26.1 syntax | ProjectOdyssey |
| validate-mojo-patterns | out self, mut | ProjectOdyssey |
| check-memory-safety | Ownership, ^ operator | ProjectOdyssey |
| mojo-format | Code formatting | ProjectOdyssey |

## References

- [ProjectScylla test-001](https://github.com/HomericIntelligence/ProjectScylla/tests/fixtures/tests/test-001) - Reference implementation
- [Judge system prompt](https://github.com/HomericIntelligence/ProjectScylla/config/judge/system_prompt.md) - Scoring criteria
- [Mojo guidelines](https://github.com/HomericIntelligence/ProjectScylla/.claude/shared/mojo-guidelines.md) - v0.26.1 patterns
- [ProjectOdyssey skills](https://github.com/mvillmow/ProjectOdyssey/.claude/skills) - Mojo skill definitions
