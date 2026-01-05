# Retry Transient Errors Plugin

Pattern for adding exponential backoff retry logic to handle transient network and I/O errors.

## Overview

This skill captures the pattern for implementing robust retry logic when operations fail due to transient issues (network errors, timeouts, connection failures). It was developed while fixing git clone failures in ProjectScylla's E2E experiment infrastructure.

## When to Use

Use this skill when:
- Operations fail intermittently with network-related errors
- Error messages indicate transient issues (connection reset, timeouts, etc.)
- The operation should succeed on retry (not permanent errors like auth failures)
- No existing retry logic is present

## What's Included

- **Verified workflow** for implementing exponential backoff retry
- **Transient error patterns** to detect (connection reset, curl errors, timeouts)
- **Failed attempts** section documenting pattern matching gotchas
- **Copy-paste code template** for quick implementation
- **Comprehensive test patterns** using unittest.mock
- **Configuration parameters** (3 retries, 1s base delay, 2x multiplier)

## Key Learnings

1. Always check project standards first (`.claude/shared/error-handling.md`)
2. Distinguish transient vs permanent errors to avoid wasting retries
3. Log retry attempts for visibility and debugging
4. Test both success and exhaustion paths
5. Use case-insensitive matching for error patterns
6. Include error message variations (e.g., "network unreachable" vs "network is unreachable")

## Results

- **Implementation:** `workspace_manager.py` retry logic
- **Tests:** 11 comprehensive unit tests (100% passing)
- **PR:** #146 (merged to ProjectScylla main)
- **Impact:** Eliminated transient git clone failures in E2E experiments

## Files

- `skills/retry-transient-errors/SKILL.md` - Complete skill documentation
- `references/notes.md` - Raw session notes and investigation details
- `.claude-plugin/plugin.json` - Plugin metadata

## Usage in Claude Code

```
Use the retry-transient-errors skill to add exponential backoff retry logic
```

The skill provides a battle-tested pattern for handling transient failures with proper error classification, timing, and test coverage.
