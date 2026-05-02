---
name: security-review-false-positive-filter
description: 'Perform security code reviews with parallel false-positive filtering
  agents to produce high-confidence findings only. Use when: reviewing PR diffs for
  security vulnerabilities, static analysis is noisy, or internal APIs need exploitability
  validation before reporting.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Purpose** | Security PR review with parallel false-positive filtering |
| **Primary trigger** | /security-review slash command on a PR diff |
| **Key insight** | Two-phase: identify candidates then parallel validate exploitability per finding |
| **Confidence threshold** | Only report findings with score 8/10 or higher |
| **Agent model** | Explore sub-agent for both phases |
| **Session date** | 2026-03-15 |

## When to Use

- A PR diff needs security review (triggered by `/security-review` command)
- Static analysis tools are producing noisy results needing exploitability validation
- Code changes touch file I/O, subprocess calls, deserialization, or network-facing code
- ML/research codebases where "unsafe pattern" does not equal "exploitable vulnerability"
- Any review where false-positive flooding would undermine trust in the output

## Verified Workflow

### Quick Reference

| Phase | Agent | Task |
| ------- | ------- | ------ |
| 1 — Identify | Single Explore agent | Read all changed files, identify candidate vulnerabilities with confidence scores |
| 2 — Filter | Parallel Explore agents (one per finding) | Validate each candidate: is there a concrete untrusted-input path? |
| 3 — Report | Orchestrator | Collect results, discard findings with confidence < 8, format report |

### Phase 1: Vulnerability Identification Agent

Spawn a single Explore agent with the full PR diff and file context:

```text
Agent prompt:
"You are a senior security engineer. Read the following modified files and identify
candidate security vulnerabilities. For each finding, assign a confidence score 1-10.
Only report findings with confidence >= 7.

Modified files: [list]
Security categories: command_injection, path_traversal, sql_injection, xxe,
                     deserialization_rce, hardcoded_secrets, weak_crypto,
                     auth_bypass, data_exposure

EXCLUSIONS — do NOT report:
- DOS / resource exhaustion
- Secrets on disk
- Rate limiting
- Memory safety (Mojo/Rust are memory-safe)
- Unit test files only
- Log spoofing
- SSRF path-only control
- Regex injection / ReDoS
- Markdown documentation files
- GitHub Action workflow inputs (unless concrete untrusted path exists)

For each finding: file, line, severity, category, description, exploit scenario, confidence score"
```

### Phase 2: Parallel False-Positive Filtering

For each candidate finding from Phase 1, spawn a parallel Explore agent:

```text
Agent prompt (per finding):
"Validate whether this vulnerability is a TRUE POSITIVE or FALSE POSITIVE.

Finding: [copy finding from Phase 1]
File: [path]

Read the actual code. Assess:
1. Does untrusted user input (network, file upload, API, CLI) ever reach this parameter?
2. Is this an internal-only function called only with hardcoded/developer-controlled values?
3. Is this a web service or a local research tool? (web = higher risk)
4. Is there a safe alternative already in the codebase that should have been used?
5. Would a real attacker have any path to control the vulnerable parameter?

FALSE POSITIVE RULES (auto-exclude):
- CLI flags and env vars are trusted inputs
- Hardcoded strings in source code are not attacker-controlled
- Internal ML pipeline functions with no public API surface
- Parameters that only ever receive developer-defined constants
- Functions that are dead code (defined but never called)

Output:
- Confidence: [1-10]
- Verdict: TRUE POSITIVE or FALSE POSITIVE
- Reasoning: [1-3 sentences]"
```

### Phase 3: Filter and Report

Collect all filtering verdicts. Discard any finding where:
- Confidence < 8, OR
- Verdict == FALSE POSITIVE

Format surviving findings as:

```markdown
# Vuln N: <Category>: `file.py:LINE`

* Severity: High|Medium|Low
* Description: [what the code does unsafely]
* Exploit Scenario: [concrete attacker action -> impact]
* Recommendation: [specific fix]
```

If zero findings survive: output `No security vulnerabilities identified above the confidence threshold.`

### Key False-Positive Patterns for ML/Research Codebases

These are common false positives in Mojo/Python ML platforms:

| Pattern | Why It Is a False Positive |
| --------- | -------------------------- |
| Path concatenation in checkpoint save/load | `name` param is always hardcoded layer name like `"conv1_kernel"` |
| `subprocess.run()` in training script | Arguments are hardcoded; no user-controlled input |
| `open(filepath)` in data loader | Filepath comes from argparse, which is trusted CLI input |
| Config parser with dynamic dispatch | Config files are developer-controlled, not user-uploaded |
| Model checkpoint deserialization | Checkpoint files are developer-generated artifacts |

The key question for every finding: **"Can an attacker realistically control the vulnerable parameter through a public interface?"**

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Single-agent identify + filter | Ask one agent to both find and filter | Agent anchors on initial findings; does not critically re-evaluate own output | Separate identification from validation with independent agents |
| Reporting all findings >= 7 confidence | Include path traversal in file_io.mojo at confidence 9 | Pattern was technically unsafe but param is always hardcoded — false positive | Confidence from pattern matching != confidence from exploitability analysis; use dedicated filter agents |
| Static analysis only without reading callers | Flag `path + "/" + name` as path traversal without reading call sites | Missed that `name` is exclusively hardcoded layer names in model_utils.mojo | Always read the full call chain, not just the vulnerable line in isolation |
| Parallel Phase 1 agents one per file | Spawn separate identification agents per modified file | Agents lacked cross-file context since call chains span multiple files | Phase 1 needs full-codebase context in a single agent; only Phase 2 benefits from parallelism |

## Results & Parameters

### Session Result (2026-03-15)

```text
Modified files reviewed: 4
  - shared/utils/file_io.mojo
  - scripts/convert_image_to_idx.py
  - tests/test_validate_test_coverage.py
  - split_test_files.py

Phase 1 candidates: 2 (both path traversal in file_io.mojo)
Phase 2 filtered: 2/2 FALSE POSITIVE (confidence 2/10 each)
Final report: 0 vulnerabilities above threshold
```

Both findings were `save_tensor_to_checkpoint()` and `load_tensor_from_checkpoint()` —
unsafe path concatenation without traversal validation. The `name` parameter is exclusively
populated with hardcoded strings like `"conv1_kernel"` in `model_utils.mojo`. The load
function was additionally dead code (defined but never called anywhere in the codebase).

### Agent Configuration

```python
# Phase 1: Single identification agent
Agent(
    subagent_type="Explore",
    description="Identify security vulnerabilities in PR changes",
    prompt=PHASE_1_PROMPT,
)

# Phase 2: Parallel filter agents (one per finding)
for finding in phase1_findings:
    Agent(
        subagent_type="Explore",
        run_in_background=True,  # Parallel
        description=f"Filter false positives: {finding.category} in {finding.file}",
        prompt=PHASE_2_PROMPT_TEMPLATE.format(finding=finding),
    )
```

### Confidence Threshold

```text
Report threshold: 8/10 or higher
  - 9-10: Certain exploit path, concrete PoC possible
  -  8-9: Clear vulnerability with known exploitation method
  -  7-8: Suspicious but needs specific conditions (filter phase may downgrade)
  -  <7:  Do not report (too speculative)
```
