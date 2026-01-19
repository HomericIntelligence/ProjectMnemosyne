# References: containerize-e2e-experiments

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | E2E containerization | Imported from ProjectScylla .claude-plugin/skills/containerize-e2e-experiments |

## Source

Originally created for ProjectScylla to containerize E2E experiment execution.

## Additional Context

This skill documents the evolution from complex nested container architecture to a simple single-container approach:

**Architecture Evolution:**
- OLD: Host → Container per agent → Container per judge (nested)
- NEW: Host → Single container → All agents + judges (simple)

**Key Benefits:**
- No container startup overhead per execution
- Simpler credential management (mount once)
- Better debugging (everything in one place)
- Easier resource control

**Technical Details:**
- Python 3.14.2 upgrade
- Credential mounting from host
- Interactive shell support
- 84% test pass rate

## Related Skills

- claude-code-settings-config: Workspace configuration for E2E
- evaluation-report-fixes: E2E report improvements
