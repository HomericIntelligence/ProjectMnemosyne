# References: claude-code-settings-config

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | E2E framework | Imported from ProjectScylla .claude-plugin/skills/claude-code-settings-config |

## Source

Originally created for ProjectScylla to configure Claude Code settings per test workspace.

## Additional Context

This skill demonstrates how to properly control Claude Code's thinking mode via workspace settings rather than prompt injection. Key insights:

1. Create `.claude/settings.json` in every test workspace
2. Set `alwaysThinkingEnabled` based on CLI flags
3. Handle special cases (T0/00 and T0/01) where `.claude/` is normally removed
4. CLI `--thinking` flag takes global priority over per-test configuration

## Related Skills

- e2e-framework-bug-fixes: General E2E framework improvements
- containerize-e2e-experiments: Docker setup for E2E tests
