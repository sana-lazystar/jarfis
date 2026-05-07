"""Tests for jarfis.migrate — v4.3 → v4.4 org-root data-source restructure."""

import json
import os
import subprocess

import pytest

from jarfis import migrate


def _seed_v43_layout(jarfis_env, tmp_path):
    """Helper: build a v4.3-style layout (in-fixture) and a non-fixture org root.

    The fixture's testorg_root already exists; this helper creates the LEGACY
    structure under {personal}/orgs/{name}/ with sample data so migrate has
    something to move.

    Returns dict with relevant paths.
    """
    personal = jarfis_env["personal_dir"]
    legacy_orgs = os.path.join(personal, "orgs")
    org_root = jarfis_env["testorg_root"]  # registered as TestOrg in fixture

    # Build v4.3 legacy directory structure for TestOrg.
    legacy_testorg = os.path.join(legacy_orgs, "TestOrg")
    legacy_meetings = os.path.join(legacy_testorg, "meetings")
    legacy_works = os.path.join(legacy_testorg, "works")
    os.makedirs(legacy_meetings, exist_ok=True)
    os.makedirs(legacy_works, exist_ok=True)
    # Sample meeting/work directories.
    sample_meeting = os.path.join(legacy_meetings, "20260101-test-meeting")
    os.makedirs(sample_meeting, exist_ok=True)
    with open(os.path.join(sample_meeting, "summary.md"), "w") as f:
        f.write("---\ndate: 2026-01-01\n---\n# Test\n")
    sample_work = os.path.join(legacy_works, "20260102-feature-x")
    os.makedirs(sample_work, exist_ok=True)
    with open(os.path.join(sample_work, ".jarfis-state.json"), "w") as f:
        json.dump({
            "work": {
                "name": "20260102-feature-x",
                "docsDir": sample_work,
            },
            "docs_dir": sample_work,
        }, f)
    # legacy learnings.md
    with open(os.path.join(legacy_testorg, "learnings.md"), "w") as f:
        f.write("# TestOrg Learnings (legacy)\n")

    # Standalone bucket (legacy)
    legacy_standalone = os.path.join(legacy_orgs, "_standalone")
    legacy_sa_works = os.path.join(legacy_standalone, "works")
    legacy_sa_meetings = os.path.join(legacy_standalone, "meetings")
    os.makedirs(legacy_sa_works, exist_ok=True)
    os.makedirs(legacy_sa_meetings, exist_ok=True)
    with open(os.path.join(legacy_standalone, "learnings.md"), "w") as f:
        f.write("# Standalone Learnings\n")

    return {
        "legacy_orgs": legacy_orgs,
        "legacy_testorg": legacy_testorg,
        "legacy_meetings": legacy_meetings,
        "legacy_works": legacy_works,
        "sample_meeting": sample_meeting,
        "sample_work": sample_work,
        "legacy_standalone": legacy_standalone,
        "legacy_sa_works": legacy_sa_works,
        "legacy_sa_meetings": legacy_sa_meetings,
        "org_root": org_root,
    }


class TestMigrateDryRun:
    def test_dry_run_lists_actions_without_mutation(self, jarfis_env, tmp_path, capsys):
        """--dry-run prints the action plan and performs zero filesystem mutations."""
        seed = _seed_v43_layout(jarfis_env, tmp_path)
        # Snapshot pre-state.
        pre_existing_legacy = os.path.isdir(seed["legacy_meetings"])
        pre_existing_sample = os.path.isdir(seed["sample_meeting"])

        migrate.main(["v4.3-to-v4.4", "--dry-run", "--no-backup"])
        out = capsys.readouterr().out
        # Should mention "dry-run" and list at least one MOVE action.
        result = json.loads(out)
        assert result.get("dry_run") is True
        assert "actions" in result
        assert len(result["actions"]) >= 1

        # Filesystem unchanged.
        assert os.path.isdir(seed["legacy_meetings"]) == pre_existing_legacy
        assert os.path.isdir(seed["sample_meeting"]) == pre_existing_sample
        # The new org-root targets must NOT have meetings/works moved in (yet).
        new_meetings = os.path.join(seed["org_root"], ".jarfis-org", "meetings", "20260101-test-meeting")
        assert not os.path.isdir(new_meetings)


class TestMigrateApply:
    def test_apply_moves_meetings(self, jarfis_env, tmp_path, capsys):
        """Apply mode moves legacy meetings/ into {org_root}/.jarfis-org/meetings/."""
        seed = _seed_v43_layout(jarfis_env, tmp_path)
        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        new_meeting = os.path.join(
            seed["org_root"], ".jarfis-org", "meetings", "20260101-test-meeting"
        )
        assert os.path.isdir(new_meeting)
        assert os.path.isfile(os.path.join(new_meeting, "summary.md"))
        # Legacy meetings dir should be cleared (or absent) — at minimum the
        # sample meeting no longer lives there.
        assert not os.path.isdir(seed["sample_meeting"])

    def test_apply_moves_works(self, jarfis_env, tmp_path, capsys):
        """Apply mode moves legacy works/ into {org_root}/.jarfis-org/works/."""
        seed = _seed_v43_layout(jarfis_env, tmp_path)
        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        new_work = os.path.join(
            seed["org_root"], ".jarfis-org", "works", "20260102-feature-x"
        )
        assert os.path.isdir(new_work)
        assert os.path.isfile(os.path.join(new_work, ".jarfis-state.json"))
        assert not os.path.isdir(seed["sample_work"])

    def test_apply_moves_learnings(self, jarfis_env, tmp_path, capsys):
        """Apply mode moves legacy learnings.md into {org_root}/.jarfis-org/learnings.md."""
        seed = _seed_v43_layout(jarfis_env, tmp_path)
        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        new_learnings = os.path.join(seed["org_root"], ".jarfis-org", "learnings.md")
        assert os.path.isfile(new_learnings)
        # Legacy learnings should have been moved/removed.
        legacy_learnings = os.path.join(seed["legacy_testorg"], "learnings.md")
        assert not os.path.isfile(legacy_learnings)

    def test_standalone_flatten(self, jarfis_env, tmp_path, capsys):
        """Standalone bucket: orgs/_standalone/* → flat .personal/{works,meetings,learnings.md}/."""
        seed = _seed_v43_layout(jarfis_env, tmp_path)
        # Add a sample meeting to standalone legacy
        sa_meeting = os.path.join(seed["legacy_sa_meetings"], "20260105-sa-meeting")
        os.makedirs(sa_meeting, exist_ok=True)
        with open(os.path.join(sa_meeting, "summary.md"), "w") as f:
            f.write("# Standalone meeting\n")

        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        personal = jarfis_env["personal_dir"]
        # Should flatten into {personal}/meetings/ and {personal}/learnings.md
        flat_meeting = os.path.join(personal, "meetings", "20260105-sa-meeting")
        assert os.path.isdir(flat_meeting)
        flat_learn = os.path.join(personal, "learnings.md")
        assert os.path.isfile(flat_learn)


class TestMigrateSyncDetection:
    def test_writes_sync_none_for_non_git_org(self, jarfis_env, tmp_path, capsys):
        """Non-git org_root → org-profile.md gets sync: none."""
        seed = _seed_v43_layout(jarfis_env, tmp_path)
        # testorg_root already has org-profile.md (with sync: none) from the
        # fixture. Ensure migrate preserves/writes a sync field. Wipe sync to
        # confirm migrate writes it.
        profile_path = os.path.join(seed["org_root"], ".jarfis-org", "org-profile.md")
        with open(profile_path) as f:
            content = f.read()
        # Strip any existing 'sync:' line
        new_content = "\n".join(l for l in content.split("\n") if not l.startswith("sync:"))
        with open(profile_path, "w") as f:
            f.write(new_content)

        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        with open(profile_path) as f:
            updated = f.read()
        # testorg_root is not a git repo → sync: none expected.
        assert "sync: none" in updated

    def test_writes_sync_git_for_git_org(self, jarfis_env, tmp_path, capsys):
        """Git org_root → org-profile.md gets sync: git."""
        # Create a fresh git-backed org and register it in orgs.json.
        git_org_root = tmp_path / "git-backed-org"
        git_org_root.mkdir()
        subprocess.run(["git", "init", "-q", str(git_org_root)], check=True)
        jarfis_org = git_org_root / ".jarfis-org"
        jarfis_org.mkdir()
        (jarfis_org / "org-profile.md").write_text(
            "---\norg: GitOrg\nroot: " + str(git_org_root) + "\n---\n"
        )
        # Register
        orgs_json_path = os.path.join(jarfis_env["orgs_dir"], "orgs.json")
        with open(orgs_json_path) as f:
            data = json.load(f)
        data["orgs"].append({"name": "GitOrg", "root": str(git_org_root)})
        with open(orgs_json_path, "w") as f:
            json.dump(data, f)

        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        with open(jarfis_org / "org-profile.md") as f:
            updated = f.read()
        assert "sync: git" in updated


class TestMigrateStateRewrite:
    def test_rewrites_state_docsdir(self, jarfis_env, tmp_path, capsys):
        """Active .jarfis-state.json files have docs_dir / work.docsDir rewritten."""
        seed = _seed_v43_layout(jarfis_env, tmp_path)
        # Pre-state: state file at legacy_works/sample → docs_dir is legacy path
        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        new_work = os.path.join(seed["org_root"], ".jarfis-org", "works", "20260102-feature-x")
        with open(os.path.join(new_work, ".jarfis-state.json")) as f:
            state = json.load(f)
        # docs_dir + work.docsDir should now point to the new location.
        assert os.path.normpath(state["docs_dir"]) == os.path.normpath(new_work)
        assert os.path.normpath(state["work"]["docsDir"]) == os.path.normpath(new_work)


class TestMigrateBackup:
    def test_creates_backup_tarball_unless_disabled(self, jarfis_env, tmp_path, capsys):
        """Without --no-backup, a tarball under .personal/orgs/ is created."""
        _seed_v43_layout(jarfis_env, tmp_path)
        migrate.main(["v4.3-to-v4.4"])
        capsys.readouterr()
        # Backup tarball should be at .personal/orgs/.backup-v4.3-*.tgz
        legacy_orgs_archived = os.path.join(jarfis_env["personal_dir"], "orgs.v4.3-archive")
        # Either the rename happened (so the tarball lives in orgs.v4.3-archive parent)
        # or it stayed in orgs/. Look for any matching file.
        candidates = []
        for root in (
            os.path.join(jarfis_env["personal_dir"], "orgs"),
            legacy_orgs_archived,
            jarfis_env["personal_dir"],
        ):
            if os.path.isdir(root):
                for entry in os.listdir(root):
                    if entry.startswith(".backup-v4.3-") and entry.endswith(".tgz"):
                        candidates.append(os.path.join(root, entry))
        assert candidates, "Expected at least one backup tarball under .personal/"


class TestMigrateIdempotent:
    def test_no_op_on_second_run(self, jarfis_env, tmp_path, capsys):
        """Second migration run is a no-op (no errors, no double-move)."""
        _seed_v43_layout(jarfis_env, tmp_path)
        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        capsys.readouterr()
        # Second run.
        migrate.main(["v4.3-to-v4.4", "--no-backup"])
        out = capsys.readouterr().out
        result = json.loads(out)
        # Idempotent: should report "already_migrated" or actions == [] or
        # an explicit completed:true with no moves performed.
        # We accept any of these signals so the implementation has some
        # latitude, but the run must not raise an exception.
        assert result.get("status") in ("completed", "already_migrated", "no_op") or result.get("idempotent") is True
