"""Tests for jarfis_cli — CLI dispatcher."""

import os
import subprocess
import sys

import pytest


class TestCLIDispatcher:
    """Test the CLI dispatcher by invoking it as a subprocess."""

    def _run_cli(self, *args, jarfis_env=None):
        """Run jarfis_cli.py as subprocess and return (returncode, stdout, stderr)."""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "jarfis_cli.py",
        )
        env = os.environ.copy()
        if jarfis_env:
            env["HOME"] = jarfis_env["tmp_path"]
        result = subprocess.run(
            [sys.executable, cli_path, *args],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return result.returncode, result.stdout, result.stderr

    def test_no_args_shows_error(self):
        rc, stdout, stderr = self._run_cli()
        assert rc == 1
        assert "Usage" in stderr or "error" in stderr

    def test_help_flag(self):
        rc, stdout, stderr = self._run_cli("--help")
        assert rc == 0
        assert "Commands" in stdout or "jarfis_cli" in stdout

    def test_unknown_command(self):
        rc, stdout, stderr = self._run_cli("nonexistent-command")
        assert rc == 1
        assert "Unknown command" in stderr or "error" in stderr

    def test_detect_command(self, tmp_path):
        """Test detect command against an empty directory."""
        rc, stdout, stderr = self._run_cli("detect", str(tmp_path))
        assert rc == 0
        import json
        output = json.loads(stdout)
        assert output["confidence"] == "low"

    def test_wiki_venv_reexec_needed_when_not_in_venv(self, tmp_path):
        """When running outside venv and venv exists, should need re-exec."""
        # Create a fake venv structure
        venv_dir = tmp_path / ".claude" / ".jarfis-venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        fake_python = venv_bin / "python3"
        fake_python.write_text("#!/bin/sh\n")
        fake_python.chmod(0o755)

        # Import the function
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from jarfis_cli import _needs_venv_reexec

        # System python should need re-exec (not in venv)
        result = _needs_venv_reexec(str(venv_dir))
        assert result is True

    def test_wiki_venv_reexec_not_needed_when_in_venv(self, tmp_path):
        """When venv site-packages is already in sys.path, no re-exec needed."""
        venv_dir = tmp_path / ".claude" / ".jarfis-venv"
        site_pkg = venv_dir / "lib" / "python3.14" / "site-packages"
        site_pkg.mkdir(parents=True)
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        fake_python = venv_bin / "python3"
        fake_python.write_text("#!/bin/sh\n")
        fake_python.chmod(0o755)

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from jarfis_cli import _needs_venv_reexec

        # Simulate being in venv by adding site-packages to sys.path
        original_path = sys.path[:]
        sys.path.append(str(site_pkg))
        try:
            result = _needs_venv_reexec(str(venv_dir))
            assert result is False
        finally:
            sys.path[:] = original_path

    def test_wiki_venv_reexec_not_needed_when_no_venv(self, tmp_path):
        """When venv doesn't exist, no re-exec needed."""
        venv_dir = tmp_path / "nonexistent-venv"

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from jarfis_cli import _needs_venv_reexec

        result = _needs_venv_reexec(str(venv_dir))
        assert result is False

    def test_state_no_subcommand(self):
        rc, stdout, stderr = self._run_cli("state")
        assert rc == 1
