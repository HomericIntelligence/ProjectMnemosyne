# Security Policy

## Supported Versions

| Version | Supported |
| --------- | ----------- |
| Latest on `main` | Yes |
| Older releases | No |

## Reporting a Vulnerability

If you discover a security vulnerability in ProjectMnemosyne, please report it
responsibly using **GitHub Private Security Advisories**:

1. Go to the [Security Advisories page](https://github.com/HomericIntelligence/ProjectMnemosyne/security/advisories)
2. Click **"New draft security advisory"**
3. Fill in the details of the vulnerability

**Please do not open a public issue for security vulnerabilities.**

## Response Timeline

- **Acknowledgment**: Within 48 hours of report
- **Assessment**: Within 7 days
- **Fix or mitigation**: Dependent on severity and complexity

## Scope

ProjectMnemosyne is a **skills/knowledge marketplace** — it stores markdown
documentation and skill files, not production application code. The repository
does include Python scripts for validation and marketplace generation, but does
not handle user data or run production services.

This policy covers:
- Python scripts (validation, marketplace generation, CI automation)
- CI/CD workflows and GitHub Actions configurations
- Pre-commit hook configurations

Skill content (markdown files contributed by the community) is informational
and does not execute code directly.

## Security Scanning

Pre-commit hooks are configured for basic file hygiene (YAML/JSON validation,
large file checks). Bandit (Python security linter) is **not** currently
configured in `.pre-commit-config.yaml`. Given the limited Python surface area,
this is acceptable but can be added if the codebase grows.

## Contact

For questions about this policy, open a GitHub Issue or reach out to the
HomericIntelligence project maintainers.
