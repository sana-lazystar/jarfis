"""M4.7 — detect.indicators weighted scoring (ADR-0003 §2.6).

Replaces the old ``confidence = mean(matched_indicators)`` scoring with:

    confidence    = max(matched_indicators)
    matched_count = len(matched_indicators)

Sort key (highest priority first) becomes:
    (-confidence, -matched_count, domain_name)

so equal-confidence domains break the tie on which one matched MORE
indicators. Tauri-as-web vs Tauri-as-desktop case adds a multiplier:
when ``tauri.conf.json`` or ``src-tauri/`` is present, every desktop
indicator score is multiplied by 1.5x before comparison.

These tests live alongside ``test_dispatch.py`` (which still asserts
the high-conf Tauri case) so the M4.7 contract regression-protects
both code paths.
"""

import json
import os

import pytest
import yaml


FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "jarfis", "tests", "fixtures",
)


def _fixture(name):
    return os.path.abspath(os.path.join(FIXTURES_DIR, name))


# ── Tauri fixture must still hit ≥ 0.85 with new scoring ──────────────


class TestTauriSampleNewScoring:
    """Sanity: M3.1 Tauri fixture must keep its high-conf desktop result
    after M4.7 swaps mean→max with desktop tiebreaker."""

    def test_tauri_sample_max_scoring_hits_top_indicator(self):
        from jarfis.domain import detect
        result = detect(_fixture("tauri-sample"))
        assert result["matches"], "Tauri fixture must still yield a match"
        top = result["matches"][0]
        assert top["domain"] == "desktop"
        # Old scoring: mean(0.95, 0.95, 0.8, 0.7) = 0.85
        # New scoring: max(0.95, 0.95, 0.8, 0.7) = 0.95
        # 1.5x desktop tiebreaker keeps it ≥ 0.95 (clamped at 1.0).
        assert top["confidence"] >= 0.95, (
            f"max-scoring should bump Tauri to >=0.95, got {top['confidence']}"
        )

    def test_tauri_matched_count_exposed(self):
        """matched_count helps caller break confidence ties on quantity."""
        from jarfis.domain import detect
        result = detect(_fixture("tauri-sample"))
        top = result["matches"][0]
        assert "matched_indicators" in top, (
            "matches[*] must expose matched_indicators for tiebreaking"
        )
        assert top["matched_indicators"] >= 3


# ── Synthetic same-confidence different-count scenario ───────────────


class TestMatchedCountTiebreak:
    """When two domains share max confidence, the one matching MORE
    indicators wins. Builds a self-contained domains_dir to avoid
    depending on the live web/desktop yaml."""

    @pytest.fixture
    def domains_env(self, tmp_path):
        domains_dir = tmp_path / "domains"
        domains_dir.mkdir()
        # Domain A — 1 indicator at 0.9
        a_yaml = {
            "schema_version": 2,
            "domain": {"name": "alpha", "display_name": "Alpha"},
            "roles": {"implement": []},
            "detect": {
                "indicators": [
                    {"file": "alpha.cfg", "framework": "alpha", "confidence": 0.9},
                ]
            },
        }
        # Domain B — 3 indicators all at 0.9 (same max, more matches)
        b_yaml = {
            "schema_version": 2,
            "domain": {"name": "beta", "display_name": "Beta"},
            "roles": {"implement": []},
            "detect": {
                "indicators": [
                    {"file": "beta1.cfg", "framework": "beta", "confidence": 0.9},
                    {"file": "beta2.cfg", "framework": "beta", "confidence": 0.9},
                    {"file": "beta3.cfg", "framework": "beta", "confidence": 0.9},
                ]
            },
        }
        (domains_dir / "alpha.yaml").write_text(yaml.dump(a_yaml))
        (domains_dir / "beta.yaml").write_text(yaml.dump(b_yaml))
        return str(domains_dir)

    def test_more_matches_wins_at_same_confidence(self, tmp_path, domains_env):
        from jarfis.domain import detect
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "alpha.cfg").write_text("x")
        (proj / "beta1.cfg").write_text("x")
        (proj / "beta2.cfg").write_text("x")
        (proj / "beta3.cfg").write_text("x")

        result = detect(str(proj), domains_env)
        # Both have max=0.9; beta has 3 matched, alpha has 1.
        # Beta should rank #1.
        assert result["matches"][0]["domain"] == "beta", (
            f"matched_count tiebreak failed: {result['matches']}"
        )

    def test_actual_tie_still_emits_tie_flag(self, tmp_path, domains_env):
        """If matched_count is ALSO equal, ``tie=True`` is preserved."""
        from jarfis.domain import detect
        proj = tmp_path / "proj"
        proj.mkdir()
        # Only one of each domain's indicators present → both have
        # confidence=0.9 AND matched_count=1.
        (proj / "alpha.cfg").write_text("x")
        (proj / "beta1.cfg").write_text("x")
        result = detect(str(proj), domains_env)
        assert result["tie"] is True


# ── Tauri-as-desktop tiebreaker ──────────────────────────────────────


class TestTauriDesktopTiebreaker:
    """When ``tauri.conf.json`` / ``src-tauri/`` exists, desktop indicator
    scores are multiplied by 1.5x. This ensures Tauri projects that ALSO
    match a web framework (because ``package.json`` is present) still
    rank desktop above web."""

    @pytest.fixture
    def domains_env(self, tmp_path):
        """Mini web + desktop yaml that both can match the same project."""
        domains_dir = tmp_path / "domains"
        domains_dir.mkdir()
        web_yaml = {
            "schema_version": 2,
            "domain": {"name": "web", "display_name": "Web"},
            "roles": {"implement": []},
            "detect": {
                "indicators": [
                    {"file": "package.json", "key": "react",
                     "framework": "react", "confidence": 0.9},
                ]
            },
        }
        desktop_yaml = {
            "schema_version": 2,
            "domain": {"name": "desktop", "display_name": "Desktop"},
            "roles": {"implement": []},
            "detect": {
                "indicators": [
                    {"file": "tauri.conf.json", "framework": "tauri",
                     "confidence": 0.6},  # Lower than web's 0.9
                    {"file": "package.json", "key": "tauri",
                     "framework": "tauri-npm", "confidence": 0.5},
                ]
            },
        }
        (domains_dir / "web.yaml").write_text(yaml.dump(web_yaml))
        (domains_dir / "desktop.yaml").write_text(yaml.dump(desktop_yaml))
        return str(domains_dir)

    def test_tauri_marker_boosts_desktop(self, tmp_path, domains_env):
        """Project has react+tauri. Without tiebreaker desktop max=0.6
        and web max=0.9 → web wins. With 1.5x boost on desktop indicators
        when tauri marker present: 0.6 * 1.5 = 0.9 → still tie or desktop
        wins via matched_count (tauri has 2 indicators here)."""
        from jarfis.domain import detect
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18", "tauri": "^1"}})
        )
        (proj / "tauri.conf.json").write_text("{}")

        result = detect(str(proj), domains_env)
        domains_ranked = [m["domain"] for m in result["matches"]]
        # Desktop should rank at least equal to web; matched_count=2 vs 1
        # tiebreaks in desktop's favor.
        assert "desktop" in domains_ranked
        assert "web" in domains_ranked
        desktop_idx = domains_ranked.index("desktop")
        web_idx = domains_ranked.index("web")
        assert desktop_idx <= web_idx, (
            f"Tauri-marker tiebreaker should not let web outrank desktop: "
            f"{result['matches']}"
        )

    def test_no_tauri_marker_no_boost(self, tmp_path, domains_env):
        """Without ``tauri.conf.json`` / ``src-tauri/``, desktop scoring
        is unmodified — a plain react project should still rank web first."""
        from jarfis.domain import detect
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18"}})
        )
        result = detect(str(proj), domains_env)
        # Only web matches (desktop indicators all need files this project
        # doesn't have); ensure no spurious desktop score appears.
        domains_ranked = [m["domain"] for m in result["matches"]]
        assert "web" in domains_ranked
        if "desktop" in domains_ranked:
            assert domains_ranked.index("web") < domains_ranked.index("desktop")


# ── Confidence is now max, not mean — direct check ───────────────────


class TestMaxConfidenceScoring:
    @pytest.fixture
    def domains_env(self, tmp_path):
        domains_dir = tmp_path / "domains"
        domains_dir.mkdir()
        # Three indicators with very different confidences. mean=0.5;
        # max=0.9. The change matters at the 0.85 dispatch threshold
        # (work.md case 1 vs case 3).
        d_yaml = {
            "schema_version": 2,
            "domain": {"name": "delta", "display_name": "Delta"},
            "roles": {"implement": []},
            "detect": {
                "indicators": [
                    {"file": "high.cfg", "framework": "delta", "confidence": 0.9},
                    {"file": "mid.cfg", "framework": "delta", "confidence": 0.4},
                    {"file": "low.cfg", "framework": "delta", "confidence": 0.2},
                ]
            },
        }
        (domains_dir / "delta.yaml").write_text(yaml.dump(d_yaml))
        return str(domains_dir)

    def test_max_not_mean(self, tmp_path, domains_env):
        from jarfis.domain import detect
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "high.cfg").write_text("x")
        (proj / "mid.cfg").write_text("x")
        (proj / "low.cfg").write_text("x")
        result = detect(str(proj), domains_env)
        assert len(result["matches"]) == 1
        top = result["matches"][0]
        # Old (mean): (0.9+0.4+0.2)/3 = 0.5 — would NOT trip the 0.85 gate
        # New (max):  0.9 — TRIPS the 0.85 gate
        assert top["confidence"] >= 0.85, (
            f"max scoring should yield 0.9 (≥0.85), got {top['confidence']}"
        )


# ── M4.6/M4.7 — RN sample fixture lands as mobile high-conf ─────────


class TestRnSampleFixture:
    """Sanity test for the M4.6 mobile.yaml + the M4 RN testbed fixture
    (``scripts/jarfis/tests/fixtures/rn-sample/``).

    The fixture has 4 mobile indicators (package.json+react-native,
    metro.config.js, ios/Podfile, android/build.gradle) and zero web
    triggers, so detect must rank mobile first with confidence >= 0.85.
    """

    def test_rn_fixture_files_exist(self):
        for relpath in (
            "package.json",
            "metro.config.js",
            "ios/Podfile",
            "android/build.gradle",
        ):
            assert os.path.isfile(os.path.join(_fixture("rn-sample"), relpath)), (
                f"RN fixture missing {relpath}"
            )

    def test_detect_returns_mobile(self):
        from jarfis.domain import detect
        result = detect(_fixture("rn-sample"))
        assert result["matches"], "RN fixture must yield at least one match"
        # Mobile indicators dominate; mobile must rank #1.
        assert result["matches"][0]["domain"] == "mobile", (
            f"Expected mobile #1, got {[m['domain'] for m in result['matches']]}"
        )

    def test_rn_fixture_high_confidence(self):
        from jarfis.domain import detect
        result = detect(_fixture("rn-sample"))
        top = result["matches"][0]
        assert top["confidence"] >= 0.85, (
            f"RN fixture should hit ≥0.85, got {top['confidence']}"
        )

    def test_rn_fixture_matched_count(self):
        """At least 3 indicators (package.json+key, metro.config.js,
        ios/Podfile, android/build.gradle) should match."""
        from jarfis.domain import detect
        result = detect(_fixture("rn-sample"))
        top = result["matches"][0]
        assert top["matched_indicators"] >= 3
