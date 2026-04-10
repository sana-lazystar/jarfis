"""Tests for level_check.py — AI-native maturity data collection."""

import json
import os
import time

import pytest

from jarfis.level_check import collect_all, scan_filesystem, parse_jsonl_sessions


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture
def level_check_env(jarfis_env):
    """Extend jarfis_env with level-check specific structures."""
    claude_dir = jarfis_env["claude_dir"]

    # Create projects dir with sample jsonl
    projects_dir = os.path.join(claude_dir, "projects", "test-project")
    os.makedirs(projects_dir, exist_ok=True)

    # Create a sample session jsonl
    session_lines = [
        json.dumps({
            "type": "summary", "version": "2.1.49",
            "sessionId": "sess-001",
            "model": "claude-opus-4-6",
            "costUsd": 0.5,
            "duration": 3600,
            "numTurns": 10,
        }),
        json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Bash"},
                    {"type": "tool_use", "name": "Read"},
                    {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "tech-lead"}},
                ]
            }
        }),
        json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "jarfis:work"}},
                    {"type": "tool_use", "name": "Edit"},
                    {"type": "tool_use", "name": "Bash"},
                ]
            }
        }),
        json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "mcp__playwright__navigate", "input": {}},
                    {"type": "tool_use", "name": "mcp__slack__send_message", "input": {}},
                ]
            }
        }),
    ]
    session_file = os.path.join(projects_dir, "sess-001.jsonl")
    with open(session_file, "w") as f:
        f.write("\n".join(session_lines))

    # Create agents
    agents_dir = os.path.join(claude_dir, "agents", "jarfis")
    for name in ["tech-lead.md", "senior-fe.md", "qa.md"]:
        with open(os.path.join(agents_dir, name), "w") as f:
            f.write(f"# {name}")

    # Create personas
    personas_dir = os.path.join(agents_dir, "personas")
    os.makedirs(personas_dir, exist_ok=True)
    for name in ["po.md", "architect.md"]:
        with open(os.path.join(personas_dir, name), "w") as f:
            f.write(f"# {name}")

    # Create dialectic agents
    with open(os.path.join(agents_dir, "jarfis-advocate.md"), "w") as f:
        f.write("# advocate")
    with open(os.path.join(agents_dir, "jarfis-critic.md"), "w") as f:
        f.write("# critic")

    # Create commands
    commands_dir = os.path.join(claude_dir, "commands", "jarfis")
    for name in ["work.md", "sys-implement.md", "level-check.md"]:
        with open(os.path.join(commands_dir, name), "w") as f:
            f.write(f"# {name}\nsome content\n")

    # Create sc commands (SuperClaude)
    sc_dir = os.path.join(claude_dir, "commands", "sc")
    os.makedirs(sc_dir, exist_ok=True)
    with open(os.path.join(sc_dir, "analyze.md"), "w") as f:
        f.write("# analyze")

    # Create memory files
    memory_dir = os.path.join(claude_dir, "projects", "test-project", "memory")
    os.makedirs(memory_dir, exist_ok=True)
    for name, mtype in [("fb1.md", "feedback"), ("fb2.md", "feedback"), ("proj1.md", "project")]:
        with open(os.path.join(memory_dir, name), "w") as f:
            f.write(f"---\ntype: {mtype}\n---\n# {name}")

    # Create hooks in settings.json
    settings = {
        "hooks": {
            "PreToolUse": [{"type": "command", "description": "quality-gate"}],
            "PostToolUse": [{"type": "command", "description": "safety"}],
            "SessionStart": [{"type": "command", "description": "init"}],
        },
        "permissions": {"allow": [], "deny": [], "mode": "bypassPermissions"},
    }
    with open(os.path.join(claude_dir, "settings.json"), "w") as f:
        json.dump(settings, f)

    # Create CLAUDE.md files in fake projects
    home = os.path.dirname(claude_dir)
    proj1 = os.path.join(home, "projects", "app1")
    os.makedirs(proj1, exist_ok=True)
    with open(os.path.join(proj1, "CLAUDE.md"), "w") as f:
        f.write("# Rules\n" * 50)  # 50 lines

    # Create domains
    domains_dir = os.path.join(commands_dir, "domains")
    os.makedirs(domains_dir, exist_ok=True)
    with open(os.path.join(domains_dir, "web.yaml"), "w") as f:
        f.write("name: web")

    # Create domain skills
    domain_skills_dir = os.path.join(domains_dir, "web", "skills")
    os.makedirs(domain_skills_dir, exist_ok=True)
    for s in ["react.md", "vue.md"]:
        with open(os.path.join(domain_skills_dir, s), "w") as f:
            f.write(f"# {s}")

    # Create plugins dir (empty)
    os.makedirs(os.path.join(claude_dir, "plugins"), exist_ok=True)

    return jarfis_env


# ── Tests: scan_filesystem ────────────────────────────────


class TestScanFilesystem:
    def test_counts_custom_agents(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        # 3 agents + 2 personas + 2 dialectic = 7 (but personas counted separately)
        assert result["agents"]["custom"] >= 5  # agents in agents/jarfis/

    def test_counts_personas(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["agents"]["personas"] == 2

    def test_detects_dialectic_agents(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["agents"]["dialectic"] == 2

    def test_counts_commands(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["skills"]["total"] >= 4  # jarfis/ + sc/

    def test_counts_hooks(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["hooks"]["total"] == 3
        assert result["hooks"]["events"] == 3

    def test_counts_memory(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["memory"]["total"] >= 3
        assert "feedback" in result["memory"]["types"]

    def test_detects_jarfis(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["orchestration"]["jarfis"] is True

    def test_detects_superclaude(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["orchestration"]["superclaude"] is True

    def test_detects_no_omc(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["orchestration"]["omc"] is False

    def test_counts_domain_packs(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["domains"]["packs"] >= 1

    def test_counts_domain_skills(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["domains"]["skills"] >= 2

    def test_counts_claude_md(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["claude_md"]["total_lines"] >= 50
        assert result["claude_md"]["files"] >= 1

    def test_permission_mode(self, level_check_env):
        result = scan_filesystem(level_check_env["claude_dir"])
        assert result["permissions"]["mode"] == "bypassPermissions"


# ── Tests: parse_jsonl_sessions ───────────────────────────


class TestParseJsonlSessions:
    def test_counts_sessions(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = parse_jsonl_sessions(claude_dir, recent_days=None)
        assert result["sessions"] >= 1

    def test_counts_tools(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = parse_jsonl_sessions(claude_dir, recent_days=None)
        assert result["tools"]["Bash"] == 2
        assert result["tools"]["Read"] == 1
        assert result["tools"]["Edit"] == 1

    def test_counts_agents(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = parse_jsonl_sessions(claude_dir, recent_days=None)
        assert result["agents"]["delegations"] == 1
        assert "tech-lead" in [a["name"] for a in result["agents"]["types"]]

    def test_counts_skills(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = parse_jsonl_sessions(claude_dir, recent_days=None)
        assert any(s["name"] == "jarfis:work" for s in result["skills"]["usage"])

    def test_counts_mcp(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = parse_jsonl_sessions(claude_dir, recent_days=None)
        assert any(m["name"] == "playwright" for m in result["mcp"]["servers"])
        assert any(m["name"] == "slack" for m in result["mcp"]["servers"])

    def test_counts_models(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = parse_jsonl_sessions(claude_dir, recent_days=None)
        assert len(result["models"]) >= 1

    def test_graceful_degradation_on_bad_json(self, level_check_env):
        """Bad JSON lines should be skipped, not crash."""
        claude_dir = level_check_env["claude_dir"]
        projects_dir = os.path.join(claude_dir, "projects", "test-project")
        bad_file = os.path.join(projects_dir, "bad-session.jsonl")
        with open(bad_file, "w") as f:
            f.write("not valid json\n")
            f.write('{"type": "summary", "sessionId": "s2", "model": "opus"}\n')
        result = parse_jsonl_sessions(claude_dir, recent_days=None)
        # Should not crash, should still parse other sessions
        assert result["sessions"] >= 1


# ── Tests: collect_all ────────────────────────────────────


class TestCollectAll:
    def test_returns_valid_json_structure(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = collect_all(claude_dir, recent_days=None)
        required_keys = [
            "sessions", "avg_prompts", "tools", "skills", "mcp",
            "agents", "hooks", "memory", "claude_md", "models",
            "permissions", "orchestration", "domains", "plugins",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_json_serializable(self, level_check_env):
        claude_dir = level_check_env["claude_dir"]
        result = collect_all(claude_dir, recent_days=None)
        # Should not raise
        json.dumps(result)
