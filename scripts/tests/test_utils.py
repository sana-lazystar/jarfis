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
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: MyOrg\nroot: /path\n---\n")
        assert _resolve_org_name(str(project)) == "MyOrg"

    def test_fallback_to_dirname_when_no_org_field(self, tmp_path):
        org_root = tmp_path / "FallbackName"
        project = org_root / "proj"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("# No frontmatter\n")
        assert _resolve_org_name(str(project)) == "FallbackName"


class TestGetOrgDir:
    def test_returns_standalone_personal_flat_without_project_dir(self, jarfis_env):
        """v4.4: standalone returns {personal_dir}/ flat (no orgs/_standalone/ wrapper)."""
        result = get_org_dir()
        # Result should equal the personal_dir itself (with optional trailing slash).
        assert os.path.normpath(result) == os.path.normpath(jarfis_env["personal_dir"])

    def test_returns_org_root_jarfis_org_with_project_dir(self, jarfis_env, tmp_path):
        """v4.4: registered org returns {org_root}/.jarfis-org/."""
        org_root = tmp_path / "org"
        project = org_root / "project1"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: TestOrg\n---\n")
        result = get_org_dir(str(project))
        # Result must end with .jarfis-org under the org_root.
        assert os.path.normpath(result) == os.path.normpath(str(jarfis_dir))

    def test_standalone_returns_personal_flat_when_no_org_marker(self, jarfis_env, tmp_path):
        """v4.4: a project_dir without org marker also returns flat personal_dir."""
        project = tmp_path / "loose-project"
        project.mkdir()
        result = get_org_dir(str(project))
        assert os.path.normpath(result) == os.path.normpath(jarfis_env["personal_dir"])


class TestGetAllWorkspaces:
    def test_reads_orgs_json_and_yields_jarfis_org_paths(self, jarfis_env):
        """v4.4: get_all_workspaces reads orgs.json and yields {root}/.jarfis-org/ for each."""
        result = get_all_workspaces()
        # TestOrg's .jarfis-org directory must be in result (via orgs.json lookup).
        testorg_jarfis_org = jarfis_env["testorg_dir"]
        assert any(os.path.normpath(p) == os.path.normpath(testorg_jarfis_org) for p in result)

    def test_includes_standalone_personal_dir(self, jarfis_env):
        """v4.4: get_all_workspaces also appends {personal_dir}/ as standalone bucket."""
        result = get_all_workspaces()
        personal = jarfis_env["personal_dir"]
        assert any(os.path.normpath(p) == os.path.normpath(personal) for p in result)

    def test_filters_to_existing_dirs_only(self, jarfis_env):
        """Orgs registered in orgs.json with non-existent .jarfis-org dirs are filtered out."""
        # Add a bogus entry to orgs.json
        orgs_json_path = os.path.join(jarfis_env["orgs_dir"], "orgs.json")
        with open(orgs_json_path) as f:
            data = json.load(f)
        data["orgs"].append({"name": "GhostOrg", "root": "/nonexistent/ghost"})
        with open(orgs_json_path, "w") as f:
            json.dump(data, f)
        result = get_all_workspaces()
        # GhostOrg's .jarfis-org dir does not exist, so it should be filtered out.
        assert not any("ghost" in p.lower() for p in result)

    def test_empty_when_no_orgs_dir_and_no_personal(self, tmp_path, monkeypatch):
        """No personal_dir at all (and no orgs.json) → empty result."""
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".claude").mkdir()
        result = get_all_workspaces()
        assert result == []

    def test_two_registered_orgs_both_yielded(self, jarfis_env, tmp_path):
        """orgs.json with 2 entries → both .jarfis-org dirs are yielded."""
        # Create a second org's physical root with .jarfis-org
        org2_root = tmp_path / "org2-root"
        org2_jarfis_org = org2_root / ".jarfis-org"
        org2_jarfis_org.mkdir(parents=True)
        (org2_jarfis_org / "org-profile.md").write_text("---\norg: Org2\n---\n")

        # Append to orgs.json
        orgs_json_path = os.path.join(jarfis_env["orgs_dir"], "orgs.json")
        with open(orgs_json_path) as f:
            data = json.load(f)
        data["orgs"].append({"name": "Org2", "root": str(org2_root)})
        with open(orgs_json_path, "w") as f:
            json.dump(data, f)

        result = get_all_workspaces()
        normalized = [os.path.normpath(p) for p in result]
        assert os.path.normpath(jarfis_env["testorg_dir"]) in normalized
        assert os.path.normpath(str(org2_jarfis_org)) in normalized


class TestGetLearningsPath:
    def test_standalone_learnings_under_personal_flat(self, jarfis_env):
        """v4.4: standalone learnings.md sits directly under {personal_dir}/."""
        result = get_learnings_path()
        expected = os.path.join(jarfis_env["personal_dir"], "learnings.md")
        assert os.path.normpath(result) == os.path.normpath(expected)

    def test_org_learnings_under_jarfis_org(self, jarfis_env, tmp_path):
        """v4.4: org learnings.md sits under {org_root}/.jarfis-org/learnings.md."""
        org_root = tmp_path / "org"
        project = org_root / "proj"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: TestOrg\n---\n")
        result = get_learnings_path(str(project))
        expected = os.path.join(str(jarfis_dir), "learnings.md")
        assert os.path.normpath(result) == os.path.normpath(expected)


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

    def test_parses_empty_array(self):
        assert parse_json_value("[]") == []

    def test_parses_populated_array(self):
        assert parse_json_value('[{"title":"A","url":"u"}]') == [{"title": "A", "url": "u"}]

    def test_over_quoted_empty_array(self):
        # v4.0.2 OBS-2: shell over-quoting passes '"[]"' where json.loads returns "[]" string.
        # Expect re-parse into an empty list.
        assert parse_json_value('"[]"') == []

    def test_over_quoted_object(self):
        assert parse_json_value('"{\\"k\\": 1}"') == {"k": 1}

    def test_non_json_string_unchanged(self):
        # Plain string starting with bracket char but not valid JSON stays a string.
        assert parse_json_value("[not json") == "[not json"

    def test_non_str_pass_through(self):
        # Defensive: non-str inputs returned as-is (prevents double-encoding downstream).
        assert parse_json_value(123) == 123
        assert parse_json_value(None) is None
        assert parse_json_value([1, 2]) == [1, 2]


class TestReadFileStripped:
    def test_reads_and_strips(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("  hello world  \n")
        assert read_file_stripped(str(f)) == "hello world"


class TestFindOrgRoot:
    def test_finds_org_root_in_current_dir(self, tmp_path):
        jarfis_dir = tmp_path / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        assert find_org_root(str(tmp_path)) == str(tmp_path)

    def test_finds_org_root_in_parent(self, tmp_path):
        org_root = tmp_path / "org"
        project = org_root / "project1" / "src"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        assert find_org_root(str(project)) == str(org_root)

    def test_returns_none_when_not_found(self, tmp_path):
        assert find_org_root(str(tmp_path)) is None

    def test_stops_after_5_levels(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "g"
        deep.mkdir(parents=True)
        jarfis_dir = tmp_path / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        assert find_org_root(str(deep)) is None
