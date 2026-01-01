#!/usr/bin/env python3
"""Stop hook for Guardian Coach.

Sets task_completed flag so next UserPromptSubmit knows to start a new task.
"""

import sys

# Add lib to path
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0] + "scripts")

from lib.context import (
    fix_stdin_encoding,
    load_context,
    save_context,
    load_hook_input,
)

fix_stdin_encoding()


def main() -> int:
    input_data = load_hook_input()
    if not input_data:
        return 0

    cwd = input_data.get("cwd", "")
    session_id = input_data.get("session_id", "")
    if not cwd or not session_id:
        return 0

    # Set task_completed flag
    context = load_context(cwd, session_id) or {}
    context["task_completed"] = True
    save_context(cwd, session_id, context)

    return 0


if __name__ == "__main__":
    sys.exit(main())
