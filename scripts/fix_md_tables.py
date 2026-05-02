#!/usr/bin/env python3
"""
Reformat markdown tables to pass MD060 markdownlint checks.

Normalises every markdown table in each file to "compact" style:
    | cell content |
so that markdownlint (MD060 style: consistent) sees a uniform style
within every table and raises no errors.

Tables inside YAML frontmatter or fenced code blocks are left unchanged.

Usage:
    python3 scripts/fix_md_tables.py file1.md file2.md ...
    python3 scripts/fix_md_tables.py --all          # process all *.md under cwd
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List  # noqa: UP006

_SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")


def _is_table_line(line: str) -> bool:
    stripped = line.rstrip("\n")
    return stripped.lstrip().startswith("|") and stripped.rstrip().endswith("|")


def _is_separator_cell(cell: str) -> bool:
    return bool(_SEPARATOR_CELL_RE.match(cell))


def _normalise_separator_cell(cell: str) -> str:
    lead = ":" if cell.startswith(":") else ""
    trail = ":" if cell.endswith(":") and cell != ":" else ""
    dashes = cell.strip(":")
    dash_count = max(3, len(dashes))
    return lead + "-" * dash_count + trail


def _normalise_row(line: str) -> str:
    stripped = line.rstrip("\n")
    lstrip_count = len(stripped) - len(stripped.lstrip())
    indent = stripped[:lstrip_count]
    inner = stripped.lstrip().lstrip("|").rstrip("|")

    cells = inner.split("|")
    normalised: List[str] = []
    for cell in cells:
        content = cell.strip()
        if not content:
            normalised.append(" ")
        elif _is_separator_cell(content):
            normalised.append(f" {_normalise_separator_cell(content)} ")
        else:
            normalised.append(f" {content} ")

    return indent + "|" + "|".join(normalised) + "|\n"


def _process_lines(lines: List[str]) -> List[str]:
    result: List[str] = []
    in_frontmatter = False
    in_code_block = False
    code_fence: str = ""

    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")

        if i == 0 and stripped == "---":
            in_frontmatter = True
            result.append(line)
            continue

        if in_frontmatter:
            result.append(line)
            if stripped in ("---", "..."):
                in_frontmatter = False
            continue

        if not in_code_block:
            fence_match = stripped.lstrip()
            if fence_match.startswith("```") or fence_match.startswith("~~~"):
                code_fence = fence_match[:3]
                in_code_block = True
                result.append(line)
                continue
        else:
            fence_match = stripped.lstrip()
            if fence_match.startswith(code_fence):
                in_code_block = False
                code_fence = ""
            result.append(line)
            continue

        if _is_table_line(line):
            result.append(_normalise_row(line))
        else:
            result.append(line)

    return result


def fix_file(path: Path) -> bool:
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR reading {path}: {exc}", file=sys.stderr)
        return False

    lines = original.splitlines(keepends=True)
    fixed_lines = _process_lines(lines)
    fixed = "".join(fixed_lines)

    if fixed == original:
        return False

    try:
        path.write_text(fixed, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR writing {path}: {exc}", file=sys.stderr)
        return False

    return True


def _collect_all_md_files(root: Path) -> List[Path]:
    return sorted(root.rglob("*.md"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reformat markdown tables to compact style (MD060 compatible).",
    )
    parser.add_argument("files", nargs="*", metavar="FILE", help="Markdown files to process.")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_files",
        help="Process all *.md files found recursively under the current directory.",
    )
    args = parser.parse_args()

    if not args.files and not args.all_files:
        parser.print_help()
        return 1

    paths: List[Path] = []
    if args.all_files:
        paths = _collect_all_md_files(Path("."))
    else:
        paths = [Path(f) for f in args.files]

    modified = 0
    errors = 0
    for path in paths:
        if not path.exists():
            print(f"WARNING: {path} does not exist — skipping", file=sys.stderr)
            errors += 1
            continue
        changed = fix_file(path)
        if changed:
            print(f"fixed: {path}")
            modified += 1

    print(f"\nDone. {modified} file(s) modified, {errors} error(s).")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
