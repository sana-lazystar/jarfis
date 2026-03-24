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

    def test_state_no_subcommand(self):
        rc, stdout, stderr = self._run_cli("state")
        assert rc == 1
