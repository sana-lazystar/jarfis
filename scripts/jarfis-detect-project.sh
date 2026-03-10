#!/bin/bash
# JARFIS Detect Project — 프레임워크/언어 자동 감지
# project-init/work에서 프로젝트 유형을 자동으로 파악.
#
# Usage:
#   jarfis-detect-project.sh [project_dir]
#
# Output: JSON (stdout)
# {
#   "project_dir": "/path/to/project",
#   "languages": ["typescript", "javascript"],
#   "frameworks": ["next.js"],
#   "package_managers": ["npm"],
#   "project_type": "fullstack",
#   "runtime": "node",
#   "manifests_found": ["package.json", "tsconfig.json"],
#   "confidence": "high",
#   "details": { ... }
# }

set -eo pipefail

PROJECT_DIR="${1:-$(pwd)}"

# ── Detection arrays ──
LANGUAGES=()
FRAMEWORKS=()
PACKAGE_MANAGERS=()
MANIFESTS=()
PROJECT_TYPE=""
RUNTIME=""
CONFIDENCE="high"
DETAILS=""

# ── Helper: add unique ──
add_unique() {
  local arr_name="$1"
  local value="$2"
  eval "local existing=\"\${${arr_name}[*]}\""
  if [[ ! " $existing " =~ " $value " ]]; then
    eval "${arr_name}+=(\"$value\")"
  fi
}

# ── Step 1: Manifest detection ──

# Node.js ecosystem
if [ -f "$PROJECT_DIR/package.json" ]; then
  MANIFESTS+=("package.json")
  add_unique LANGUAGES "javascript"

  # Package manager detection
  if [ -f "$PROJECT_DIR/pnpm-lock.yaml" ]; then
    add_unique PACKAGE_MANAGERS "pnpm"
  elif [ -f "$PROJECT_DIR/yarn.lock" ]; then
    add_unique PACKAGE_MANAGERS "yarn"
  elif [ -f "$PROJECT_DIR/bun.lockb" ] || [ -f "$PROJECT_DIR/bun.lock" ]; then
    add_unique PACKAGE_MANAGERS "bun"
    RUNTIME="bun"
  elif [ -f "$PROJECT_DIR/package-lock.json" ]; then
    add_unique PACKAGE_MANAGERS "npm"
  else
    add_unique PACKAGE_MANAGERS "npm"
  fi

  # TypeScript check
  if [ -f "$PROJECT_DIR/tsconfig.json" ]; then
    add_unique LANGUAGES "typescript"
    MANIFESTS+=("tsconfig.json")
  fi

  # Framework detection from dependencies
  if [ -f "$PROJECT_DIR/package.json" ]; then
    DEPS=$(cat "$PROJECT_DIR/package.json" 2>/dev/null || echo "{}")

    # FE frameworks
    if echo "$DEPS" | grep -q '"next"'; then
      add_unique FRAMEWORKS "next.js"
      # Check for app router vs pages
      if [ -d "$PROJECT_DIR/app" ] || [ -d "$PROJECT_DIR/src/app" ]; then
        DETAILS="$DETAILS\"next_router\":\"app\","
      elif [ -d "$PROJECT_DIR/pages" ] || [ -d "$PROJECT_DIR/src/pages" ]; then
        DETAILS="$DETAILS\"next_router\":\"pages\","
      fi
      # Fullstack if api routes exist
      if [ -d "$PROJECT_DIR/pages/api" ] || [ -d "$PROJECT_DIR/app/api" ] || [ -d "$PROJECT_DIR/src/app/api" ]; then
        PROJECT_TYPE="fullstack"
      else
        PROJECT_TYPE="frontend"
      fi
    elif echo "$DEPS" | grep -q '"nuxt"'; then
      add_unique FRAMEWORKS "nuxt"
      if [ -d "$PROJECT_DIR/server" ]; then
        PROJECT_TYPE="fullstack"
      else
        PROJECT_TYPE="frontend"
      fi
    elif echo "$DEPS" | grep -q '"react"'; then
      add_unique FRAMEWORKS "react"
      PROJECT_TYPE="frontend"
    elif echo "$DEPS" | grep -q '"vue"'; then
      add_unique FRAMEWORKS "vue"
      PROJECT_TYPE="frontend"
    elif echo "$DEPS" | grep -q '"svelte"'; then
      add_unique FRAMEWORKS "svelte"
      PROJECT_TYPE="frontend"
    elif echo "$DEPS" | grep -q '"@angular/core"'; then
      add_unique FRAMEWORKS "angular"
      PROJECT_TYPE="frontend"
    elif echo "$DEPS" | grep -q '"solid-js"'; then
      add_unique FRAMEWORKS "solid"
      PROJECT_TYPE="frontend"
    elif echo "$DEPS" | grep -q '"astro"'; then
      add_unique FRAMEWORKS "astro"
      PROJECT_TYPE="frontend"
    fi

    # Remix / SvelteKit
    if echo "$DEPS" | grep -q '"@remix-run"'; then
      add_unique FRAMEWORKS "remix"
      PROJECT_TYPE="fullstack"
    fi
    if echo "$DEPS" | grep -q '"@sveltejs/kit"'; then
      add_unique FRAMEWORKS "sveltekit"
      PROJECT_TYPE="fullstack"
    fi

    # BE frameworks (Node.js)
    if echo "$DEPS" | grep -q '"express"'; then
      add_unique FRAMEWORKS "express"
      [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
    fi
    if echo "$DEPS" | grep -q '"fastify"'; then
      add_unique FRAMEWORKS "fastify"
      [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
    fi
    if echo "$DEPS" | grep -q '"@nestjs/core"'; then
      add_unique FRAMEWORKS "nestjs"
      [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
    fi
    if echo "$DEPS" | grep -q '"koa"'; then
      add_unique FRAMEWORKS "koa"
      [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
    fi
    if echo "$DEPS" | grep -q '"hono"'; then
      add_unique FRAMEWORKS "hono"
      [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
    fi

    # React Native
    if echo "$DEPS" | grep -q '"react-native"'; then
      add_unique FRAMEWORKS "react-native"
      PROJECT_TYPE="mobile"
    fi

    # Electron
    if echo "$DEPS" | grep -q '"electron"'; then
      add_unique FRAMEWORKS "electron"
      PROJECT_TYPE="desktop"
    fi
  fi

  [ -z "$RUNTIME" ] && RUNTIME="node"
fi

# Java/Kotlin ecosystem
if [ -f "$PROJECT_DIR/pom.xml" ]; then
  MANIFESTS+=("pom.xml")
  add_unique LANGUAGES "java"
  add_unique PACKAGE_MANAGERS "maven"
  PROJECT_TYPE="backend"
  RUNTIME="jvm"
  if grep -q "spring-boot" "$PROJECT_DIR/pom.xml" 2>/dev/null; then
    add_unique FRAMEWORKS "spring-boot"
  fi
fi
if [ -f "$PROJECT_DIR/build.gradle" ] || [ -f "$PROJECT_DIR/build.gradle.kts" ]; then
  MANIFESTS+=("build.gradle")
  add_unique PACKAGE_MANAGERS "gradle"
  RUNTIME="jvm"
  [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
  if [ -f "$PROJECT_DIR/build.gradle.kts" ]; then
    add_unique LANGUAGES "kotlin"
  else
    add_unique LANGUAGES "java"
  fi
  if grep -q "spring" "$PROJECT_DIR/build.gradle" 2>/dev/null || grep -q "spring" "$PROJECT_DIR/build.gradle.kts" 2>/dev/null; then
    add_unique FRAMEWORKS "spring-boot"
  fi
fi

# Python ecosystem
if [ -f "$PROJECT_DIR/requirements.txt" ] || [ -f "$PROJECT_DIR/pyproject.toml" ] || [ -f "$PROJECT_DIR/Pipfile" ]; then
  add_unique LANGUAGES "python"
  RUNTIME="python"
  [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
  if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    MANIFESTS+=("requirements.txt")
    add_unique PACKAGE_MANAGERS "pip"
  fi
  if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    MANIFESTS+=("pyproject.toml")
    if grep -q "poetry" "$PROJECT_DIR/pyproject.toml" 2>/dev/null; then
      add_unique PACKAGE_MANAGERS "poetry"
    elif grep -q "uv" "$PROJECT_DIR/pyproject.toml" 2>/dev/null; then
      add_unique PACKAGE_MANAGERS "uv"
    else
      add_unique PACKAGE_MANAGERS "pip"
    fi
  fi
  if [ -f "$PROJECT_DIR/Pipfile" ]; then
    MANIFESTS+=("Pipfile")
    add_unique PACKAGE_MANAGERS "pipenv"
  fi
  # Python framework detection
  for reqfile in "$PROJECT_DIR/requirements.txt" "$PROJECT_DIR/pyproject.toml"; do
    if [ -f "$reqfile" ]; then
      if grep -qi "django" "$reqfile" 2>/dev/null; then add_unique FRAMEWORKS "django"; fi
      if grep -qi "flask" "$reqfile" 2>/dev/null; then add_unique FRAMEWORKS "flask"; fi
      if grep -qi "fastapi" "$reqfile" 2>/dev/null; then add_unique FRAMEWORKS "fastapi"; fi
    fi
  done
fi

# Go
if [ -f "$PROJECT_DIR/go.mod" ]; then
  MANIFESTS+=("go.mod")
  add_unique LANGUAGES "go"
  add_unique PACKAGE_MANAGERS "go-modules"
  RUNTIME="go"
  [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
  if grep -q "gin-gonic" "$PROJECT_DIR/go.mod" 2>/dev/null; then add_unique FRAMEWORKS "gin"; fi
  if grep -q "labstack/echo" "$PROJECT_DIR/go.mod" 2>/dev/null; then add_unique FRAMEWORKS "echo"; fi
  if grep -q "gofiber" "$PROJECT_DIR/go.mod" 2>/dev/null; then add_unique FRAMEWORKS "fiber"; fi
fi

# Rust
if [ -f "$PROJECT_DIR/Cargo.toml" ]; then
  MANIFESTS+=("Cargo.toml")
  add_unique LANGUAGES "rust"
  add_unique PACKAGE_MANAGERS "cargo"
  RUNTIME="rust"
  [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
fi

# Flutter/Dart
if [ -f "$PROJECT_DIR/pubspec.yaml" ]; then
  MANIFESTS+=("pubspec.yaml")
  add_unique LANGUAGES "dart"
  add_unique PACKAGE_MANAGERS "pub"
  RUNTIME="dart"
  if grep -q "flutter" "$PROJECT_DIR/pubspec.yaml" 2>/dev/null; then
    add_unique FRAMEWORKS "flutter"
    PROJECT_TYPE="mobile"
  fi
fi

# Ruby
if [ -f "$PROJECT_DIR/Gemfile" ]; then
  MANIFESTS+=("Gemfile")
  add_unique LANGUAGES "ruby"
  add_unique PACKAGE_MANAGERS "bundler"
  RUNTIME="ruby"
  [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="backend"
  if grep -q "rails" "$PROJECT_DIR/Gemfile" 2>/dev/null; then add_unique FRAMEWORKS "rails"; fi
fi

# ── Confidence assessment ──
if [ ${#MANIFESTS[@]} -eq 0 ]; then
  CONFIDENCE="low"
  PROJECT_TYPE="unknown"
elif [ ${#FRAMEWORKS[@]} -eq 0 ]; then
  CONFIDENCE="medium"
fi

# ── Build JSON arrays ──
json_array() {
  local arr=("$@")
  local result="["
  local first=true
  for item in "${arr[@]}"; do
    if $first; then first=false; else result="$result,"; fi
    result="$result\"$item\""
  done
  echo "$result]"
}

LANG_JSON=$(json_array "${LANGUAGES[@]}")
FW_JSON=$(json_array "${FRAMEWORKS[@]}")
PM_JSON=$(json_array "${PACKAGE_MANAGERS[@]}")
MF_JSON=$(json_array "${MANIFESTS[@]}")

# ── Output ──
# Clean up DETAILS trailing comma
DETAILS="${DETAILS%,}"
DETAILS_JSON=""
if [ -n "$DETAILS" ]; then
  DETAILS_JSON=",\"details\":{$DETAILS}"
fi

cat <<EOF
{"project_dir":"$PROJECT_DIR","languages":$LANG_JSON,"frameworks":$FW_JSON,"package_managers":$PM_JSON,"project_type":"${PROJECT_TYPE:-unknown}","runtime":"${RUNTIME:-unknown}","manifests_found":$MF_JSON,"confidence":"$CONFIDENCE"$DETAILS_JSON}
EOF
