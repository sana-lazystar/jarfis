"""Tests for tmux_claude helpers that can be exercised without a live tmux."""

import json
import os
import subprocess
import time

import pytest

from jarfis import tmux_claude


class TestSavePaneNonFatal:
    def test_writes_file_when_capture_succeeds(self, tmp_path, monkeypatch):
        dest = tmp_path / "nested" / "attempt1.pane.log"

        class FakeResult:
            def __init__(self, rc, stdout, stderr):
                self.returncode = rc
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, capture_output=False, text=False):
            assert cmd[:2] == ["tmux", "capture-pane"]
            assert "-S" in cmd and "-" in cmd
            return FakeResult(0, "pane contents\nline2\n", "")

        monkeypatch.setattr(subprocess, "run", fake_run)

        ok = tmux_claude.save_pane("jf-abc-phase4", str(dest))
        assert ok is True
        assert dest.exists()
        assert dest.read_text() == "pane contents\nline2\n"

    def test_returns_false_and_warns_on_capture_nonzero(self, tmp_path, monkeypatch, capsys):
        dest = tmp_path / "attempt1.pane.log"

        class FakeResult:
            def __init__(self, rc, stdout, stderr):
                self.returncode = rc
                self.stdout = stdout
                self.stderr = stderr

        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: FakeResult(1, "", "can't find pane"),
        )

        ok = tmux_claude.save_pane("jf-abc-phase4", str(dest))
        assert ok is False
        assert not dest.exists()
        err = capsys.readouterr().err
        assert "save-pane capture failed" in err
        assert "can't find pane" in err

    def test_returns_false_and_warns_on_write_error(self, tmp_path, monkeypatch, capsys):
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o500)
        dest = readonly_dir / "attempt1.pane.log"

        class FakeResult:
            returncode = 0
            stdout = "whatever\n"
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())

        try:
            ok = tmux_claude.save_pane("jf-abc-phase4", str(dest))
        finally:
            readonly_dir.chmod(0o700)

        assert ok is False
        err = capsys.readouterr().err
        assert "save-pane write failed" in err


# ── Completion signal (sentinel + atomic + idle watchdog) ────────────


def _write_result_atomic(result_path: str, payload: dict) -> None:
    """Helper — write tmp, atomic rename, then touch sentinel."""
    tmp = result_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.rename(tmp, result_path)
    open(result_path + ".done", "w").close()


class TestPollSentinel:
    """`poll()` returns when sentinel `.done` appears."""

    def test_returns_immediately_on_existing_sentinel(self, tmp_path, monkeypatch):
        result_path = str(tmp_path / "attempt1.json")
        _write_result_atomic(result_path, {"status": "completed", "tdd_results": {"passed": 5}})

        monkeypatch.setattr(tmux_claude, "session_alive", lambda _: True)
        monkeypatch.setattr(tmux_claude, "capture_pane", lambda _n, lines=100: "")
        monkeypatch.setattr(tmux_claude, "POLL_INTERVAL", 0.01)

        result = tmux_claude.poll("jf-test", result_path)
        assert result["status"] == "completed"
        assert result["tdd_results"]["passed"] == 5

    def test_waits_then_returns_when_sentinel_appears(self, tmp_path, monkeypatch):
        result_path = str(tmp_path / "attempt2.json")
        call_count = {"n": 0}

        def fake_capture(_name, lines=100):
            call_count["n"] += 1
            if call_count["n"] == 3:
                _write_result_atomic(result_path, {"status": "completed"})
            return f"working... line {call_count['n']}\n"

        monkeypatch.setattr(tmux_claude, "session_alive", lambda _: True)
        monkeypatch.setattr(tmux_claude, "capture_pane", fake_capture)
        monkeypatch.setattr(tmux_claude, "POLL_INTERVAL", 0.01)

        result = tmux_claude.poll("jf-test", result_path)
        assert result["status"] == "completed"
        assert call_count["n"] >= 3


class TestPollSessionCrash:
    def test_returns_error_when_session_dies_before_sentinel(self, tmp_path, monkeypatch):
        result_path = str(tmp_path / "attempt1.json")
        alive_calls = {"n": 0}

        def fake_alive(_name):
            alive_calls["n"] += 1
            return alive_calls["n"] < 2

        monkeypatch.setattr(tmux_claude, "session_alive", fake_alive)
        monkeypatch.setattr(tmux_claude, "capture_pane", lambda _n, lines=100: "boom\n")
        monkeypatch.setattr(tmux_claude, "POLL_INTERVAL", 0.01)

        result = tmux_claude.poll("jf-test", result_path)
        assert result["status"] == "error"
        assert "session crashed" in result["reason"].lower() or "crash" in result["reason"].lower()


class TestPollIdleWatchdog:
    """Pane at `❯` with no content change for N polls → error."""

    def test_trips_when_pane_idle_with_prompt_marker(self, tmp_path, monkeypatch):
        result_path = str(tmp_path / "attempt1.json")
        monkeypatch.setattr(tmux_claude, "session_alive", lambda _: True)
        monkeypatch.setattr(tmux_claude, "POLL_INTERVAL", 0.005)
        monkeypatch.setattr(tmux_claude, "IDLE_WATCHDOG_THRESHOLD", 3)

        idle_pane = "previous output\n\n❯ \n"
        monkeypatch.setattr(tmux_claude, "capture_pane", lambda _n, lines=100: idle_pane)

        result = tmux_claude.poll("jf-test", result_path)
        assert result["status"] == "error"
        assert "idle" in result["reason"].lower()

    def test_does_not_trip_while_pane_content_changes(self, tmp_path, monkeypatch):
        result_path = str(tmp_path / "attempt2.json")
        monkeypatch.setattr(tmux_claude, "session_alive", lambda _: True)
        monkeypatch.setattr(tmux_claude, "POLL_INTERVAL", 0.005)
        monkeypatch.setattr(tmux_claude, "IDLE_WATCHDOG_THRESHOLD", 3)

        call_count = {"n": 0}

        def changing_pane(_name, lines=100):
            call_count["n"] += 1
            if call_count["n"] >= 5:
                _write_result_atomic(result_path, {"status": "completed"})
            return f"working iteration {call_count['n']}\n❯ "

        monkeypatch.setattr(tmux_claude, "capture_pane", changing_pane)

        result = tmux_claude.poll("jf-test", result_path)
        assert result["status"] == "completed"


class TestCleanupRemovesSentinelAndTmp:
    """`kill_existing_session` removes stale result.json + result.json.done + result.json.tmp."""

    def test_cleanup_removes_all_three(self, tmp_path, monkeypatch):
        result_path = tmp_path / "attempt1.json"
        result_path.write_text('{"status": "stale"}')
        sentinel = tmp_path / "attempt1.json.done"
        sentinel.write_text("")
        tmp = tmp_path / "attempt1.json.tmp"
        tmp.write_text("partial...")

        monkeypatch.setattr(tmux_claude, "session_alive", lambda _: False)

        tmux_claude.cleanup_result_files(str(result_path))

        assert not result_path.exists()
        assert not sentinel.exists()
        assert not tmp.exists()

    def test_cleanup_is_idempotent_when_files_absent(self, tmp_path, monkeypatch):
        result_path = tmp_path / "attempt1.json"
        tmux_claude.cleanup_result_files(str(result_path))
        assert not result_path.exists()


class TestCreateSessionEnvPropagation:
    """Fix B — `create_session` injects `JARFIS_WORKFLOW` env into tmux."""

    def test_create_session_injects_workflow_env(self, monkeypatch):
        captured = {}

        def fake_run(cmd, check=False):
            captured["cmd"] = cmd
            class R:
                returncode = 0
            return R()

        monkeypatch.setattr(subprocess, "run", fake_run)
        tmux_claude.create_session(
            name="jf-test-phase1",
            workspace="/tmp/ws",
            workflow_id="wf-xyz",
        )
        cmd = captured["cmd"]
        assert "-e" in cmd
        # `-e VAR=value` pair must be present
        idx = cmd.index("-e")
        assert cmd[idx + 1] == "JARFIS_WORKFLOW=wf-xyz"

    def test_create_session_omits_env_when_workflow_id_absent(self, monkeypatch):
        captured = {}

        def fake_run(cmd, check=False):
            captured["cmd"] = cmd
            class R:
                returncode = 0
            return R()

        monkeypatch.setattr(subprocess, "run", fake_run)
        tmux_claude.create_session(name="jf-test-phase1", workspace="/tmp/ws")
        cmd = captured["cmd"]
        # No JARFIS_WORKFLOW present
        assert not any(
            isinstance(arg, str) and arg.startswith("JARFIS_WORKFLOW=") for arg in cmd
        )

    def test_create_session_omits_env_when_workflow_id_empty_string(self, monkeypatch):
        captured = {}

        def fake_run(cmd, check=False):
            captured["cmd"] = cmd
            class R:
                returncode = 0
            return R()

        monkeypatch.setattr(subprocess, "run", fake_run)
        tmux_claude.create_session(
            name="jf-test-phase1", workspace="/tmp/ws", workflow_id=""
        )
        cmd = captured["cmd"]
        assert not any(
            isinstance(arg, str) and arg.startswith("JARFIS_WORKFLOW=") for arg in cmd
        )


class TestDeprecatedTimeoutRemoved:
    def test_default_timeout_constant_removed(self):
        assert not hasattr(tmux_claude, "DEFAULT_TIMEOUT"), (
            "DEFAULT_TIMEOUT should be removed in tmux-claude-completion-signal-v1"
        )

    def test_poll_signature_has_no_timeout(self):
        import inspect
        sig = inspect.signature(tmux_claude.poll)
        assert "timeout" not in sig.parameters, (
            "poll() should not accept timeout parameter"
        )
