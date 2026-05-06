"""Tests for jarfis.compose.context7_research — Context7 MCP integration helpers.

ADR-0005 (v4.1.1) defines the contract these tests pin down:

  * skill-hint parsing (Tier 1) — HTML-comment block extraction
  * autonomous decision tree (Tier 3) — official-org allowlist, score
    gate, snippet tie-break
  * versioned ID match (Tier 2) — Tech Stack version → versioned library ID
  * :class:`ResearchSession` — cost guard, cache, telemetry surface

The MCP tools themselves are *not* called from tests; the wrapper is
pure-Python logic. Telemetry is verified by injecting a list-collector
so the production trace.log_event path stays untouched.
"""

import os

import pytest

from jarfis.compose.context7_research import (
    DEFAULT_COST_GUARD,
    OFFICIAL_ORG_ALLOWLIST,
    CostGuardExceeded,
    ResearchSession,
    parse_skill_hint,
    select_library_id,
)


# ── Hint parsing (Tier 1) ──────────────────────────────────────────────


class TestParseSkillHint:
    def test_extracts_library_id_and_topics(self, tmp_path):
        skill = tmp_path / "react-native.md"
        skill.write_text(
            "<!-- jarfis:context7\n"
            "library_id: /facebook/react-native-website\n"
            "query_topics: [navigation, native modules, gradle]\n"
            "-->\n"
            "\n"
            "# React Native Expertise\n"
            "> blah blah\n"
        )
        hint = parse_skill_hint(str(skill))
        assert hint == {
            "library_id": "/facebook/react-native-website",
            "query_topics": ["navigation", "native modules", "gradle"],
        }

    def test_no_topics_returns_empty_list(self, tmp_path):
        skill = tmp_path / "x.md"
        skill.write_text(
            "<!-- jarfis:context7\n"
            "library_id: /vercel/next.js\n"
            "-->\n"
            "# X\n"
        )
        hint = parse_skill_hint(str(skill))
        assert hint == {
            "library_id": "/vercel/next.js",
            "query_topics": [],
        }

    def test_missing_library_id_returns_none(self, tmp_path):
        skill = tmp_path / "x.md"
        skill.write_text(
            "<!-- jarfis:context7\n"
            "query_topics: [foo, bar]\n"
            "-->\n"
        )
        assert parse_skill_hint(str(skill)) is None

    def test_no_block_returns_none(self, tmp_path):
        skill = tmp_path / "x.md"
        skill.write_text("# Just a skill, no hint\n")
        assert parse_skill_hint(str(skill)) is None

    def test_missing_file_returns_none(self, tmp_path):
        assert parse_skill_hint(str(tmp_path / "nope.md")) is None

    def test_empty_path_returns_none(self):
        assert parse_skill_hint("") is None
        assert parse_skill_hint(None) is None

    def test_first_block_wins_when_multiple(self, tmp_path):
        skill = tmp_path / "x.md"
        skill.write_text(
            "<!-- jarfis:context7\n"
            "library_id: /first/one\n"
            "-->\n"
            "<!-- jarfis:context7\n"
            "library_id: /second/two\n"
            "-->\n"
        )
        hint = parse_skill_hint(str(skill))
        assert hint["library_id"] == "/first/one"

    def test_extra_whitespace_tolerated(self, tmp_path):
        skill = tmp_path / "x.md"
        skill.write_text(
            "<!--   jarfis:context7   \n"
            "   library_id:   /vercel/next.js   \n"
            "   query_topics:  [a,  b ,c]\n"
            "-->\n"
        )
        hint = parse_skill_hint(str(skill))
        assert hint["library_id"] == "/vercel/next.js"
        assert hint["query_topics"] == ["a", "b", "c"]


# ── Autonomous decision tree (Tier 3) ──────────────────────────────────


def _candidate(library_id, *, source_reputation="High", benchmark_score=80,
               code_snippets=1000, versions=None):
    return {
        "library_id": library_id,
        "source_reputation": source_reputation,
        "benchmark_score": benchmark_score,
        "code_snippets": code_snippets,
        "versions": versions or [],
    }


class TestSelectLibraryId:
    def test_picks_highest_snippet_among_official(self):
        candidates = [
            _candidate("/facebook/react-native-website", code_snippets=1565, benchmark_score=81),
            _candidate("/facebook/react-native", code_snippets=443, benchmark_score=70),
            _candidate("/storybookjs/react-native", code_snippets=889, benchmark_score=76),
        ]
        # Both /facebook/* are in allowlist; storybookjs is not. Among
        # official, snippet count breaks tie → website wins.
        assert select_library_id(candidates) == "/facebook/react-native-website"

    def test_filters_low_reputation(self):
        candidates = [
            _candidate("/facebook/x", source_reputation="Low"),
            _candidate("/facebook/y", source_reputation="High"),
        ]
        assert select_library_id(candidates) == "/facebook/y"

    def test_filters_archive_token(self):
        candidates = [
            _candidate("/websites/reactnative-archive-2023", code_snippets=8000),
            _candidate("/facebook/react-native-website", code_snippets=1565),
        ]
        assert select_library_id(candidates) == "/facebook/react-native-website"

    def test_filters_score_below_threshold(self):
        candidates = [
            _candidate("/facebook/low", benchmark_score=37, code_snippets=10000),
            _candidate("/facebook/ok", benchmark_score=70, code_snippets=100),
        ]
        assert select_library_id(candidates) == "/facebook/ok"

    def test_all_filtered_returns_none(self):
        candidates = [
            _candidate("/x/old-archive", source_reputation="High"),
            _candidate("/y/deprecated", source_reputation="High"),
        ]
        assert select_library_id(candidates) is None

    def test_empty_candidates_returns_none(self):
        assert select_library_id([]) is None
        assert select_library_id(None) is None

    def test_falls_back_to_non_official_when_no_official(self):
        candidates = [
            _candidate("/community/maintained", benchmark_score=75, code_snippets=500),
        ]
        assert select_library_id(candidates) == "/community/maintained"

    def test_score_tiebreak_when_snippets_equal(self):
        candidates = [
            _candidate("/facebook/a", code_snippets=100, benchmark_score=70),
            _candidate("/facebook/b", code_snippets=100, benchmark_score=85),
        ]
        assert select_library_id(candidates) == "/facebook/b"

    def test_websites_namespace_recognized_via_allowlist_extension(self):
        """The official allowlist excludes 'websites'; tests that this
        falls through to the non-official pool path correctly."""
        candidates = [
            _candidate("/websites/react_dev", benchmark_score=73),
            _candidate("/facebook/react", benchmark_score=85),
        ]
        # /facebook is official → picks facebook even though websites is High.
        assert select_library_id(candidates) == "/facebook/react"

    def test_custom_allowlist(self):
        candidates = [
            _candidate("/myorg/lib", benchmark_score=70),
            _candidate("/facebook/lib", benchmark_score=70),
        ]
        chosen = select_library_id(
            candidates, allowlist=frozenset({"myorg"})
        )
        assert chosen == "/myorg/lib"


# ── Versioned ID (Tier 2) ──────────────────────────────────────────────


class TestVersionedId:
    def test_exact_version_match(self):
        candidates = [
            _candidate(
                "/facebook/react-native",
                versions=["v0.81.5", "v0.70.6"],
            ),
        ]
        chosen = select_library_id(candidates, scope_version="0.81.5")
        assert chosen == "/facebook/react-native/v0.81.5"

    def test_prefix_match(self):
        candidates = [
            _candidate(
                "/facebook/react-native",
                versions=["v0.81.5", "v0.70.6"],
            ),
        ]
        chosen = select_library_id(candidates, scope_version="0.81")
        assert chosen == "/facebook/react-native/v0.81.5"

    def test_no_match_returns_base(self):
        candidates = [
            _candidate(
                "/facebook/react-native",
                versions=["v0.81.5", "v0.70.6"],
            ),
        ]
        chosen = select_library_id(candidates, scope_version="0.99.0")
        assert chosen == "/facebook/react-native"

    def test_no_versions_published_returns_base(self):
        candidates = [
            _candidate("/vercel/next.js", versions=[]),
        ]
        chosen = select_library_id(candidates, scope_version="14.0.0")
        assert chosen == "/vercel/next.js"

    def test_v_prefix_normalization(self):
        candidates = [
            _candidate(
                "/facebook/react-native",
                versions=["v0.81.5"],
            ),
        ]
        # caller uses leading-v form
        chosen = select_library_id(candidates, scope_version="v0.81.5")
        assert chosen == "/facebook/react-native/v0.81.5"


# ── ResearchSession — cost guard ───────────────────────────────────────


class TestResearchSessionCostGuard:
    def test_default_cost_guard(self):
        s = ResearchSession()
        assert s.cost_guard == DEFAULT_COST_GUARD == 5

    def test_custom_cost_guard(self):
        s = ResearchSession(cost_guard=3)
        assert s.cost_guard == 3
        assert s.remaining == 3

    def test_records_under_guard(self):
        s = ResearchSession(cost_guard=3)
        s.record("/a/x", "q1", "docs1")
        s.record("/a/y", "q2", "docs2")
        assert s.calls_made == 2
        assert s.remaining == 1

    def test_record_at_guard_raises(self):
        s = ResearchSession(cost_guard=2)
        s.record("/a/x", "q1", "d1")
        s.record("/a/y", "q2", "d2")
        with pytest.raises(CostGuardExceeded):
            s.record("/a/z", "q3", "d3")

    def test_can_query_blocked_at_guard(self):
        s = ResearchSession(cost_guard=1)
        s.record("/a/x", "q1", "d1")
        assert s.can_query("/a/y", "q2") == "blocked"

    def test_cached_record_does_not_count(self):
        """Re-recording the same (library_id, query) overwrites the
        cached result without consuming another guard slot."""
        s = ResearchSession(cost_guard=2)
        s.record("/a/x", "q1", "d1")
        s.record("/a/x", "q1", "d1-updated")
        assert s.calls_made == 1
        assert s.cached("/a/x", "q1") == "d1-updated"


# ── ResearchSession — cache + classification ───────────────────────────


class TestResearchSessionCache:
    def test_cache_hit_classification(self):
        s = ResearchSession()
        s.record("/a/x", "q1", "docs")
        assert s.can_query("/a/x", "q1") == "cache"
        assert s.cached("/a/x", "q1") == "docs"

    def test_skill_blocked_classification(self):
        s = ResearchSession()
        assert s.can_query("/a/x", "q1", skill_blocked=True) == "skill_blocked"

    def test_fresh_query_classification(self):
        s = ResearchSession()
        assert s.can_query("/a/x", "q1") == "ok"

    def test_can_query_does_not_mutate(self):
        s = ResearchSession()
        s.can_query("/a/x", "q1")
        s.can_query("/a/x", "q1", skill_blocked=True)
        assert s.calls_made == 0
        assert s.cached("/a/x", "q1") is None

    def test_cache_isolation_per_query_string(self):
        s = ResearchSession()
        s.record("/a/x", "q1", "d1")
        # Same library, different query → not a cache hit
        assert s.can_query("/a/x", "q2") == "ok"


# ── ResearchSession — telemetry ────────────────────────────────────────


class TestResearchSessionTelemetry:
    def test_emits_on_real_call(self):
        events = []
        s = ResearchSession(telemetry=events.append)
        s.emit(
            library_id="/facebook/react-native-website",
            query="navigation",
            source="hint",
            tier_used=1,
        )
        assert len(events) == 1
        e = events[0]
        assert e["library_id"] == "/facebook/react-native-website"
        assert e["query"] == "navigation"
        assert e["source"] == "hint"
        assert e["tier_used"] == 1
        assert e["cache_hit"] is False
        assert e["skill_pre_check_blocked"] is False

    def test_emits_with_cache_hit_flag(self):
        events = []
        s = ResearchSession(telemetry=events.append)
        s.emit(
            library_id="/x/y",
            query="q",
            source="autonomous",
            tier_used=3,
            cache_hit=True,
        )
        assert events[0]["cache_hit"] is True

    def test_emits_with_skill_blocked_flag(self):
        events = []
        s = ResearchSession(telemetry=events.append)
        s.emit(
            library_id="/x/y",
            query="q",
            source="hint",
            tier_used=1,
            skill_pre_check_blocked=True,
        )
        assert events[0]["skill_pre_check_blocked"] is True

    def test_telemetry_failure_does_not_propagate(self):
        def boom(_):
            raise RuntimeError("disk full")

        s = ResearchSession(telemetry=boom)
        # Must not raise — telemetry is best-effort.
        s.emit(library_id="/a/b", query="q", source="hint", tier_used=1)


# ── OFFICIAL_ORG_ALLOWLIST sanity ──────────────────────────────────────


class TestAllowlist:
    def test_facebook_in_allowlist(self):
        assert "facebook" in OFFICIAL_ORG_ALLOWLIST

    def test_vuejs_in_allowlist(self):
        assert "vuejs" in OFFICIAL_ORG_ALLOWLIST

    def test_tauri_apps_in_allowlist(self):
        assert "tauri-apps" in OFFICIAL_ORG_ALLOWLIST

    def test_random_org_not_in_allowlist(self):
        assert "random-fork-12345" not in OFFICIAL_ORG_ALLOWLIST

    def test_allowlist_is_frozen(self):
        # frozenset prevents mutation at import time
        with pytest.raises(AttributeError):
            OFFICIAL_ORG_ALLOWLIST.add("malicious-org")
