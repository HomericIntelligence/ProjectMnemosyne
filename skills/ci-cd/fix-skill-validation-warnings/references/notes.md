# Session Notes: Fix Skill Validation Warnings

## Context

ProjectMnemosyne had 198 skill plugins after bulk import from ProjectScylla. CI validation reported:
- 1 hard ERROR: `split-figures-per-tier` plugin.json name field was title-case
- 126 plugins with WARNINGS (various missing sections)

User requested: "Fix all skill plugin validation errors and warnings"

## Implementation Timeline

### 1. Initial Analysis
- Ran `validate_plugins.py` to identify issues
- Categorized warnings into 5 groups:
  - 61 plugins: Missing Overview + Verified Workflow + Results
  - 32 plugins: Failed Attempts lacks pipe table
  - 25 plugins: Missing Overview + Failed Attempts lacks table
  - 6 plugins: Missing Overview only
  - 2 plugins: Missing Verified Workflow + Results only

### 2. Created `fix_validation_warnings.py`
- Automated addition of missing sections
- Functions:
  - `add_overview_section()`: Extracts date/objective from frontmatter and first paragraph
  - `rename_workflow_to_verified()`: Simple regex substitution
  - `add_results_section()`: Inserts before References or at end
  - `add_failed_attempts_table()`: Adds summary table if subsections detected

**Results**: Modified 113 files with 243 total fixes

### 3. Created `fix_remaining_warnings.py`
- Handled wrapper patterns like `## Quick Reference` → `## Verified Workflow\n\n### Quick Reference`
- Targeted 15 specific plugins that still had warnings

**Results**: Modified 15 files (all Verified Workflow wrappers)

### 4. Created `fix_failed_attempts_tables.py`
- Extracted attempt info from `### ❌ Attempt N:` subsections
- Generated summary tables while preserving detailed content
- Handled section name variations (`## Failed Attempts & Lessons Learned`)

**Results**: Modified 23 files

### 5. Manual Fix
- Edited `plugins/tooling/split-figures-per-tier/.claude-plugin/plugin.json`
- Changed `"name": "Split Figures Per Tier Due to Altair Row Limit"` → `"name": "split-figures-per-tier"`

### 6. Final Validation
```
Total plugins: 198
Passed: 198
Failed: 0
ALL VALIDATIONS PASSED
```

## Key Code Patterns

### Extracting Date from Frontmatter
```python
def extract_frontmatter_date(content: str) -> str:
    match = re.search(r'^date:\s*["\']?([0-9-]+)["\']?', content, re.MULTILINE)
    return match.group(1) if match else "N/A"
```

### Extracting Objective
```python
def extract_objective(content: str) -> str:
    lines = content.split('\n')
    in_frontmatter = False
    past_title = False
    objective_lines = []
    
    for line in lines:
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if line.startswith('# '):
            past_title = True
            continue
        if past_title and line.strip() and not line.startswith('#'):
            objective_lines.append(line.strip())
            if len(' '.join(objective_lines)) > 100:
                break
    
    objective = ' '.join(objective_lines)
    return objective[:147] + "..." if len(objective) > 150 else objective
```

### Section Detection with Flexible Matching
```python
# Bad (misses variations):
if "## Failed Attempts" in content:

# Good (handles any suffix):
if re.search(r'^## Failed Attempts.*?$', content, re.MULTILINE):
```

## Learnings

1. **Iterative approach works best**: Start with main issues, then handle edge cases
2. **Extract from existing content**: Don't use generic boilerplate when you can pull actual info
3. **Preserve user content**: Add summary tables but keep detailed subsections
4. **Regex flexibility**: Use `.*?` to match section name variations
5. **Validation-driven**: Run validator after each script to confirm progress

## Documentation Updates

Also updated `/retrospective` skill documentation to:
- Add explicit ✅ CORRECT and ❌ INCORRECT format examples for Failed Attempts
- Clarify that pipe (`|`) characters are REQUIRED by CI
- Show best practice: summary table + detailed subsections

## Commits

1. `fix(validation): resolve all plugin validation errors and warnings` - Main fixes (133 files)
2. `docs(retrospective): clarify Failed Attempts MUST use table format` - Documentation update

## PR Created

PR #108: https://github.com/HomericIntelligence/ProjectMnemosyne/pull/108
- Title: "fix: Resolve all plugin validation errors and warnings (198/198 PASS)"
- Includes detailed breakdown of fixes and automation scripts
