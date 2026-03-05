# ruff-c901-mccabe-complexity — Raw Notes

## Session: 2026-03-05

### Context

Issue #1377 — follow-up from #1356 where `# noqa: C901` directives were removed as
unused (C901 was not in the ruff select list). This exposed that the codebase has
many complex functions that need to be addressed.

### Key Discovery: noqa placement for multi-line def signatures

Ruff reports C901 at the line number of the `def` keyword. For single-line defs,
the noqa comment can go anywhere on that line. For multi-line signatures:

```python
# WORKS
def my_func(  # noqa: C901  # rationale here
    arg1: str,
    arg2: int,
) -> str:

# FAILS silently (violation persists)
def my_func(
    arg1: str,
    arg2: int,
) -> str:  # noqa: C901
```

This burned one iteration — two violations remained after the initial pass because
`validate_frontmatter` and `run_subtest` had their noqa on the closing line.

### Threshold decision: 12 vs 10

- 65 violations at threshold 10
- 43 violations at threshold 12 (need suppression)
- 22 violations at threshold 11-12 (accepted without suppression)
- Rationale: complexity 11-12 is common for real orchestration/validation logic
  and doesn't meaningfully benefit from extraction. Threshold 12 was the sweet
  spot to enforce meaningful simplification without noise.

### ruff CLI does not support --max-complexity flag

Attempted: `ruff check scylla/ scripts/ --select C901 --max-complexity 10`
Result: `error: unexpected argument '--max-complexity' found`
Fix: must be in pyproject.toml `[tool.ruff.lint.mccabe]` section.

### Suppression rationale taxonomy

Used consistent rationale phrases across suppressions to make future searches easy:
- `orchestration with many retry/outcome paths`
- `pipeline with sequential conditional stages`
- `CLI dispatch with many command branches`
- `validation with many independent rule checks`
- `config loader with many format/version branches`
- `workspace state detection with many file patterns`
- `action map with many tier state branches`
- `text report formatting with many conditional branches`
- `AST traversal with many node type branches`
- `pairwise comparison with many metric types`
- `table generation with many criteria branches`
- `TUI rendering with many display states`
- `grade mapping with many score thresholds`

### Files touched (29 source files + pyproject.toml)

scripts/: agent_stats.py, check_frontmatter.py, validate_agents.py,
  check_doc_config_consistency.py, check_model_config_consistency.py,
  check_type_alias_shadowing.py, filter_audit.py, fix_markdown.py,
  generate_figures.py, manage_experiment.py, migrate_skills_to_mnemosyne.py

scylla/: analysis/loader.py, analysis/tables/comparison.py,
  automation/curses_ui.py, automation/implementer.py, config/loader.py,
  e2e/checkpoint.py, e2e/llm_judge.py, e2e/parallel_executor.py,
  e2e/regenerate.py, e2e/rerun.py, e2e/rerun_judges.py,
  e2e/run_report_sections.py, e2e/runner.py, e2e/subtest_executor.py,
  e2e/tier_action_builder.py, e2e/tier_manager.py, judge/evaluator.py (not needed,
  was at 11), reporting/scorecard.py
