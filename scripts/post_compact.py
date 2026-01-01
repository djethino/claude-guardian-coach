#!/usr/bin/env python3
"""Post-compaction hook for Guardian Coach.

Injects a system message after context compaction with:
1. Reminder that knowledge is partial
2. The initial task prompt (captured before compaction)
3. User interventions during the task
4. Recently modified files
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0] + "scripts")

from lib.context import (
    fix_stdin_encoding,
    get_context_file,
    load_context,
    save_context,
    load_hook_input,
)

fix_stdin_encoding()


def get_recent_files_with_mtime(cwd: str, since_timestamp: str, limit: int = 15) -> list[tuple[str, str]]:
    """Get files modified since timestamp with their mtime (HH:MM format)."""
    try:
        cwd_path = Path(cwd)
        since_dt = datetime.fromisoformat(since_timestamp)
        since_ts = since_dt.timestamp()
        files_with_mtime = []

        for f in cwd_path.rglob("*"):
            if f.is_file():
                # Skip hidden dirs, common non-relevant paths
                parts = f.relative_to(cwd_path).parts
                if any(p.startswith(".") or p in ("node_modules", "__pycache__", "venv", ".venv") for p in parts):
                    continue
                try:
                    mtime = f.stat().st_mtime
                    if mtime >= since_ts:
                        # Normalize path with forward slashes
                        rel_path = str(f.relative_to(cwd_path)).replace("\\", "/")
                        mtime_str = datetime.fromtimestamp(mtime).strftime("%H:%M")
                        files_with_mtime.append((rel_path, mtime, mtime_str))
                except OSError:
                    pass

        # Sort by mtime descending
        files_with_mtime.sort(key=lambda x: x[1], reverse=True)
        return [(f, t) for f, _, t in files_with_mtime[:limit]]
    except Exception:
        return []


def get_file_mtime(cwd: str, file_path: str) -> str | None:
    """Get mtime of a file in HH:MM format."""
    try:
        full_path = Path(cwd) / file_path
        if full_path.exists():
            mtime = full_path.stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime("%H:%M")
    except OSError:
        pass
    return None


def reset_context(cwd: str, session_id: str) -> None:
    """Reset the context file for a new session."""
    context = {
        "initial_prompt": None,
        "initial_timestamp": None,
        "interventions": []
    }
    save_context(cwd, session_id, context)


def main() -> int:
    input_data = load_hook_input()
    if not input_data:
        return 0

    source = input_data.get("source", "")
    cwd = input_data.get("cwd", "")
    session_id = input_data.get("session_id", "")

    if not cwd or not session_id:
        return 0

    # New session (not compaction) = reset context
    if source != "compact":
        reset_context(cwd, session_id)
        return 0

    # Compaction = inject context message
    now = datetime.now()
    now_str = now.strftime("%H:%M")

    lines = [
        "⚠️ CONTEXT COMPACTED",
        "",
        "Le contexte a été compressé. Tu as reçu un résumé, mais il capture le QUOI, rarement le POURQUOI.",
        ""
    ]

    # Load captured context
    context = load_context(cwd, session_id)

    if context:
        # Show timestamps
        initial_ts = context.get("initial_timestamp")
        if initial_ts:
            try:
                start_time = datetime.fromisoformat(initial_ts).strftime("%H:%M")
                lines.append(f"📅 Tâche démarrée à : {start_time}")
                lines.append(f"📅 Compaction à : {now_str}")
                lines.append("")
            except ValueError:
                pass

        if context.get("initial_prompt"):
            lines.append("📋 DEMANDE INITIALE :")
            lines.append(context["initial_prompt"])
            lines.append("")

        interventions = context.get("interventions", [])
        if interventions:
            lines.append("💬 INTERVENTIONS UTILISATEUR :")
            for interv in interventions[-5:]:  # Last 5 only
                lines.append(f"  - {interv.get('prompt', '')[:200]}")
            lines.append("")

        # Only show file sections if we have a timestamp
        if initial_ts:
            # Show files accessed during this task (tracked via PostToolUse hook)
            # Structure: {"path": ["read", "update"], ...}
            file_access = context.get("file_access", {})
            if file_access:
                lines.append("📁 FICHIERS ACCÉDÉS PENDANT CETTE TÂCHE :")
                for f, accesses in file_access.items():
                    mtime = get_file_mtime(cwd, f)
                    # Format access types
                    access_str = "+".join(sorted(accesses, key=lambda x: {"read": 0, "update": 1, "write": 2}.get(x, 3)))
                    time_str = f" ({mtime})" if mtime else ""
                    lines.append(f"  - {f} [{access_str}]{time_str}")
                lines.append("")

            # Show other files modified since task start (mtime-based)
            # These could be from subagents, other Claude instances, or external tools
            tracked_files = set(file_access.keys())
            all_recent_files = get_recent_files_with_mtime(cwd, initial_ts)
            other_files = [(f, t) for f, t in all_recent_files if f not in tracked_files]
            if other_files:
                lines.append("📁 AUTRES FICHIERS MODIFIÉS DEPUIS LE DÉBUT DE LA TÂCHE :")
                lines.append("   (subagents, autres instances, outils externes)")
                for f, mtime in other_files:
                    lines.append(f"  - {f} ({mtime})")
                lines.append("")
    else:
        lines.append("(Pas de contexte de tâche capturé)")
        lines.append("")

    lines.extend([
        "Analyse ces informations et continue la tâche.",
        "",
        "Pendant ton travail, si tu sens que :",
        "- Tu es perdu ou tu ne comprends plus le POURQUOI",
        "- Tu vas simplifier ou couper des coins pour aller plus vite",
        "- Tu risques de casser quelque chose qui existait avant",
        "",
        "→ ARRÊTE et fais un point avec l'utilisateur :",
        "  - Ce qui a été complètement fait",
        "  - Ce qui reste à faire",
        "  - Ce que tu n'es pas sûr de comprendre"
    ])

    message = "\n".join(lines)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
