# Module Decomposition Pattern - Reference Notes

## ProjectScylla Context

### Original file
- `scylla/e2e/llm_judge.py` - 1,488 lines, 35 functions/classes
- Issue: HomericIntelligence/ProjectScylla#1446

### Cluster mapping

| Cluster | Functions | New Module |
| --------- | ----------- | ------------ |
| Pipeline execution | `_is_modular_repo`, `_run_mojo_build_step`, `_run_mojo_format_step`, `_run_mojo_test_step`, `_run_precommit_step`, `_run_mojo_pipeline`, `_get_pipeline_env`, `_execute_python_scripts`, `_run_python_build_step`, `_run_python_format_step`, `_run_python_test_step`, `_run_python_pipeline`, `_run_build_pipeline` + `BuildPipelineResult` | `build_pipeline.py` |
| Workspace context | `_get_workspace_state`, `_get_patchfile`, `_get_deleted_files`, `_load_reference_patch`, `_run_and_log_pipeline`, `_format_pipeline_result`, `_gather_judge_context` | `judge_context.py` |
| Judge execution | `_call_claude_judge`, `_parse_judge_response`, `_execute_judge_with_retry` | `judge_execution.py` |
| Log/script saving | `_create_python_scripts`, `_create_mojo_build_script`, `_create_mojo_format_script`, `_create_mojo_test_script`, `_create_mojo_scripts`, `_create_precommit_script`, `_create_run_all_script`, `_save_pipeline_commands`, `_save_pipeline_outputs`, `_save_judge_logs` | `judge_artifacts.py` |
| Orchestrator | `JudgeResult`, `run_llm_judge`, `_score_to_grade` | `llm_judge.py` (kept) |

### Extraction order rationale

1. `build_pipeline.py` - No cross-cluster deps, leaf module
2. `judge_artifacts.py` - Only TYPE_CHECKING dep on build_pipeline + llm_judge
3. `judge_execution.py` - Depends on judge_artifacts (lazy import for_save_judge_logs)
4. `judge_context.py` - Depends on build_pipeline + judge_artifacts (lazy imports)

### Full patch target diff

```
# test_llm_judge.py (12 changes)
scylla.e2e.llm_judge._run_python_pipeline -> scylla.e2e.build_pipeline._run_python_pipeline
scylla.e2e.llm_judge._run_mojo_pipeline -> scylla.e2e.build_pipeline._run_mojo_pipeline
scylla.e2e.llm_judge._run_build_pipeline -> scylla.e2e.build_pipeline._run_build_pipeline
scylla.e2e.llm_judge._get_workspace_state -> scylla.e2e.judge_context._get_workspace_state
scylla.e2e.llm_judge._get_patchfile -> scylla.e2e.judge_context._get_patchfile
scylla.e2e.llm_judge._get_deleted_files -> scylla.e2e.judge_context._get_deleted_files
scylla.e2e.llm_judge._call_claude_judge -> scylla.e2e.judge_execution._call_claude_judge

# test_stages.py (10 changes)
scylla.e2e.llm_judge._run_build_pipeline -> scylla.e2e.build_pipeline._run_build_pipeline
scylla.e2e.llm_judge._get_workspace_state -> scylla.e2e.judge_context._get_workspace_state
scylla.e2e.llm_judge._get_patchfile -> scylla.e2e.judge_context._get_patchfile
scylla.e2e.llm_judge._get_deleted_files -> scylla.e2e.judge_context._get_deleted_files
scylla.e2e.llm_judge._save_pipeline_commands -> scylla.e2e.judge_artifacts._save_pipeline_commands
scylla.e2e.llm_judge._save_pipeline_outputs -> scylla.e2e.judge_artifacts._save_pipeline_outputs
scylla.e2e.llm_judge._call_claude_judge -> scylla.e2e.judge_execution._call_claude_judge
scylla.e2e.llm_judge._parse_judge_response -> scylla.e2e.judge_execution._parse_judge_response
scylla.e2e.llm_judge._save_judge_logs -> scylla.e2e.judge_artifacts._save_judge_logs

# test_stage_finalization.py (2 changes)
scylla.e2e.llm_judge._call_claude_judge -> scylla.e2e.judge_execution._call_claude_judge

# test_experiment_setup_manager.py (4 changes)
scylla.e2e.llm_judge._run_build_pipeline -> scylla.e2e.build_pipeline._run_build_pipeline
```
