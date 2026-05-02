---
name: scan-vulnerabilities
description: Detect security vulnerabilities in code and dependencies. Use when auditing
  security.
category: tooling
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Scan Vulnerabilities

## Overview

| Item | Details |
| ------ | --------- |
| Date | N/A |
| Objective | Systematically scan code for security vulnerabilities including unsafe patterns, known CVEs, and potential exploits. |
| Outcome | Operational |

Systematically scan code for security vulnerabilities including unsafe patterns, known CVEs, and potential exploits.

## When to Use

- Regular security audits
- Before releasing code to production
- When updating dependencies
- In CI/CD security checks

### Quick Reference

```bash
# Python security scanning
pip install bandit safety

# Scan code for security issues
bandit -r . -ll

# Check for known vulnerabilities in dependencies
safety check

# Advanced: SAST scanning
python3 -m pip install semgrep
semgrep --config=p/security-audit --json .
```

## Verified Workflow

1. **Scan code for issues**: Identify unsafe patterns (SQL injection, exec, hardcoded secrets)
2. **Check dependencies**: Scan for known vulnerabilities (CVEs)
3. **Review findings**: Analyze severity and exploitability
4. **Prioritize fixes**: Address critical/high severity issues first
5. **Document fixes**: Record how vulnerabilities were resolved

## Output Format

Security scan report:

- Vulnerability type (SQL injection, hardcoded secret, etc.)
- Location (file, line number)
- Severity (critical/high/medium/low)
- CVSS score (if applicable)
- Vulnerable dependency version (if applicable)
- Recommended fix
- Fixed version (if dependency)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See CLAUDE.md > Security standards for security guidelines
- See `quality-security-scan` skill for automated CI scanning
- OWASP Top 10 for common vulnerability categories
