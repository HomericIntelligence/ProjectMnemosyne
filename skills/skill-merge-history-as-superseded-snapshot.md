---
name: skill-merge-history-as-superseded-snapshot
description: "Pattern for preserving absorbed skill content when merging N narrow skills into 1 canonical. Use when: (1) a merge PR deletes multiple narrow skills and you need to retain their full body for grep/advise searchability, (2) you want deletions to be reversible-by-inspection without git-log archaeology, (3) you need an audit trail that /advise can surface for absorbed skill triggers."
category: tooling
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [skill-merge, history, superseded, canonical, audit-trail, deletion, advise]
---

# Skill Merge — History as Superseded Snapshot

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Preserve full content of absorbed skills when a merge PR consolidates N narrow skills into 1 canonical and deletes the originals |
| **Outcome** | Successful — 20 PRs auto-merged on green CI using this pattern |
| **Verification** | verified-ci |

## When to Use

- A merge PR consolidates multiple narrow skills into one canonical skill and deletes the originals
- You need deleted skills to remain searchable and reversible without `git log` archaeology
- The `/advise` traffic from absorbed skill triggers must continue surfacing the new canonical
- You want a structured audit trail that validators can grep and enforce

## Verified Workflow

### Quick Reference

```bash
# 1. Create the .history file for the canonical skill
cat > skills/<canonical-name>.history << 'EOF'
# <canonical-name> — History

## v1.0.0 (YYYY-MM-DD)

**Changed by:** Merge — absorbed <N> narrow skills
**Verification:** verified-ci

### What changed
- Initial canonical version, absorbing: skill-a, skill-b, skill-c

### Superseded from skill-a

```yaml
name: skill-a
description: "..."
category: tooling
date: YYYY-MM-DD
version: "1.0.0"
...
```

`<full body of skill-a verbatim>`

---

### Superseded from skill-b

```yaml
name: skill-b
...
```

`<full body of skill-b verbatim>`

---
EOF

# 2. Reference .history from the canonical's frontmatter
# Add to skills/`<canonical-name>`.md YAML frontmatter
# history: `<canonical-name>`.history

# 3. Sweep-delete the absorbed skills (skip-missing-safe)
for f in $(jq -r '.absorbed_skills[]' manifest.json); do
  git rm "skills/$f.md" "skills/$f.notes.md" "skills/$f.history" 2>/dev/null || true
done
```

### Detailed Steps

1. **Identify absorbed skills** — List every narrow skill that will be deleted in the merge PR.
   Their names become the `## Superseded from <name>` section headings.

2. **Read each absorbed skill in full** — Before deleting, read both `.md` and `.notes.md` (if
   present) for each skill to be absorbed.

3. **Create `skills/<canonical-name>.history`** — Use the format below. Each absorbed skill
   gets its own `## Superseded from <skill-name>` section containing:
   - The original YAML frontmatter as a fenced ` ```yaml ` block
   - The full body verbatim (all markdown sections)

4. **Reference history from canonical frontmatter** — Add `history: <canonical-name>.history`
   to the canonical's YAML frontmatter. Validators will fail if this field names a non-existent
   file.

5. **Canonicalize the `description` field** — Incorporate the "Use when:" triggers from all
   absorbed skills so `/advise` keyword search continues to surface the canonical.

6. **Delete absorbed skill files** — Use `git rm` (not `rm`) so the deletion is tracked:

   ```bash
   for f in skill-a skill-b skill-c; do
     git rm "skills/$f.md" 2>/dev/null || true
     git rm "skills/$f.notes.md" 2>/dev/null || true
     git rm "skills/$f.history" 2>/dev/null || true
   done
   ```

7. **Validate** — Run `python3 scripts/validate_plugins.py`. The validator checks:
   - `history:` frontmatter field matches the actual `.history` filename
   - All five required markdown sections are present in the canonical

8. **Commit both canonical and history together**:

   ```bash
   git add skills/<canonical-name>.md skills/<canonical-name>.history
   git commit -m "feat(skill-merge): absorb <N> skills into canonical <name>"
   ```

## Superseded-From Section Template

Copy-paste template for each absorbed skill block inside the `.history` file:

```markdown
### Superseded from <absorbed-skill-name>

**Original date:** YYYY-MM-DD
**Original version:** X.Y.Z

```yaml
name: <absorbed-skill-name>
description: "..."
category: <category>
date: YYYY-MM-DD
version: "X.Y.Z"
verification: <level>
tags: []
```

### Overview

`<paste original Overview table>`

### When to Use

`<paste original When to Use bullets>`

### Verified Workflow

`<paste original workflow content>`

### Failed Attempts

`<paste original Failed Attempts table>`

### Results & Parameters

`<paste original Results & Parameters content>`

---
```

## Key Invariants

| Rule | Rationale |
| ------ | ----------- |
| Canonical `.md` stays under 700 LOC | Readability — reviewers can skim a PR diff |
| `.history` file is unbounded in size | Every absorbed body must be verbatim — no summarizing |
| Heading is exactly `## Superseded from <skill-name>` | Enables `grep "Superseded from" skills/*.history` audits |
| `history:` frontmatter must match actual filename | Validators auto-reject mismatches |
| YAML frontmatter of absorbed skill is a fenced code block | Preserves structure without confusing the YAML parser |
| Canonical `description` incorporates all absorbed triggers | `/advise` keyword search must still surface the canonical |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | --------------- |
| Summary-only history | Wrote a brief "what changed" paragraph per absorbed skill instead of full body | Lost the ability to recover absorbed skill content without `git log` | Always paste the full original body verbatim |
| In-place amendment style | Used same `.history` format as a version-bump amendment (recording diffs only) | Diffs are meaningless when the entire file is being deleted | Merges record absorbed bodies, amendments record what changed |
| Omitting frontmatter reference | Created `.history` but did not add `history:` field to canonical `.md` | Validator rejected the skill file with "orphan history file" error | Always add `history:` field to canonical frontmatter first |
| Deleting with `rm` instead of `git rm` | Used shell `rm` to remove absorbed skill files | Files showed as unstaged deletions; history file was not staged | Always use `git rm` so deletions are tracked in the commit |
| Merging triggers into a single long description | Concatenated all absorbed "Use when:" items verbatim | Description exceeded single-line limit and failed YAML parsing | Summarize trigger themes; keep description under ~300 characters |

## Results & Parameters

Expected outputs after following this workflow:

- `skills/<canonical-name>.md` — under 700 LOC, references `.history` in frontmatter
- `skills/<canonical-name>.history` — one `### Superseded from <name>` section per absorbed skill
- No remaining `.md` files for absorbed skills in `skills/`
- `python3 scripts/validate_plugins.py` exits 0
- `grep "Superseded from" skills/*.history` lists all absorbed skill names

Grep audit command for CI:

```bash
# Verify all absorbed skills are documented in .history files
grep -h "### Superseded from" skills/*.history | sort
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | 20 merge PRs, all auto-merged on green CI | Session 2026-05-18 |
