# References: fix-evaluation-framework-bugs

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | E2E framework bugs | Imported from ProjectScylla .claude-plugin/skills/fix-evaluation-framework-bugs |

## Source

Originally created for ProjectScylla to fix three critical E2E evaluation framework bugs causing false negative agent scores.

## Additional Context

This skill documents systematic fixes for three interconnected bugs:

**Bug 1: Directory Assignment != Directory Creation**
- Intermittent FileNotFoundError during parallel execution
- Fix: Add `mkdir()` before writing files

**Bug 2: Framework Files in Judge Patchfile**
- Agents penalized for CLAUDE.md modifications they didn't make
- Fix: Filter out test configuration files from patchfile

**Bug 3: Markdown Lint Violations in Generated Files**
- Framework creates invalid markdown in CLAUDE.md
- Fix: Ensure generated markdown passes linting

**Impact:**
- All bugs fixed, CI passing
- Framework now scores agents correctly
- No false negatives from framework issues

## Related Skills

- fix-directory-not-created-before-write: Directory creation pattern
- evaluation-report-fixes: E2E report improvements
- fix-judge-file-access: Judge verification improvements
