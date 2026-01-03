"""Path correction rules: convert absolute paths to relative paths.

This module detects when Claude uses absolute paths for files within the
current working directory and converts them to relative paths. This prevents
the "File has been unexpectedly modified" error that occurs when Claude
uses absolute paths with Edit/Write tools.
"""

import os
import posixpath


def analyze_and_fix_path(
    file_path: str,
    cwd: str | None,
) -> tuple[str | None, str | None]:
    """Analyze a file path and return a corrected relative path if needed.

    Args:
        file_path: The file path from tool_input
        cwd: The current working directory

    Returns:
        Tuple of (corrected_path, reason) where:
        - corrected_path is the relative path if correction needed, None otherwise
        - reason is the explanation message if corrected, None otherwise
    """
    if not cwd or not file_path:
        return None, None

    # Normalize paths for comparison
    # Handle both Unix and Windows style paths
    normalized_cwd = _normalize_path(cwd)
    normalized_file = _normalize_path(file_path)

    # Check if it's an absolute path within cwd
    if _is_absolute_path_in_cwd(normalized_file, normalized_cwd):
        relative_path = _make_relative(normalized_file, normalized_cwd)
        reason = (
            f"COACHING: Use relative path instead of absolute path.\n"
            f"Replace: {file_path}\n"
            f"With: {relative_path}\n\n"
            f"Absolute paths cause 'File unexpectedly modified' errors."
        )
        return relative_path, reason

    return None, None


def _normalize_path(path: str) -> str:
    """Normalize a path for comparison.

    Converts backslashes to forward slashes and removes trailing slashes.
    """
    # Convert Windows backslashes to forward slashes
    normalized = path.replace("\\", "/")

    # Remove trailing slash
    normalized = normalized.rstrip("/")

    # Handle Windows drive letters (C: -> /c)
    if len(normalized) >= 2 and normalized[1] == ":":
        drive = normalized[0].lower()
        normalized = "/" + drive + normalized[2:]

    return normalized


def _is_absolute_path_in_cwd(file_path: str, cwd: str) -> bool:
    """Check if file_path is an absolute path that points inside cwd.

    Args:
        file_path: Normalized file path
        cwd: Normalized current working directory

    Returns:
        True if file_path is absolute and inside cwd, False otherwise
    """
    # Check if it's an absolute path
    if not file_path.startswith("/"):
        return False

    # Check if it's inside cwd
    # Must start with cwd + "/" to be inside (not just a prefix match)
    if file_path == cwd:
        # Path is exactly cwd - this is unusual for a file path
        return False

    return file_path.startswith(cwd + "/")


def _make_relative(file_path: str, cwd: str) -> str:
    """Convert an absolute path to a relative path from cwd.

    Args:
        file_path: Normalized absolute file path inside cwd
        cwd: Normalized current working directory

    Returns:
        Relative path from cwd to file_path
    """
    # Remove cwd prefix and leading slash
    relative = file_path[len(cwd):]
    if relative.startswith("/"):
        relative = relative[1:]

    return relative


def should_fix_path(tool_name: str) -> bool:
    """Check if a tool should have its paths fixed.

    Args:
        tool_name: The name of the tool being called

    Returns:
        True if the tool's file_path should be checked and fixed
    """
    return tool_name in {"Read", "Edit", "Write", "MultiEdit"}
