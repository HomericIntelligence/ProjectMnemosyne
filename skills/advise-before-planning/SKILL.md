# Skill: Advise Before Planning

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-13 |
| **Objective** | Integrate team knowledge base search into automated planning workflows |
| **Outcome** | ✅ Two-step workflow implemented with graceful degradation |
| **Context** | Enhancing `plan_issues.py` to leverage ProjectMnemosyne skills registry |

## Overview

This skill documents the pattern for integrating team knowledge base searches before automated planning or implementation tasks. The approach uses a two-step workflow: (1) search for relevant prior learnings, (2) inject findings into the main task context.

## When to Use

Use this skill when:

- Building automation workflows that could benefit from prior team learnings
- Integrating a skills registry or knowledge base into CLI tools
- Implementing "advise before action" patterns in agent systems
- Creating multi-step LLM workflows where context from step 1 informs step 2

## Verified Workflow

### 1. Extract Reusable Claude CLI Caller

**Problem:** Need to call Claude CLI from multiple steps (advise + plan) with consistent retry logic.

**Solution:** Extract a DRY helper method:

```python
def _call_claude(
    self,
    prompt: str,
    *,
    max_retries: int = 3,
    timeout: int = 300,
    extra_args: list[str] | None = None,
) -> str:
    """Call Claude CLI with retry logic for rate limits."""
    cmd = [
        "claude",
        "--print",  # Non-interactive mode
        prompt,
        "--output-format",
        "text",
    ]

    # Add system prompt if configured
    if self.options.system_prompt_file and self.options.system_prompt_file.exists():
        cmd.extend(["--system-prompt", str(self.options.system_prompt_file)])

    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
        env={"CLAUDECODE": ""},  # Avoid nested-session guard
    )

    response = result.stdout.strip()
    if not response:
        raise RuntimeError("Claude returned empty response")

    return response
```

**Key Details:**

- Use `--print` for non-interactive mode (not `--message`)
- Set `CLAUDECODE=""` to bypass nested-session detection
- Shorter timeout for advise (180s) vs plan (300s)
- Return stripped stdout text

### 2. Implement Advise Step with Graceful Degradation

**Problem:** Need to search team knowledge base before planning, but should work even if knowledge base is missing.

**Solution:** Implement advise with fallback to empty findings:

```python
def _run_advise(self, issue_number: int, issue_title: str, issue_body: str) -> str:
    """Search team knowledge base for relevant prior learnings."""
    try:
        # Locate ProjectMnemosyne
        repo_root = get_repo_root()
        mnemosyne_root = repo_root / "build" / "ProjectMnemosyne"

        if not mnemosyne_root.exists():
            logger.warning(
                "ProjectMnemosyne not found, skipping advise step"
            )
            return ""

        marketplace_path = mnemosyne_root / ".claude-plugin" / "marketplace.json"
        if not marketplace_path.exists():
            logger.warning(f"Marketplace not found, skipping advise step")
            return ""

        # Build advise prompt
        advise_prompt = get_advise_prompt(
            issue_number=issue_number,
            issue_title=issue_title,
            issue_body=issue_body,
            marketplace_path=str(marketplace_path),
        )

        # Call Claude with shorter timeout
        logger.info(f"Running advise for issue #{issue_number}...")
        findings = self._call_claude(advise_prompt, timeout=180)

        return findings

    except Exception as e:
        logger.warning(f"Advise step failed: {e}")
        return ""  # Graceful degradation
```

**Key Details:**

- Return `""` (empty string) on any failure
- Log warnings but don't raise exceptions
- Check for both directory and marketplace.json existence
- Use relative path from repo root (`build/ProjectMnemosyne`)

### 3. Inject Findings into Main Context

**Problem:** Need to incorporate advise findings into the plan generation prompt.

**Solution:** Conditionally inject findings between issue body and plan instructions:

```python
def _generate_plan(self, issue_number: int) -> str:
    """Generate implementation plan using Claude Code."""
    # Fetch issue data
    issue_data = gh_issue_json(issue_number)
    issue_title = issue_data.get("title", f"Issue #{issue_number}")
    issue_body = issue_data.get("body", "")

    # Run advise step if enabled
    advise_findings = ""
    if self.options.enable_advise:
        advise_findings = self._run_advise(issue_number, issue_title, issue_body)

    # Build prompt
    prompt = get_plan_prompt(issue_number)

    # Add issue context
    context_parts = [f"# Issue #{issue_number}: {issue_title}", "", issue_body]

    # Inject advise findings if available
    if advise_findings:
        context_parts.extend([
            "",
            "---",
            "",
            "## Prior Learnings from Team Knowledge Base",
            "",
            advise_findings,
        ])

    context_parts.extend(["", "---", "", prompt])
    context = "\n".join(context_parts)

    # Call Claude to generate plan
    plan = self._call_claude(context, timeout=300)
    return plan
```

**Key Details:**

- Check `if advise_findings:` to avoid injecting empty sections
- Clear section header: "Prior Learnings from Team Knowledge Base"
- Insert between issue context and plan instructions (middle of prompt)
- Only call `_run_advise()` if `enable_advise` is True

### 4. Add Configuration Option

**Problem:** Need to allow disabling advise step for testing or when knowledge base is unavailable.

**Solution:** Add boolean field to options model with default enabled:

```python
class PlannerOptions(BaseModel):
    """Options for the Planner."""
    issues: list[int]
    dry_run: bool = False
    force: bool = False
    parallel: int = 3
    system_prompt_file: Path | None = None
    skip_closed: bool = True
    enable_advise: bool = True  # Default enabled
```

**CLI Flag:**

```python
parser.add_argument(
    "--no-advise",
    action="store_true",
    help="Skip the advise step (don't search team knowledge base before planning)",
)

# Wire into options
options = PlannerOptions(
    issues=args.issues,
    enable_advise=not args.no_advise,  # Invert the flag
)
```

**Key Details:**

- Default to `True` (advise enabled by default)
- Use `--no-advise` flag (negative flag pattern)
- Follow existing pattern like `--no-skip-closed`

### 5. Create Advise Prompt Template

**Problem:** Need to instruct Claude how to search the knowledge base in non-interactive mode.

**Solution:** Create structured prompt that directs file reading:

```python
ADVISE_PROMPT = """
Search the team knowledge base for relevant prior learnings before planning this issue.

**Issue:** #{issue_number}: {issue_title}

{issue_body}

---

**Your task:**
1. Read the skills marketplace: {marketplace_path}
2. Search for plugins matching this issue's topic by:
   - Keywords in plugin names and descriptions
   - Tags and categories
   - Similar problem domains
3. For each relevant plugin, read its SKILL.md file to understand:
   - What worked (successful approaches)
   - What failed (common pitfalls)
   - Recommended parameters and configurations
   - Related patterns and conventions

**Output format:**
## Related Skills
| Plugin | Category | Relevance |
|--------|----------|-----------|
| plugin-name | category | Why it's relevant |

## What Worked
- Successful approach 1
- Successful approach 2

## What Failed
- Common pitfall 1 (from plugin X)
- Common pitfall 2 (from plugin Y)

## Recommended Parameters
- Parameter/configuration 1
- Parameter/configuration 2

If no relevant skills are found, output:
## Related Skills
None found

**Important:** Only return findings from the actual marketplace. Do not speculate or invent skills.
"""
```

**Key Details:**

- Direct Claude to read files using absolute path
- Structure output for easy parsing/injection
- Include issue title and body for better search relevance
- Explicit instruction not to speculate (ground in actual files)

## Failed Attempts

### ❌ Attempt 1: Using `--message` flag

**What was tried:**

```python
result = subprocess.run(
    ["claude-code", "--message", prompt],
    ...
)
```

**Why it failed:**

- `claude-code` binary doesn't exist (correct binary is `claude`)
- `--message` is for interactive sessions, not batch/automation mode
- This would hang waiting for user interaction

**Fix:**

```python
result = subprocess.run(
    ["claude", "--print", prompt],  # Use --print for non-interactive
    ...
)
```

### ❌ Attempt 2: Using `/advise` slash command directly

**What was tried:**
Initially planned to invoke the `/advise` skill directly as a slash command in the prompt.

**Why it failed:**

- Slash commands only work in interactive Claude Code sessions
- `--print` mode doesn't support slash command invocation
- Would require spawning an interactive session (heavyweight)

**Fix:**
Instead, the advise prompt instructs Claude to:

1. Read the marketplace.json file directly using its file-reading tools
2. Search for relevant plugins by keywords/tags
3. Read matching SKILL.md files
4. Output structured findings

This achieves the same result without slash command infrastructure.

### ❌ Attempt 3: Not setting CLAUDECODE environment variable

**What was tried:**
Running `claude` CLI from within a Claude Code session without special handling.

**Why it failed:**

- Claude CLI detects nested sessions and may show warnings or alter behavior
- Can cause confusion in error messages

**Fix:**

```python
result = subprocess.run(
    cmd,
    env={"CLAUDECODE": ""},  # Bypass nested-session guard
    ...
)
```

## Results & Parameters

### Copy-Paste Configuration

**PlannerOptions model:**

```python
class PlannerOptions(BaseModel):
    """Options for the Planner."""
    issues: list[int]
    dry_run: bool = False
    force: bool = False
    parallel: int = 3
    system_prompt_file: Path | None = None
    skip_closed: bool = True
    enable_advise: bool = True  # Add this field
```

**CLI usage:**

```bash
# Plan with advise (default)
pixi run plan-issues --issues 123 456

# Plan without advise
pixi run plan-issues --issues 123 --no-advise

# Dry run to see what would happen
pixi run plan-issues --issues 123 --dry-run -v
```

**Pixi task:**

```toml
[tasks]
plan-issues = "python scripts/plan_issues.py"
```

### Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `enable_advise` | `True` | Enable team knowledge search by default |
| Advise timeout | `180s` | Shorter timeout for knowledge search |
| Plan timeout | `300s` | Longer timeout for plan generation |
| CLI binary | `claude` | Correct Claude CLI binary name |
| CLI flag | `--print` | Non-interactive mode for automation |
| CLAUDECODE env | `""` | Bypass nested-session detection |

### Test Coverage

**Created 14 new tests:**

- `test_prompts.py`: 4 tests for prompt generation
  - `test_get_advise_prompt()` - Verify advise prompt formatting
  - `test_get_plan_prompt()` - Verify plan prompt formatting
  - `test_get_implementation_prompt()` - Verify implementation prompt
  - `test_get_pr_description()` - Verify PR description generation

- `test_planner.py`: 10 tests for planner functionality
  - `TestCallClaude`: 5 tests
    - Successful call
    - Empty response handling
    - Timeout handling
    - Rate limit retry logic
    - System prompt passthrough
  - `TestRunAdvise`: 3 tests
    - Returns findings on success
    - Graceful failure on error
    - Skips when ProjectMnemosyne missing
  - `TestGeneratePlan`: 2 tests
    - Plan with advise findings injected
    - Plan without advise (disabled)

### Verification

```bash
# Run all automation tests
pixi run python -m pytest tests/unit/automation/ -v

# Run specific test files
pixi run python -m pytest tests/unit/automation/test_planner.py -v
pixi run python -m pytest tests/unit/automation/test_prompts.py -v

# Run pre-commit hooks
pre-commit run --all-files
```

## Related Patterns

- **Two-step LLM workflows**: Use output from step 1 as context for step 2
- **Graceful degradation**: Feature works even when dependencies are missing
- **DRY helpers**: Extract common subprocess patterns into reusable methods
- **Knowledge base integration**: Search prior learnings before planning new work

## Tags

`automation` `planning` `knowledge-base` `two-step-workflow` `claude-cli` `team-learning` `graceful-degradation` `dry-pattern`
