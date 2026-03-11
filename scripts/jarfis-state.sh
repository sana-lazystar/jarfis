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
      JARFIS_STATE_FILE="$STATE_FILE" JARFIS_KEY="$KEY" python3 -c "
import json, sys, os
with open(os.environ['JARFIS_STATE_FILE']) as f:
    data = json.load(f)
keys = os.environ['JARFIS_KEY'].split('.')
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
    echo "$JSON_STRING" | JARFIS_STATE_FILE="$STATE_FILE" python3 -c "
import json, sys, os
data = json.load(sys.stdin)
state_file = os.environ['JARFIS_STATE_FILE']
with open(state_file, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'path': state_file}))
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
    JARFIS_STATE_FILE="$STATE_FILE" JARFIS_KEY="$KEY" JARFIS_VALUE="$VALUE" python3 -c "
import json, sys, os
state_file = os.environ['JARFIS_STATE_FILE']
key = os.environ['JARFIS_KEY']
value = os.environ.get('JARFIS_VALUE', '')
with open(state_file) as f:
    data = json.load(f)
# Try to parse as JSON (for numbers, booleans, objects)
try:
    value = json.loads(value)
except (json.JSONDecodeError, ValueError):
    pass
data[key] = value
with open(state_file, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'key': key}))
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
    JARFIS_STATE_FILE="$STATE_FILE" JARFIS_KEY_PATH="$KEY_PATH" JARFIS_VALUE="$VALUE" python3 -c "
import json, os
state_file = os.environ['JARFIS_STATE_FILE']
key_path = os.environ['JARFIS_KEY_PATH']
value = os.environ.get('JARFIS_VALUE', '')
with open(state_file) as f:
    data = json.load(f)
keys = key_path.split('.')
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
with open(state_file, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'key_path': key_path}))
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
    JARFIS_STATE_FILE="$STATE_FILE" JARFIS_PROJECT="$PROJECT_NAME" JARFIS_WORK="$WORK_NAME" JARFIS_DOCS="$DOCS_DIR" python3 -c "
import json, os
from datetime import datetime, timezone
project_name = os.environ['JARFIS_PROJECT']
work_name = os.environ['JARFIS_WORK']
docs_dir = os.environ['JARFIS_DOCS']
state_file = os.environ['JARFIS_STATE_FILE']
state = {
    'project_name': project_name,
    'work_name': work_name,
    'work_input': '',
    'docs_dir': docs_dir,
    'branch': work_name,
    'branches': {},
    'source_meeting': None,
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
with open(state_file, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print(json.dumps({'success': True, 'path': state_file, 'work_name': work_name}))
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
    JARFIS_COMPLETED_ONLY="$COMPLETED_ONLY" JARFIS_STATE_FILES="$STATE_FILES" python3 -c "
import json, os
completed_only = os.environ.get('JARFIS_COMPLETED_ONLY', 'false') == 'true'
results = []
state_files = os.environ.get('JARFIS_STATE_FILES', '').strip().split('\n')
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
