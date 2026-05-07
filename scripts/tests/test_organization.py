"""Tests for jarfis.organization — Org-level project management."""

import json
import os

import pytest

from jarfis.organization import EXCLUDE_DIRS, _scan_projects, cmd_init, cmd_info, cmd_scan, discover_unregistered_orgs, ensure_project_in_org_profile, main, read_orgs, register_org


class TestScanProjects:
    def test_finds_project_with_profile(self, tmp_path):
        proj = tmp_path / "project1"
        jarfis_dir = proj / ".jarfis-project"
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
        nm = tmp_path / "node_modules" / "some-pkg" / ".jarfis-project"
        nm.mkdir(parents=True)
        (nm / "project-profile.md").write_text("# Should not find")
        results = _scan_projects(str(tmp_path))
        assert results == []

    def test_multiple_projects(self, tmp_path):
        for name in ["proj-a", "proj-b", "proj-c"]:
            jarfis = tmp_path / name / ".jarfis-project"
            jarfis.mkdir(parents=True)
            (jarfis / "project-profile.md").write_text(f"# Project Profile: {name}")
        results = _scan_projects(str(tmp_path))
        assert len(results) == 3


class TestCmdInit:
    def test_scan_only_without_confirm(self, tmp_path, capsys):
        proj = tmp_path / "project1" / ".jarfis-project"
        proj.mkdir(parents=True)
        (proj / "project-profile.md").write_text("# Project Profile: P1")
        cmd_init([str(tmp_path)])
        output = json.loads(capsys.readouterr().out)
        assert output["action"] == "scan"
        assert output["project_count"] == 1
        # No files should be created
        assert not os.path.isfile(os.path.join(str(tmp_path), ".jarfis-org", "org-profile.md"))

    def test_creates_org_files_with_confirm(self, jarfis_env, capsys):
        # Use jarfis_env to isolate HOME — prevents writing to real orgs.json
        base = os.path.dirname(jarfis_env["claude_dir"])  # tmp root
        org_root = os.path.join(base, "test-org-root")
        proj = os.path.join(org_root, "project1", ".jarfis-project")
        os.makedirs(proj, exist_ok=True)
        with open(os.path.join(proj, "project-profile.md"), "w") as f:
            f.write("# Project Profile: P1\n\n> Type: backend\n> Last-Commit: abc123\n")

        cmd_init([org_root, "--confirm", "--name", "TestInitOrg"])
        output = json.loads(capsys.readouterr().out)
        assert output["action"] == "init"
        assert output["org_name"] == "TestInitOrg"

        # Verify created files
        assert os.path.isfile(os.path.join(org_root, ".jarfis-org", "org-profile.md"))
        assert os.path.isfile(os.path.join(org_root, ".jarfis-org", "wiki", "INDEX.md"))
        for section in ["PO", "DESIGN", "TA", "QA"]:
            assert os.path.isfile(
                os.path.join(org_root, ".jarfis-org", "wiki", section, "_index.md")
            )

    def test_create_org_files_creates_meetings_works_dirs(self, jarfis_env, capsys):
        """v4.4: _create_org_files also creates meetings/ and works/ in .jarfis-org/."""
        base = os.path.dirname(jarfis_env["claude_dir"])
        org_root = os.path.join(base, "v44-org-root")
        os.makedirs(org_root, exist_ok=True)
        cmd_init([org_root, "--confirm", "--name", "V44Org"])
        capsys.readouterr()
        assert os.path.isdir(os.path.join(org_root, ".jarfis-org", "meetings"))
        assert os.path.isdir(os.path.join(org_root, ".jarfis-org", "works"))

    def test_create_org_files_writes_learnings_md(self, jarfis_env, capsys):
        """v4.4: _create_org_files writes learnings.md inside .jarfis-org/."""
        base = os.path.dirname(jarfis_env["claude_dir"])
        org_root = os.path.join(base, "v44-learn-root")
        os.makedirs(org_root, exist_ok=True)
        cmd_init([org_root, "--confirm", "--name", "V44LearnOrg"])
        capsys.readouterr()
        learnings_path = os.path.join(org_root, ".jarfis-org", "learnings.md")
        assert os.path.isfile(learnings_path)
        with open(learnings_path) as f:
            content = f.read()
        # Has a heading referring to the org name.
        assert "V44LearnOrg" in content or "Learnings" in content

    def test_create_org_files_writes_sync_field_none_for_non_git(self, jarfis_env, capsys):
        """Critic Fix B: non-git org_root → org-profile.md frontmatter has sync: none."""
        base = os.path.dirname(jarfis_env["claude_dir"])
        org_root = os.path.join(base, "non-git-root")
        os.makedirs(org_root, exist_ok=True)
        # No .git here → not a git repo
        cmd_init([org_root, "--confirm", "--name", "NonGitOrg"])
        capsys.readouterr()
        profile_path = os.path.join(org_root, ".jarfis-org", "org-profile.md")
        with open(profile_path) as f:
            content = f.read()
        # YAML frontmatter contains sync: none
        assert "sync: none" in content

    def test_create_org_files_writes_sync_field_git_for_git_repo(self, jarfis_env, tmp_path, capsys):
        """Critic Fix B: git org_root → org-profile.md frontmatter has sync: git."""
        import subprocess
        org_root = tmp_path / "git-org-root"
        org_root.mkdir()
        # Initialize git repo so `git -C ... rev-parse --show-toplevel` succeeds
        subprocess.run(["git", "init", "-q", str(org_root)], check=True)
        cmd_init([str(org_root), "--confirm", "--name", "GitOrg"])
        capsys.readouterr()
        profile_path = org_root / ".jarfis-org" / "org-profile.md"
        content = profile_path.read_text()
        assert "sync: git" in content

    def test_error_on_missing_dir(self):
        with pytest.raises(SystemExit):
            cmd_init(["/nonexistent/dir"])


class TestCmdScan:
    def test_scans_projects(self, tmp_path, capsys):
        for name in ["a", "b"]:
            jarfis = tmp_path / name / ".jarfis-project"
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
        jarfis = tmp_path / ".jarfis-org"
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


class TestOrgsJson:
    def test_read_orgs_empty(self, jarfis_env):
        # Remove existing orgs.json
        orgs_path = os.path.join(jarfis_env["orgs_dir"], "orgs.json")
        os.remove(orgs_path)
        data = read_orgs()
        assert data == {"orgs": []}

    def test_read_orgs_existing(self, jarfis_env):
        data = read_orgs()
        assert len(data["orgs"]) == 1
        assert data["orgs"][0]["name"] == "TestOrg"

    def test_register_org_new_returns_registered_dict(self, jarfis_env):
        """v4.4: register_org returns dict with 'registered': True for new entries."""
        result = register_org("NewOrg", "/path/to/new")
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert result.get("registered") is True
        data = read_orgs()
        names = [o["name"] for o in data["orgs"]]
        assert "NewOrg" in names

    def test_register_org_collision_returns_collision_flag(self, jarfis_env):
        """v4.4 (defect D7): same name, DIFFERENT root → collision=True, no overwrite."""
        # TestOrg is already registered to <tmp>/org-root
        existing_root = jarfis_env["testorg_root"]
        result = register_org("TestOrg", "/some/other/root")
        assert result.get("success") is False
        assert result.get("collision") is True
        assert os.path.normpath(result["existing_root"]) == os.path.normpath(existing_root)
        # Registry should NOT have been overwritten.
        data = read_orgs()
        registered = next(o for o in data["orgs"] if o["name"] == "TestOrg")
        assert os.path.normpath(registered["root"]) == os.path.normpath(existing_root)

    def test_register_org_idempotent_same_root(self, jarfis_env):
        """v4.4 (defect D7): same name, SAME root → already_registered, no change."""
        existing_root = jarfis_env["testorg_root"]
        result = register_org("TestOrg", existing_root)
        assert result.get("success") is True
        assert result.get("already_registered") is True
        # Registry has exactly one TestOrg entry (no duplicate).
        data = read_orgs()
        matches = [o for o in data["orgs"] if o["name"] == "TestOrg"]
        assert len(matches) == 1

    def test_register_org_reserved_prefix(self, jarfis_env):
        """Reserved prefix rejection still returns dict with reserved=True."""
        result = register_org("_reserved", "/path")
        assert result.get("success") is False
        assert result.get("reserved") is True

    def test_cmd_init_registers_org(self, jarfis_env, tmp_path, capsys):
        proj = tmp_path / "project1" / ".jarfis-project"
        proj.mkdir(parents=True)
        (proj / "project-profile.md").write_text(
            "# Project Profile: P1\n\n> Type: backend\n> Last-Commit: abc\n"
        )
        cmd_init([str(tmp_path), "--confirm", "--name", "AutoRegOrg"])
        output = json.loads(capsys.readouterr().out)
        assert output["orgs_json_registered"] is True
        data = read_orgs()
        names = [o["name"] for o in data["orgs"]]
        assert "AutoRegOrg" in names


class TestDiscoverUnregisteredOrgs:
    def test_discovers_sibling_org(self, jarfis_env, tmp_path):
        """Registered org at parent/OrgA → discovers parent/OrgB."""
        parent = tmp_path / "Integration"
        # OrgA: registered
        org_a = parent / "OrgA" / "Projects"
        org_a_jarfis = org_a / ".jarfis-org"
        org_a_jarfis.mkdir(parents=True)
        (org_a_jarfis / "org-profile.md").write_text("---\norg: OrgA\n---\n")
        register_org("OrgA", str(org_a))

        # OrgB: exists but NOT registered
        org_b = parent / "OrgB" / "Projects"
        org_b_jarfis = org_b / ".jarfis-org"
        org_b_jarfis.mkdir(parents=True)
        (org_b_jarfis / "org-profile.md").write_text("---\norg: OrgB\n---\n")

        discovered = discover_unregistered_orgs()
        assert len(discovered) >= 1
        names = [d["name"] for d in discovered]
        assert "OrgB" in names

        # Verify auto-registered
        data = read_orgs()
        registered_names = [o["name"] for o in data["orgs"]]
        assert "OrgB" in registered_names

    def test_no_duplicates(self, jarfis_env, tmp_path):
        """Already registered orgs are not re-discovered."""
        parent = tmp_path / "Integration"
        org_a = parent / "OrgA" / "Projects"
        org_a_jarfis = org_a / ".jarfis-org"
        org_a_jarfis.mkdir(parents=True)
        (org_a_jarfis / "org-profile.md").write_text("---\norg: OrgA\n---\n")
        register_org("OrgA", str(org_a))

        discovered = discover_unregistered_orgs()
        names = [d["name"] for d in discovered]
        assert "OrgA" not in names

    def test_no_orgs_registered(self, jarfis_env):
        """No registered orgs → nothing to scan → empty result."""
        # Remove all orgs
        import json
        orgs_path = os.path.join(jarfis_env["orgs_dir"], "orgs.json")
        with open(orgs_path, "w") as f:
            json.dump({"orgs": []}, f)
        discovered = discover_unregistered_orgs()
        assert discovered == []


class TestEnsureProjectInOrgProfile:
    def _make_org_with_profile(self, tmp_path, org_name="TestOrg", projects=None):
        """Helper: create org-profile.md with a project table."""
        org_root = tmp_path / "org"
        jarfis = org_root / ".jarfis-org"
        jarfis.mkdir(parents=True)
        rows = ""
        if projects:
            for p in projects:
                rows += f"| {p} | {p} | unknown | {p}/.jarfis-project/project-profile.md |\n"
        else:
            rows = "| (none) | | | |\n"
        (jarfis / "org-profile.md").write_text(
            f"---\norg: {org_name}\nroot: {org_root}\n---\n\n"
            f"# Organization Profile\n\n## Projects\n\n"
            f"| Name | Path | Type | Profile |\n"
            f"|------|------|------|---------|"
            f"\n{rows}"
        )
        return org_root

    def test_adds_missing_project(self, tmp_path):
        org_root = self._make_org_with_profile(tmp_path, projects=["proj-a"])
        # Create new project with profile
        new_proj = org_root / "proj-b"
        new_jarfis = new_proj / ".jarfis-project"
        new_jarfis.mkdir(parents=True)
        (new_jarfis / "project-profile.md").write_text(
            "# Project Profile: proj-b\n\n> Type: frontend\n"
        )
        result = ensure_project_in_org_profile(str(org_root), str(new_proj))
        assert result is True
        # Verify table now contains proj-b
        profile = (org_root / ".jarfis-org" / "org-profile.md").read_text()
        assert "proj-b" in profile

    def test_skips_already_registered(self, tmp_path):
        org_root = self._make_org_with_profile(tmp_path, projects=["proj-a"])
        proj = org_root / "proj-a"
        proj.mkdir(exist_ok=True)
        result = ensure_project_in_org_profile(str(org_root), str(proj))
        assert result is False

    def test_skips_no_project_profile(self, tmp_path):
        org_root = self._make_org_with_profile(tmp_path)
        proj = org_root / "proj-no-profile"
        proj.mkdir(parents=True)
        # No .jarfis-project/project-profile.md
        result = ensure_project_in_org_profile(str(org_root), str(proj))
        assert result is False

    def test_skips_no_org_profile(self, tmp_path):
        org_root = tmp_path / "no-org"
        org_root.mkdir()
        proj = org_root / "proj"
        proj.mkdir()
        result = ensure_project_in_org_profile(str(org_root), str(proj))
        assert result is False


class TestExcludeDirs:
    def test_common_excludes(self):
        assert "node_modules" in EXCLUDE_DIRS
        assert ".git" in EXCLUDE_DIRS
        assert "__pycache__" in EXCLUDE_DIRS
