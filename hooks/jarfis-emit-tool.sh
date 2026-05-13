#!/bin/bash
# JARFIS PostToolUse — auto-emit `tool` events to events.jsonl (event-stream-v1, D2/D10).
#
# Gate: $JARFIS_WORKFLOW env must be set (= sub-Claude running under JARFIS
#       foreman/tmux launch). Main Claude session leaves this empty so the
#       hook is a no-op — main session emits via skill markdown (D10).
# Kill switch: JARFIS_EMIT_HOOK=0
# PostToolUse contract: never block; always exit 0 even on internal errors.

if [[ "${JARFIS_EMIT_HOOK:-1}" == "0" ]]; then
  exit 0
fi
if [[ -z "${JARFIS_WORKFLOW:-}" ]]; then
  exit 0
fi

INPUT=$(cat)

# Extract tool_name + a short summary string. python3 required (already a
# dependency of jarfis_cli.py). Failures are silent.
SUMMARY=$(printf '%s' "$INPUT" | python3 -c "
import json, sys, os

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = d.get('tool_name', '') or ''
ti = d.get('tool_input', {}) or {}

if not tool:
    sys.exit(0)

if tool in ('Edit', 'Write', 'MultiEdit'):
    fp = ti.get('file_path', '') or ''
    name = os.path.basename(fp) if fp else '?'
    summary = f'{tool} {name}'
elif tool == 'Bash':
    cmd = (ti.get('command', '') or '').splitlines()[0] if ti.get('command') else ''
    cmd = cmd[:55].rstrip()
    summary = f'Bash: {cmd}' if cmd else 'Bash'
elif tool in ('Read', 'Grep', 'Glob', 'LS'):
    fp = ti.get('file_path') or ti.get('path') or ti.get('pattern') or ''
    name = os.path.basename(fp) if fp and '/' in fp else fp
    summary = f'{tool} {name}'.strip()
elif tool == 'Task':
    sub = ti.get('subagent_type', '') or ''
    summary = f'agent.done {sub}' if sub else 'agent.done'
else:
    sys.exit(0)

# Strip trailing period (emit() rejects)
summary = summary.rstrip('. ')
# Hard cap at 80 chars (emit() rejects above)
print(summary[:80])
" 2>/dev/null)

if [[ -z "$SUMMARY" ]]; then
  exit 0
fi

# Determine type: Read/Grep/Glob/LS = debug noise; everything else = info tool.
TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
case "$TOOL_NAME" in
  Read|Grep|Glob|LS)
    LEVEL_FLAG="--level=debug"
    ;;
  Task)
    LEVEL_FLAG=""
    EVENT_TYPE="agent.done"
    ;;
  *)
    LEVEL_FLAG=""
    ;;
esac
EVENT_TYPE="${EVENT_TYPE:-tool}"

JARFIS_CLI="$HOME/.claude/scripts/jarfis_cli.py"
if [[ ! -f "$JARFIS_CLI" ]]; then
  exit 0
fi

python3 "$JARFIS_CLI" emit \
  "--type=${EVENT_TYPE}" \
  "--summary=${SUMMARY}" \
  ${LEVEL_FLAG} >/dev/null 2>&1

exit 0
