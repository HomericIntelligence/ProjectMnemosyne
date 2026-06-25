---
name: communication-redaction-avoid-internal-leaks
description: "Prevent internal infrastructure identifiers from leaking into user-facing summaries, durable notes, PR bodies, reports, and reusable examples. Use when: (1) reporting operational validation or launch details, (2) writing durable artifacts from logs, endpoints, checkpoints, or commands."
category: documentation
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [communication, redaction, documentation, reporting]
---

# Communication Redaction: Avoid Internal Leaks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Keep operational reporting useful while preventing internal infrastructure identifiers from appearing in user-facing or durable artifacts unless explicitly requested. |
| **Outcome** | Use neutral placeholders for commands, endpoints, logs, checkpoints, and launch details by default. |
| **Verification** | verified-local - repository plugin validation passed locally; CI validation pending. |

## When to Use

- Reporting validation results, operational commands, launch details, endpoints, logs, checkpoints, or run summaries.
- Writing PR bodies, issue comments, notes, runbooks, postmortems, learnings, or other durable artifacts from an operational session.
- Turning raw terminal output or logs into a user-facing summary.
- Creating examples that could otherwise reveal infrastructure identifiers.

## Verified Workflow

### Quick Reference

```text
Before publishing a user-facing or durable artifact:
1. Identify operational identifiers.
2. Replace them with neutral placeholders.
3. Preserve the workflow shape and outcome.
4. Include exact internal details only when the user explicitly asks for that exact detail.
```

### Detailed Steps

1. **Classify the target surface.** Treat final answers, PR bodies, issue comments, notes, skills, runbooks, report files, and examples as user-facing or durable unless the user says otherwise.
2. **Scan for internal identifiers.** Look for absolute paths, filenames, project or repository names, cluster or node names, job identifiers, IP addresses, ports, checkpoint identifiers, model checkpoint paths, usernames, account names, partition names, service names, and other infrastructure identifiers.
3. **Replace identifiers with placeholders.** Prefer neutral terms such as `<internal-path>`, `<service-name>`, `<node-id>`, `<endpoint>`, `<checkpoint>`, and `<project>`.
4. **Preserve operational meaning.** Keep the command category, validation result, failure mode, sequence of steps, and decision logic. Remove only the identifying values.
5. **Respect explicit requests.** If the user asks for an exact command, exact endpoint, exact log path, or exact identifier, provide only the requested detail and avoid adding unrelated identifiers.
6. **Do a final redaction pass.** Re-read the artifact before publishing and check code blocks, tables, commit messages, branch names, PR bodies, and references.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Raw operational copy-paste | Copied commands, log excerpts, and validation details directly into a durable artifact | Operational output often contains paths, endpoints, job identifiers, ports, service names, and checkpoint values that are not needed for the learning | Summarize the workflow and outcome first, then add placeholders only where structure matters |
| Over-redacting everything | Removed all command and validation structure | The artifact became hard to reuse because readers could not tell what was validated or in what order | Redact identifiers, not the process |
| Treating non-secret identifiers as harmless | Left infrastructure identifiers visible because they were not credentials | Internal topology and operational metadata can still be sensitive or unnecessary in durable artifacts | Apply least-disclosure to all internal identifiers, not only secrets |

## Results & Parameters

### Placeholder Policy

| Internal detail type | Placeholder |
|----------------------|-------------|
| Absolute path or generated file location | `<internal-path>` |
| Repository, project, or product-specific name | `<project>` |
| Cluster, host, or node identity | `<node-id>` |
| API URL, IP address, hostname, or port-bearing target | `<endpoint>` |
| Runtime service or process name | `<service-name>` |
| Job, run, task, or allocation identifier | `<job-id>` |
| Checkpoint, artifact, or model checkpoint path | `<checkpoint>` |
| User, account, tenant, or partition name | `<account>` |

### Safe Reporting Template

```text
Validation: <passed|failed|blocked>
Command category: <what was checked, without exact internal command text>
Target: <project> / <service-name> / <endpoint>
Evidence: <short sanitized result>
Next step: <sanitized action>
```

### Review Checklist

- No absolute paths, concrete filenames, repository or project names, node names, job identifiers, IPs, ports, checkpoint paths, usernames, account names, partition names, or internal service names appear unless explicitly requested.
- Examples use placeholders such as `<internal-path>`, `<service-name>`, `<node-id>`, `<endpoint>`, `<checkpoint>`, and `<project>`.
- The artifact still explains what was validated, what happened, and what action follows.
- Verification status states only what actually ran.
