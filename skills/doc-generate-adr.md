---
name: doc-generate-adr
description: Generate Architecture Decision Records (ADRs) to document significant
  architectural decisions
category: architecture
date: 2025-12-30
version: 1.0.0
---
# Generate Architecture Decision Records

Create Architecture Decision Records for technical decisions.

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2025-12-30 | Standardized architectural documentation | Consistent, traceable technical decisions |

## When to Use

- (1) Making significant architectural decisions
- (2) Choosing between technical alternatives
- (3) Documenting design trade-offs
- (4) Recording rationale for future reference

## Verified Workflow

1. **Identify decision** - What choice needs documentation?
2. **Research alternatives** - Gather evidence and performance data
3. **Create ADR** - Run script or manually create file
4. **Fill sections** - Context, Decision, Rationale, Consequences, Alternatives
5. **Review** - Get team approval
6. **Update status** - Change from "Proposed" to "Accepted"

## Results

Copy-paste ready commands:

```bash
# Create new ADR (if script available)
./scripts/create_adr.sh "Decision Title"

# Manual creation
mkdir -p docs/adr
cat > docs/adr/ADR-XXX-decision-title.md << 'EOF'
# ADR-XXX: Decision Title

**Status**: Proposed
**Date**: $(date +%Y-%m-%d)
**Deciders**: [Names/roles]

## Context
What is the issue we're facing?

## Decision
What decision are we making?

## Rationale
Why this decision? Key reasons.

## Consequences
### Positive
- Benefit 1

### Negative
- Drawback 1

## Alternatives Considered
### Alternative 1
Why not chosen.
EOF
```

### ADR Format Template

```markdown
# ADR-XXX: Title

**Status**: Proposed | Accepted | Deprecated | Superseded
**Date**: YYYY-MM-DD
**Deciders**: Names/roles

## Context
What is the issue we're facing?

## Decision
What decision are we making?

## Rationale
Why this decision? Key reasons.

## Consequences
### Positive
- Benefit 1

### Negative
- Drawback 1

### Neutral
- Other impact 1

## Alternatives Considered
### Alternative 1
Why not chosen.
```

### Status Lifecycle

- **Proposed** - Under consideration
- **Accepted** - Decision made and active
- **Deprecated** - No longer recommended
- **Superseded** - Replaced by newer ADR

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Error Handling

| Problem | Solution |
| --------- | ---------- |
| Missing context | Add background and constraints |
| Unclear decision | Make decision more specific |
| Missing alternatives | Document at least 2 alternatives |
| No consequences | Think through positive and negative impacts |

## References

- See existing ADRs in `/docs/adr/` for examples
- Related skill: doc-validate-markdown for markdown validation
