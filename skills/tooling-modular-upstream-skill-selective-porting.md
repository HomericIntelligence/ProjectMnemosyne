---
name: tooling-modular-upstream-skill-selective-porting
description: "Port skills from Modular's official skills repo (Agent Skills Standard format) into ProjectMnemosyne with Apache 2.0 attribution. Use when: (1) integrating skills from modular/skills or similar Agent Skills Standard repos, (2) adapting directory-per-skill format to Mnemosyne flat-file format, (3) merging upstream content with existing overlapping skills, (4) handling Apache 2.0 attribution requirements for ported skills."
category: tooling
date: 2026-04-09
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [modular, mojo, skills, porting, apache-2.0, agent-skills-standard, modular-upstream, selective-port]
---

# Tooling: Modular Upstream Skill Selective Porting

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-09 |
| **Objective** | Port 4 skills from Modular's official skills repo (Agent Skills Standard format) into ProjectMnemosyne with Apache 2.0 attribution, adapting to flat-file format |
| **Outcome** | Successful — 3 new skills created, 1 merged into existing skill (v2.0.0 to v3.0.0), all 948 skills pass validation, PR #1213 created |
| **Verification** | verified-precommit — validation passes, PR created, CI pending |
| **Source** | https://github.com/modular/skills (Apache 2.0), PR #1213 |

## When to Use

- Porting skills from Modular's official `modular/skills` repo (or any Agent Skills Standard repo from agentskills.io)
- Converting directory-per-skill format (`skill-name/SKILL.md`) to Mnemosyne flat-file format (`skills/skill-name.md`)
- Merging upstream content into an existing skill rather than creating a duplicate
- Applying Apache 2.0 attribution (distinct from MIT — see attribution section)
- Deciding between `npx skills add` (automated install) vs manual selective port

## Verified Workflow

### Quick Reference

```bash
# Step 1: Clone and audit source repo
gh repo clone modular/skills /tmp/modular-skills
ls /tmp/modular-skills/  # directory-per-skill: mojo-syntax/SKILL.md, etc.

# Step 2: Examine source format (Agent Skills Standard)
cat /tmp/modular-skills/mojo-syntax/SKILL.md  # simple YAML: name + description only

# Step 3: Overlap analysis against existing skills
ls <project-root>/skills/ | grep mojo

# Step 4: Port each skill with format adaptation (see checklist below)
# Step 5: Validate
python3 scripts/validate_plugins.py

# Step 6: Commit, push, PR
```

### Detailed Steps

#### 1. Understand the Agent Skills Standard Format

The `modular/skills` repo uses the [Agent Skills Standard](https://agentskills.io) format:

| Feature | Agent Skills Standard | Mnemosyne Format |
|---------|----------------------|------------------|
| Structure | Directory per skill (`skill-name/SKILL.md`) | Flat file (`skills/skill-name.md`) |
| Frontmatter | `name` and `description` only | `name`, `description`, `category`, `date`, `version`, `verification`, `tags` |
| Sections | Free-form markdown (terse "correction layer" style) | Structured: Overview, When to Use, Verified Workflow, Failed Attempts, Results |
| Installation | `npx skills add modular/skills` | Manual copy + adaptation |

**Important:** Do NOT use `npx skills add` — it installs in Agent Skills Standard format which is incompatible with Mnemosyne's validator. Always do manual selective port.

#### 2. Overlap Analysis

Before porting, check for existing skills that cover the same topic:

```bash
# Search for overlapping skills
grep -rl "mojo.*syntax\|breaking.*change" <project-root>/skills/
```

**Decision matrix for overlaps:**

| Scenario | Action |
|----------|--------|
| Upstream covers same topic as existing skill | Merge into existing skill, bump version |
| Upstream covers new topic | Create new skill |
| Upstream content is subset of existing | Skip — existing skill is sufficient |

**modular/skills overlap analysis:**

| Source Skill | Decision | Reason |
|---|---|---|
| `mojo-syntax` | MERGE into `mojo-026-breaking-changes.md` | Overlapping Mojo syntax content; added "Authoritative Syntax Reference" section, bumped v2.0.0 to v3.0.0 |
| `mojo-gpu` | CREATE `mojo-gpu-fundamentals-programming-guide.md` | New topic — GPU programming patterns |
| `mojo-python-interop` | CREATE `mojo-python-interop-patterns-guide.md` | New topic — Python/Mojo interop patterns |
| `modular-project-setup` | CREATE `tooling-modular-project-setup-wizard.md` | New topic — project scaffolding |

#### 3. Format Adaptation Checklist

For each skill being ported, apply all of these:

```
[ ] Add full Mnemosyne YAML frontmatter (category, date, version, verification, tags)
[ ] Add `modular-upstream` tag for traceability
[ ] Restructure into required sections (Overview table, When to Use, Verified Workflow, Failed Attempts, Results)
[ ] For Failed Attempts on upstream-sourced skills with no local experimentation, use: "(none -- sourced from upstream)"
[ ] Add Apache 2.0 attribution footer on each ported file
[ ] Cross-reference related existing skills in the skill body
[ ] If merging into existing skill: preserve all existing Failed Attempts and battle-tested content
[ ] Validate: python3 scripts/validate_plugins.py
```

#### 4. Apache 2.0 Attribution

Add this footer to every ported skill file:

```markdown
---
*Adapted from [modular/skills](https://github.com/modular/skills) under Apache License 2.0.
Copyright (c) Modular Inc.*
```

Create `THIRD_PARTY_LICENSES.md` at the **repo root** (NOT in `skills/` — the validator rejects files without frontmatter in that directory):

- Apache 2.0 license text
- Source repo link
- Table mapping each ported skill to its source
- Date of derivation

#### 5. Merge Strategy for Overlapping Skills

When upstream content overlaps with an existing skill:

1. Keep all existing content intact (especially Failed Attempts — these are battle-tested)
2. Add upstream content as a clearly labeled new section (e.g., "Authoritative Syntax Reference (Modular)")
3. Bump the version (minor for additive content, major for restructuring)
4. Add the `modular-upstream` tag to the existing skill's tag list
5. Update the Overview table to reflect the merge

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Placed THIRD_PARTY_LICENSES.md in skills/ directory | Centralized license file alongside skill files | Validator rejected it — all files in skills/ must have YAML frontmatter | Always place non-skill files (licenses, READMEs) at repo root, not in skills/ |
| Considered `npx skills add modular/skills` automated install | Would save manual porting effort | Installs in Agent Skills Standard format (directory-per-skill), incompatible with Mnemosyne validator and flat-file convention | Always do manual selective port when target format differs from source |
| Considered creating separate `mojo-syntax.md` skill | Would be a 1:1 port of upstream | Duplicates content already in `mojo-026-breaking-changes.md` | Merge overlapping upstream content into existing skills rather than creating duplicates |

## Results & Parameters

### Source Repository Details

```yaml
source: https://github.com/modular/skills
license: Apache 2.0
format: Agent Skills Standard (agentskills.io)
total_skills: 4
total_lines: ~1557
install_command: npx skills add modular/skills  # NOT recommended — use manual port
```

### Skills Ported

| Ported/Updated Skill | Source Skill | Action | Category |
|---|---|---|---|
| `mojo-026-breaking-changes.md` (v3.0.0) | `mojo-syntax` | Merged — added "Authoritative Syntax Reference" section | training |
| `mojo-gpu-fundamentals-programming-guide.md` | `mojo-gpu` | Created new | optimization |
| `mojo-python-interop-patterns-guide.md` | `mojo-python-interop` | Created new | architecture |
| `tooling-modular-project-setup-wizard.md` | `modular-project-setup` | Created new | tooling |

### Validation

```bash
python3 scripts/validate_plugins.py
# Expected: 948 skills validated, 0 errors
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | Modular skills integration, PR #1213 | 4 skills ported (3 new, 1 merged) from Apache 2.0 repo, all 948 pass validation |

## References

- [modular/skills](https://github.com/modular/skills) — Source repository (Apache 2.0)
- [Agent Skills Standard](https://agentskills.io) — Format specification
- [tooling-claude-plugin-third-party-skill-porting](tooling-claude-plugin-third-party-skill-porting.md) — Prior art: obra/superpowers porting (MIT license)
- [tooling-skill-deduplication-semver-versioning](tooling-skill-deduplication-semver-versioning.md) — Deduplication and version bumping guidance
