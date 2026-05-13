"""Tests for jarfis.cli — register/unregister/emit/status/tail/bind-session.

Active registry SSOT: ~/.jarfis/active.json (D8).
events.jsonl location: $DOCS_DIR/events.jsonl (D1).
Every test uses $JARFIS_ACTIVE_PATH override + tmp_path for isolation.
"""

import io
import json
import os
from contextlib import redirect_stdout

import pytest

from jarfis import cli, emit


@pytest.fixture
def active(tmp_path, monkeypatch):
    """Isolate active.json + provide helpers."""
    active_path = tmp_path / "active.json"
    monkeypatch.setenv("JARFIS_ACTIVE_PATH", str(active_path))
    return active_path


@pytest.fixture
def docs_dir(tmp_path):
    d = tmp_path / "docs" / "wf-A"
    d.mkdir(parents=True)
    return d


# ---------------------------------------------------------------- registry I/O


class TestReadWriteActive:
    def test_read_returns_empty_when_missing(self, active):
        assert cli._read_active() == {"workflows": []}

    def test_write_then_read_roundtrip(self, active):
        data = {
            "workflows": [
                {
                    "workflow_id": "wf-1",
                    "skill": "work",
                    "docs_dir": "/x",
                    "session_id": None,
                    "tmux_session": None,
                    "started_at": "2026-05-13T00:00:00+00:00",
                }
            ]
        }
        cli._write_active(data)
        assert cli._read_active() == data

    def test_write_creates_parent_dir(self, tmp_path, monkeypatch):
        deep = tmp_path / "a" / "b" / "active.json"
        monkeypatch.setenv("JARFIS_ACTIVE_PATH", str(deep))
        cli._write_active({"workflows": []})
        assert deep.exists()

    def test_read_handles_corrupt_file(self, active):
        active.write_text("not-json{")
        # Corrupt → treat as empty, do not crash
        assert cli._read_active() == {"workflows": []}


# ---------------------------------------------------------------- register


class TestRegister:
    def test_basic_registration(self, active, docs_dir, capsys):
        rc = cli.main(
            ["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"]
        )
        assert rc == 0
        data = cli._read_active()
        assert len(data["workflows"]) == 1
        wf = data["workflows"][0]
        assert wf["workflow_id"] == "wf-1"
        assert wf["skill"] == "work"
        assert wf["docs_dir"] == str(docs_dir)
        assert wf["session_id"] is None
        assert wf["tmux_session"] is None
        assert "started_at" in wf

    def test_duplicate_workflow_id_replaces(self, active, docs_dir, tmp_path):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        new_docs = tmp_path / "docs2"
        new_docs.mkdir()
        cli.main(
            ["register", "--workflow-id=wf-1", "--skill=work-meeting", f"--docs-dir={new_docs}"]
        )
        data = cli._read_active()
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["skill"] == "work-meeting"
        assert data["workflows"][0]["docs_dir"] == str(new_docs)

    def test_two_workflows_coexist(self, active, tmp_path):
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        cli.main(["register", "--workflow-id=a", "--skill=work", f"--docs-dir={d1}"])
        cli.main(["register", "--workflow-id=b", "--skill=sys-implement", f"--docs-dir={d2}"])
        ids = [w["workflow_id"] for w in cli._read_active()["workflows"]]
        assert sorted(ids) == ["a", "b"]

    def test_optional_tmux_session(self, active, docs_dir):
        cli.main(
            [
                "register",
                "--workflow-id=wf-1",
                "--skill=work",
                f"--docs-dir={docs_dir}",
                "--tmux-session=mysession-phase4",
            ]
        )
        wf = cli._read_active()["workflows"][0]
        assert wf["tmux_session"] == "mysession-phase4"

    def test_missing_required_args_fail(self, active):
        with pytest.raises(SystemExit):
            cli.main(["register", "--workflow-id=x"])


# ---------------------------------------------------------------- unregister


class TestUnregister:
    def test_removes_matching_workflow(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(["unregister", "--workflow-id=wf-1"])
        assert cli._read_active()["workflows"] == []

    def test_unknown_id_is_silent_noop(self, active):
        # Already-unregistered (e.g. crash-restart double-call) must not error
        rc = cli.main(["unregister", "--workflow-id=nonexistent"])
        assert rc == 0

    def test_only_target_removed(self, active, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        cli.main(["register", "--workflow-id=a", "--skill=work", f"--docs-dir={d}"])
        cli.main(["register", "--workflow-id=b", "--skill=work", f"--docs-dir={d}"])
        cli.main(["unregister", "--workflow-id=a"])
        ids = [w["workflow_id"] for w in cli._read_active()["workflows"]]
        assert ids == ["b"]


# ---------------------------------------------------------------- emit (CLI)


class TestEmitSubcommand:
    def test_writes_to_workflow_events_jsonl(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        rc = cli.main(
            [
                "emit",
                "--workflow-id=wf-1",
                "--type=phase.start",
                "--summary=Workflow wf-1 시작",
            ]
        )
        assert rc == 0
        events_file = docs_dir / "events.jsonl"
        assert events_file.exists()
        line = events_file.read_text(encoding="utf-8").strip()
        ev = json.loads(line)
        assert ev["type"] == "phase.start"
        assert ev["summary"] == "Workflow wf-1 시작"
        assert ev["level"] == "highlight"

    def test_resolves_workflow_id_from_env(self, active, docs_dir, monkeypatch):
        cli.main(["register", "--workflow-id=wf-env", "--skill=work", f"--docs-dir={docs_dir}"])
        monkeypatch.setenv("JARFIS_WORKFLOW", "wf-env")
        rc = cli.main(["emit", "--type=note", "--summary=from env"])
        assert rc == 0
        ev = json.loads((docs_dir / "events.jsonl").read_text().strip())
        assert ev["summary"] == "from env"

    def test_explicit_level_override(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(
            [
                "emit",
                "--workflow-id=wf-1",
                "--type=tool",
                "--level=debug",
                "--summary=Read foo",
            ]
        )
        ev = json.loads((docs_dir / "events.jsonl").read_text().strip())
        assert ev["level"] == "debug"

    def test_extras_via_kv(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(
            [
                "emit",
                "--workflow-id=wf-1",
                "--type=agent.spawn",
                "--summary=spawn jarfis-engineer",
                "--extra=agent=jarfis-engineer",
                "--extra=task=BE-impl",
            ]
        )
        ev = json.loads((docs_dir / "events.jsonl").read_text().strip())
        assert ev["agent"] == "jarfis-engineer"
        assert ev["task"] == "BE-impl"

    def test_unknown_workflow_fails_clean(self, active, docs_dir, capsys):
        with pytest.raises(SystemExit):
            cli.main(
                [
                    "emit",
                    "--workflow-id=ghost",
                    "--type=note",
                    "--summary=x",
                ]
            )
        err = capsys.readouterr().err
        assert "ghost" in err or "unknown" in err.lower()

    def test_missing_workflow_resolution_fails_clean(self, active, capsys, monkeypatch):
        monkeypatch.delenv("JARFIS_WORKFLOW", raising=False)
        with pytest.raises(SystemExit):
            cli.main(["emit", "--type=note", "--summary=x"])

    def test_invalid_summary_propagates_emit_error(self, active, docs_dir, capsys):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        with pytest.raises(SystemExit):
            cli.main(
                [
                    "emit",
                    "--workflow-id=wf-1",
                    "--type=note",
                    "--summary=ends with period.",
                ]
            )


# ---------------------------------------------------------------- status


class TestStatus:
    def test_empty_when_no_workflows(self, active, capsys):
        rc = cli.main(["status", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data == {"workflows": []}

    def test_lists_workflows_with_event_counts(self, active, docs_dir, capsys):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(["emit", "--workflow-id=wf-1", "--type=phase.start", "--summary=a"])
        cli.main(["emit", "--workflow-id=wf-1", "--type=note", "--summary=b"])
        rc = cli.main(["status", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert len(data["workflows"]) == 1
        wf = data["workflows"][0]
        assert wf["workflow_id"] == "wf-1"
        assert wf["event_count"] == 2
        assert wf["last_event"]["type"] == "note"

    def test_human_readable_default(self, active, docs_dir, capsys):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        rc = cli.main(["status"])
        assert rc == 0
        out = capsys.readouterr().out
        # Default output is text — must mention the workflow id
        assert "wf-1" in out


# ---------------------------------------------------------------- tail


class TestTail:
    def test_default_n_5_for_single_workflow(self, active, docs_dir, capsys):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        for i in range(10):
            cli.main(["emit", "--workflow-id=wf-1", "--type=tool", f"--summary=t{i}"])
        rc = cli.main(["tail", "wf-1", "--no-color"])
        assert rc == 0
        out = capsys.readouterr().out
        # Last 5 by default
        for i in range(5, 10):
            assert f"t{i}" in out
        assert "t0" not in out  # earlier events trimmed

    def test_explicit_n(self, active, docs_dir, capsys):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        for i in range(10):
            cli.main(["emit", "--workflow-id=wf-1", "--type=tool", f"--summary=t{i}"])
        cli.main(["tail", "wf-1", "-n", "3", "--no-color"])
        out = capsys.readouterr().out
        for i in (7, 8, 9):
            assert f"t{i}" in out
        assert "t6" not in out

    def test_tail_all_active(self, active, tmp_path, capsys):
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        cli.main(["register", "--workflow-id=a", "--skill=work", f"--docs-dir={d1}"])
        cli.main(["register", "--workflow-id=b", "--skill=work", f"--docs-dir={d2}"])
        cli.main(["emit", "--workflow-id=a", "--type=note", "--summary=from-a"])
        cli.main(["emit", "--workflow-id=b", "--type=note", "--summary=from-b"])
        cli.main(["tail", "-a", "--no-color"])
        out = capsys.readouterr().out
        assert "from-a" in out
        assert "from-b" in out

    def test_tail_unknown_workflow_fails(self, active, capsys):
        with pytest.raises(SystemExit):
            cli.main(["tail", "ghost"])


# ---------------------------------------------------------------- bind-session (D9)


class TestBindSession:
    def test_binds_session_to_workflow_with_matching_cwd(self, active, docs_dir, capsys):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        # Auto-bind step: cwd is under docs_dir → bind session
        cli.main(
            [
                "bind-session",
                f"--cwd={docs_dir}",
                "--session-id=session-uuid-AAA",
            ]
        )
        wf = cli._read_active()["workflows"][0]
        assert wf["session_id"] == "session-uuid-AAA"

    def test_binds_when_cwd_is_descendant(self, active, docs_dir):
        deep = docs_dir / "subdir" / "more"
        deep.mkdir(parents=True)
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(
            [
                "bind-session",
                f"--cwd={deep}",
                "--session-id=sess-1",
            ]
        )
        assert cli._read_active()["workflows"][0]["session_id"] == "sess-1"

    def test_no_bind_when_cwd_unrelated(self, active, docs_dir, tmp_path):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        unrelated = tmp_path / "elsewhere"
        unrelated.mkdir()
        cli.main(
            [
                "bind-session",
                f"--cwd={unrelated}",
                "--session-id=sess-1",
            ]
        )
        assert cli._read_active()["workflows"][0]["session_id"] is None

    def test_already_bound_session_id_not_overwritten(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(
            ["bind-session", f"--cwd={docs_dir}", "--session-id=first"]
        )
        cli.main(
            ["bind-session", f"--cwd={docs_dir}", "--session-id=second"]
        )
        # First binding wins (per D9 — "1회 박음")
        assert cli._read_active()["workflows"][0]["session_id"] == "first"


# ---------------------------------------------------------------- helper lookups


class TestFindByCwd:
    def test_returns_entry_when_descendant(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        sub = docs_dir / "x"
        sub.mkdir()
        wf = cli.find_by_cwd_ancestor(str(sub))
        assert wf is not None
        assert wf["workflow_id"] == "wf-1"

    def test_returns_none_when_unrelated(self, active, docs_dir, tmp_path):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        unrelated = tmp_path / "x"
        unrelated.mkdir()
        assert cli.find_by_cwd_ancestor(str(unrelated)) is None


class TestFindBySession:
    def test_lookup_by_session_id(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(["bind-session", f"--cwd={docs_dir}", "--session-id=SESS"])
        wf = cli.find_by_session_id("SESS")
        assert wf is not None
        assert wf["workflow_id"] == "wf-1"

    def test_returns_none_for_unknown_session(self, active, docs_dir):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        assert cli.find_by_session_id("ghost") is None


# ---------------------------------------------------------------- render-statusline


class TestRenderStatusline:
    """Multi-line 6-row statusline render (D6).

    Input: statusline stdin JSON ({session_id, cwd, workspace.current_dir, ...})
    Output (stdout):
        - "FALLBACK\n" if no JARFIS match → shell shim defers to original statusline
        - 6-line block (header + 5 body lines) with ANSI colors otherwise
    Side effect: auto-binds session_id to matching workflow on first call (D9).
    """

    def _stdin(self, session_id: str, cwd: str) -> str:
        return json.dumps(
            {
                "session_id": session_id,
                "cwd": cwd,
                "workspace": {"current_dir": cwd},
            }
        )

    def _run(self, stdin_str: str, capsys, monkeypatch) -> str:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_str))
        cli.main(["render-statusline"])
        return capsys.readouterr().out

    def test_fallback_when_no_active_workflows(self, active, capsys, monkeypatch):
        stdin = self._stdin("sess-1", "/tmp/anywhere")
        out = self._run(stdin, capsys, monkeypatch)
        assert out.strip() == "FALLBACK"

    def test_fallback_when_cwd_unrelated(self, active, docs_dir, capsys, monkeypatch, tmp_path):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()
        stdin = self._stdin("sess-x", str(unrelated))
        out = self._run(stdin, capsys, monkeypatch)
        assert out.strip() == "FALLBACK"

    def test_renders_6_lines_when_matched(self, active, docs_dir, capsys, monkeypatch):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(["emit", "--workflow-id=wf-1", "--type=phase.start", "--summary=boot"])
        stdin = self._stdin("sess-A", str(docs_dir))
        out = self._run(stdin, capsys, monkeypatch)
        # 6 lines = 1 header + 5 body slots (empty body slots are blank lines)
        lines = out.rstrip("\n").split("\n")
        assert len(lines) == 6
        # Header includes "JARFIS" + workflow_id + active count
        assert "JARFIS" in lines[0]
        assert "wf-1" in lines[0]
        assert "1 active" in lines[0]
        # First body line = the only event
        assert "boot" in lines[1]
        assert "phase.start" in lines[1]

    def test_auto_binds_session_id_on_first_render(self, active, docs_dir, capsys, monkeypatch):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        # Pre-condition: not bound yet
        assert cli._read_active()["workflows"][0]["session_id"] is None
        stdin = self._stdin("sess-AUTO", str(docs_dir))
        self._run(stdin, capsys, monkeypatch)
        # Post-condition: session bound
        assert cli._read_active()["workflows"][0]["session_id"] == "sess-AUTO"

    def test_subsequent_render_uses_session_id_match(self, active, docs_dir, capsys, monkeypatch, tmp_path):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        # First render: auto-bind from cwd
        self._run(self._stdin("sess-X", str(docs_dir)), capsys, monkeypatch)
        # User cd's away — but session_id stays bound
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        capsys.readouterr()  # clear
        out = self._run(self._stdin("sess-X", str(elsewhere)), capsys, monkeypatch)
        # Should still render JARFIS body (matched by session_id, not cwd)
        assert "FALLBACK" not in out
        assert "wf-1" in out

    def test_body_includes_last_5_events_filtered(self, active, docs_dir, capsys, monkeypatch):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(["emit", "--workflow-id=wf-1", "--type=phase.start", "--summary=p"])
        for i in range(7):
            cli.main(["emit", "--workflow-id=wf-1", "--type=tool", f"--summary=t{i}"])
        cli.main(["emit", "--workflow-id=wf-1", "--type=tool", "--summary=debug-only", "--level=debug"])
        out = self._run(self._stdin("sess-1", str(docs_dir)), capsys, monkeypatch)
        # Only last 5 highlight+info events shown (debug filtered)
        # Total events: phase.start + 7×tool + 1×debug-tool = 9, after filter = 8 → last 5 = t3,t4,t5,t6
        assert "t3" in out
        assert "t6" in out
        assert "debug-only" not in out  # filtered
        assert "t0" not in out  # trimmed (only last 5)

    def test_header_shows_active_count(self, active, tmp_path, capsys, monkeypatch):
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d3 = tmp_path / "d3"
        for d in (d1, d2, d3):
            d.mkdir()
        cli.main(["register", "--workflow-id=a", "--skill=work", f"--docs-dir={d1}"])
        cli.main(["register", "--workflow-id=b", "--skill=work", f"--docs-dir={d2}"])
        cli.main(["register", "--workflow-id=c", "--skill=work", f"--docs-dir={d3}"])
        out = self._run(self._stdin("sess-1", str(d1)), capsys, monkeypatch)
        lines = out.rstrip("\n").split("\n")
        assert "3 active" in lines[0]
        assert "←a" in lines[0]  # focus = first matched workflow

    def test_body_padding_when_few_events(self, active, docs_dir, capsys, monkeypatch):
        cli.main(["register", "--workflow-id=wf-1", "--skill=work", f"--docs-dir={docs_dir}"])
        cli.main(["emit", "--workflow-id=wf-1", "--type=phase.start", "--summary=only"])
        out = self._run(self._stdin("sess-1", str(docs_dir)), capsys, monkeypatch)
        lines = out.rstrip("\n").split("\n")
        assert len(lines) == 6  # always 6 — pad with blank if <5 events
