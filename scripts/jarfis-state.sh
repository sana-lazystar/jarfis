#!/bin/bash
# JARFIS State — .jarfis-state.json CRUD
# work/continue 워크플로우에서 상태 파일을 읽기/쓰기/갱신.
# jq 의존성 없이 python3 -c 사용. python3 미설치 시 에러 반환.
#
# Usage:
#   jarfis-state.sh read <state_file> [key]
#   jarfis-state.sh write <state_file> <json_string>
#   jarfis-state.sh set <state_file> <key> <value>
#   jarfis-state.sh set-nested <state_file> <path.to.key> <value>
#   jarfis-state.sh init <state_file> <project_name> <work_name> <docs_dir>
#   jarfis-state.sh list-workflows <workspace_dir> [--completed-only]
#
# Output: JSON (stdout)
# Errors: JSON with "error" key (stderr, exit 1)

set -eo pipefail

# ── Python3 check ──
if ! command -v python3 >/dev/null 2>&1; then
  echo '{"error":"python3 is required but not installed. Install Python 3 to use JARFIS state management."}' >&2
  exit 1
fi

ACTION="${1:-}"
STATE_FILE="${2:-}"

if [ -z "$ACTION" ]; then
  echo '{"error":"Usage: jarfis-state.sh <read|write|set|set-nested|init|list-workflows> <state_file> [args...]"}' >&2
  exit 1
fi

# ── Actions ──
case "$ACTION" in

  read)
    if [ ! -f "$STATE_FILE" ]; then
      echo '{"error":"State file not found","path":"'"$STATE_FILE"'"}' >&2
      exit 1
    fi
    KEY="${3:-}"
    if [ -z "$KEY" ]; then
      cat "$STATE_FILE"
    else
      python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
keys = '$KEY'.split('.')
val = data
for k in keys:
    if isinstance(val, dict) and k in val:
        val = val[k]
    else:
        print(json.dumps(None))
        sys.exit(0)
print(json.dumps(val))
"
    fi
    ;;

  write)
    JSON_STRING="${3:-}"
    if [ -z "$JSON_STRING" ]; then
      echo '{"error":"write requires a JSON string argument"}' >&2
      exit 1
    fi
    # Validate and pretty-print
    echo "$JSON_STRING" | python3 -c "
import json, sys
data = json.load(sys.stdin)
with open('$STATE_FILE', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'path': '$STATE_FILE'}))
"
    ;;

  set)
    KEY="${3:-}"
    VALUE="${4:-}"
    if [ -z "$KEY" ]; then
      echo '{"error":"set requires key and value arguments"}' >&2
      exit 1
    fi
    if [ ! -f "$STATE_FILE" ]; then
      echo '{"error":"State file not found","path":"'"$STATE_FILE"'"}' >&2
      exit 1
    fi
    python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
value = '$VALUE'
# Try to parse as JSON (for numbers, booleans, objects)
try:
    value = json.loads(value)
except (json.JSONDecodeError, ValueError):
    pass
data['$KEY'] = value
with open('$STATE_FILE', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'key': '$KEY'}))
"
    ;;

  set-nested)
    KEY_PATH="${3:-}"
    VALUE="${4:-}"
    if [ -z "$KEY_PATH" ]; then
      echo '{"error":"set-nested requires path.to.key and value arguments"}' >&2
      exit 1
    fi
    if [ ! -f "$STATE_FILE" ]; then
      echo '{"error":"State file not found","path":"'"$STATE_FILE"'"}' >&2
      exit 1
    fi
    python3 -c "
import json
with open('$STATE_FILE') as f:
    data = json.load(f)
keys = '$KEY_PATH'.split('.')
value = '$VALUE'
try:
    value = json.loads(value)
except (json.JSONDecodeError, ValueError):
    pass
obj = data
for k in keys[:-1]:
    if k not in obj or not isinstance(obj[k], dict):
        obj[k] = {}
    obj = obj[k]
obj[keys[-1]] = value
with open('$STATE_FILE', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'key_path': '$KEY_PATH'}))
"
    ;;

  init)
    PROJECT_NAME="${3:-}"
    WORK_NAME="${4:-}"
    DOCS_DIR="${5:-}"
    if [ -z "$PROJECT_NAME" ] || [ -z "$WORK_NAME" ] || [ -z "$DOCS_DIR" ]; then
      echo '{"error":"init requires project_name, work_name, and docs_dir"}' >&2
      exit 1
    fi
    # Ensure directory exists
    mkdir -p "$(dirname "$STATE_FILE")"
    python3 -c "
import json
from datetime import datetime, timezone
state = {
    'project_name': '$PROJECT_NAME',
    'work_name': '$WORK_NAME',
    'docs_dir': '$DOCS_DIR',
    'branch': '$WORK_NAME',
    'branches': {},
    'started_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'current_phase': 0,
    'workspace': {},
    'phases': {
        '0': {'status': 'in_progress'},
        '1': {'status': 'pending'},
        '2': {'status': 'pending'},
        '3': {'status': 'pending'},
        '4': {'status': 'pending'},
        '4.5': {'status': 'pending'},
        '5': {'status': 'pending'},
        '6': {'status': 'pending'}
    },
    'required_roles': {},
    'gate_results': {},
    'last_checkpoint': {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'phase': 0,
        'summary': 'Initialized'
    }
}
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'path': '$STATE_FILE', 'work_name': '$WORK_NAME'}))
"
    ;;

  list-workflows)
    WORKSPACE_DIR="$STATE_FILE"  # 2nd arg is workspace_dir in this case
    COMPLETED_ONLY=false
    if [ "${3:-}" = "--completed-only" ]; then
      COMPLETED_ONLY=true
    fi
    if [ -z "$WORKSPACE_DIR" ]; then
      echo '{"error":"list-workflows requires workspace_dir"}' >&2
      exit 1
    fi
    if [ ! -d "$WORKSPACE_DIR/works" ]; then
      echo '{"workflows":[],"count":0}'
      exit 0
    fi
    # Find all state files
    STATE_FILES=$(find "$WORKSPACE_DIR/works/" -name ".jarfis-state.json" -type f 2>/dev/null || true)
    if [ -z "$STATE_FILES" ]; then
      echo '{"workflows":[],"count":0}'
      exit 0
    fi
    python3 -c "
import json, os, glob
workspace = '$WORKSPACE_DIR'
completed_only = $( $COMPLETED_ONLY && echo 'True' || echo 'False' )
results = []
state_files = '''$STATE_FILES'''.strip().split('\n')
for sf in state_files:
    sf = sf.strip()
    if not sf or not os.path.isfile(sf):
        continue
    try:
        with open(sf) as f:
            data = json.load(f)
        cp = data.get('current_phase', '')
        phases = data.get('phases', {})
        is_done = str(cp) == 'done' or phases.get('6', {}).get('status') == 'completed'
        if completed_only and not is_done:
            continue
        results.append({
            'path': os.path.dirname(sf),
            'state_file': sf,
            'project_name': data.get('project_name', ''),
            'work_name': data.get('work_name', ''),
            'current_phase': cp,
            'is_completed': is_done,
            'started_at': data.get('started_at', ''),
            'docs_dir': data.get('docs_dir', '')
        })
    except Exception:
        pass
results.sort(key=lambda x: x.get('started_at', ''), reverse=True)
print(json.dumps({'workflows': results, 'count': len(results)}, ensure_ascii=False))
"
    ;;

  *)
    echo "{\"error\":\"Unknown action: $ACTION. Use read|write|set|set-nested|init|list-workflows.\"}" >&2
    exit 1
    ;;
esac
