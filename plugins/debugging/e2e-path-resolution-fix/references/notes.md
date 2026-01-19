# References: e2e-path-resolution-fix

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | E2E path resolution | Imported from ProjectScylla .claude-plugin/skills/e2e-path-resolution-fix |

## Source

Originally created for ProjectScylla to fix E2E agent execution failures caused by relative path handling.

## Additional Context

This skill documents a critical bug that caused 100% agent execution failure:

**Symptoms:**
- All tiers: 0% pass rate, $0.00 cost
- Agent execution: 0.0s duration, exit code 1
- Error: "cd: No such file or directory"

**Root Cause:**
- `subprocess.run()` received relative path in `cwd` parameter
- Relative paths don't work for subprocess working directory

**Solution:**
- Convert workspace path to absolute before passing to subprocess
- Use `workspace.resolve()` or `Path.cwd() / workspace`

**Impact:**
- Fixed silent failures across all E2E experiments
- Restored proper agent execution

## Related Skills

- fix-directory-not-created-before-write: Path/directory handling
- fix-evaluation-framework-bugs: Framework issue patterns
