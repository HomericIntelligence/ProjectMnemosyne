# Mnemosyne command runner — wraps Python scripts for consistent developer experience.
# All path variables are configurable at the top of the file.
# Note: equivalent tasks are also defined in pixi.toml for pixi users.

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
    python3 scripts/validate_plugins.py

# === Packaging ===

# Build the Python wheel + sdist (mnemosyne_skill_utils) into dist/
package:
    python3 -m build

# === Testing ===

# Run all tests
test:
    python3 -m pytest {{ test_dir }}

# === Composite ===

# Run validate + test (full check)
check: validate test
