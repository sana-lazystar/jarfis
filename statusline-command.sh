#!/usr/bin/env bash
# Claude Code status line — inspired by Oh My Zsh agnoster theme

input=$(cat)

user=$(whoami)
host=$(hostname -s)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd')
model=$(echo "$input" | jq -r '.model.display_name // "Claude"')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Get short directory (basename only, unless it's home)
home_dir="$HOME"
if [ "$cwd" = "$home_dir" ]; then
  short_dir="~"
else
  short_dir=$(basename "$cwd")
fi

# Git branch (skip optional locks)
git_branch=""
if git -C "$cwd" rev-parse --git-dir --no-optional-locks > /dev/null 2>&1; then
  branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
  if [ -n "$branch" ]; then
    git_branch=" $branch"
  fi
fi

# Context usage indicator
ctx_info=""
if [ -n "$used" ]; then
  used_int=${used%.*}
  ctx_info=" | ctx ${used_int}%"
fi

# Build status line with ANSI colors
printf "\033[1;34m%s@%s\033[0m \033[1;36m%s\033[0m\033[1;33m%s\033[0m \033[0;35m[%s]\033[0m\033[0;90m%s\033[0m" \
  "$user" "$host" "$short_dir" "$git_branch" "$model" "$ctx_info"
