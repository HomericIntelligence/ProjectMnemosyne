"""Behavioral regression tests for staged GitHub merge-queue readiness."""

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
REQUIRED_WORKFLOW = WORKFLOWS_DIR / "_required.yml"
VALIDATE_WORKFLOW = WORKFLOWS_DIR / "validate-plugins.yml"
RELEASE_WORKFLOW = WORKFLOWS_DIR / "release.yml"
MERGE_QUEUE_POLICY = REPO_ROOT / "configs" / "github" / "merge-queue-policy.json"

EXPECTED_REQUIRED_CONTEXTS_BY_RULESET = {
    "homeric-main-baseline": [
        "build",
        "deps/version-sync",
        "integration-tests",
        "lint",
        "schema-validation",
        "security/dependency-scan",
        "security/secrets-scan",
        "test",
        "unit-tests",
    ],
    "homeric-main-extras": [
        "pixi-check",
        "symlink-check",
    ],
}
EXPECTED_REQUIRED_CONTEXTS = sorted(
    context for contexts in EXPECTED_REQUIRED_CONTEXTS_BY_RULESET.values() for context in contexts
)
EXPECTED_MERGE_QUEUE_RULE = {
    "type": "merge_queue",
    "parameters": {
        "check_response_timeout_minutes": 60,
        "grouping_strategy": "ALLGREEN",
        "max_entries_to_build": 10,
        "max_entries_to_merge": 5,
        "merge_method": "SQUASH",
        "min_entries_to_merge": 1,
        "min_entries_to_merge_wait_minutes": 5,
    },
}


def _load_workflow(path: Path) -> dict[Any, Any]:
    workflow = yaml.safe_load(path.read_text())
    assert isinstance(workflow, dict), f"{path} must contain a workflow mapping"
    return workflow


def _on_block(workflow: dict[Any, Any]) -> dict[Any, Any]:
    """Return the Actions trigger block despite PyYAML 1.1 coercing `on`."""
    on_block = workflow.get(True, workflow.get("on"))
    assert isinstance(on_block, dict), "workflow `on` block must be a mapping"
    return on_block


def _load_policy() -> dict[str, Any]:
    policy = json.loads(MERGE_QUEUE_POLICY.read_text())
    assert isinstance(policy, dict), "merge-queue policy must be a JSON object"
    return policy


def test_policy_pins_exact_live_required_contexts_by_ruleset() -> None:
    policy = _load_policy()

    assert policy["required_contexts_by_ruleset"] == EXPECTED_REQUIRED_CONTEXTS_BY_RULESET
    assert policy["required_contexts"] == EXPECTED_REQUIRED_CONTEXTS


def test_policy_contexts_are_exact_union_of_ruleset_contexts() -> None:
    policy = _load_policy()
    contexts_by_ruleset = policy["required_contexts_by_ruleset"]
    derived_contexts = sorted(context for contexts in contexts_by_ruleset.values() for context in contexts)

    assert policy["required_contexts"] == derived_contexts
    assert len(derived_contexts) == len(set(derived_contexts))


def test_policy_pins_exact_approved_queue_rule() -> None:
    assert _load_policy()["merge_queue_rule"] == EXPECTED_MERGE_QUEUE_RULE


def test_only_required_workflow_adds_exact_merge_group_trigger() -> None:
    required_on = _on_block(_load_workflow(REQUIRED_WORKFLOW))
    validate_on = _on_block(_load_workflow(VALIDATE_WORKFLOW))

    assert required_on == {
        "pull_request": {"branches": ["main"]},
        "push": {"branches": ["main"]},
        "merge_group": {"types": ["checks_requested"]},
    }
    assert validate_on == {
        "pull_request": None,
        "push": {"branches": ["main"]},
        "workflow_dispatch": None,
    }


def test_required_workflow_emits_every_policy_context_exactly_once() -> None:
    jobs = _load_workflow(REQUIRED_WORKFLOW)["jobs"]
    emitted_names = [job.get("name", job_id) for job_id, job in jobs.items() if isinstance(job, dict)]
    policy_contexts = _load_policy()["required_contexts"]
    emitted_policy_contexts = [name for name in emitted_names if name in policy_contexts]

    assert sorted(emitted_policy_contexts) == policy_contexts
    assert len(emitted_policy_contexts) == len(set(emitted_policy_contexts))


def test_workflows_keep_existing_least_privilege_permissions() -> None:
    required_workflow = _load_workflow(REQUIRED_WORKFLOW)
    validate_workflow = _load_workflow(VALIDATE_WORKFLOW)
    release_workflow = _load_workflow(RELEASE_WORKFLOW)

    assert required_workflow["permissions"] == {"contents": "read"}
    assert validate_workflow["permissions"] == {"contents": "read"}
    assert release_workflow["permissions"] == {"contents": "write"}


def test_required_secrets_scan_still_blocks_detected_secrets() -> None:
    workflow = _load_workflow(REQUIRED_WORKFLOW)
    job = workflow["jobs"]["security-secrets-scan"]
    scan = next(step for step in job["steps"] if step.get("name") == "Run Gitleaks")
    upload = next(step for step in job["steps"] if step.get("name") == "Upload Gitleaks SARIF")

    assert "--exit-code 0" not in scan["run"]
    assert upload["if"] == "always() && hashFiles('gitleaks.sarif') != ''"


def test_release_publisher_remains_tag_only() -> None:
    on_block = _on_block(_load_workflow(RELEASE_WORKFLOW))

    assert on_block == {"push": {"tags": ["v*"]}}
