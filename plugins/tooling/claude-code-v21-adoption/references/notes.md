# Claude Code v2.1.0 Adoption - Session Notes

## Context

User requested implementation of 5 Claude Code v2.1.0 features based on CHANGELOG analysis. Used `/advise` to research existing skills before implementing.

## Session Timeline

1. **Research phase**: Used `/advise` with CHANGELOG URL to find:
   - claude-plugin-format skill (schema requirements)
   - claude-plugin-marketplace skill (marketplace setup)
   - retrospective-hook-integration skill (SessionEnd hooks)

2. **Feature identification** (from v2.1.0):
   - ✅ user-invocable field for skills
   - ✅ agent hooks field (PreToolUse/PostToolUse/Stop)
   - ⚠️ disallowedTools (CLI only, NOT frontmatter)
   - ✅ agent field for skills
   - ✅ once field for hooks

3. **Implementation**:
   - PR #70: user-invocable field (13 sub-skills)
   - PR #71: agent-hooks-pattern skill + tool blocking via hooks
   - PR #72: skills-agent-field skill
   - PR #73: once field documentation

## PRs Created

### PR #70: Skills user-invocable field
**Branch**: `feature/user-invocable-field`
**Files**: 16 changed (13 skills + template + script + CLAUDE.md)

Updated sub-skills:
- ci-failure-workflow: analyze, fix
- gh-pr-review-workflow: fix-feedback, get-comments, reply-comment
- git-worktree-workflow: cleanup, create, switch, sync
- skills-registry-commands: advise, documentation-patterns, retrospective, validation-workflow

### PR #71: Agent hooks + tool blocking
**Branch**: `feature/agent-hooks`
**Files**: 4 new files (agent-hooks-pattern skill)

Documented:
- PreToolUse/PostToolUse/Stop hooks
- Junior engineer template (blocks Bash/WebFetch/Task)
- Review specialist template (read-only)
- Tool blocking via deny decisions

### PR #72: Skills agent field
**Branch**: `feature/skills-agent-field`
**Files**: 5 new files (skills-agent-field skill)

Documented:
- Language-specific routing (Mojo → mojo-specialist)
- Role-based routing (GitHub → implementation-engineer)
- Domain-specific routing (Quality → review-specialist)

### PR #73: Hooks once field
**Branch**: `feature/hooks-once-field`
**Files**: 2 changed (retrospective-hook-integration + CLAUDE.md)

Updated:
- SessionEnd hook examples with `once: true`
- CLAUDE.md hooks configuration section

## Key Learnings

1. **disallowedTools confusion**: User originally requested `disallowedTools` array in agent frontmatter, but CHANGELOG only mentions CLI `--disallowedTools` flag. Reframed as hooks-based tool blocking pattern.

2. **Combined PRs**: PR #71 combines agent hooks (PR2) and tool blocking (PR3) since they use the same implementation mechanism.

3. **Script automation**: Created `scripts/add_user_invocable.py` for bulk frontmatter updates - pattern reusable for future field additions.

4. **Documentation skills**: Created dedicated skills for complex patterns (agent-hooks-pattern, skills-agent-field) rather than just updating templates.

## Commands Used

```bash
# Research
/advise Analyze the release notes https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md

# Implementation
git checkout -b feature/<name>
python3 scripts/add_user_invocable.py
python3 scripts/generate_marketplace.py
git commit -m "feat(...): ..."
gh pr create --title "..." --label "enhancement"
gh pr merge --auto --rebase

# Retrospective
/retrospective
```

## Stats

- **Features adopted**: 5 (user-invocable, agent hooks, tool blocking, agent field, once)
- **PRs created**: 5 (#70, #71, #72, #73, this retrospective)
- **Skills updated**: 13 sub-skills with user-invocable: false
- **New skills created**: 3 (agent-hooks-pattern, skills-agent-field, claude-code-v2.1-adoption)
- **Time**: ~1 hour for all 5 features + documentation

## Links

- [Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- [ProjectMnemosyne PRs](https://github.com/HomericIntelligence/ProjectMnemosyne/pulls)
