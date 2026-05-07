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
        assert "has_rule" in output
        assert "has_context" in output
        assert "git_available" in output
        assert "warnings" in output

    def test_no_profile_warns(self, jarfis_env, tmp_path, capsys):
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_profile"] is False
        assert any("No project profile" in w for w in output["warnings"])

    def test_profile_found(self, jarfis_env, tmp_path, capsys):
        jarfis_dir = tmp_path / ".jarfis-project"
        jarfis_dir.mkdir()
        (jarfis_dir / "project-profile.md").write_text("# Profile")
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_profile"] is True

    def test_context_found(self, jarfis_env, tmp_path, capsys):
        jarfis_dir = tmp_path / ".jarfis-project"
        jarfis_dir.mkdir()
        (jarfis_dir / "project-context.md").write_text("# Context")
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_context"] is True

    def test_rule_found(self, jarfis_env, capsys, tmp_path):
        jarfis_dir = tmp_path / ".jarfis-project"
        jarfis_dir.mkdir(exist_ok=True)
        (jarfis_dir / "project-rule.md").write_text("")
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_rule"] is True

    def test_rule_not_found(self, jarfis_env, capsys, tmp_path):
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["has_rule"] is False

    def test_non_git_dir_warns(self, jarfis_env, tmp_path, capsys):
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["git_available"] is False

    def test_org_detection(self, jarfis_env, tmp_path, capsys):
        org_root = tmp_path / "org"
        project = org_root / "project1"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("org: test")
        wiki_dir = jarfis_dir / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "INDEX.md").write_text("# Wiki")
        main([str(project)])
        output = json.loads(capsys.readouterr().out)
        assert output["org_root"] == str(org_root)
        assert output["has_wiki"] is True

    def test_org_dir_override(self, jarfis_env, tmp_path, capsys):
        custom_ws = str(tmp_path / "custom-workspace")
        os.makedirs(custom_ws)
        main(["--org-dir", custom_ws, str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["org_dir"] == custom_ws

    def test_org_auto_register(self, jarfis_env, tmp_path, capsys):
        """v4.4: Org detected but not in orgs.json → auto-register (registry only).

        register_org now only updates orgs.json; the per-org workspace dirs
        ({org_root}/.jarfis-org/{works,meetings}) are owned by _create_org_files
        (org-init), not by register_org.
        """
        org_root = tmp_path / "new-org"
        project = org_root / "project1"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: NewAutoOrg\n---\n")
        wiki_dir = jarfis_dir / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "INDEX.md").write_text("# Wiki")

        main([str(project)])
        output = json.loads(capsys.readouterr().out)
        assert output["org_root"] == str(org_root)
        assert output["org_name"] == "NewAutoOrg"
        assert output["org_auto_registered"] is True

        # Verify orgs.json was updated
        from jarfis.organization import read_orgs
        data = read_orgs()
        names = [o["name"] for o in data["orgs"]]
        assert "NewAutoOrg" in names

    def test_org_already_registered_no_duplicate(self, jarfis_env, tmp_path, capsys):
        """Org detected and already in orgs.json → no duplicate."""
        org_root = tmp_path / "existing-org"
        project = org_root / "project1"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: TestOrg\n---\n")

        main([str(project)])
        output = json.loads(capsys.readouterr().out)
        assert output["org_name"] == "TestOrg"
        assert output["org_auto_registered"] is False

    def test_org_auto_adds_project_to_profile(self, jarfis_env, tmp_path, capsys):
        """Org detected, project has profile but not in org-profile.md table → auto-add."""
        org_root = tmp_path / "org"
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir(parents=True)
        (jarfis_dir / "org-profile.md").write_text(
            "---\norg: AutoAddOrg\n---\n\n# Organization Profile\n\n## Projects\n\n"
            "| Name | Path | Type | Profile |\n|------|------|------|---------|"
            "\n| (none) | | | |\n"
        )
        wiki = jarfis_dir / "wiki"
        wiki.mkdir()
        (wiki / "INDEX.md").write_text("# Wiki")
        # Create project with profile
        proj = org_root / "my-project"
        proj_jarfis = proj / ".jarfis-project"
        proj_jarfis.mkdir(parents=True)
        (proj_jarfis / "project-profile.md").write_text("# Project Profile: my-project\n\n> Type: frontend\n")

        main([str(proj)])
        output = json.loads(capsys.readouterr().out)
        assert output["org_project_added"] is True
        # Verify org-profile.md was updated
        profile_content = (jarfis_dir / "org-profile.md").read_text()
        assert "my-project" in profile_content

    def test_no_org_no_registration(self, jarfis_env, tmp_path, capsys):
        """No org detected → no registration attempt."""
        main([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["org_root"] is None
        assert output["org_auto_registered"] is False

    def test_preflight_emits_org_dir_as_org_root_jarfis_org(self, jarfis_env, tmp_path, capsys):
        """v4.4: preflight's org_dir reflects {org_root}/.jarfis-org/ for registered orgs."""
        org_root = tmp_path / "v44-preflight-org"
        project = org_root / "proj"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: V44Pre\n---\n")
        main([str(project)])
        output = json.loads(capsys.readouterr().out)
        # org_dir must equal {org_root}/.jarfis-org
        assert os.path.normpath(output["org_dir"]) == os.path.normpath(str(jarfis_dir))


class TestPreflightDocsDirValidation:
    """Defect D6: --check-docsdir flag validates docsDir position under {org_dir}/works/."""

    def test_check_docsdir_valid_for_org(self, jarfis_env, tmp_path, capsys):
        """docsDir under {org_root}/.jarfis-org/works/ → valid: True."""
        org_root = tmp_path / "docsdir-org"
        project = org_root / "proj"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: DocsDirOrg\n---\n")
        good_docs = jarfis_dir / "works" / "20260507-feature-x"
        good_docs.mkdir(parents=True)
        main([str(project), "--check-docsdir", str(good_docs)])
        output = json.loads(capsys.readouterr().out)
        # The output JSON should contain a docsDir_validated section.
        assert output.get("docsDir_validated", {}).get("valid") is True

    def test_check_docsdir_invalid_outside_works(self, jarfis_env, tmp_path, capsys):
        """docsDir NOT under {org_dir}/works/ → valid: False with explanation."""
        org_root = tmp_path / "docsdir-bad-org"
        project = org_root / "proj"
        project.mkdir(parents=True)
        jarfis_dir = org_root / ".jarfis-org"
        jarfis_dir.mkdir()
        (jarfis_dir / "org-profile.md").write_text("---\norg: BadDocsDir\n---\n")
        bad_docs = tmp_path / "elsewhere" / "20260507-feature-y"
        bad_docs.mkdir(parents=True)
        main([str(project), "--check-docsdir", str(bad_docs)])
        output = json.loads(capsys.readouterr().out)
        validated = output.get("docsDir_validated", {})
        assert validated.get("valid") is False
        assert "expected_prefix" in validated
        # Expected prefix should reference {org_dir}/works/
        assert ".jarfis-org" in validated["expected_prefix"]
        assert "works" in validated["expected_prefix"]
        assert validated.get("actual") == str(bad_docs)

    def test_check_docsdir_valid_for_standalone(self, jarfis_env, tmp_path, capsys):
        """Standalone: docsDir under {personal_dir}/works/ → valid: True."""
        good_docs = os.path.join(jarfis_env["personal_dir"], "works", "20260507-standalone-feat")
        os.makedirs(good_docs, exist_ok=True)
        # Use an unmarked tmp dir as project_dir → standalone resolution.
        loose_project = tmp_path / "loose"
        loose_project.mkdir()
        main([str(loose_project), "--check-docsdir", good_docs])
        output = json.loads(capsys.readouterr().out)
        assert output.get("docsDir_validated", {}).get("valid") is True
