#!/usr/bin/env python3
"""UserPromptSubmit hook for Guardian Coach.

Captures user prompts to provide context after compaction.

Logic:
- If task_completed flag is True (set by Stop hook):
  → This is a NEW task, reset and save as initial prompt
- Otherwise:
  → This is an intervention on the current task, add to list
"""

import sys
from datetime import datetime

# Add lib to path
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0] + "scripts")

from lib.context import (
    fix_stdin_encoding,
    get_contexts_dir,
    get_context_file,
    load_context,
    save_context,
    load_hook_input,
)

fix_stdin_encoding()

MAX_CONTEXT_FILES = 10


def cleanup_old_contexts(cwd: str) -> None:
    """Keep only the MAX_CONTEXT_FILES most recent context files."""
    contexts_dir = get_contexts_dir(cwd)
    if not contexts_dir.exists():
        return
    try:
        files = list(contexts_dir.glob("*.json"))
        if len(files) <= MAX_CONTEXT_FILES:
            return
        # Sort by mtime, oldest first
        files.sort(key=lambda f: f.stat().st_mtime)
        # Delete oldest files
        for f in files[:-MAX_CONTEXT_FILES]:
            f.unlink()
    except OSError:
        pass


def main() -> int:
    input_data = load_hook_input()
    if not input_data:
        return 0

    cwd = input_data.get("cwd", "")
    prompt = input_data.get("prompt", "")
    session_id = input_data.get("session_id", "")

    if not cwd or not prompt or not session_id:
        return 0

    timestamp = datetime.now().isoformat()
    context = load_context(cwd, session_id) or {
        "initial_prompt": None,
        "initial_timestamp": None,
        "interventions": [],
        "task_completed": True  # Default to True so first prompt starts a task
    }

    # Check if this is a new task (task_completed flag set by Stop hook)
    if context.get("task_completed", True):
        # New task - reset and save as initial prompt
        context = {
            "initial_prompt": prompt[:1000],
            "initial_timestamp": timestamp,
            "interventions": [],
            "task_completed": False  # Clear flag
        }
    else:
        # Same task - add as intervention
        context["interventions"].append({
            "timestamp": timestamp,
            "prompt": prompt[:500]
        })

    save_context(cwd, session_id, context)
    cleanup_old_contexts(cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
