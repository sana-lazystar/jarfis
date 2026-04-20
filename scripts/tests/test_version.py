"""Tests for jarfis.version — semver version bump automation."""

import json
import os
import re

import pytest

from jarfis.version import main


class TestVersionBump:
    def _setup_version_env(self, jarfis_env):
        return jarfis_env

    def test_patch_bump(self, jarfis_env, capsys):
        self._setup_version_env(jarfis_env)
        main(["patch", "test change"])
        output = json.loads(capsys.readouterr().out)
        assert output["previous"] == "2.2.2"
        assert output["new"] == "2.2.3"
        assert output["bump_type"] == "patch"

        # Verify VERSION file
        with open(os.path.join(jarfis_env["repo_dir"], "VERSION")) as f:
            assert f.read().strip() == "2.2.3"

        # Verify .jarfis-version
        with open(os.path.join(jarfis_env["claude_dir"], ".jarfis-version")) as f:
            assert f.read().strip() == "2.2.3"

        # Verify claude_dir/scripts/jarfis/__init__.py bumped
        init_path = os.path.join(
            jarfis_env["claude_dir"], "scripts", "jarfis", "__init__.py"
        )
        with open(init_path) as f:
            assert '__version__ = "2.2.3"' in f.read()

    def test_patch_bump_does_not_mutate_installed_init(self, jarfis_env):
        """Regression: version.main must never touch the real installed __init__.py.

        Historical bug (pre-v4.0.6): init_file was resolved via __file__, so
        running the test suite silently rewrote the installed __init__.py to
        the test fixture's bumped version (e.g. 4.0.5 → 2.2.3).
        """
        import jarfis.version as _v
        installed_init = os.path.join(
            os.path.dirname(_v.__file__), "__init__.py"
        )
        if not os.path.isfile(installed_init):
            pytest.skip("no installed __init__.py to guard")
        with open(installed_init) as f:
            before = f.read()
        main(["patch", "regression guard"])
        with open(installed_init) as f:
            after = f.read()
        assert before == after, (
            f"version bump mutated installed __init__.py at {installed_init}"
        )

    def test_minor_bump(self, jarfis_env, capsys):
        self._setup_version_env(jarfis_env)
        main(["minor", "new feature"])
        output = json.loads(capsys.readouterr().out)
        assert output["new"] == "2.3.0"

    def test_major_bump(self, jarfis_env, capsys):
        self._setup_version_env(jarfis_env)
        main(["major", "breaking change"])
        output = json.loads(capsys.readouterr().out)
        assert output["new"] == "3.0.0"

    def test_invalid_bump_type_exits(self, jarfis_env):
        with pytest.raises(SystemExit):
            main(["invalid", "msg"])

    def test_no_args_exits(self):
        with pytest.raises(SystemExit):
            main([])

    def test_changelog_updated(self, jarfis_env, capsys):
        self._setup_version_env(jarfis_env)
        main(["patch", "changelog test entry"])
        changelog = os.path.join(jarfis_env["repo_dir"], "CHANGELOG.md")
        with open(changelog) as f:
            content = f.read()
        assert "changelog test entry" in content
        assert "[2.2.3]" in content

    def test_index_version_updated(self, jarfis_env, capsys):
        self._setup_version_env(jarfis_env)
        main(["patch", "index test"])
        index = os.path.join(jarfis_env["claude_dir"], "commands", "jarfis", "jarfis-index.md")
        with open(index) as f:
            content = f.read()
        assert "Version: 2.2.3" in content
