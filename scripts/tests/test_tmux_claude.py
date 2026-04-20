"""Tests for tmux_claude helpers that can be exercised without a live tmux."""

import os
import subprocess

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
