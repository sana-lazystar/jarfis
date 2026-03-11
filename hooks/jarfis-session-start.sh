#!/bin/bash
# JARFIS SessionStart Context Restore Hook
# Finds in-progress workflows and outputs context summary to stdout.
# stdout output is injected into Claude's context automatically.
#
# Kill switch: JARFIS_SESSION_RESTORE=0

# Kill switch
if [[ "${JARFIS_SESSION_RESTORE:-1}" == "0" ]]; then
  exit 0
fi

# Workspace directory resolution (same logic as pre-compact)
WORKS_DIR_FILE="$HOME/.claude/.jarfis-works-dir"
if [[ -f "$WORKS_DIR_FILE" ]]; then
  JARFIS_WORKSPACE_DIR=$(cat "$WORKS_DIR_FILE" | tr -d '[:space:]')
else
  SOURCE_FILE="$HOME/.claude/.jarfis-source"
  if [[ -f "$SOURCE_FILE" ]]; then
    JARFIS_WORKSPACE_DIR="$(cat "$SOURCE_FILE" | tr -d '[:space:]')/.local/workspace"
  else
    JARFIS_WORKSPACE_DIR="$HOME/repos/jarfis/.local/workspace"
  fi
fi

WORKS_DIR="$JARFIS_WORKSPACE_DIR/works"

if [[ ! -d "$WORKS_DIR" ]]; then
  exit 0
fi

# Resolve JARFIS scripts directory
SCRIPTS_DIR="$HOME/.claude/scripts"
if [[ ! -f "$SCRIPTS_DIR/jarfis_cli.py" ]]; then
  SOURCE_FILE="$HOME/.claude/.jarfis-source"
  if [[ -f "$SOURCE_FILE" ]]; then
    SCRIPTS_DIR="$(cat "$SOURCE_FILE" | tr -d '[:space:]')/scripts"
  fi
fi

# Use jarfis_cli.py to list workflows
if command -v python3 >/dev/null 2>&1 && [[ -f "$SCRIPTS_DIR/jarfis_cli.py" ]]; then
  WORKFLOW_JSON=$(python3 "$SCRIPTS_DIR/jarfis_cli.py" state list-workflows "$JARFIS_WORKSPACE_DIR" 2>/dev/null)
else
  # Fallback: manual scan
  WORKFLOW_JSON=""
fi

# Parse and format output
if [[ -n "$WORKFLOW_JSON" ]]; then
  # Use python3 to format the output
  python3 -c "
import json, sys

try:
    data = json.loads('''$WORKFLOW_JSON''')
except:
    sys.exit(0)

workflows = data.get('workflows', [])
in_progress = [w for w in workflows if not w.get('is_completed', False)]

if not in_progress:
    sys.exit(0)

print('## JARFIS: In-Progress Workflows Detected')
print()

for w in in_progress:
    name = w.get('work_name', 'unknown')
    phase = w.get('current_phase', '?')
    project = w.get('project_name', '')
    checkpoint = ''

    # Try to read last_checkpoint from state file
    sf = w.get('state_file', '')
    if sf:
        try:
            with open(sf) as f:
                state = json.load(f)
            lc = state.get('last_checkpoint', {})
            checkpoint = lc.get('summary', '')
        except:
            pass

    line = f'- **{name}** — Phase {phase}'
    if project:
        line += f' ({project})'
    print(line)
    if checkpoint:
        print(f'  Last checkpoint: {checkpoint}')

print()
print('To continue: /jarfis:continue')
" 2>/dev/null
fi

exit 0
