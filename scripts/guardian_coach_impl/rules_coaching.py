"""Coaching rules: guide Claude toward native tools instead of bash commands.

This module detects when Claude tries to use bash commands for file operations
that should be done with native Claude Code tools (Read, Write, Edit, Grep, Glob).
"""

import shlex


def _shlex_split(command: str) -> list[str] | None:
    """Split a shell command into tokens, returning None on parse error."""
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return None

# Coaching messages - these guide Claude to use the right tool
_COACH_USE_EDIT = (
    "COACHING: Use the Edit tool instead of '{cmd}' for file modifications. "
    "The Edit tool is more reliable and won't cause 'File unexpectedly modified' errors."
)

_COACH_USE_WRITE = (
    "COACHING: Use the Write tool instead of '{cmd}' for creating/overwriting files. "
    "The Write tool is the proper way to create files in Claude Code."
)

_COACH_USE_READ = (
    "COACHING: Use the Read tool instead of '{cmd}' for viewing file contents. "
    "The Read tool supports offset/limit for large files."
)

_COACH_USE_GREP = (
    "COACHING: Use the Grep tool instead of '{cmd}' for searching file contents. "
    "The Grep tool is optimized for Claude Code and provides better results."
)

_COACH_USE_GLOB = (
    "COACHING: Use the Glob tool instead of '{cmd}' for finding files. "
    "The Glob tool is faster and designed for codebase exploration."
)


def _analyze_coaching(tokens: list[str], command: str) -> str | None:
    """Analyze a command for coaching opportunities.

    Returns a coaching message if Claude should use a native tool instead,
    or None if the command is fine as-is.
    """
    if not tokens:
        return None

    head = tokens[0].lower()

    # File modification commands -> Edit tool
    if head == "sed":
        if _is_inplace_sed(tokens):
            return _COACH_USE_EDIT.format(cmd="sed -i")

    if head == "awk":
        if _has_output_redirect(command):
            return _COACH_USE_EDIT.format(cmd="awk with redirect")

    # File creation/overwrite -> Write tool
    if _is_echo_redirect(command) or _is_cat_heredoc(command):
        return _COACH_USE_WRITE.format(cmd="echo/cat redirect")

    if head == "printf" and _has_output_redirect(command):
        return _COACH_USE_WRITE.format(cmd="printf redirect")

    # File reading -> Read tool
    if head == "cat" and not _is_cat_heredoc(command) and not _has_pipe(command):
        # cat without pipe is just reading a file
        if len(tokens) > 1 and not tokens[1].startswith("-"):
            return _COACH_USE_READ.format(cmd="cat")

    if head in ("head", "tail"):
        # Only coach if there's a file argument (not just flags like -50, -n 10)
        # If only flags, it's likely receiving piped input: cmd | head -50
        has_file_arg = any(not t.startswith("-") for t in tokens[1:])
        if has_file_arg and not _has_pipe(command):
            return _COACH_USE_READ.format(cmd=head)

    # Search commands -> Grep tool
    if head in ("grep", "rg", "ripgrep"):
        if not _has_pipe_input(command):
            return _COACH_USE_GREP.format(cmd=head)

    # File finding -> Glob tool
    if head == "find":
        if not _has_exec_or_delete(tokens):
            return _COACH_USE_GLOB.format(cmd="find")

    if head == "ls" and _is_glob_pattern_ls(tokens):
        return _COACH_USE_GLOB.format(cmd="ls with pattern")

    return None


def _is_inplace_sed(tokens: list[str]) -> bool:
    """Check if sed is used with -i (in-place editing)."""
    for tok in tokens[1:]:
        if tok == "-i" or tok.startswith("-i"):
            return True
        if tok == "--in-place":
            return True
        # Handle combined options like -ni, -ie
        if tok.startswith("-") and not tok.startswith("--") and "i" in tok:
            return True
    return False


def _has_output_redirect(command: str) -> bool:
    """Check if command has output redirection (> or >>)."""
    # Simple check - could be more sophisticated
    # Avoid matching inside quotes
    in_single = False
    in_double = False
    i = 0
    while i < len(command):
        c = command[i]
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == ">" and not in_single and not in_double:
            return True
        i += 1
    return False


def _is_echo_redirect(command: str) -> bool:
    """Check if command is echo with redirect to file."""
    stripped = command.strip()
    if not (stripped.startswith("echo ") or stripped.startswith("echo\t")):
        return False
    return _has_output_redirect(command)


def _is_cat_heredoc(command: str) -> bool:
    """Check if command is cat with heredoc (cat << EOF > file)."""
    if "<<" not in command or "cat" not in command.lower():
        return False
    # Command substitution with cat is not file writing
    if "$(cat" in command.lower():
        return False
    return _has_output_redirect(command)


def _has_pipe(command: str) -> bool:
    """Check if command has a pipe."""
    in_single = False
    in_double = False
    for c in command:
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == "|" and not in_single and not in_double:
            return True
    return False


def _has_pipe_input(command: str) -> bool:
    """Check if command receives input from a pipe (appears after |)."""
    # If grep/rg is after a pipe, it's processing pipe input which is valid
    parts = command.split("|")
    if len(parts) <= 1:
        return False
    # Check if our command is NOT the first part
    first_part = parts[0].strip().lower()
    return not (first_part.startswith("grep") or
                first_part.startswith("rg") or
                first_part.startswith("ripgrep"))


def _has_exec_or_delete(tokens: list[str]) -> bool:
    """Check if find has -exec or -delete (legitimate use cases)."""
    for tok in tokens:
        if tok in ("-exec", "-execdir", "-delete", "-ok", "-okdir"):
            return True
    return False


def _is_glob_pattern_ls(tokens: list[str]) -> bool:
    """Check if ls is being used with glob patterns (should use Glob tool)."""
    for tok in tokens[1:]:
        if tok.startswith("-"):
            continue
        # Check for glob characters
        if any(c in tok for c in ("*", "?", "[", "]")):
            return True
    return False
