#!/usr/bin/env python3
"""
Hook triggered on UserPromptSubmit when user types session-ending keywords.
Adds context reminding about /retrospective - does not block.

Receives JSON input with:
- prompt: The user's prompt text
- session_id: Session identifier
- cwd: Current working directory

Outputs JSON to stdout for Claude to process.

Installation:
1. Copy this file to your project's .claude/hooks/ directory
2. Add the hook config to .claude/settings.json (see settings.json.example)
"""

import json
import sys
import re


def main():
    """Main entry point for the hook."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get("prompt", "").lower()

    # Check for session-ending keywords
    ending_patterns = [
        r"\b(exit|quit|bye|goodbye)\b",
        r"^/clear\b",
        r"\b(done|finished|wrapping up)\b",
        r"\b(end.*session|session.*end)\b",
    ]

    for pattern in ending_patterns:
        if re.search(pattern, prompt):
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "[Retrospective Reminder] Before ending this session, "
                        "consider running /retrospective to capture any learnings."
                    ),
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    # No match, exit silently
    sys.exit(0)


if __name__ == "__main__":
    main()
