"""Tests for jarfis.version — semver version bump automation."""

import json
import os
import re

import pytest

from jarfis.version import main


class TestVersionBump:
    def _setup_version_env(self, jarfis_env):
        """Ensure all version-related files exist."""
        repo = jarfis_env["repo_dir"]
        claude = jarfis_env["claude_dir"]
        # __init__.py in the scripts/jarfis/ of the ACTUAL module location
        # version.py reads __init__.py relative to its own __file__
        # So we need to set up the real init file
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
