"""Shared context handling for Guardian Coach hooks.

This module provides common utilities for:
- Reading/writing task context files
- UTF-8 stdin fix for Windows
- Session-based context file paths
"""

import json
import sys
from pathlib import Path


def fix_stdin_encoding() -> None:
    """Fix stdin encoding for Windows (defaults to CP1252, not UTF-8)."""
    sys.stdin.reconfigure(encoding='utf-8')


def get_contexts_dir(cwd: str) -> Path:
    """Get path to task-contexts directory."""
    return Path(cwd) / ".claude" / "task-contexts"


def get_context_file(cwd: str, session_id: str) -> Path:
    """Get path to context file for this session."""
    return get_contexts_dir(cwd) / f"{session_id}.json"


def load_context(cwd: str, session_id: str) -> dict | None:
    """Load task context if it exists."""
    context_file = get_context_file(cwd, session_id)
    if context_file.exists():
        try:
            return json.loads(context_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_context(cwd: str, session_id: str, context: dict) -> bool:
    """Save task context to file. Returns True on success."""
    context_file = get_context_file(cwd, session_id)
    try:
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_file.write_text(
            json.dumps(context, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except OSError:
        return False


def normalize_path(file_path: str, cwd: str) -> str:
    """Convert to relative path and normalize separators."""
    try:
        cwd_path = Path(cwd)
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            try:
                file_path = str(file_path_obj.relative_to(cwd_path))
            except ValueError:
                # File is outside cwd, keep absolute
                pass
        # Normalize to forward slashes for consistency
        return file_path.replace("\\", "/")
    except Exception:
        return file_path.replace("\\", "/")


def load_hook_input() -> dict | None:
    """Load and parse JSON input from stdin. Returns None on error."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return None
