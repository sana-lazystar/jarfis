"""Tests for jarfis.sync — tests/fixtures/ non-Python sync gap (B1, v4.1.1).

Background (v4.1.1 backlog B1):
    sync.py:_find_files(src_pkg, ".py") yields only .py files when walking
    ~/.claude/scripts/jarfis/. The directory ~/.claude/scripts/jarfis/tests/
    fixtures/ contains non-Python fixture files (package.json, Cargo.toml,
    Podfile, build.gradle, tauri.conf.json, .gitkeep, etc.) used by
    test_dispatch.py / test_detect_scoring.py. These files are silently
    skipped by sync_files(), causing repo-side tests to fail until manual
    cp -r recovery.

These tests document the contract: every file under
    ~/.claude/scripts/jarfis/tests/fixtures/
must reach
    {repo}/scripts/jarfis/tests/fixtures/
after a single `jarfis sync` call, regardless of extension.
"""

import os

from jarfis.sync import sync_files


class TestSyncFixturesNonPython:
    """B1 — non-Python fixture files under scripts/jarfis/tests/fixtures/ sync."""

    def test_syncs_package_json_fixture(self, jarfis_env):
        """package.json fixture (RN/web stack) should be synced."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            "sample-rn", "package.json"
        )
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as f:
            f.write('{"name": "sample-rn", "dependencies": {"react-native": "0.74.0"}}')

        sync_files(repo, claude)

        dst = os.path.join(
            repo, "scripts", "jarfis", "tests", "fixtures",
            "sample-rn", "package.json"
        )
        assert os.path.isfile(dst), (
            f"package.json fixture not synced. expected at {dst}"
        )
        with open(dst) as f:
            assert "react-native" in f.read()

    def test_syncs_cargo_toml_fixture(self, jarfis_env):
        """Cargo.toml fixture (Tauri stack) should be synced."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            "sample-tauri", "Cargo.toml"
        )
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as f:
            f.write('[package]\nname = "sample-tauri"\nversion = "0.1.0"\n')

        sync_files(repo, claude)

        dst = os.path.join(
            repo, "scripts", "jarfis", "tests", "fixtures",
            "sample-tauri", "Cargo.toml"
        )
        assert os.path.isfile(dst), (
            f"Cargo.toml fixture not synced. expected at {dst}"
        )

    def test_syncs_nested_fixture(self, jarfis_env):
        """Deeply nested fixture (ios/Podfile) should be synced — multi-level walk."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            "rn-app", "ios", "Podfile"
        )
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as f:
            f.write("platform :ios, '13.4'\n")

        sync_files(repo, claude)

        dst = os.path.join(
            repo, "scripts", "jarfis", "tests", "fixtures",
            "rn-app", "ios", "Podfile"
        )
        assert os.path.isfile(dst), (
            f"nested Podfile fixture not synced. expected at {dst}"
        )

    def test_syncs_gitkeep_in_empty_fixture(self, jarfis_env):
        """Empty-fixture marker (.gitkeep) — greenfield-empty pattern."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            "greenfield-x", ".gitkeep"
        )
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as f:
            f.write("")

        sync_files(repo, claude)

        dst = os.path.join(
            repo, "scripts", "jarfis", "tests", "fixtures",
            "greenfield-x", ".gitkeep"
        )
        assert os.path.isfile(dst), (
            f".gitkeep fixture not synced. expected at {dst}"
        )

    def test_syncs_metro_config_js(self, jarfis_env):
        """metro.config.js (.js fixture) — different extension still synced."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            "metro-app", "metro.config.js"
        )
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as f:
            f.write("module.exports = { resolver: {} };\n")

        sync_files(repo, claude)

        dst = os.path.join(
            repo, "scripts", "jarfis", "tests", "fixtures",
            "metro-app", "metro.config.js"
        )
        assert os.path.isfile(dst)

    def test_syncs_tauri_conf_json(self, jarfis_env):
        """tauri.conf.json — Tauri-specific fixture."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            "tauri-x", "src-tauri", "tauri.conf.json"
        )
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as f:
            f.write('{"productName": "x"}')

        sync_files(repo, claude)

        dst = os.path.join(
            repo, "scripts", "jarfis", "tests", "fixtures",
            "tauri-x", "src-tauri", "tauri.conf.json"
        )
        assert os.path.isfile(dst)


class TestSyncFixturesRegression:
    """Guard rails: B1 fix must not break existing sync behavior."""

    def test_python_sources_still_sync(self, jarfis_env):
        """scripts/jarfis/*.py sync (existing 5b path) preserved."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(claude, "scripts", "jarfis", "newmod.py")
        with open(src, "w") as f:
            f.write("# stub module\n")

        sync_files(repo, claude)

        dst = os.path.join(repo, "scripts", "jarfis", "newmod.py")
        assert os.path.isfile(dst)

    def test_skips_pycache(self, jarfis_env):
        """__pycache__ MUST NOT be synced — regression guard for B1 fix.

        After B1 fix relaxes the .py-only filter, the broader walk could
        pick up __pycache__/*.pyc files. Sync must explicitly exclude them.
        """
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        pyc_dir = os.path.join(claude, "scripts", "jarfis", "__pycache__")
        os.makedirs(pyc_dir, exist_ok=True)
        with open(os.path.join(pyc_dir, "module.cpython-310.pyc"), "wb") as f:
            f.write(b"\xab\xcd\xef")

        sync_files(repo, claude)

        dst = os.path.join(repo, "scripts", "jarfis", "__pycache__")
        assert not os.path.isdir(dst), "__pycache__ leaked into repo"

    def test_skips_distill_backup(self, jarfis_env):
        """.distill-backup MUST NOT be synced — existing exclusion preserved."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        backup_dir = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            ".distill-backup", "old-fixture"
        )
        os.makedirs(backup_dir, exist_ok=True)
        with open(os.path.join(backup_dir, "old.json"), "w") as f:
            f.write("{}")

        sync_files(repo, claude)

        dst = os.path.join(
            repo, "scripts", "jarfis", "tests", "fixtures", ".distill-backup"
        )
        assert not os.path.isdir(dst), ".distill-backup leaked into repo"

    def test_returns_synced_count(self, jarfis_env):
        """sync_files() return value (synced_count, changes) shape preserved."""
        claude = jarfis_env["claude_dir"]
        repo = jarfis_env["repo_dir"]

        src = os.path.join(
            claude, "scripts", "jarfis", "tests", "fixtures",
            "count-test", "manifest.json"
        )
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as f:
            f.write('{"x": 1}')

        result = sync_files(repo, claude)
        assert isinstance(result, tuple)
        assert len(result) == 2
        synced_count, changes = result
        assert synced_count >= 1
        assert isinstance(changes, list)
