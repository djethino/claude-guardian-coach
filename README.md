# Guardian Coach

Claude Code plugin for behavioral guidance and context preservation.

## Purpose

Guardian Coach addresses recurring issues in Claude Code usage:

1. **Suboptimal tool usage** — Claude sometimes uses bash commands when native tools would be more appropriate
2. **Context loss after compaction** — Automatic summaries capture the "what" but rarely the "why"
3. **Path handling on Windows** — Absolute paths cause "File unexpectedly modified" errors
4. **Multi-agent awareness** — No visibility into files modified by subagents or parallel sessions

## Features

### Coaching
Suggests native tools when appropriate:
- `sed -i` → Edit
- `cat file` → Read
- `echo > file` → Write
- `grep pattern` → Grep
- `find -name` → Glob

### Path Correction
Automatically converts absolute paths to relative paths for Edit/Write/Read.
Prevents the "File has been unexpectedly modified" error common on Windows.

### Post-Compaction Context
After context compaction, injects:
- The initial task prompt
- User interventions during the task
- Files accessed with operation type (read/write/update)
- Timestamps to situate the timeline

### Multi-Session Support
- Each Claude session gets its own context file
- Multiple Claude instances can run in parallel without conflicts
- Automatic cleanup keeps only the 10 most recent context files

### File Tracking
Tracks all file operations during a task:
- **Direct access**: Files you read/write/edit are tracked with operation type
- **Other modifications**: Files modified by subagents, other Claude instances, or external tools are detected via mtime and shown separately after compaction

This distinction helps understand what happened during the task, especially when subagents or parallel processes were involved.

## Installation

### From GitHub

```bash
/plugin marketplace add djethino/claude-guardian-coach
/plugin install claude-guardian-coach
```

### Local development

```bash
git clone https://github.com/djethino/claude-guardian-coach.git
cd claude-guardian-coach
# Edit files...
python ../deploy-guardian-coach.py  # from parent directory
```

Restart Claude Code after installation.

## Configuration

| Variable | Effect |
|----------|--------|
| `GUARDIAN_COACH_COACHING=0` | Disable coaching |

## Structure

```
scripts/
  guardian_coach.py           # Entry point
  guardian_coach_impl/
    hook.py                   # Main logic
    rules_coaching.py         # Coaching rules
    rules_paths.py            # Path correction
  lib/
    context.py                # Shared utilities
  on_prompt.py                # Prompt capture
  on_stop.py                  # Task completion detection
  on_file_access.py           # File tracking
  post_compact.py             # Post-compaction injection
```

## How It Works

1. **UserPromptSubmit** — Captures the initial prompt and user interventions
2. **Stop** — Detects when a task completes to distinguish new tasks from follow-ups
3. **PostToolUse** — Tracks Read/Edit/Write operations with access types
4. **SessionStart** — After compaction, injects context with prompts, files, and timestamps

Context is stored per-session in `.claude/task-contexts/{session_id}.json`.

## License

MIT — Copyright (c) 2025 ASymptOmatik

---

## See Also

**[claude-code-safety-net](https://github.com/kenryu42/claude-code-safety-net)** — Complementary plugin for security. Blocks destructive commands (`rm -rf`, `git reset --hard`, `git push --force`, etc.). Guardian Coach focuses on guidance; safety-net on protection. Both work together.
