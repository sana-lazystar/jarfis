"""Shared fixtures for JARFIS test suite.

Provides isolated filesystem environments so tests never touch real JARFIS data.
"""

import json
import os
import sys

import pytest

# Ensure jarfis package is importable
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture
def jarfis_env(tmp_path, monkeypatch):
    """Create an isolated JARFIS environment rooted in tmp_path.

    Structure:
        tmp_path/
        ├── claude/               (~/.claude equivalent)
        │   ├── .jarfis-source    (points to repo/)
        │   ├── .jarfis-version
        │   ├── .jarfis-works-dir (points to repo/.local/workspace)
        │   ├── commands/jarfis/jarfis-index.md
        │   └── scripts/jarfis/__init__.py
        └── repo/                 (JARFIS repo equivalent)
            ├── VERSION
            ├── CHANGELOG.md
            └── .local/workspace/
                ├── works/
                └── meetings/

    Returns a dict with key paths.
    """
    claude_dir = tmp_path / "claude"
    repo_dir = tmp_path / "repo"
    workspace_dir = repo_dir / ".local" / "workspace"
    works_dir = workspace_dir / "works"
    meetings_dir = workspace_dir / "meetings"

    # Create directories
    for d in [
        claude_dir / "commands" / "jarfis",
        claude_dir / "scripts" / "jarfis",
        claude_dir / "agents" / "jarfis",
        claude_dir / "hooks",
        repo_dir / "scripts" / "jarfis",
        repo_dir / "commands" / "jarfis",
        repo_dir / "agents" / "jarfis",
        repo_dir / "hooks",
        works_dir,
        meetings_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Write config files
    (claude_dir / ".jarfis-source").write_text(str(repo_dir))
    (claude_dir / ".jarfis-version").write_text("2.2.0\n")
    (claude_dir / ".jarfis-works-dir").write_text(str(workspace_dir))
    (repo_dir / "VERSION").write_text("2.2.0\n")
    (repo_dir / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [2.2.0] - 2026-03-24\n\n- Test entry\n"
    )
    (claude_dir / "scripts" / "jarfis" / "__init__.py").write_text(
        '__version__ = "2.2.0"\n'
    )
    (claude_dir / "commands" / "jarfis" / "jarfis-index.md").write_text(
        "> Last updated: 2026-03-24 | Version: 2.2.0\n"
    )

    # Monkeypatch HOME so get_claude_dir returns our tmp claude dir
    monkeypatch.setenv("HOME", str(tmp_path))
    # Rename claude → .claude (HOME/.claude)
    real_claude = tmp_path / ".claude"
    claude_dir.rename(real_claude)
    claude_dir = real_claude

    # Update .jarfis-source to point to repo
    (claude_dir / ".jarfis-source").write_text(str(repo_dir))
    (claude_dir / ".jarfis-works-dir").write_text(str(workspace_dir))

    return {
        "claude_dir": str(claude_dir),
        "repo_dir": str(repo_dir),
        "workspace_dir": str(workspace_dir),
        "works_dir": str(works_dir),
        "meetings_dir": str(meetings_dir),
        "tmp_path": str(tmp_path),
    }


@pytest.fixture
def state_file(tmp_path):
    """Create a valid .jarfis-state.json file and return its path."""
    sf = tmp_path / ".jarfis-state.json"
    state = {
        "project_name": "test-project",
        "work_name": "20260324-feature-test",
        "work_input": "",
        "docs_dir": str(tmp_path / "docs"),
        "branch": "20260324-feature-test",
        "branches": {},
        "source_meeting": None,
        "started_at": "2026-03-24T00:00:00Z",
        "status": "in-progress",
        "key_decisions": [],
        "current_phase": 0,
        "workspace": {},
        "phases": {
            "0": {"status": "in_progress"},
            "1": {"status": "pending"},
            "2": {"status": "pending"},
            "3": {"status": "pending"},
            "4": {"status": "pending"},
            "4.5": {"status": "pending"},
            "5": {"status": "pending"},
            "6": {"status": "pending"},
        },
        "required_roles": {},
        "gate_results": {},
        "last_checkpoint": {
            "timestamp": "2026-03-24T00:00:00Z",
            "phase": 0,
            "summary": "Initialized",
        },
    }
    (tmp_path / "docs").mkdir(exist_ok=True)
    sf.write_text(json.dumps(state, indent=2))
    return str(sf)


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with package.json."""
    proj = tmp_path / "my-project"
    proj.mkdir()
    pkg = {
        "name": "my-project",
        "dependencies": {"react": "^18.0.0", "next": "^14.0.0"},
        "devDependencies": {"typescript": "^5.0.0"},
    }
    (proj / "package.json").write_text(json.dumps(pkg))
    (proj / "tsconfig.json").write_text('{"compilerOptions": {}}')
    (proj / "pnpm-lock.yaml").write_text("")
    return str(proj)
