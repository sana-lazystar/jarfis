"""Tests for jarfis.sync — ~/.claude → repo sync + README update."""

import os

import pytest

from jarfis.sync import (
    _diff_files,
    _read_version_from,
    _replace_section,
    check_version_drift,
    sync_files,
)


class TestDiffFiles:
    def test_different_files(self, tmp_path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("hello")
        dst.write_text("world")
        assert _diff_files(str(src), str(dst)) is True

    def test_identical_files(self, tmp_path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("same content")
        dst.write_text("same content")
        assert _diff_files(str(src), str(dst)) is False

    def test_dst_not_exists(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        assert _diff_files(str(src), str(tmp_path / "nonexistent.txt")) is True


class TestReplaceSection:
    def test_replaces_section(self):
        content = "before\n<!-- START -->\nold content\n<!-- END -->\nafter"
        result = _replace_section(content, "<!-- START -->", "<!-- END -->", "new content")
        assert "new content" in result
        assert "old content" not in result
        assert "before" in result
        assert "after" in result

    def test_no_match_unchanged(self):
        content = "no markers here"
        result = _replace_section(content, "<!-- START -->", "<!-- END -->", "new")
        assert result == content


class TestSyncFiles:
    def test_syncs_changed_command_files(self, jarfis_env):
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        # Create a command file in claude dir
        cmd_file = os.path.join(claude, "commands", "jarfis.md")
        with open(cmd_file, "w") as f:
            f.write("# Updated Help")

        synced, changes = sync_files(repo, claude)
        assert synced >= 1

        # Verify file was copied
        repo_cmd = os.path.join(repo, "commands", "jarfis.md")
        assert os.path.isfile(repo_cmd)
        with open(repo_cmd) as f:
            assert f.read() == "# Updated Help"

    def test_no_sync_when_identical(self, jarfis_env):
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        # Create identical files
        cmd = "commands/jarfis.md"
        for base in [claude, repo]:
            path = os.path.join(base, cmd)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("# Same content")

        synced, changes = sync_files(repo, claude)
        # Should not count identical files
        cmd_changes = [c for c in changes if "jarfis.md" in c]
        assert len(cmd_changes) == 0

    def test_syncs_agent_files(self, jarfis_env):
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        agent_file = os.path.join(claude, "agents", "jarfis", "test-agent.md")
        with open(agent_file, "w") as f:
            f.write("# Test Agent")

        synced, changes = sync_files(repo, claude)
        repo_agent = os.path.join(repo, "agents", "jarfis", "test-agent.md")
        assert os.path.isfile(repo_agent)

    def test_syncs_hook_files(self, jarfis_env):
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        hook_file = os.path.join(claude, "hooks", "jarfis-test.sh")
        with open(hook_file, "w") as f:
            f.write("#!/bin/bash\necho test")

        synced, changes = sync_files(repo, claude)
        repo_hook = os.path.join(repo, "hooks", "jarfis-test.sh")
        assert os.path.isfile(repo_hook)

    def test_ignores_non_jarfis_hooks(self, jarfis_env):
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        other_hook = os.path.join(claude, "hooks", "other-hook.sh")
        with open(other_hook, "w") as f:
            f.write("#!/bin/bash")

        synced, changes = sync_files(repo, claude)
        assert not os.path.isfile(os.path.join(repo, "hooks", "other-hook.sh"))

    def test_syncs_test_files(self, jarfis_env):
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        # Create tests dir and a test file
        tests_dir = os.path.join(claude, "scripts", "tests")
        os.makedirs(tests_dir, exist_ok=True)
        test_file = os.path.join(tests_dir, "test_example.py")
        with open(test_file, "w") as f:
            f.write("def test_foo(): pass")

        synced, changes = sync_files(repo, claude)
        repo_test = os.path.join(repo, "scripts", "tests", "test_example.py")
        assert os.path.isfile(repo_test)
        with open(repo_test) as f:
            assert f.read() == "def test_foo(): pass"

    def test_syncs_conftest(self, jarfis_env):
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        tests_dir = os.path.join(claude, "scripts", "tests")
        os.makedirs(tests_dir, exist_ok=True)
        conftest = os.path.join(tests_dir, "conftest.py")
        with open(conftest, "w") as f:
            f.write("import pytest")

        synced, changes = sync_files(repo, claude)
        repo_conftest = os.path.join(repo, "scripts", "tests", "conftest.py")
        assert os.path.isfile(repo_conftest)


class TestReadVersionFrom:
    def test_version_plain_file(self, tmp_path):
        p = tmp_path / "VERSION"
        p.write_text("4.0.1\n")
        assert _read_version_from(str(p)) == "4.0.1"

    def test_jarfis_version_plain(self, tmp_path):
        p = tmp_path / ".jarfis-version"
        p.write_text("4.0.2\n")
        assert _read_version_from(str(p)) == "4.0.2"

    def test_init_py_extraction(self, tmp_path):
        p = tmp_path / "__init__.py"
        p.write_text('"""Doc."""\n\n__version__ = "4.0.3"\n')
        assert _read_version_from(str(p)) == "4.0.3"

    def test_init_py_no_version_attr(self, tmp_path):
        p = tmp_path / "__init__.py"
        p.write_text("# empty\n")
        assert _read_version_from(str(p)) is None

    def test_missing_file(self, tmp_path):
        assert _read_version_from(str(tmp_path / "nonexistent")) is None

    def test_empty_version_file(self, tmp_path):
        p = tmp_path / "VERSION"
        p.write_text("")
        assert _read_version_from(str(p)) is None


class TestCheckVersionDrift:
    def test_all_aligned_no_drift(self, jarfis_env):
        # jarfis_env default: all four set to 2.2.2
        versions, drift = check_version_drift(
            jarfis_env["repo_dir"], jarfis_env["claude_dir"]
        )
        # jarfis_env sets claude/.jarfis-version + claude __init__ + repo/VERSION to 2.2.2
        # repo __init__ not created by fixture, so 3 values expected
        assert drift is False
        assert set(versions.values()) == {"2.2.2"}

    def test_drift_between_sources(self, jarfis_env):
        # Introduce drift: repo VERSION at 2.2.3 while others stay at 2.2.2
        repo = jarfis_env["repo_dir"]
        version_file = os.path.join(repo, "VERSION")
        with open(version_file, "w") as f:
            f.write("2.2.3\n")

        versions, drift = check_version_drift(repo, jarfis_env["claude_dir"])
        assert drift is True
        assert "2.2.2" in versions.values()
        assert "2.2.3" in versions.values()

    def test_drift_init_py_vs_version_file(self, jarfis_env):
        # Simulate M7-style drift: __init__.py stale while VERSION/.jarfis-version moved ahead
        claude = jarfis_env["claude_dir"]
        init_path = os.path.join(claude, "scripts", "jarfis", "__init__.py")
        with open(init_path, "w") as f:
            f.write('__version__ = "1.0.0"\n')

        versions, drift = check_version_drift(jarfis_env["repo_dir"], claude)
        assert drift is True
        assert versions["claude/scripts/jarfis/__init__.py"] == "1.0.0"

    def test_missing_sources_ignored(self, tmp_path):
        # Empty repo + claude dirs. All sources missing → no drift, empty dict.
        (tmp_path / "repo").mkdir()
        (tmp_path / "claude").mkdir()
        versions, drift = check_version_drift(
            str(tmp_path / "repo"), str(tmp_path / "claude")
        )
        assert drift is False
        assert versions == {}

    def test_single_source_no_drift(self, tmp_path):
        # Only one source present → never drift.
        claude = tmp_path / "claude"
        repo = tmp_path / "repo"
        claude.mkdir()
        repo.mkdir()
        (claude / ".jarfis-version").write_text("4.0.1\n")
        versions, drift = check_version_drift(str(repo), str(claude))
        assert drift is False
        assert versions == {"claude/.jarfis-version": "4.0.1"}
