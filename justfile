# Mnemosyne command runner — wraps Python scripts for consistent developer experience.
# All path variables are configurable at the top of the file.
# Recipes run under uv (ADR-017): `uv run` resolves the locked environment from
# pyproject.toml + uv.lock, so no separate activation step is needed.

# Directory containing skill markdown files
skills_dir := "skills"

# Directory containing test files
test_dir := "tests"

# === Default ===

# List available recipes
default:
    @just --list

# === Validation ===

# Validate all skill files in the skills/ directory
validate:
    uv run python scripts/validate_plugins.py

# === Packaging ===

# Build the Python wheel + sdist (mnemosyne_skill_utils) into dist/
package:
    uv run python -m build

# === Testing ===

# Run all tests
test:
    uv run python -m pytest {{ test_dir }}

# === Composite ===

# Run validate + test (full check)
check: validate test
