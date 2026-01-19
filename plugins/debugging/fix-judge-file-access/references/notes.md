# References: fix-judge-file-access

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | E2E judge evaluation | Imported from ProjectScylla .claude-plugin/skills/fix-judge-file-access |

## Source

Originally created for ProjectScylla to fix E2E test evaluation failures where judge cannot verify agent work.

## Additional Context

This skill documents fixes for judge evaluation issues:

**Symptoms:**
- Judge scores very low (0.07) despite correct agent output
- Judge can't verify file contents or directory structure
- Git status shows only directory names, not files inside

**Root Causes:**
1. Workspace state only listed directory names for untracked directories
2. Judge had no tool access to read file contents
3. Mojo commands failed (used `mojo` instead of `pixi run mojo`)
4. System prompt didn't inform judge about available tools

**Solutions:**
1. Recursively expand untracked directories to list all files
2. Provide judge with file reading tools
3. Fix Mojo command paths
4. Update system prompt with tool information

**Impact:**
- T2 score improved from 0.07 (failing) to 0.77 (passing)
- Judge can now properly verify agent work

## Related Skills

- evaluation-report-fixes: E2E report improvements
- fix-evaluation-framework-bugs: Framework bug patterns
