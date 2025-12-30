---
name: quality-security-scan
description: "Scan code for security vulnerabilities and unsafe patterns"
category: architecture
source: ProjectOdyssey
date: 2025-12-30
---

# Security Vulnerability Scanning

Scan code for security vulnerabilities and unsafe patterns.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Detect security issues before deployment | Secure codebase free of vulnerabilities |

## When to Use

- (1) Before committing code with secrets
- (2) Security review process
- (3) Handling sensitive data
- (4) Pre-release security audit

## Verified Workflow

1. **Scan for secrets** - Check for committed credentials
2. **Check dependencies** - Audit for vulnerable packages
3. **Review patterns** - Look for unsafe code patterns
4. **Fix issues** - Address found vulnerabilities
5. **Verify fixes** - Re-scan to confirm resolution
6. **Document** - Record security decisions

## Results

Copy-paste ready commands:

```bash
# Check for committed secrets with gitleaks
gitleaks detect --source . --verbose

# Check Python dependencies with pip-audit
pip install pip-audit
pip-audit

# Alternative: safety check
pip install safety
safety check

# Check for hardcoded secrets with trufflehog
trufflehog filesystem . --only-verified

# Scan with bandit (Python security linter)
pip install bandit
bandit -r path/to/code/
```

### Security Checks

**1. Secrets Detection**

Detects:

- API keys and tokens
- Passwords and credentials
- Private keys (.key, .pem)
- AWS credentials
- Database credentials

**2. Dependency Vulnerabilities**

```bash
pip-audit              # Python packages
safety check          # Alternative scanner
```

**3. Unsafe Code Patterns**

Bandit rules check for:

- Hardcoded credentials
- SQL injection vectors
- Unsafe file operations
- Unvalidated input

### Prevention: .gitignore

```text
.env
.env.local
*.key
*.pem
credentials.json
secrets/
aws/
api-keys.txt
```

### Common Vulnerabilities

**Hardcoded Secrets**

```python
# Wrong
API_KEY = "sk_live_1234567890"

# Correct
import os
API_KEY = os.getenv("API_KEY")
```

**SQL Injection**

```python
# Wrong - string concatenation
query = "SELECT * FROM users WHERE id = " + user_id

# Correct - parameterized query
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

**Unsafe File Operations**

```python
# Wrong - no path validation
def load_file(path):
    return open(path).read()

# Correct - validate path
def load_file(path):
    if not is_safe_path(path):
        raise ValueError("Invalid path")
    return open(path).read()
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Ran security scan only before release | Found critical issues too late | Integrate scanning into CI/CD pipeline |
| Ignored low-severity warnings | Attackers chain low-severity issues | Address all severity levels, prioritize by risk |
| Added secrets to .gitignore after commit | Secrets already in git history | Use git-filter-repo to remove from history |
| Used only one scanning tool | Missed issues caught by other tools | Use multiple complementary tools |

## Error Handling

| Problem | Solution |
|---------|----------|
| "Secret detected" | Move to .env, add to .gitignore |
| "Unsafe dependency" | Update to patched version |
| "Unsafe pattern" | Refactor code to use safe approach |
| Secret in git history | Use git-filter-repo to rewrite history |

## Best Practices

1. **Never commit secrets** - Use environment variables
2. **Keep dependencies updated** - Run pip-audit regularly
3. **Validate input** - Always validate user input
4. **Use safe libraries** - Prefer parameterized queries
5. **Review PRs** - Include security review in PR process

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Related skill: quality-complexity-check for code quality
- Bandit docs: https://bandit.readthedocs.io/
