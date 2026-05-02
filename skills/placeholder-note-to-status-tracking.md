---
name: placeholder-note-to-status-tracking
description: 'Clarify ambiguous NOTE: runtime print statements as intentional placeholders
  by converting them to STATUS: messages with GitHub tracking issue links. Use when:
  (1) example/demo scripts print confusing NOTE messages during execution, (2) cleanup
  issues require disambiguating placeholder code from bugs.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# Skill: placeholder-note-to-status-tracking

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-04 |
| Objective | Resolve GitHub issue #3084 — clarify backward pass NOTEs in ML example training scripts |
| Outcome | Success — 3 files updated, 3 GitHub tracking issues created, PR #3189 merged |
| Category | documentation |

## When to Use

Use this skill when:

- Example or demo scripts contain `print("NOTE: ...")` statements at runtime that imply
  something is broken or incomplete, but the behavior is actually intentional
- A cleanup issue (e.g., `[Cleanup] Track backward pass NOTEs`) asks you to disambiguate
  placeholder code from unimplemented code
- In-docstring `# NOTE:` comments are appropriate, but runtime `print("NOTE: ...")` calls
  are not — the latter run during execution and confuse users
- The fix strategy is to *clarify* (not implement) — i.e., the backward passes are
  intentional simplifications, not bugs

**Key distinction**: `# NOTE:` in docstrings is fine (documentation). `print("NOTE: ...")` at runtime
is confusing because it appears as if something failed during execution.

## Verified Workflow

### 1. Read issue context first

```bash
gh issue view <number> --comments
```

The issue comments often contain a fully detailed implementation plan (see issue #3084).
Read it before starting — it specifies which lines to change and what approach to take.

### 2. Triage the NOTE occurrences

Enumerate all occurrences across affected files. Classify each as:

- **In-docstring** `# NOTE:` — appropriate; leave as-is
- **Runtime `print("NOTE: ...")`** — confusing; replace with `STATUS:` + issue link

For issue #3084, the affected files were:

| File | Line | Type | Action |
| ------ | ------ | ------ | -------- |
| `examples/resnet18-cifar10/train.mojo` | 313 | Runtime print | Replace |
| `examples/googlenet-cifar10/train.mojo` | 97 | Docstring | Leave |
| `examples/googlenet-cifar10/train.mojo` | 436 | Runtime print | Replace |
| `examples/mobilenetv1-cifar10/train.mojo` | 65 | Docstring | Leave |
| `examples/mobilenetv1-cifar10/train.mojo` | 215 | Runtime print | Replace |

### 3. Create GitHub tracking issues first

Before editing files, create one tracking issue per model/component:

```bash
gh issue create \
  --title "[Implementation] Full backward pass for <Model> training script" \
  --body "$(cat <<'EOF'
## Objective
Implement the full backward pass...

## Estimated Scope
~N lines

## Dependencies
- Depends on #<parent>
- Tracked in #<cleanup-issue>
EOF
)" \
  --label "implementation"
```

Record the issue numbers returned. These go into the STATUS prints and README links.

### 4. Replace runtime NOTE prints with STATUS prints

Pattern:

```mojo
# Before (confusing — implies something is broken):
print("NOTE: Full backward pass implementation would require ~3500 lines.")
print("      This is a placeholder showing the structure.")
print(
    "      For actual training, consider using automatic differentiation."
)

# After (clear — explains intent and points to tracking issue):
print("STATUS: Backward pass shown above is a documented placeholder (~3500 lines for full impl).")
print("        Full implementation tracked in GitHub issue #3184.")
print("        For actual training, consider using automatic differentiation.")
```

Key changes:
- `NOTE:` → `STATUS:` (communicates information, not warning)
- Add "documented placeholder" language (explicit that this is intentional)
- Add GitHub issue number so users know where to follow progress
- Remove the multi-line `print(...)` style in favor of plain `print("...")` for consistency

### 5. Update README Implementation Status sections

For each affected model's README, add a `### Pending (Intentional Placeholder)` section:

```markdown
### Pending (Intentional Placeholder)

- [ ] **Full backward pass**: ~N lines — tracked in [GitHub issue #XXXX](URL)
  - The training script demonstrates the structure but uses a placeholder backward pass
  - For actual training, consider using automatic differentiation
```

Place this section between the completed items list and `### Future Enhancements`.

### 6. Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

All hooks should pass. Changes are string replacements only — no logic changes.

### 7. Commit and PR

```bash
git add examples/*/train.mojo examples/*/README.md
git commit -m "docs(examples): clarify backward pass NOTEs as intentional placeholders

Replace ambiguous NOTE print statements with STATUS messages that
clearly communicate these are documented placeholders, not bugs.
Update README files to link to tracking issues.

Closes #<issue>

Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin <branch>
gh pr create --title "..." --body "..." --label "documentation,cleanup"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Changing in-docstring `# NOTE:` comments | Considered replacing `# NOTE:` at lines 97 (googlenet) and 65 (mobilenetv1) | These are appropriate documentation comments; changing them adds no value | In-docstring NOTEs are fine — only runtime `print("NOTE: ...")` calls confuse users |
| Generic STATUS message without issue link | Drafting "This is a documented placeholder" without a GitHub issue number | Users have no way to track when the implementation will happen | Always create tracking issues *before* editing prints so you can include the issue number in the message |
| Implementing the backward passes | Considered actually writing ~2000-3500 lines of backward pass code | Out of scope for a `[Cleanup]` issue; issue explicitly says "If not needed: update NOTEs to clarify" | Cleanup issues ask for documentation clarity, not full implementations |

## Results & Parameters

### Issue Numbers (for ProjectOdyssey)

| Model | Tracking Issue | Lines |
| ------- | --------------- | ------- |
| ResNet-18 | #3181 | ~2000 |
| GoogLeNet | #3184 | ~3500 |
| MobileNetV1 | #3187 | ~2000 |

### Files Changed

```text
examples/resnet18-cifar10/train.mojo     (line 313)
examples/googlenet-cifar10/train.mojo    (lines 436-438)
examples/mobilenetv1-cifar10/train.mojo  (lines 215-219)
examples/resnet18-cifar10/README.md      (Implementation Status section)
examples/googlenet-cifar10/README.md     (Implementation Status section)
examples/mobilenetv1-cifar10/README.md   (Implementation Status section)
```

### Commit Message Template

```text
docs(examples): clarify backward pass NOTEs as intentional placeholders

Replace ambiguous NOTE print statements with STATUS messages that
clearly communicate these are documented placeholders, not bugs.
Update README files to link to tracking issues.

- examples/<model>/train.mojo: NOTE -> STATUS with issue #XXXX
- Created GitHub tracking issues for full backward pass impl
- README.md: added Pending section with tracking issue links

Closes #<cleanup-issue>
```
