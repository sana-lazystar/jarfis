"""Tests for jarfis.utils — path resolution, JSON helpers, org detection."""

import json
import os

import pytest

from jarfis.utils import (
    find_org_root,
    get_claude_dir,
    get_source_path,
    get_workspace_dir,
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


class TestGetWorkspaceDir:
    def test_reads_from_works_dir_file(self, jarfis_env):
        result = get_workspace_dir()
        assert result == jarfis_env["workspace_dir"]

    def test_fallback_to_source_relative(self, jarfis_env):
        works_file = os.path.join(jarfis_env["claude_dir"], ".jarfis-works-dir")
        os.remove(works_file)
        result = get_workspace_dir()
        assert ".local" in result and "workspace" in result

    def test_fallback_to_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".claude").mkdir()
        result = get_workspace_dir()
        assert result.endswith(os.path.join(".local", "workspace"))


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
        # 7 levels deep — should NOT find org root at tmp_path
        assert find_org_root(str(deep)) is None
