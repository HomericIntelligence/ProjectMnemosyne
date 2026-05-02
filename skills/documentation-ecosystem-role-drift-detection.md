---
name: documentation-ecosystem-role-drift-detection
description: "Reconcile stale ecosystem role descriptions with actual implementation. Use when: (1) external docs describe a project differently than its code, (2) adding drift-detection tests to prevent doc/implementation divergence."
category: documentation
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags:
  - documentation
  - ecosystem
  - drift-detection
  - ablation
  - reconciliation
---

# Documentation: Ecosystem Role Drift Detection

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Reconcile ProjectScylla's ecosystem role from stale "chaos/resilience testing" description to actual "ablation benchmarking framework" implementation |
| **Outcome** | Successful — internal docs corrected, ADR created, drift-detection tests added (18 parametrized cases) |

## When to Use

- External architecture docs describe a project's role differently than its actual implementation
- Need to decide between "update docs" vs "add code" when documentation and implementation diverge
- Want to prevent future reintroduction of stale role descriptions via automated tests
- Auditing ecosystem documentation consistency across multiple projects

## Verified Workflow

### Quick Reference

```bash
# 1. Build alignment matrix — audit ALL role references
grep -rn "chaos\|resilience testing\|failure injection" README.md CLAUDE.md docs/

# 2. Fix inaccurate references (usually minimal — most internal docs are correct)
# Only change what's actually wrong, not everything tangentially related

# 3. Create ADR documenting the decision
# docs/dev/adr/ecosystem-role-reconciliation.md

# 4. Add drift-detection test
# tests/unit/docs/test_ecosystem_role_consistency.py

# 5. File cross-repo issue for external docs you can't directly modify
gh issue create --repo OtherOrg/OtherProject --title "Update architecture.md role for ProjectX"
```

### Detailed Steps

1. **Build an alignment matrix** — Audit every file that mentions the project's ecosystem role. For each, record: location, current description, whether it's accurate, and what action is needed. Most internal docs will already be correct; the problem is usually in external references.

2. **Decide: update docs or add code** — When docs say X but code does Y, the decision tree is:
   - Does the codebase have ANY code for X? → If zero, update docs (don't add code for stale claims)
   - Is the codebase purpose-built for Y with substantial investment? → Update docs to match reality
   - Adding code to match stale docs = scope creep with no supporting infrastructure

3. **Make minimal doc fixes** — Only change what's actually inaccurate. In the Scylla case, only ONE bullet in README.md needed updating ("Resilience Testing" → "Ablation Benchmarking"). The rest was already correct.

4. **Create an ADR** — Document the formal decision in `docs/dev/adr/`. Include: context (what the stale claim was), decision (formalize actual role), reasons (zero chaos code exists, 69K lines of ablation infra), consequences (cross-repo issue needed).

5. **Add drift-detection tests** — Parametrized pytest that scans key documentation files for forbidden phrases (stale claims) and verifies canonical role descriptions are present. This prevents future reintroduction.

6. **File cross-repo issues** — For external documentation you can't directly PR, file an issue in the other repository referencing your ADR and PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A — no failed approaches | Decision was straightforward: 69K lines of ablation code, zero chaos code | N/A | When implementation is overwhelmingly one thing, don't consider adding code to match stale docs |

## Results & Parameters

### Drift-Detection Test Pattern

```python
"""Drift-detection tests for ecosystem role description."""

from pathlib import Path
import re
import pytest

PROJECT_ROOT = Path(__file__).parents[3]

DOC_FILES = [
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "CLAUDE.md",
    PROJECT_ROOT / "docs" / "design" / "architecture.md",
]

FORBIDDEN_PHRASES = [
    r"chaos\s+(?:engineering|testing)",
    r"inject\s+failures",
    r"failure\s+injection",
    r"NATS\s+events?\s+from\s+ProjectHermes",
    r"resilience\s+testing",
]

@pytest.mark.parametrize("doc_path", [p for p in DOC_FILES if p.exists()])
@pytest.mark.parametrize("pattern", FORBIDDEN_PHRASES)
def test_no_stale_claims(doc_path: Path, pattern: str) -> None:
    content = doc_path.read_text()
    matches = re.findall(pattern, content, re.IGNORECASE)
    assert not matches, f"{doc_path.name} contains forbidden phrase: {matches}"

@pytest.mark.parametrize("doc_path", [p for p in DOC_FILES if p.exists()])
def test_canonical_role_present(doc_path: Path) -> None:
    content = doc_path.read_text().lower()
    assert ("testing" in content and "measurement" in content) or \
           "ablation" in content or "benchmark" in content
```

### Key Metrics

- **Files changed**: 1 modified (README.md), 2 created (ADR + test)
- **Test cases**: 18 parametrized (5 forbidden patterns x 3 docs + 3 canonical checks)
- **Test runtime**: 0.05s

### Alignment Matrix Template

| Location | Current Description | Accurate? | Action |
| ---------- | ------------------- | ----------- | -------- |
| `README.md` | "..." | Yes/No | Update/No change |
| `CLAUDE.md` | "..." | Yes/No | Update/No change |
| External repo | "..." | No | File cross-repo issue |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1503, PR #1547 | Reconciled ecosystem role from chaos testing to ablation benchmarking |
