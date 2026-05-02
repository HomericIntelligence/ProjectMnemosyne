# Session Notes: bandit-replace-pygrep-security-hook

## Context

- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3157-auto-impl
- **Issue**: #3157 — [P3-3] Improve shell injection pre-commit check
- **PR**: #3355

## Raw Findings

### Initial bandit audit (before hook change)

```bash
pixi run bandit -ll -r scripts/ tests/ 2>&1 | grep -E "Issue:|Location:"
```

Output (10 findings):

```text
>> Issue: [B108:hardcoded_tmp_directory] scripts/analyze_issues.py:1127
>> Issue: [B310:blacklist] scripts/download_cifar10.py:58
>> Issue: [B202:tarfile_unsafe_members] scripts/download_cifar10.py:123
>> Issue: [B310:blacklist] scripts/download_cifar100.py:61
>> Issue: [B202:tarfile_unsafe_members] scripts/download_cifar100.py:126
>> Issue: [B310:blacklist] scripts/download_fashion_mnist.py:61
>> Issue: [B310:blacklist] scripts/download_mnist.py:69
>> Issue: [B108:hardcoded_tmp_directory] tests/scripts/test_fix_build_errors.py:201
>> Issue: [B202:tarfile_unsafe_members] tests/test_package_papers.py:80
>> Issue: [B202:tarfile_unsafe_members] tests/test_package_papers.py:113
```

### Rationale for each suppression

**B310 (urlopen)** — Skip globally:
- All `urlopen` calls are in intentional dataset download scripts (CIFAR-10, CIFAR-100, MNIST)
- URLs are hardcoded constants defined at module top
- No user-controlled input involved

**B202 (tarfile.extractall)** — Skip globally:
- Download scripts extract known dataset archives
- Test code extracts archives in controlled temp directories
- Not processing user-supplied archives

**B108 (hardcoded /tmp)** — Inline nosec (2 occurrences):
1. `scripts/analyze_issues.py:1127` — argparse default, user can override with `--batch-dir`
2. `tests/scripts/test_fix_build_errors.py:201` — test code passing path to mock function

### Files changed

1. `.pre-commit-config.yaml` — replaced `check-shell-injection` pygrep with `bandit` hook
2. `pixi.toml` — added `bandit = ">=1.7.5"`
3. `pixi.lock` — auto-updated
4. `scripts/analyze_issues.py:1127` — added `# nosec B108`
5. `tests/scripts/test_fix_build_errors.py:201` — added `# nosec B108`

### Pre-commit run result

```text
Check for deprecated List[Type](args) syntax.............................Passed
Bandit Security Scan.....................................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Validate Test Coverage...................................................Passed
Markdown Lint............................................................Passed
Strip Notebook Outputs...................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check YAML...............................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```

Note: Mojo Format hook fails due to GLIBC incompatibility in the dev environment
(pre-existing infrastructure issue, not related to this change).
