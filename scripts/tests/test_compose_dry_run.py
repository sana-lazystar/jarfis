"""M6.3 — `compose --dry-run` flag tests (T2).

Contract (ADR / roadmap §5 T2):
    Phase execution does NOT happen; instead the composition (persona body
    + skills + injected context blocks) is rendered to stdout so a
    testbed session can inspect what would have been sent to the
    sub-agent.

Two invocation modes:

    (a) existing agent-based — ``compose --dry-run --agent <name>
        --state <state.json>`` mirrors the regular compose call, but
        emits human-readable markdown (or ``--format json``) instead of
        the JSON payload eaten by jarfis-foreman.

    (b) persona + scope — ``compose --dry-run --persona <stem> --scope
        <abs-or-rel-path>`` synthesizes a minimal state where
        ``workspace.scope[0]`` points at the given path (with the
        domain auto-detected from indicators on disk). This is the form
        a testbed session uses against an arbitrary project on disk
        without first running ``/jarfis:work``.

Side-effects:
    Dry-run MUST NOT write to ``.jarfis-state.json`` or any other file
    under the state path. We assert mtime invariance to enforce that.
"""

from __future__ import annotations

import json
import os
import time

import pytest


FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "jarfis", "tests", "fixtures",
)


def _fixture(name):
    return os.path.abspath(os.path.join(FIXTURES_DIR, name))


# ── Live-disk preconditions (mobile.yaml + skills) ──────────────────


@pytest.fixture(scope="module")
def live_mobile_assets():
    home = os.path.expanduser("~")
    claude_dir = os.environ.get("CLAUDE_DIR", os.path.join(home, ".claude"))
    mobile_yaml = os.path.join(
        claude_dir, "commands", "jarfis", "domains", "mobile.yaml"
    )
    rn_skill = os.path.join(
        claude_dir, "commands", "jarfis", "skills", "react-native.md"
    )
    persona_md = os.path.join(
        claude_dir, "agents", "jarfis", "personas", "frontend-developer.md"
    )
    for p, label in (
        (mobile_yaml, "mobile.yaml"),
        (rn_skill, "react-native.md"),
        (persona_md, "frontend-developer.md"),
    ):
        if not os.path.isfile(p):
            pytest.skip(f"{label} missing at {p}")
    return claude_dir


# ── M6.3 — CLI argument plumbing ────────────────────────────────────


class TestDryRunArgParsing:
    """The CLI must accept ``--dry-run`` (no argument) and the new
    ``--persona`` / ``--scope`` / ``--format`` flags. Pure parser
    smoke — no I/O."""

    def test_dry_run_flag_recognized(self):
        from jarfis.compose.__main__ import _parse_args
        args = _parse_args([
            "--dry-run",
            "--persona", "frontend-developer",
            "--scope", "/tmp",
        ])
        assert args.dry_run is True
        assert args.persona == "frontend-developer"
        assert args.scope == "/tmp"

    def test_format_defaults_to_markdown(self):
        from jarfis.compose.__main__ import _parse_args
        args = _parse_args([
            "--dry-run",
            "--persona", "frontend-developer",
            "--scope", "/tmp",
        ])
        assert args.format == "markdown"

    def test_format_json_accepted(self):
        from jarfis.compose.__main__ import _parse_args
        args = _parse_args([
            "--dry-run",
            "--persona", "frontend-developer",
            "--scope", "/tmp",
            "--format", "json",
        ])
        assert args.format == "json"

    def test_dry_run_without_persona_or_agent_fails(self, capsys):
        from jarfis.compose.__main__ import main
        # Neither --persona nor --agent → must exit non-zero with an
        # explanatory error; exact message may evolve so we only
        # check the exit and that some stderr text appeared.
        with pytest.raises(SystemExit) as excinfo:
            main(["--dry-run"])
        assert excinfo.value.code != 0
        captured = capsys.readouterr()
        assert captured.err.strip(), "expected stderr error message"


# ── M6.3 — persona+scope mode against the live mobile pack ──────────


class TestDryRunPersonaScopeMode:
    """End-to-end: rn_engineer compose against the multi-domain ``app``
    workspace (or rn-sample fallback). Markdown output must contain the
    persona body, the react-native skill body, and a recognizable
    composition header."""

    def test_markdown_contains_persona_and_skill(
        self, live_mobile_assets, capsys
    ):
        from jarfis.compose.__main__ import main
        scope = _fixture("multi-domain/app")
        if not os.path.isdir(scope):
            scope = _fixture("rn-sample")
        with pytest.raises(SystemExit) as excinfo:
            main([
                "--dry-run",
                "--persona", "frontend-developer",
                "--scope", scope,
                "--domain", "mobile",
            ])
        assert excinfo.value.code == 0
        out = capsys.readouterr().out
        # Markdown should include a header and the rn skill body.
        assert "# Compose Dry-Run" in out or "## Persona" in out, (
            f"missing markdown header in dry-run output:\n{out[:200]}"
        )
        assert "React Native" in out, (
            "react-native skill body missing from dry-run markdown"
        )

    def test_json_format_returns_structured_payload(
        self, live_mobile_assets, capsys
    ):
        from jarfis.compose.__main__ import main
        scope = _fixture("multi-domain/app")
        if not os.path.isdir(scope):
            scope = _fixture("rn-sample")
        with pytest.raises(SystemExit):
            main([
                "--dry-run",
                "--persona", "frontend-developer",
                "--scope", scope,
                "--domain", "mobile",
                "--format", "json",
            ])
        out = capsys.readouterr().out
        payload = json.loads(out)
        # The JSON form must expose: persona, skills_loaded, prompt
        # (or composition), and a dry_run flag.
        assert payload.get("dry_run") is True
        assert payload.get("persona") == "frontend-developer"
        assert "react-native" in payload.get("skills_loaded", [])
        assert "prompt" in payload or "composition" in payload

    def test_dry_run_does_not_create_state_file(
        self, live_mobile_assets, tmp_path, capsys
    ):
        """No ``.jarfis-state.json`` should appear in the scope dir or
        anywhere under tmp_path as a side-effect of dry-run."""
        from jarfis.compose.__main__ import main
        scope = _fixture("multi-domain/app")
        if not os.path.isdir(scope):
            scope = _fixture("rn-sample")
        # snapshot the scope dir
        before = set(os.listdir(scope))
        with pytest.raises(SystemExit):
            main([
                "--dry-run",
                "--persona", "frontend-developer",
                "--scope", scope,
                "--domain", "mobile",
            ])
        capsys.readouterr()
        after = set(os.listdir(scope))
        assert before == after, (
            f"dry-run mutated scope directory: added={after - before}, "
            f"removed={before - after}"
        )

    def test_dry_run_does_not_modify_existing_state(
        self, live_mobile_assets, tmp_path, capsys
    ):
        """If the user passes ``--state`` alongside ``--dry-run``, the
        state file must be read but never written. We verify mtime
        invariance across the call."""
        from jarfis.compose.__main__ import main
        # Build a synthetic state file pointing at the multi-domain app.
        scope = _fixture("multi-domain/app")
        if not os.path.isdir(scope):
            scope = _fixture("rn-sample")
        state_path = tmp_path / ".jarfis-state.json"
        state = {
            "domain": "mobile",
            "workspace": {
                "scope": [
                    {
                        "name": "app",
                        "path": scope,
                        "domain": "mobile",
                        "framework": "react-native",
                        "type": "mobile",
                    }
                ]
            },
        }
        state_path.write_text(json.dumps(state, indent=2))
        mtime_before = state_path.stat().st_mtime
        # Sleep enough for FS resolution to detect a write if it happened.
        time.sleep(0.01)

        with pytest.raises(SystemExit):
            main([
                "--dry-run",
                "--persona", "frontend-developer",
                "--scope", scope,
                "--domain", "mobile",
                "--state", str(state_path),
            ])
        capsys.readouterr()

        mtime_after = state_path.stat().st_mtime
        assert mtime_after == mtime_before, (
            "dry-run must not modify the state file"
        )


# ── M6.3 — markdown layout regression ───────────────────────────────


class TestDryRunMarkdownLayout:
    """Stable section headers so testbed checklists can grep for them."""

    def test_sections_present(self, live_mobile_assets, capsys):
        from jarfis.compose.__main__ import main
        scope = _fixture("multi-domain/app")
        if not os.path.isdir(scope):
            scope = _fixture("rn-sample")
        with pytest.raises(SystemExit):
            main([
                "--dry-run",
                "--persona", "frontend-developer",
                "--scope", scope,
                "--domain", "mobile",
            ])
        out = capsys.readouterr().out
        # Required structure for testbed grep / checklist verification.
        for header in ("## Persona", "## Skills", "## Meta"):
            assert header in out, (
                f"markdown dry-run missing section `{header}` in output:\n"
                f"{out[:400]}"
            )
