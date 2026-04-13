# JARFIS Health Check — Zombie Process Diagnosis and Cleanup

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Perform a system health check. Arguments: $ARGUMENTS

---

## Execution Flow

### Step 1: Verify Script Exists

Check whether the file `~/.claude/scripts/claude-cleanup.sh` exists.
If it does not exist, display the following message and exit:

```
[JARFIS Health] The cleanup script is not installed.
Path: ~/.claude/scripts/claude-cleanup.sh

⚠️ claude-cleanup.sh is an external script (not included in the JARFIS repository).
Install it separately, re-run install.sh, or update via /jarfis:version.
Other JARFIS features work normally without this script.
```

### Step 2: Determine Mode

Check `$ARGUMENTS` to determine the execution mode:

| Argument | Mode | Behavior |
|----------|------|----------|
| (none) | Diagnostic mode | Display status only |
| `--clean` | Cleanup mode | Run cleanup immediately (no confirmation) |

### Step 3: Run Diagnostics

Execute `~/.claude/scripts/claude-cleanup.sh` via Bash (no arguments, diagnostic mode).

Parse the output to extract the following information:
- Number of active processes
- Number of zombie processes
- Reclaimable memory

### Step 4: Display Summary

Display the results in the following format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Active Claude processes:    N
  Zombie Claude processes:    N
  Reclaimable memory:         ~NMB

  (Original script output is shown above)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 5: Execute Cleanup (depending on mode)

**Diagnostic mode** (no arguments):
- If zombies are found, display an additional guidance message:
  ```
  To clean up: /jarfis:sys-health --clean
  ```
- If no zombies are found, exit as-is

**Cleanup mode** (`--clean`):
- If there are 0 zombies, display "No zombie processes found. Nothing to clean up." and exit
- If zombies exist, immediately run `~/.claude/scripts/claude-cleanup.sh --kill` without confirmation
- Display a summary of the cleanup results
