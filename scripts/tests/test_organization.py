"""Tests for jarfis.organization — Org-level project management."""

import json
import os

import pytest

from jarfis.organization import EXCLUDE_DIRS, _scan_projects, cmd_init, cmd_info, cmd_scan, main


class TestScanProjects:
    def test_finds_project_with_profile(self, tmp_path):
        proj = tmp_path / "project1"
        jarfis_dir = proj / ".jarfis"
        jarfis_dir.mkdir(parents=True)
        (jarfis_dir / "project-profile.md").write_text(
            "# Project Profile: MyApp\n\n> Type: frontend\n"
        )
        results = _scan_projects(str(tmp_path))
        assert len(results) == 1
        assert results[0]["name"] == "MyApp"
        assert results[0]["type"] == "frontend"

    def test_no_projects(self, tmp_path):
        results = _scan_projects(str(tmp_path))
        assert results == []

    def test_excludes_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "some-pkg" / ".jarfis"
        nm.mkdir(parents=True)
        (nm / "project-profile.md").write_text("# Should not find")
        results = _scan_projects(str(tmp_path))
        assert results == []

    def test_multiple_projects(self, tmp_path):
        for name in ["proj-a", "proj-b", "proj-c"]:
            jarfis = tmp_path / name / ".jarfis"
            jarfis.mkdir(parents=True)
            (jarfis / "project-profile.md").write_text(f"# Project Profile: {name}")
        results = _scan_projects(str(tmp_path))
        assert len(results) == 3


class TestCmdInit:
    def test_scan_only_without_confirm(self, tmp_path, capsys):
        proj = tmp_path / "project1" / ".jarfis"
        proj.mkdir(parents=True)
        (proj / "project-profile.md").write_text("# Project Profile: P1")
        cmd_init([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["action"] == "scan"
        assert output["project_count"] == 1
        # No files should be created
        assert not os.path.isfile(os.path.join(str(tmp_path), ".jarfis", "org-profile.md"))

    def test_creates_org_files_with_confirm(self, tmp_path, capsys):
        proj = tmp_path / "project1" / ".jarfis"
        proj.mkdir(parents=True)
        (proj / "project-profile.md").write_text(
            "# Project Profile: P1\n\n> Type: backend\n> Last-Commit: abc123\n"
        )
        cmd_init([str(tmp_path), "--confirm", "--name", "TestOrg"])
        output = json.loads(capsys.readouterr().out)
        assert output["action"] == "init"
        assert output["org_name"] == "TestOrg"

        # Verify created files
        assert os.path.isfile(os.path.join(str(tmp_path), ".jarfis", "org-profile.md"))
        assert os.path.isfile(os.path.join(str(tmp_path), ".jarfis", "wiki", "INDEX.md"))
        for section in ["PO", "DESIGN", "TA", "QA"]:
            assert os.path.isfile(
                os.path.join(str(tmp_path), ".jarfis", "wiki", section, "_index.md")
            )

    def test_error_on_missing_dir(self):
        with pytest.raises(SystemExit):
            cmd_init(["/nonexistent/dir"])


class TestCmdScan:
    def test_scans_projects(self, tmp_path, capsys):
        for name in ["a", "b"]:
            jarfis = tmp_path / name / ".jarfis"
            jarfis.mkdir(parents=True)
            (jarfis / "project-profile.md").write_text(f"# Project Profile: {name}")
        cmd_scan([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["project_count"] == 2


class TestCmdInfo:
    def test_unregistered_org(self, tmp_path, capsys):
        cmd_info([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["registered"] is False

    def test_registered_org(self, tmp_path, capsys):
        jarfis = tmp_path / ".jarfis"
        jarfis.mkdir()
        (jarfis / "org-profile.md").write_text("---\norg: TestOrg\n---\n# Org")
        wiki = jarfis / "wiki"
        wiki.mkdir()
        (wiki / "INDEX.md").write_text("# Wiki")
        cmd_info([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["registered"] is True
        assert output["org_name"] == "TestOrg"
        assert output["has_wiki"] is True


class TestMain:
    def test_unknown_action_exits(self):
        with pytest.raises(SystemExit):
            main(["unknown"])

    def test_no_args_exits(self):
        with pytest.raises(SystemExit):
            main([])


class TestExcludeDirs:
    def test_common_excludes(self):
        assert "node_modules" in EXCLUDE_DIRS
        assert ".git" in EXCLUDE_DIRS
        assert "__pycache__" in EXCLUDE_DIRS
