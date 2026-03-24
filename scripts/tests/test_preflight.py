"""Tests for jarfis.preflight — pre-work validation checks."""

import json
import os

import pytest

from jarfis.preflight import main


class TestPreflight:
    def test_basic_output_structure(self, jarfis_env, tmp_path, capsys):
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert "project_dir" in output
        assert "has_profile" in output
        assert "has_learnings" in output
        assert "has_context" in output
        assert "git_available" in output
        assert "warnings" in output

    def test_no_profile_warns(self, jarfis_env, tmp_path, capsys):
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_profile"] is False
        assert any("프로필" in w for w in output["warnings"])

    def test_profile_found(self, jarfis_env, tmp_path, capsys):
        jarfis_dir = tmp_path / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "project-profile.md").write_text("# Profile")
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_profile"] is True

    def test_context_found(self, jarfis_env, tmp_path, capsys):
        jarfis_dir = tmp_path / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "project-context.md").write_text("# Context")
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_context"] is True

    def test_learnings_found(self, jarfis_env, capsys, tmp_path):
        repo = jarfis_env["repo_dir"]
        learnings_dir = os.path.join(repo, ".local")
        os.makedirs(learnings_dir, exist_ok=True)
        with open(os.path.join(learnings_dir, "jarfis-learnings.md"), "w") as f:
            f.write("# Learnings")
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_learnings"] is True

    def test_non_git_dir_warns(self, jarfis_env, tmp_path, capsys):
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["git_available"] is False

    def test_org_detection(self, jarfis_env, tmp_path, capsys):
        org_root = tmp_path / "org"
        project = org_root / "project1"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        wiki_dir = jarfis_dir / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "INDEX.md").write_text("# Wiki")
        main([str(project)])
        output = json.loads(capsys.readouterr().out)
        assert output["org_root"] == str(org_root)
        assert output["has_wiki"] is True

    def test_workspace_dir_override(self, jarfis_env, tmp_path, capsys):
        custom_ws = str(tmp_path / "custom-workspace")
        os.makedirs(custom_ws)
        main(["--workspace-dir", custom_ws, str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["workspace_dir"] == custom_ws
