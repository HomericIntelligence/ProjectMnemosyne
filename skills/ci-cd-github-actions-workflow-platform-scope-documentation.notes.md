# Session Notes: CI/CD GitHub Actions Workflow Platform Scope Documentation

## Session Context

This skill captures learning from issue #794 in ProjectHephaestus where a strict audit finding flagged the test.yml workflow as "Linux-only matrix (macOS/Windows out of scope per #539)" — treating it as a potential documentation gap.

## Problem Discovered

The original `.github/workflows/test.yml` in ProjectHephaestus had:
- A test matrix that only runs on `ubuntu-latest` (Linux)
- No explanation of why other platforms were excluded
- No documentation of what platforms are/aren't supported
- No indication of whether this was intentional or an oversight

This created ambiguity:
- Are macOS/Windows intentionally out of scope?
- Is the package actually cross-platform, or only Linux?
- When might this change?

Audit reviewers flagged this as misleading because the package metadata/README might claim "cross-platform" but CI only tested Linux.

## Solution Pattern

Rather than expanding CI to all platforms immediately (which required unblocking #539 — cross-platform pixi environments), document the intentional asymmetry honestly with:

1. **What platforms are tested** (Linux via ubuntu-latest)
2. **Why** (pixi environment targets linux-64 exclusively)
3. **What's out of scope** (macOS/Windows) and tracked where (issue #539)
4. **What still works** despite CI gap (pure-Python wheels, unit tests remain platform-agnostic)
5. **When scope expands** (when #539 lands)

## Implementation Details

### File Changed
- `.github/workflows/test.yml` in ProjectHephaestus (PR #977)

### Change Made
Added a 14-line YAML comment block at the very top of the file, BEFORE the `name: Test` line:

```yaml
# Platform Scope: Linux Only (CI)
#
# This workflow exercises tests only on Linux (ubuntu-latest) due to pixi environment
# constraints that target linux-64 exclusively. macOS and Windows support is out of scope
# for this test matrix and tracked separately per #539.
#
# CAPABILITY: Despite this CI limitation, the package remains pure-Python importable
# on all platforms and wheels are generated in GitHub Actions with platform-specific tags.
# Unit tests are platform-agnostic and designed to pass on any POSIX-compatible environment.
#
# EXPAND TRIGGER: When #539 lands with cross-platform pixi environment support, expand
# matrix.os to include [ubuntu-latest, macos-latest, windows-latest] and verify all
# tests pass on each platform before merging.
#
# See also: CONTRIBUTING.md (platform asymmetry documentation)
#
```

### Why This Works

1. **Visibility**: Placement BEFORE `name:` means it's the first thing anyone sees
2. **Honesty**: Names both limitation ("only Linux") and capability ("still pure-Python importable")
3. **Stability**: Issue links (#539, #794) survive doc refactors; file paths break when docs move
4. **Clarity**: Explicit about what's tested, why, what works anyway, and when to expand
5. **Simplicity**: No code changes, no CI expansion until #539 is ready

### Related Patterns

This pattern validates and extends the learning from issue #749 (platform asymmetry documentation with semantic anchors). Where #749 focused on README/CONTRIBUTING.md documentation, this skill applies the same principles to GitHub Actions workflows.

Key principle: **Use issue links (#NNN) instead of doc file references** because issue links are stable across refactors, while doc paths break when documentation is reorganized.

## Validation

- YAML syntax validated (comment block doesn't break workflow parsing)
- Pre-commit hooks passed (formatting, linting)
- Workflow executed successfully in ProjectHephaestus CI
- Pattern accepted in code review

## Key Learnings

1. **Platform scope is a workflow-wide property** — document it at the top, not scattered through the file
2. **Honesty requires both limitation AND capability** — saying "only Linux tested" is incomplete; you also need to say what still works cross-platform
3. **Issue links outlive doc refs** — `#539` is stable across a decade of doc reorganizations; `docs/platform-support.md` breaks on the first doc refactor
4. **Clear expansion triggers** — linking to #539 and saying "When #539 lands, expand matrix.os..." makes it obvious what gate blocks expansion
5. **Audit-proof documentation** — audit findings about "misleading cross-platform claims" are prevented by explicitly documenting scope asymmetries upfront

## Related Issues/PRs

- **Issue #794**: "test.yml:48-50 Linux-only matrix (macOS/Windows out of scope per #539)" — audit finding that prompted this pattern
- **Issue #539**: macOS/Windows support — tracked separately; gates CI expansion
- **Issue #749**: Platform asymmetry documentation — prior learning about using semantic anchors instead of doc file paths
- **PR #977**: Implementation in ProjectHephaestus; merged with pre-commit validation passing

## Potential Extensions

1. **Multi-workflow patterns**: Apply this pattern to other workflows (e.g., build.yml, deploy.yml) with different platform asymmetries
2. **Automated expansion**: When #539 lands, a PR could automatically update all workflows' EXPAND TRIGGER sections from proposed to completed
3. **Audit automation**: Pre-commit hook could check that all workflows with platform-specific matrix definitions have this scope comment
4. **Cross-repo sync**: Share this pattern with other HomericIntelligence projects that have similar platform asymmetries
