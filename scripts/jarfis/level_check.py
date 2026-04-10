"""AI-native developer maturity data collection.

Collects data from local Claude Code environment for jarfis:level-check.
No external dependencies — only uses stdlib + filesystem scanning.

Usage:
    python3 -m jarfis.level_check [--all] [--recent-days N]
"""

import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


def _get_claude_dir() -> str:
    """Return ~/.claude path."""
    return os.path.join(os.path.expanduser("~"), ".claude")


def _safe_read_json(path: str) -> dict:
    """Read JSON file, return empty dict on failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _count_files(directory: str, pattern: str = "*.md") -> int:
    """Count files matching pattern recursively."""
    return len(glob.glob(os.path.join(directory, "**", pattern), recursive=True))


def _count_lines(filepath: str) -> int:
    """Count lines in a file."""
    try:
        with open(filepath) as f:
            return sum(1 for _ in f)
    except (FileNotFoundError, PermissionError):
        return 0


# ── Filesystem scanning (no jsonl parsing) ────────────────


def scan_filesystem(claude_dir: str) -> dict:
    """Scan ~/.claude/ filesystem for AI-native maturity indicators."""

    # --- Agents ---
    agents_dir = os.path.join(claude_dir, "agents")
    agent_files = glob.glob(os.path.join(agents_dir, "**", "*.md"), recursive=True)

    personas_count = 0
    dialectic_count = 0
    for af in agent_files:
        rel = os.path.relpath(af, agents_dir)
        if "personas" in rel:
            personas_count += 1
        if "advocate" in os.path.basename(af) or "critic" in os.path.basename(af):
            dialectic_count += 1

    custom_agents = len([f for f in agent_files if "personas" not in os.path.relpath(f, agents_dir)])

    # --- Commands/Skills ---
    commands_dir = os.path.join(claude_dir, "commands")
    command_files = glob.glob(os.path.join(commands_dir, "**", "*.md"), recursive=True)
    skills_total = len(command_files)

    # --- Hooks ---
    settings = _safe_read_json(os.path.join(claude_dir, "settings.json"))
    hooks_data = settings.get("hooks", {})
    hook_names = []
    for event, hook_list in hooks_data.items():
        for h in hook_list:
            desc = h.get("description", h.get("command", "unknown"))
            hook_names.append(desc)
    hooks_total = len(hook_names)
    hooks_events = len(hooks_data)

    # --- Memory ---
    memory_files = glob.glob(
        os.path.join(claude_dir, "projects", "*", "memory", "*.md"), recursive=False
    )
    # Also check nested project paths
    memory_files += glob.glob(
        os.path.join(claude_dir, "projects", "*", "*", "memory", "*.md"), recursive=False
    )
    memory_types = Counter()
    for mf in memory_files:
        try:
            with open(mf) as f:
                content = f.read(500)  # Only read frontmatter
            if "---" in content:
                match = re.search(r"type:\s*(\w+)", content)
                if match:
                    memory_types[match.group(1)] += 1
        except (FileNotFoundError, PermissionError):
            pass

    # --- CLAUDE.md files ---
    home = os.path.dirname(claude_dir)
    claude_md_files = []
    total_lines = 0
    # Search home directory (limited depth to avoid slowness)
    for depth_pattern in [
        os.path.join(home, "CLAUDE.md"),
        os.path.join(home, "*", "CLAUDE.md"),
        os.path.join(home, "*", "*", "CLAUDE.md"),
        os.path.join(home, "*", "*", "*", "CLAUDE.md"),
        os.path.join(home, "*", "*", "*", "*", "CLAUDE.md"),
    ]:
        for f in glob.glob(depth_pattern):
            if "node_modules" not in f and ".git" not in f:
                lines = _count_lines(f)
                total_lines += lines
                claude_md_files.append(f)

    # --- Orchestration detection ---
    jarfis_detected = os.path.isfile(os.path.join(commands_dir, "jarfis", "work.md"))
    omc_detected = (
        os.path.isdir(os.path.join(claude_dir, "plugins", "oh-my-claudecode"))
        or any("omc" in os.path.basename(f).lower() for f in command_files)
    )
    superclaude_detected = os.path.isdir(os.path.join(commands_dir, "sc"))

    # Detect custom orchestration (work*.md or implement*.md in commands/)
    custom_orch = []
    for cf in command_files:
        basename = os.path.basename(cf).lower()
        if basename.startswith("work") and "jarfis" not in cf:
            custom_orch.append(basename)
        elif "implement" in basename and "jarfis" not in cf and "sys-implement" not in basename:
            custom_orch.append(basename)

    # --- Domains ---
    domain_yamls = glob.glob(
        os.path.join(commands_dir, "**", "domains", "*.yaml"), recursive=True
    )
    domain_skills = glob.glob(
        os.path.join(commands_dir, "**", "domains", "**", "skills", "*.md"), recursive=True
    )

    # --- Wiki ---
    personal_dir_file = os.path.join(claude_dir, ".jarfis-personal-dir")
    wiki_exists = False
    if os.path.isfile(personal_dir_file):
        try:
            personal_dir = open(personal_dir_file).read().strip()
            wiki_dirs = glob.glob(os.path.join(personal_dir, "orgs", "*", "wiki"))
            wiki_exists = len(wiki_dirs) > 0
        except (FileNotFoundError, PermissionError):
            pass

    # --- Tests ---
    tests_dir = os.path.join(claude_dir, "scripts", "tests")
    test_count = 0
    for tf in glob.glob(os.path.join(tests_dir, "test_*.py")):
        try:
            with open(tf) as f:
                content = f.read()
            test_count += len(re.findall(r"def test_", content))
        except (FileNotFoundError, PermissionError):
            pass

    # --- Plugins ---
    plugins_dir = os.path.join(claude_dir, "plugins")
    plugin_count = 0
    if os.path.isdir(plugins_dir):
        plugin_count = len([
            d for d in os.listdir(plugins_dir)
            if os.path.isdir(os.path.join(plugins_dir, d))
        ])

    # --- Permissions ---
    perm_mode = settings.get("permissions", {}).get("mode", "default")

    return {
        "agents": {
            "custom": custom_agents,
            "personas": personas_count,
            "dialectic": dialectic_count,
        },
        "skills": {"total": skills_total},
        "hooks": {
            "total": hooks_total,
            "events": hooks_events,
            "names": hook_names,
        },
        "memory": {
            "total": len(memory_files),
            "types": dict(memory_types),
        },
        "claude_md": {
            "total_lines": total_lines,
            "files": len(claude_md_files),
        },
        "orchestration": {
            "jarfis": jarfis_detected,
            "omc": omc_detected,
            "superclaude": superclaude_detected,
            "custom": custom_orch,
        },
        "domains": {
            "packs": len(domain_yamls),
            "skills": len(domain_skills),
        },
        "wiki": wiki_exists,
        "tests": test_count,
        "plugins": plugin_count,
        "permissions": {"mode": perm_mode},
    }


# ── JSONL session parsing ─────────────────────────────────


def parse_jsonl_sessions(claude_dir: str, recent_days: int = 30) -> dict:
    """Parse ~/.claude/projects/**/*.jsonl for usage statistics.

    Args:
        claude_dir: Path to ~/.claude
        recent_days: Only parse files modified within N days. None = all files.
    """
    projects_dir = os.path.join(claude_dir, "projects")
    if not os.path.isdir(projects_dir):
        return _empty_session_data()

    # Find all jsonl files
    jsonl_files = glob.glob(
        os.path.join(projects_dir, "**", "*.jsonl"), recursive=True
    )

    # Filter by recency
    if recent_days is not None:
        cutoff = time.time() - (recent_days * 86400)
        jsonl_files = [f for f in jsonl_files if os.path.getmtime(f) > cutoff]

    # Skip subagent files (they're sub-sessions)
    jsonl_files = [f for f in jsonl_files if "subagents" not in f]

    tools = Counter()
    agent_types = Counter()
    agent_delegations = 0
    skill_usage = Counter()
    mcp_servers = Counter()
    models = Counter()
    total_prompts = 0
    sessions = 0

    for jf in jsonl_files:
        try:
            with open(jf) as f:
                session_prompts = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # graceful degradation

                    rtype = record.get("type", "")

                    # Summary record — session metadata
                    if rtype == "summary":
                        sessions += 1
                        model = record.get("model", "unknown")
                        # Normalize model name
                        if "opus" in model.lower():
                            models["Opus"] += 1
                        elif "sonnet" in model.lower():
                            models["Sonnet"] += 1
                        elif "haiku" in model.lower():
                            models["Haiku"] += 1
                        else:
                            models[model] += 1
                        session_prompts = record.get("numTurns", 0)
                        total_prompts += session_prompts
                        continue

                    # Assistant messages — tool usage
                    if rtype == "assistant":
                        msg = record.get("message", {})
                        content = msg.get("content", [])
                        if not isinstance(content, list):
                            continue
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if block.get("type") != "tool_use":
                                continue
                            tool_name = block.get("name", "")
                            inp = block.get("input", {})

                            # Agent delegation
                            if tool_name == "Agent":
                                agent_delegations += 1
                                st = inp.get("subagent_type", "general-purpose")
                                agent_types[st] += 1
                                tools["Agent"] += 1
                                continue

                            # Skill invocation
                            if tool_name == "Skill":
                                skill_name = inp.get("skill", "unknown")
                                skill_usage[skill_name] += 1
                                continue

                            # MCP tool
                            if tool_name.startswith("mcp__"):
                                parts = tool_name.split("__")
                                if len(parts) >= 2:
                                    server = parts[1]
                                    # Normalize server names
                                    server = server.replace("-", "_").split("_")[0]
                                    mcp_servers[server] += 1
                                continue

                            # Standard tools
                            tools[tool_name] += 1

        except (FileNotFoundError, PermissionError):
            continue

    avg_prompts = round(total_prompts / sessions, 1) if sessions > 0 else 0

    return {
        "sessions": sessions,
        "avg_prompts": avg_prompts,
        "tools": dict(tools),
        "agents": {
            "delegations": agent_delegations,
            "types": [
                {"name": name, "count": count}
                for name, count in agent_types.most_common()
            ],
        },
        "skills": {
            "usage": [
                {"name": name, "count": count}
                for name, count in skill_usage.most_common()
            ],
        },
        "mcp": {
            "servers": [
                {"name": name, "count": count}
                for name, count in mcp_servers.most_common()
            ],
        },
        "models": [
            {"name": name, "pct": round(count / max(sessions, 1) * 100)}
            for name, count in models.most_common()
        ],
    }


def _empty_session_data() -> dict:
    return {
        "sessions": 0, "avg_prompts": 0, "tools": {},
        "agents": {"delegations": 0, "types": []},
        "skills": {"usage": []}, "mcp": {"servers": []}, "models": [],
    }


# ── Main entry point ──────────────────────────────────────


def collect_all(claude_dir: str = None, recent_days: int = 30) -> dict:
    """Collect all AI-native maturity data.

    Args:
        claude_dir: Override ~/.claude path (for testing)
        recent_days: Parse jsonl from last N days. None = all.
    """
    if claude_dir is None:
        claude_dir = _get_claude_dir()

    fs = scan_filesystem(claude_dir)
    sessions = parse_jsonl_sessions(claude_dir, recent_days)

    return {
        # Session data
        "sessions": sessions["sessions"],
        "avg_prompts": sessions["avg_prompts"],
        "tools": sessions["tools"],
        "models": sessions["models"],
        # Merged agents (filesystem + session)
        "agents": {
            **fs["agents"],
            "delegations": sessions["agents"]["delegations"],
            "types": sessions["agents"]["types"],
        },
        # Merged skills (filesystem + session)
        "skills": {
            "total": fs["skills"]["total"],
            "usage": sessions["skills"]["usage"],
        },
        # MCP
        "mcp": {
            "total": len(sessions["mcp"]["servers"]),
            "servers": sessions["mcp"]["servers"],
        },
        # Filesystem only
        "hooks": fs["hooks"],
        "memory": fs["memory"],
        "claude_md": fs["claude_md"],
        "permissions": fs["permissions"],
        "orchestration": fs["orchestration"],
        "domains": fs["domains"],
        "wiki": fs["wiki"],
        "tests": fs["tests"],
        "plugins": fs["plugins"],
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="AI-native maturity data collection")
    parser.add_argument("--all", action="store_true", help="Parse all sessions (no time limit)")
    parser.add_argument("--recent-days", type=int, default=30, help="Parse sessions from last N days")
    args = parser.parse_args()

    recent = None if args.all else args.recent_days
    result = collect_all(recent_days=recent)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
