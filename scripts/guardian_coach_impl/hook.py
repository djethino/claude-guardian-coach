"""Guardian Coach for Claude Code.

Lightweight coaching plugin:
1. Path correction: Converts absolute paths to relative for Edit/Write/Read
2. Coaching: Guides Claude toward native tools (Edit/Write instead of sed/echo)
"""

import json
import sys
from os import getenv

from .rules_coaching import _analyze_coaching, _shlex_split
from .rules_paths import analyze_and_fix_path, should_fix_path


def main() -> int:
    """Main entry point for the Guardian Coach hook."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if not isinstance(input_data, dict):
        return 0

    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input")

    if not isinstance(tool_input, dict):
        return 0

    cwd_val = input_data.get("cwd")
    cwd = cwd_val.strip() if isinstance(cwd_val, str) else None
    if cwd == "":
        cwd = None

    # Handle Edit/Write/Read tools - rewrite absolute paths to relative
    if should_fix_path(tool_name):
        file_path = tool_input.get("file_path")
        if isinstance(file_path, str):
            corrected_path, reason = analyze_and_fix_path(file_path, cwd)
            if corrected_path:
                # For Edit: Claude checks "file read" status BEFORE applying updatedInput,
                # so we must deny with coaching instead of rewriting
                if tool_name == "Edit":
                    output = {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": (
                                f"PATH CORRECTION: Use relative path instead.\n\n"
                                f"Change: {file_path}\n"
                                f"To:     {corrected_path}\n\n"
                                f"Reason: {reason}"
                            ),
                        }
                    }
                else:
                    # For Read/Write: updatedInput works fine
                    output = {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "allow",
                            "updatedInput": {
                                **tool_input,
                                "file_path": corrected_path,
                            },
                            "systemMessage": f"PATH CORRECTED: {file_path} -> {corrected_path}",
                        }
                    }
                print(json.dumps(output))
                return 0
        return 0

    # Handle Bash tool - coaching checks only
    if tool_name != "Bash":
        return 0

    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    # Check if coaching is enabled (default: yes)
    coaching_enabled = getenv("GUARDIAN_COACH_COACHING", "1") == "1"
    if not coaching_enabled:
        return 0

    # Tokenize the command
    tokens = _shlex_split(command)
    if not tokens:
        return 0

    # Check for coaching opportunities
    coaching_reason = _analyze_coaching(tokens, command)
    if coaching_reason:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"{coaching_reason}\n\n"
                    f"Command: {command[:300]}{'…' if len(command) > 300 else ''}\n"
                ),
            }
        }
        print(json.dumps(output))
        return 0

    return 0
