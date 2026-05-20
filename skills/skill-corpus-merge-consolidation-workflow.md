---
name: skill-corpus-merge-consolidation-workflow
description: "Workflows for maintaining a skills corpus: deduplicating overlapping skills, merging clusters into canonicals, preserving history snapshots, enumerating cluster members from examples, migrating formats (hierarchical→flat, dual-dir→single), and generalizing skills for cross-repo compatibility. Use when: (1) multiple skills share a common prefix and cover redundant content, (2) a merge epic lists only example members and a full member list is needed, (3) a merge PR deletes originals and their content must remain searchable, (4) legacy skills/<category>/<name>/SKILL.md files need migration to flat skills/<name>.md format, (5) skills have hardcoded repo paths that must be generalized, (6) a dual plugins/+skills/ directory must be consolidated, (7) bulk-migrating skills from one project to another, (8) a skill topic is now OBSOLETE and needs a prominent notice."
category: tooling
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: skill-corpus-merge-consolidation-workflow.history
tags: [skill-merge, deduplication, semver, consolidation, history, manifest, enumeration, flat-format, migration, plugin-generalization, corpus-maintenance]
---

# Skill Corpus Merge Consolidation Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Consolidate all skills-corpus maintenance operations: deduplication, cluster merges, history preservation, member enumeration, format migration, and cross-repo generalization |
| **Outcome** | Absorbed 8 narrow skills covering overlapping corpus-maintenance topics |
| **Verification** | verified-ci |
| **History** | [absorbed skills](./skill-corpus-merge-consolidation-workflow.history) |

## When to Use

- Multiple skills share a common prefix (`pr-review-*`, `mojo-test-*`) or cover the same topic
- `/advise` returns redundant or contradictory advice for the same query
- A merge epic provides only 3 representative examples and you need the full member list
- A merge PR deletes originals and their full body must remain searchable via grep or `/advise`
- `find skills/ -type d -mindepth 1` returns results — legacy nested format still present
- Skills have `source: ProjectName` in frontmatter or hardcoded repo-specific paths
- A dual `plugins/` + `skills/` directory structure is causing contributor confusion
- Porting skills from a source repo to ProjectMnemosyne for the first time (bulk migration)
- A skill topic is OBSOLETE (underlying bug/workaround fixed) and needs a prominent notice

## Verified Workflow

### Quick Reference

```bash
# Detect duplicate clusters by 2-part prefix
ls skills/*.md | grep -v notes.md | grep -v history | sed 's|skills/||;s|\.md$||' | \
  awk -F'-' '{print $1"-"$2}' | sort | uniq -c | sort -rn | head -20

# Enumerate full cluster from marketplace.json (no file reads)
python3 - <<'EOF'
import json, difflib
from collections import defaultdict
with open('marketplace.json') as f:
    skills = json.load(f)
prefix2 = defaultdict(list)
for s in skills:
    parts = s['name'].split('-')
    if len(parts) >= 2: prefix2['-'.join(parts[:2])].append(s['name'])
for k, v in sorted(prefix2.items(), key=lambda x: -len(x[1])):
    if len(v) >= 3: print(len(v), k, v)
EOF

# Skip-missing-safe deletion of absorbed originals
for f in skill-a skill-b skill-c; do
  [ -f "skills/$f.md" ]    && git rm "skills/$f.md"    || echo "skip $f.md"
  [ -f "skills/$f.notes.md" ] && git rm "skills/$f.notes.md" || true
  [ -f "skills/$f.history"   ] && git rm "skills/$f.history"  || true
done

# Detect legacy hierarchical skills
find skills/ -type d -mindepth 1
find skills/ -name "SKILL.md"

# Validate
python3 scripts/validate_plugins.py
```

### Part A — Deduplication and Cluster Merging

**Phase 1: Identify duplicate clusters**

1. List all skill names, extract 2-part prefixes, count occurrences (see Quick Reference)
2. For large registries (900+), use `marketplace.json` — no need to read 975 files
3. Use `difflib.SequenceMatcher` at >80% threshold to find semantically similar descriptions
4. Manually group by intent for different-named skills covering the same concept

**Phase 2: Enumerate full member list (when epic gives only examples)**

When an issue lists only 3 examples per cluster:

1. Dispatch one Haiku enumeration agent per cluster (isolated, non-bundled)
2. Each agent reads the 3 examples → greps corpus → decides IN or OUT per candidate
3. Agent writes `/tmp/skill-merge-manifests/<cluster_id>.json`:

```json
{
  "cluster_id": "MXX",
  "canonical_name": "kebab-case-canonical-name",
  "absorbed_skills": ["skill-a.md", "skill-b.md"],
  "boundary_notes": "Excludes swarm meta-skills",
  "estimated_loc_after_merge": 420,
  "overflow_warning": false
}
```

4. Gate 1 — cross-cluster duplicate check before any merge launches:

```bash
jq -r '.absorbed_skills[]' /tmp/skill-merge-manifests/*.json | sort | uniq -d
```

5. For second-pass sessions (existing canonicals from prior wave), pass the existing-canonicals list to every enumeration agent and require two-bucket output: `clusters[]` (new only) + `absorb_into_canonical[]`

**Protected meta-skills (always exclude from every manifest)**:

```
worktree-parallel-agent-execution
myrmidon-swarm-end-to-end-orchestration-full-workflow
tooling-sub-agent-pr-trust-but-verify
tooling-myrmidon-swarm-prompt-guardrails-reduce-stall-rate
stop-reassess-gate-bulk-transformation
```

**Phase 3: Merge each cluster**

1. Read ALL source skills — extract unique content (deduplicate by lesson/concept, not exact text)
2. Write consolidated skill at `skills/<merged-name>.md` with `version: "1.0.0"`
3. Create `skills/<merged-name>.history` with `## Superseded from <name>` per absorbed skill (see Part B)
4. Delete all source `.md`, `.notes.md`, and `.history` files (skip-missing-safe)
5. Parallel agents: assign non-overlapping files to avoid conflicts; 3 at a time for large batches

**Special case: OBSOLETE topics**

When the underlying topic is no longer applicable (bug fixed at compiler level):

```markdown
## <Topic> Status: OBSOLETE

> **<Topic> has been fixed.** <Brief explanation.>
>
> **Do NOT use this skill to implement <workaround> on new code.**
>
> This skill is preserved for historical reference only.
```

Consolidate to 1 file even if subtopics were well-organized — the OBSOLETE notice is the
dominant content and must not be fragmented across multiple files.

### Part B — History Preservation (Superseded Snapshots)

When a merge PR deletes originals, create `skills/<canonical-name>.history`:

```bash
# Template per absorbed skill
cat >> skills/<canonical-name>.history << 'EOF'
## Superseded from <absorbed-skill-name>

**Original date:** YYYY-MM-DD
**Original version:** X.Y.Z

```yaml
name: <absorbed-skill-name>
description: "..."
category: <category>
date: YYYY-MM-DD
version: "X.Y.Z"
```

`<full body verbatim>`

---
EOF
```

Key invariants:

| Rule | Rationale |
| ------ | ----------- |
| Heading is exactly `## Superseded from <name>` | Enables `grep "Superseded from" skills/*.history` audits |
| Full body verbatim — no summarizing | Content must be recoverable without `git log` |
| `history:` frontmatter references actual filename | Validator rejects mismatches |
| Canonical `description` incorporates all absorbed triggers | `/advise` search continues to surface canonical |
| Canonical `.md` stays under 700 LOC | Reviewers can skim PR diff |

### Part C — Format Migration (Hierarchical → Flat)

When `find skills/ -type d -mindepth 1` returns results:

```bash
# For each legacy skill at skills/<cat>/<name>/skills/<name>/SKILL.md
cp skills/<cat>/<name>/skills/<name>/SKILL.md skills/<name>.md
cp skills/<cat>/<name>/references/notes.md skills/<name>.notes.md   # if present
rm -rf skills/<cat>/<name>/
rmdir skills/<cat>/  # only if empty

# Verify required frontmatter fields after copy
# Add version: "1.0.0" if missing (common in partial migrations)
```

For migration scripts that copy skills between projects:

```python
# Idempotent bulk migration pattern
def migrate_skill(skill_name, source_dir, dest_dir, dry_run=False):
    if skill_already_exists(skill_name, dest_dir):
        return False  # skip
    # Copy SKILL.md + ALL subdirs (scripts/, templates/, hooks/, references/)
    import shutil
    source_dir_path = source_skill_md.parent
    for subdir in sorted(source_dir_path.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("."):
            continue
        dest = plugin_dir / "references" if subdir.name == "references" \
               else skill_md_dir / subdir.name
        shutil.copytree(subdir, dest, dirs_exist_ok=True)  # dirs_exist_ok for idempotency
```

### Part D — Directory Consolidation (dual plugins/ + skills/)

When both `plugins/<category>/<name>/` and `skills/<name>/` exist:

```bash
for category in plugins/*/; do
  cat_name=$(basename "$category")
  for plugin in "$category"*/; do
    plugin_name=$(basename "$plugin")
    [ "$cat_name/$plugin_name" = "tooling/mnemosyne" ] && continue
    mkdir -p "skills/$cat_name"
    [ -d "skills/$cat_name/$plugin_name" ] && rm -rf "skills/$cat_name/$plugin_name"
    mv "$plugin" "skills/$cat_name/$plugin_name"
  done
  [ "$cat_name" != "tooling" ] && rmdir "$category" 2>/dev/null
done
```

Critical: detect in-place migrations (`target_dir == legacy_dir`) and skip file copies to avoid
`shutil.rmtree` deleting references before copy.

### Part E — Cross-Repo Generalization

```bash
# Find skills with repo-specific source field
grep -r "^source:" skills/ --include="*.md"

# Batch remove source lines
for file in skills/*.md; do
  sed -i '/^source: ProjectName$/d' "$file"
done
```

Replace hardcoded values with placeholders (longest patterns first):

| Placeholder | Replaces |
| ------------- | --------- |
| `<project-root>` | `/home/username/ProjectName/` |
| `<package-manager>` | `pixi run`, `npm run`, etc. |
| `<test-path>` | `tests/shared/core/` |
| `<pr-number>` | Embedded PR numbers in workflow text |

Add "Verified On" table to each generalized skill. Move project-specific details to `references/notes.md`.

### Semver Rules for Skill Amendments

| Change Type | Bump | When |
| ------------- | ------ | ------ |
| Major (X.0.0) | `1.0.0` → `2.0.0` | Merge skills, rewrite workflow, change core recommendation |
| Minor (0.X.0) | `1.0.0` → `1.1.0` | Add findings, failed attempts, extend workflow |
| Patch (0.0.X) | `1.0.0` → `1.0.1` | Fix typos, formatting, metadata |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct merge without enumeration phase | Merge agent given 3 examples and told to discover the rest | Agent stalled or drifted scope — no definitive boundary | Always enumerate first; merge agents need a fixed manifest |
| Single agent enumerating all clusters | One agent iterated all 17 clusters sequentially | Cross-contamination: agent conflated keywords across adjacent clusters | One enumeration agent per cluster, fully isolated |
| Omitting protected meta-skill exclusions | Enumeration agents allowed to include any skill | Cluster absorbed and deleted its own tooling | Hard-code the protected list in every enumeration agent prompt |
| Skipping Gate 1 duplicate check | Manifests shipped directly to merge agents | Same skill appeared in two merge PRs, causing double-deletion | Gate 1 duplicate detection is mandatory before any merge launches |
| Parallel agents in same worktree conflicting | Launched 3 agents to merge 3 groups simultaneously | Worked fine — no conflicts since each agent writes different files | Parallel agents in a shared worktree work when they touch non-overlapping files |
| Major-only version bumps | Always bump X.0.0 for any amendment | Loses information about change scale | Use semver: Major for rewrites/merges, Minor for new findings, Patch for typos |
| Merging by exact text dedup | Deduplicated Failed Attempts by exact row match | Different skills describe the same lesson with different wording | Deduplicate by lesson/concept, not by exact text match |
| Forgetting .notes.md files | Deleted .md but forgot accompanying .notes.md | Orphaned .notes.md files clutter the skills directory | Always delete both .md and .notes.md when removing source skills |
| Summary-only history | Wrote brief summary per absorbed skill instead of full body | Lost ability to recover absorbed content without `git log` | Always paste the full original body verbatim |
| In-place amendment style for merge history | Used diff-only history format | Diffs are meaningless when the entire file is being deleted | Merges record absorbed bodies; amendments record what changed |
| Omitting frontmatter `history:` reference | Created .history but omitted `history:` in canonical .md | Validator rejected with "orphan history file" error | Always add `history:` to canonical frontmatter |
| Deleting with `rm` instead of `git rm` | Used shell `rm` to remove absorbed skill files | Files showed as unstaged deletions; not tracked in commit | Always use `git rm` so deletions are tracked |
| Stopping at 3 sub-skills when topic is OBSOLETE | Organized 12 skills into 3 well-structured sub-skills | When topic declared OBSOLETE, notice was fragmented across 3 files | When a topic is OBSOLETE, consolidate to 1 — notice is the dominant content |
| Assuming deduplication is durable | Merged cluster once, assumed stable | Subsequent `/learn` calls re-created duplicate skills organically | Schedule periodic re-consolidation passes |
| Reading all 975 skill files for detection | Tried to read every `.md` to find duplicates | Extremely slow; times out and wastes context | Use `marketplace.json` (names + descriptions) — no file reads needed for detection |
| Committing directly to main | Made dedup commits on main branch | Bypasses PR review process | Always use a feature branch via git worktree |
| Planning merges without checking file existence | Identified 42 groups, started merging | Many files already merged in prior sessions | Always `ls skills/<name>.md` before attempting to read or merge |
| Running second-pass without existing-canonicals list | Documentation-shard agent proposed clusters already existing as M16/M17 canonicals | 27 members had to be re-routed at gate stage | Always pass existing-canonicals list + require two-bucket output |
| Migration script copying only SKILL.md | `migrate_skill()` only wrote `.claude-plugin/plugin.json` + `SKILL.md` | Subdirs (`scripts/`, `templates/`) were silently dropped | Iterate `source_skill_md.parent` for all subdirs; copy with `shutil.copytree(..., dirs_exist_ok=True)` |
| `shutil.copytree` without `dirs_exist_ok` | Called `copytree(src, dest)` | `FileExistsError` on second migration run | Always use `dirs_exist_ok=True` for idempotent behavior |
| Placing `references/` alongside SKILL.md | `references/` inside `skills/<name>/` | Mnemosyne convention puts `references/` at plugin root | Check plugin layout spec before routing subdirs |
| In-place migration calling `shutil.rmtree` | Deleted refs before copying (src == dest) | Deleted the file being copied | Detect `target_dir == legacy_dir` and skip file copies |
| Assumed SKILL.md needed full rewrite | Expected old format without frontmatter | All 4 legacy files already had YAML frontmatter | Check SKILL.md content before assuming full rewrite needed |
| Forgot `version` field after copying SKILL.md | Copied SKILL.md without checking required fields | 3 of 4 were missing `version: "1.0.0"` and failed validation | Always verify all required frontmatter fields after copy |
| Bulk removing `source:` without checking URL sources | Removed all `^source:` lines | Removed legitimate `source: https://...` references | Keep URL sources; only remove project-name sources (`source: ProjectName`) |

## Results & Parameters

### Deduplication Scale Examples

| Session | Skills Before | Skills After | Net Reduction | Method |
| --------- | -------------- | ------------ | -------------- | -------- |
| test-splitting cluster | 16 | 3 | -13 (-81%) | Prefix grouping |
| mojo-test-* cluster | 10 | 1 | -9 (-90%) | Prefix grouping |
| deprecated-file-cleanup-* | 6 | 1 | -5 (-83%) | Prefix grouping |
| conv2d-gradient-* cluster | 9 | 3 | -6 (-67%) | Topic sub-grouping |
| Large-scale algorithmic pass | 975 | 933 | -42 (-4.3%) | marketplace.json + SequenceMatcher |

### Algorithmic Detection Parameters

```python
threshold = 0.80  # >80% SequenceMatcher ratio = near-duplicate
prefix_min_cluster_size = 3  # min skills sharing prefix to flag as cluster
cap_absorbed_skills = 100    # overflow_warning: true above this
```

### Bulk Migration Script Parameters

| Parameter | Default | Description |
| ----------- | --------- | ------------- |
| `--dry-run` | false | Show planned actions without creating files |
| `--skill NAME` | all | Migrate only a specific skill by name |
| `--force` | false | Overwrite skills that already exist |
| `--skip-existing` | true | Skip skills already present (idempotency guard) |

### Category Mapping (bulk migration from legacy source)

| Source Category | Mnemosyne Category |
| --- | --- |
| `github`, `worktree`, `agent`, `plan`, `generation` | `tooling` |
| `ci`, `phase` | `ci-cd` |
| `mojo` | `architecture` |
| `doc` | `documentation` |
| `quality`, `review` | `evaluation` |
| `testing` | `testing` |
| `analysis`, `ml` | `optimization` |
| `training` | `training` |

### Validation Commands

```bash
python3 scripts/validate_plugins.py
npx markdownlint-cli2 skills/*.md

# Grep audit for absorbed skills in history files
grep -h "### Superseded from" skills/*.history | sort

# Confirm no legacy nested skills remain
find skills/ -type d -mindepth 1
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | PR #1040, merged 16 test-splitting skills + added semver | 2026-03-25 |
| ProjectMnemosyne | PR #1075–#1097, six deduplication rounds | 2026-03-27 to 2026-03-28 |
| ProjectMnemosyne | Large-scale algorithmic pass: 975 → 933 skills (-42) | 2026-04-07 |
| ProjectMnemosyne | PR #183, dual plugins/+skills/ → single skills/ (971 files changed) | 2026-02-23 |
| ProjectMnemosyne | PR #326, bulk migration of 4 worktree skills from ProjectOdyssey2 | 2026-03-04 |
| ProjectMnemosyne | PR #1017, migrated last 4 hierarchical skills to flat format | 2026-03-25 |
| ProjectMnemosyne | 20 merge PRs using history-as-superseded-snapshot pattern | 2026-05-18 |
| ProjectMnemosyne | 17-cluster 1100-skill consolidation with manifest-first enumeration | 2026-05-19 |
