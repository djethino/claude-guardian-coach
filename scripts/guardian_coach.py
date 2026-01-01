#!/usr/bin/env python3
"""
Guardian Coach for Claude Code.

Two modes:
1. Security: Blocks destructive commands (git reset --hard, rm -rf, etc.)
2. Coaching: Guides Claude toward native tools (Edit/Write instead of sed/echo)

Exit behavior:
  - Exit 0 with JSON containing permissionDecision: "deny" = block command
  - Exit 0 with no output = allow command
"""

try:
    from scripts.guardian_coach_impl.hook import main as _impl_main
except ImportError:  # When executed as a script from the scripts/ directory.
    from guardian_coach_impl.hook import main as _impl_main  # type: ignore[no-redef]


def main() -> int:
    return _impl_main()


if __name__ == "__main__":
    import sys

    sys.exit(main())
