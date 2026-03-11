#!/bin/bash
# JARFIS PreToolUse Safety Hook
# Blocks dangerous Bash commands before execution.
# Exit 2 = block, Exit 0 = allow (with optional stderr warnings).
#
# Kill switch: JARFIS_SAFETY_HOOK=0

# Kill switch
if [[ "${JARFIS_SAFETY_HOOK:-1}" == "0" ]]; then
  exit 0
fi

INPUT=$(cat)

# JSON parsing: jq if available, python3 fallback
_json_get() {
  local json="$1" key="$2" default="$3"
  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -r ".$key // \"$default\""
  elif command -v python3 >/dev/null 2>&1; then
    echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$key','$default'))"
  else
    echo "$default"
  fi
}

TOOL_NAME=$(_json_get "$INPUT" "tool_name" "")

# Only check Bash tool
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

# Extract command from tool_input.command
if command -v jq >/dev/null 2>&1; then
  CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
elif command -v python3 >/dev/null 2>&1; then
  CMD=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('command', ''))
")
else
  # No JSON parser available, allow through
  exit 0
fi

# ── BLOCK patterns (exit 2) ────────────────────

# Block: git push --force / -f
if echo "$CMD" | grep -qE 'git\s+push\s+.*(-f|--force)'; then
  echo "JARFIS Safety: git push --force is blocked. Use regular push." >&2
  exit 2
fi

# Block: --no-verify flag (git commit, git push, etc.)
if echo "$CMD" | grep -qE 'git\s+.*--no-verify'; then
  echo "JARFIS Safety: --no-verify is blocked. Fix the hook issue instead." >&2
  exit 2
fi

# Block: direct commit to main/master
if echo "$CMD" | grep -qE 'git\s+commit\b' && ! echo "$CMD" | grep -qE 'git\s+commit.*--amend'; then
  # Check current branch
  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
  if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    echo "JARFIS Safety: Direct commit to $CURRENT_BRANCH is blocked. Create a feature branch first." >&2
    exit 2
  fi
fi

# ── WARN patterns (stderr, exit 0) ─────────────

WARNED=false

# Warn: .env file access
if echo "$CMD" | grep -qE '\.env\b'; then
  echo "JARFIS Warning: .env file detected in command. Ensure no secrets are exposed." >&2
  WARNED=true
fi

# Warn: rm -rf
if echo "$CMD" | grep -qE 'rm\s+.*-[a-zA-Z]*r[a-zA-Z]*f|rm\s+.*-[a-zA-Z]*f[a-zA-Z]*r|rm\s+-rf'; then
  echo "JARFIS Warning: rm -rf detected. Verify target path carefully." >&2
  WARNED=true
fi

# Warn: credential/secret files
if echo "$CMD" | grep -qiE '(credentials?|secrets?|\.pem|\.key|id_rsa|\.p12)\b'; then
  echo "JARFIS Warning: Credential/secret file pattern detected." >&2
  WARNED=true
fi

# Warn: curl piped to bash
if echo "$CMD" | grep -qE 'curl\s.*\|\s*(ba)?sh|wget\s.*\|\s*(ba)?sh'; then
  echo "JARFIS Warning: curl|bash pattern detected. Verify the source URL." >&2
  WARNED=true
fi

exit 0
