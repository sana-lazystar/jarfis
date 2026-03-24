"""Tests for jarfis.utils — path resolution, JSON helpers, org detection."""

import json
import os

import pytest

from jarfis.utils import (
    STANDALONE_ORG,
    _resolve_org_name,
    find_org_root,
    get_all_workspaces,
    get_claude_dir,
    get_learnings_path,
    get_personal_dir,
    get_source_path,
    get_org_dir,
    json_error,
    json_output,
    parse_json_value,
    read_file_stripped,
)


class TestGetClaudeDir:
    def test_returns_home_dot_claude(self, jarfis_env):
        result = get_claude_dir()
        assert result == jarfis_env["claude_dir"]
        assert result.endswith(".claude")


class TestGetSourcePath:
    def test_reads_from_jarfis_source_file(self, jarfis_env):
        result = get_source_path()
        assert result == jarfis_env["repo_dir"]

    def test_fallback_when_no_source_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".claude").mkdir()
        result = get_source_path()
        assert result.endswith(os.path.join("repos", "jarfis"))


class TestGetPersonalDir:
    def test_reads_from_personal_dir_file(self, jarfis_env):
        result = get_personal_dir()
        assert result == jarfis_env["personal_dir"]

    def test_fallback_to_source_relative(self, jarfis_env):
        personal_file = os.path.join(jarfis_env["claude_dir"], ".jarfis-personal-dir")
        os.remove(personal_file)
        result = get_personal_dir()
        assert result.endswith(".personal")

    def test_fallback_to_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".claude").mkdir()
        result = get_personal_dir()
        assert result.endswith(".personal")


class TestResolveOrgName:
    def test_returns_standalone_without_project_dir(self):
        assert _resolve_org_name(None) == STANDALONE_ORG

    def test_returns_standalone_when_no_org(self, tmp_path):
        assert _resolve_org_name(str(tmp_path)) == STANDALONE_ORG

    def test_returns_org_name_from_profile(self, tmp_path):
        org_root = tmp_path / "org"
        project = org_root / "project1"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: MyOrg\nroot: /path\n---\n")
        assert _resolve_org_name(str(project)) == "MyOrg"

    def test_fallback_to_dirname_when_no_org_field(self, tmp_path):
        org_root = tmp_path / "FallbackName"
        project = org_root / "proj"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("# No frontmatter\n")
        assert _resolve_org_name(str(project)) == "FallbackName"


class TestGetOrgDir:
    def test_returns_standalone_without_project_dir(self, jarfis_env):
        result = get_org_dir()
        assert result.endswith(os.path.join("orgs", "_standalone"))

    def test_returns_org_workspace_with_project_dir(self, jarfis_env, tmp_path):
        org_root = tmp_path / "org"
        project = org_root / "project1"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: TestOrg\n---\n")
        result = get_org_dir(str(project))
        assert result.endswith(os.path.join("orgs", "TestOrg"))


class TestGetAllWorkspaces:
    def test_lists_all_org_dirs(self, jarfis_env):
        result = get_all_workspaces()
        names = [os.path.basename(p) for p in result]
        assert "TestOrg" in names
        assert "_standalone" in names

    def test_empty_when_no_orgs_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".claude").mkdir()
        result = get_all_workspaces()
        assert result == []


class TestGetLearningsPath:
    def test_standalone_learnings(self, jarfis_env):
        result = get_learnings_path()
        assert result.endswith(os.path.join("_standalone", "learnings.md"))

    def test_org_learnings(self, jarfis_env, tmp_path):
        org_root = tmp_path / "org"
        project = org_root / "proj"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: TestOrg\n---\n")
        result = get_learnings_path(str(project))
        assert result.endswith(os.path.join("TestOrg", "learnings.md"))


class TestJsonOutput:
    def test_prints_json_to_stdout(self, capsys):
        json_output({"key": "value"})
        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"key": "value"}

    def test_handles_unicode(self, capsys):
        json_output({"msg": "한국어 테스트"})
        captured = capsys.readouterr()
        assert "한국어 테스트" in captured.out


class TestJsonError:
    def test_exits_with_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            json_error("test error")
        assert exc_info.value.code == 1

    def test_prints_to_stderr(self, capsys):
        with pytest.raises(SystemExit):
            json_error("test error", detail="extra")
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert err["error"] == "test error"
        assert err["detail"] == "extra"


class TestParseJsonValue:
    def test_parses_number(self):
        assert parse_json_value("42") == 42

    def test_parses_bool(self):
        assert parse_json_value("true") is True
        assert parse_json_value("false") is False

    def test_parses_object(self):
        assert parse_json_value('{"a": 1}') == {"a": 1}

    def test_fallback_to_string(self):
        assert parse_json_value("hello") == "hello"

    def test_null(self):
        assert parse_json_value("null") is None


class TestReadFileStripped:
    def test_reads_and_strips(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("  hello world  \n")
        assert read_file_stripped(str(f)) == "hello world"


class TestFindOrgRoot:
    def test_finds_org_root_in_current_dir(self, tmp_path):
        jarfis_dir = tmp_path / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        assert find_org_root(str(tmp_path)) == str(tmp_path)

    def test_finds_org_root_in_parent(self, tmp_path):
        org_root = tmp_path / "org"
        project = org_root / "project1" / "src"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        assert find_org_root(str(project)) == str(org_root)

    def test_returns_none_when_not_found(self, tmp_path):
        assert find_org_root(str(tmp_path)) is None

    def test_stops_after_5_levels(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "g"
        deep.mkdir(parents=True)
        jarfis_dir = tmp_path / ".jarfis"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        assert find_org_root(str(deep)) is None
