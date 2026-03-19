# Advise & Retrospective Commands - Updated for Flat Files

## Summary

Both `/advise` and `/retrospective` commands have been updated to work with the new flat-format skill structure.

**Completed**: 2026-03-19

## Changes Overview

### /advise Command
**File**: `plugins/tooling/skills-registry-commands/commands/advise.md`

#### Key Updates:
1. **Clone Location**
   - Before: `<ProjectRoot>/build/<PID>/ProjectMnemosyne/` (isolated per session)
   - After: `$HOME/.agent-brain/ProjectMnemosyne/` (shared, single clone)

2. **Repository Setup**
   - Simpler logic: create once, then fetch+pull before each search
   - No more PID-based isolation (not needed for read-only searches)
   - Automatic update to latest main branch

3. **Skill Reading**
   - Before: Read from nested `skills/<name>/skills/<name>/SKILL.md`
   - After: Read directly from flat `skills/<name>.md` files

4. **Search & Presentation**
   - Unchanged: still searches marketplace.json, presents findings
   - Focus sections: Failed Attempts, When to Use, Results & Parameters

### /retrospective Command
**File**: `plugins/tooling/skills-registry-commands/commands/retrospective.md`

#### Key Updates:
1. **Auto-Generate Filename** (Major Change!)
   - Before: Prompt user for category + skill name
   - After: Auto-generate filename from conversation
   - Format: `<topic>-<subtopic>-<short-4-word-summary>`
   - Example: `training-grpo-external-vllm-setup.md`
   - Auto-detect category from conversation context

2. **Clone Location**
   - Before: `<ProjectRoot>/build/<PID>/ProjectMnemosyne/` (isolated)
   - After: `$HOME/.agent-brain/ProjectMnemosyne/` (shared)
   - Automatic cleanup after PR creation

3. **File Structure**
   - Before:
     ```
     skills/<category>/<name>/
     ├── .claude-plugin/plugin.json
     ├── skills/<name>/SKILL.md
     └── references/notes.md
     ```
   - After:
     ```
     skills/<name>.md (single flat file)
     skills/<name>.notes.md (optional)
     ```

4. **File Format**
   - YAML frontmatter in `.md` file (no separate plugin.json)
   - Required fields: name, description, category, date, version
   - All markdown sections in single file
   - Optional `.notes.md` for raw session context

5. **Branch Naming**
   - Before: `skill/<category>/<name>`
   - After: `skill/<name>` (simpler, no category in path)

6. **Validation**
   - Updated checklist for flat format
   - Single command: `python3 scripts/validate_plugins.py`
   - No need to pass `skills/ plugins/` arguments

## Workflow Comparison

### Advise - Before vs After

**Before**:
```
1. Clone with PID isolation
2. Search marketplace.json
3. Read nested SKILL.md files
4. Present findings
```

**After**:
```
1. Clone to shared $HOME/.agent-brain (fetch+pull if exists)
2. Search marketplace.json
3. Read flat skills/*.md files
4. Present findings
```

### Retrospective - Before vs After

**Before**:
```
1. Clone with PID isolation
2. Prompt for category and skill name
3. Create nested directory structure + plugin.json + SKILL.md
4. Validate (complex)
5. Commit and create PR
6. Manual cleanup
```

**After**:
```
1. Clone to shared $HOME/.agent-brain
2. Auto-generate skill filename (no user input!)
3. Create single flat skills/<name>.md file + optional notes
4. Validate (simpler, single command)
5. Commit and create PR
6. Auto-cleanup (remove clone)
```

## Key Improvements

### For Users
1. **No manual metadata entry** — filename auto-generated from conversation
2. **Simpler file structure** — single .md file instead of nested directories
3. **Faster retrospective** — skip the prompt dialogs
4. **Auto-cleanup** — no accumulating build directories

### For System
1. **Reduced disk usage** — shared clone instead of PID-scoped copies
2. **Simpler validation** — flat file format is easier to check
3. **Cleaner repository** — no nested plugin directories
4. **Better UX** — fewer prompts, faster feedback

## Testing Checklist

- [ ] `/advise <query>` reads from flat `skills/*.md` files
- [ ] Marketplace.json is correctly parsed with `source: ./skills/<name>.md`
- [ ] `/retrospective` auto-generates filename from conversation
- [ ] Auto-generated filename follows `<topic>-<subtopic>-<4words>` pattern
- [ ] Category is auto-detected (not prompted)
- [ ] Skill file created in correct format (YAML frontmatter + markdown)
- [ ] Validation passes with `python3 scripts/validate_plugins.py`
- [ ] PR created with correct title and body
- [ ] Clone auto-cleaned after PR creation
- [ ] Re-running `/advise` uses cached clone and updates it

## Migration Complete

✅ All 930 skills converted to flat format
✅ Advise and retrospective commands updated
✅ Validation and marketplace generation updated
✅ CI workflows updated
✅ Documentation (CLAUDE.md) updated

**Status**: Ready for use. Commands follow new flat-file workflows.
