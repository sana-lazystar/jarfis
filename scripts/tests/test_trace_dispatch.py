"""M6.4 — Telemetry hooks for dispatch + skills (T3).

These tests pin down the trace events emitted along the v4.1 dispatch /
compose code paths when ``JARFIS_TRACE=1``. Three families:

    * ``domain_detect`` — emitted by ``jarfis.domain.detect`` with the
      input path, top-1 domain, confidence, matched_count, tie flag,
      and a synthesized greenfield boolean.
    * ``domain_yaml_load`` — emitted whenever ``_load_domain_yaml``
      reads a domain pack from disk so testbed runs can confirm
      ``mobile.yaml`` / ``desktop.yaml`` are actually being consulted.
    * ``dispatch_branch`` — emitted by ``jarfis.work_args.parse_work_args``
      when an explicit ``--domain`` / ``--scope-domain`` override is
      detected (the only branch the parser is responsible for); plus
      ``jarfis.domain.detect`` emits the ``high-conf`` / ``low-conf`` /
      ``tie`` / ``greenfield`` branch derived from its own outcome.
    * ``external_skills_resolution`` — emitted from the compose skill
      loader so the testbed can confirm bare-name (e.g. ``"browser"``)
      versus slash-form (e.g. ``"web/react"``) external_skills both
      hit the lookup path.

Performance contract: when ``JARFIS_TRACE`` is unset or ``0``, every
hook is a no-op and writes nothing. We verify both the disabled
(default) path and the enabled emission shape.
"""

from __future__ import annotations

import json
import os

import pytest


FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "jarfis", "tests", "fixtures",
)


def _fixture(name):
    return os.path.abspath(os.path.join(FIXTURES_DIR, name))


@pytest.fixture
def trace_on(monkeypatch, tmp_path):
    """Enable JARFIS_TRACE and route output to a tmp file."""
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("JARFIS_TRACE", "1")
    monkeypatch.setenv("JARFIS_TRACE_PATH", str(trace_path))
    return trace_path


@pytest.fixture
def trace_off(monkeypatch, tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("JARFIS_TRACE", "0")
    monkeypatch.setenv("JARFIS_TRACE_PATH", str(trace_path))
    return trace_path


def _read_events(trace_path):
    if not os.path.exists(trace_path):
        return []
    out = []
    with open(trace_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


# ── domain_detect / dispatch_branch (high-conf) ─────────────────────


class TestDetectTelemetry:
    def test_high_confidence_emits_domain_detect(self, trace_on):
        from jarfis.domain import detect
        detect(_fixture("tauri-sample"))
        events = _read_events(trace_on)
        kinds = [e["event"] for e in events]
        assert "domain_detect" in kinds, (
            f"expected domain_detect event, got: {kinds}"
        )
        ev = next(e for e in events if e["event"] == "domain_detect")
        attrs = ev["attrs"]
        # Required fields per ADR-0003 §3.4.
        assert attrs.get("domain") == "desktop"
        assert attrs.get("confidence", 0) >= 0.85
        assert "matched_count" in attrs
        assert attrs.get("tie") is False
        assert attrs.get("greenfield") is False
        # Path must be recorded so testbed sessions can identify the run.
        assert "path" in attrs

    def test_high_confidence_dispatch_branch_emitted(self, trace_on):
        from jarfis.domain import detect
        detect(_fixture("tauri-sample"))
        events = _read_events(trace_on)
        branches = [
            e["attrs"].get("branch")
            for e in events
            if e["event"] == "dispatch_branch"
        ]
        assert "high-conf" in branches, (
            f"expected high-conf branch, got: {branches}"
        )

    def test_greenfield_branch(self, trace_on):
        from jarfis.domain import detect
        detect(_fixture("greenfield-empty"))
        events = _read_events(trace_on)
        branches = [
            e["attrs"].get("branch")
            for e in events
            if e["event"] == "dispatch_branch"
        ]
        assert "greenfield" in branches
        # And domain_detect must mark greenfield True.
        det = next(e for e in events if e["event"] == "domain_detect")
        assert det["attrs"]["greenfield"] is True

    def test_low_confidence_branch(self, trace_on):
        from jarfis.domain import detect
        detect(_fixture("lowconf-sample"))
        events = _read_events(trace_on)
        branches = [
            e["attrs"].get("branch")
            for e in events
            if e["event"] == "dispatch_branch"
        ]
        # Low-conf fixture either matches nothing (greenfield) or matches
        # below 0.85; both are acceptable testbed signals.
        assert any(b in ("low-conf", "greenfield") for b in branches), (
            f"expected low-conf or greenfield, got: {branches}"
        )

    def test_disabled_emits_nothing(self, trace_off):
        from jarfis.domain import detect
        detect(_fixture("tauri-sample"))
        assert _read_events(trace_off) == [], (
            "JARFIS_TRACE=0 must be a no-op"
        )


# ── domain_yaml_load ────────────────────────────────────────────────


class TestDomainYamlLoadTelemetry:
    def test_mobile_yaml_load_event(self, trace_on):
        """Loading ``mobile.yaml`` (via detect → list_domains →
        _load_domain_yaml) must emit a yaml-load breadcrumb so testbed
        runs can confirm the pack was consulted.
        """
        from jarfis.domain import detect
        # Tauri fixture exercises every installed domain pack as part of
        # detection (it scores against each yaml), so mobile.yaml is
        # guaranteed to be loaded.
        detect(_fixture("tauri-sample"))
        events = _read_events(trace_on)
        loads = [
            e["attrs"].get("domain")
            for e in events
            if e["event"] == "domain_yaml_load"
        ]
        assert "mobile" in loads, (
            f"expected mobile.yaml load event, got loads={loads}"
        )
        assert "desktop" in loads
        assert "web" in loads


# ── dispatch_branch override (work_args) ────────────────────────────


class TestWorkArgsOverrideBranch:
    def test_domain_override_emits_branch(self, trace_on):
        from jarfis.work_args import parse_work_args
        parse_work_args("--domain desktop")
        events = _read_events(trace_on)
        branches = [
            e["attrs"].get("branch")
            for e in events
            if e["event"] == "dispatch_branch"
        ]
        assert "override" in branches, (
            f"expected override branch, got: {branches}"
        )

    def test_scope_domain_override_emits_branch(self, trace_on):
        from jarfis.work_args import parse_work_args
        parse_work_args(
            "--scope-domain shell=desktop --scope-domain app=mobile"
        )
        events = _read_events(trace_on)
        branches = [
            e["attrs"].get("branch")
            for e in events
            if e["event"] == "dispatch_branch"
        ]
        # Per-scope override is a multi-domain signal — testbed wants
        # to see this distinctly so it can verify monorepo dispatch.
        assert any(b in ("override", "multi-domain") for b in branches)

    def test_no_overrides_no_branch(self, trace_on):
        from jarfis.work_args import parse_work_args
        parse_work_args("just a free-text input")
        events = _read_events(trace_on)
        branches = [
            e["attrs"].get("branch")
            for e in events
            if e["event"] == "dispatch_branch"
        ]
        # Free-text input should not emit a dispatch_branch from the parser.
        assert "override" not in branches
        assert "multi-domain" not in branches


# ── external_skills_resolution ──────────────────────────────────────


class TestExternalSkillsResolutionTelemetry:
    """rn_engineer in mobile.yaml uses ``external_skills: ["browser"]``
    (bare-name form). The compose path must emit a
    ``external_skills_resolution`` event with form=bare-name. We also
    cover the slash-form path through a synthetic role config.
    """

    def test_bare_name_emits_event(self, trace_on):
        from jarfis.compose.skills import load_skills_for_agent
        # The live mobile pack provides rn_engineer with bare-name
        # external_skills (browser); skip if the pack isn't installed
        # (matches the contract used in test_rn_engineer_compose.py).
        home = os.path.expanduser("~")
        claude_dir = os.environ.get("CLAUDE_DIR", os.path.join(home, ".claude"))
        if not os.path.isfile(
            os.path.join(claude_dir, "commands", "jarfis", "domains",
                         "mobile.yaml")
        ):
            pytest.skip("mobile.yaml not installed")
        scope = {
            "path": _fixture("rn-sample"),
            "framework": "react-native",
            "domain": "mobile",
        }
        load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
        )
        events = _read_events(trace_on)
        ext = [
            e["attrs"]
            for e in events
            if e["event"] == "external_skills_resolution"
        ]
        assert ext, (
            f"expected external_skills_resolution event, got events: "
            f"{[e['event'] for e in events]}"
        )
        # `browser` is bare-name (no slash).
        forms = [e.get("form") for e in ext]
        assert "bare-name" in forms

    def test_disabled_emits_nothing(self, trace_off):
        from jarfis.compose.skills import load_skills_for_agent
        home = os.path.expanduser("~")
        claude_dir = os.environ.get("CLAUDE_DIR", os.path.join(home, ".claude"))
        if not os.path.isfile(
            os.path.join(claude_dir, "commands", "jarfis", "domains",
                         "mobile.yaml")
        ):
            pytest.skip("mobile.yaml not installed")
        scope = {
            "path": _fixture("rn-sample"),
            "framework": "react-native",
            "domain": "mobile",
        }
        load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
        )
        # JARFIS_TRACE=0 → no events recorded at all.
        events = _read_events(trace_off)
        assert events == [], (
            f"JARFIS_TRACE=0 must be no-op; got events: "
            f"{[e['event'] for e in events]}"
        )


# ── Disabled-path performance contract ──────────────────────────────


class TestDisabledNoopContract:
    """Belt-and-suspenders: no event family writes to disk when the env
    flag is unset (the M6 spec calls this the "micro-overhead only"
    invariant). Each detect/parse/skill-load path is exercised and the
    trace file must remain unwritten."""

    def test_detect_noop(self, trace_off):
        from jarfis.domain import detect
        detect(_fixture("tauri-sample"))
        assert not os.path.exists(trace_off)

    def test_work_args_noop(self, trace_off):
        from jarfis.work_args import parse_work_args
        parse_work_args("--domain desktop")
        assert not os.path.exists(trace_off)


# ── context7_query_emitted (B15, v4.1.1) ────────────────────────────


class TestContext7Telemetry:
    """7th telemetry event — Context7 MCP query lifecycle (ADR-0005 §2.7).

    The :class:`ResearchSession.emit` method routes through
    :func:`jarfis.trace.log_event` when no explicit telemetry callable
    is injected; this is the production path used by Phase 4 sub-agents.
    Tests pin the on/off behavior end-to-end so the trace contract
    matches the prior 6 events.
    """

    def test_emits_on_real_call(self, trace_on):
        from jarfis.compose.context7_research import ResearchSession

        s = ResearchSession()
        s.emit(
            library_id="/facebook/react-native-website",
            query="navigation API",
            source="hint",
            tier_used=1,
        )
        events = _read_events(trace_on)
        kinds = [e["event"] for e in events]
        assert "context7_query_emitted" in kinds, (
            f"context7_query_emitted not present, got: {kinds}"
        )
        ev = next(e for e in events if e["event"] == "context7_query_emitted")
        attrs = ev["attrs"]
        assert attrs["library_id"] == "/facebook/react-native-website"
        assert attrs["query"] == "navigation API"
        assert attrs["source"] == "hint"
        assert attrs["tier_used"] == 1
        assert attrs["cache_hit"] is False
        assert attrs["skill_pre_check_blocked"] is False

    def test_emits_with_cache_hit_flag(self, trace_on):
        from jarfis.compose.context7_research import ResearchSession

        s = ResearchSession()
        s.emit(
            library_id="/vercel/next.js",
            query="middleware",
            source="hint",
            tier_used=1,
            cache_hit=True,
        )
        events = _read_events(trace_on)
        ev = next(e for e in events if e["event"] == "context7_query_emitted")
        assert ev["attrs"]["cache_hit"] is True

    def test_emits_with_skill_blocked_flag(self, trace_on):
        from jarfis.compose.context7_research import ResearchSession

        s = ResearchSession()
        s.emit(
            library_id="/facebook/react-native-website",
            query="setState in onScroll",
            source="hint",
            tier_used=1,
            skill_pre_check_blocked=True,
        )
        events = _read_events(trace_on)
        ev = next(e for e in events if e["event"] == "context7_query_emitted")
        assert ev["attrs"]["skill_pre_check_blocked"] is True

    def test_emits_autonomous_source(self, trace_on):
        from jarfis.compose.context7_research import ResearchSession

        s = ResearchSession()
        s.emit(
            library_id="/some/community-lib",
            query="basic usage",
            source="autonomous",
            tier_used=3,
        )
        events = _read_events(trace_on)
        ev = next(e for e in events if e["event"] == "context7_query_emitted")
        assert ev["attrs"]["source"] == "autonomous"
        assert ev["attrs"]["tier_used"] == 3

    def test_noop_when_trace_disabled(self, trace_off):
        from jarfis.compose.context7_research import ResearchSession

        s = ResearchSession()
        s.emit(
            library_id="/x/y",
            query="q",
            source="hint",
            tier_used=1,
        )
        # JARFIS_TRACE=0 → no file written.
        assert not os.path.exists(trace_off)
