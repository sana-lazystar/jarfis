"""Tests for jarfis.sync — ~/.claude → repo sync + README update."""

import os

import pytest

from jarfis.sync import _diff_files, _replace_section, sync_files


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
