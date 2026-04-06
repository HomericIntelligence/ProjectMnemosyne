# ProjectMnemosyne command runner — wraps Python scripts for consistent developer experience.
# All path variables are configurable at the top of the file.

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

# === Marketplace ===

# Regenerate marketplace.json index from all skill files
generate-marketplace:
    python3 scripts/generate_marketplace.py

# === Testing ===

# Run all tests
test:
    python3 -m pytest {{ test_dir }}

# === Composite ===

# Run validate + test (full check)
check: validate test
