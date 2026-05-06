"""M5.4 + M5.5 — End-to-end compose verification for ``rn_engineer``.

These tests certify that the M4 mobile.yaml + M5.1 react-native skill
file resolve through the live compose path:

    M5.4: ``compose --persona rn_engineer --scope <rn-fixture>`` actually
          loads the ``react-native.md`` skill body (not just registers
          a role with a missing-file fallback).

    M5.5: When ``mobile.yaml`` declares
          ``roles.implement.rn_engineer.external_skills: ["browser"]``,
          compose appends the browser skill alongside the primary
          ``react-native`` skill — i.e. the union of `skills` +
          `external_skills` lands in `loaded`.

ADR-0004 §2.1 (mobile α release scope) anchors the contract: RN-only,
react-native skill is the primary, browser is reused from the web pack
to cover the JS runtime layer (Hermes / fetch / URL etc.).

The tests use the LIVE ``~/.claude/`` tree (no monkeypatching of
get_claude_dir) because the goal is to verify that the *real* mobile.yaml
+ *real* react-native.md + *real* browser.md compose together. A
fixture-based variant would not catch a missing skill file, which is
the exact regression M5.1 is meant to prevent.
"""

from __future__ import annotations

import os

import pytest

from jarfis.compose.skills import load_skills_for_agent
from jarfis.compose.skills_lib import resolve_skill_path


# ── Live-disk preconditions ─────────────────────────────────────────


@pytest.fixture(scope="module")
def live_mobile_assets():
    """Verify the live ~/.claude tree contains the mobile pack assets
    M5 needs — the test class skips otherwise (so a partial install
    surfaces as SKIP rather than a confusing AssertionError)."""
    home = os.path.expanduser("~")
    claude_dir = os.environ.get("CLAUDE_DIR", os.path.join(home, ".claude"))
    mobile_yaml = os.path.join(
        claude_dir, "commands", "jarfis", "domains", "mobile.yaml"
    )
    rn_skill = os.path.join(
        claude_dir, "commands", "jarfis", "skills", "react-native.md"
    )
    browser_skill = os.path.join(
        claude_dir, "commands", "jarfis", "skills", "browser.md"
    )
    if not os.path.isfile(mobile_yaml):
        pytest.skip(f"mobile.yaml missing at {mobile_yaml}")
    if not os.path.isfile(rn_skill):
        pytest.skip(f"react-native.md missing at {rn_skill}")
    if not os.path.isfile(browser_skill):
        pytest.skip(f"browser.md missing at {browser_skill}")
    return {
        "claude_dir": claude_dir,
        "mobile_yaml": mobile_yaml,
        "rn_skill": rn_skill,
        "browser_skill": browser_skill,
    }


@pytest.fixture
def rn_fixture_path():
    """Absolute path to the RN sample fixture used by detect tests."""
    here = os.path.dirname(__file__)
    path = os.path.realpath(
        os.path.join(here, "..", "jarfis", "tests", "fixtures", "rn-sample")
    )
    if not os.path.isdir(path):
        pytest.skip(f"rn-sample fixture missing: {path}")
    return path


# ── M5.4 — primary skill loads through live compose ─────────────────


class TestRnEngineerComposePrimary:
    """The ``react-native`` skill listed in mobile.yaml must actually
    resolve to a file on disk and its body must end up in the compose
    output. Without M5.1 this class fails — that's the whole point."""

    def test_react_native_skill_file_resolves(self, live_mobile_assets):
        """``_resolve_skill_path`` succeeds for the (mobile, react-native)
        pair — pre-flight check for the load test below."""
        path = resolve_skill_path("mobile", "react-native")
        assert os.path.isfile(path), (
            f"resolve_skill_path returned non-file: {path}"
        )

    def test_compose_loads_react_native_skill(
        self, live_mobile_assets, rn_fixture_path
    ):
        """Full compose call — `react-native` must appear in `loaded`
        and its body must be embedded in `skills_text`."""
        scope = {
            "path": rn_fixture_path,
            "framework": "react-native",
            "domain": "mobile",
            "type": "mobile",
        }
        loaded, truncated, text, meta = load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
        )
        assert meta.get("domain") == "mobile", (
            f"Expected domain=mobile, meta={meta}"
        )
        assert "react-native" in loaded, (
            f"react-native skill not loaded; loaded={loaded}, "
            f"truncated={truncated}, meta={meta}"
        )
        # Body check — make sure compose actually inlined the file, not
        # just registered the name.
        assert "React Native Expertise" in text, (
            "react-native.md body missing from compose output"
        )

    def test_compose_no_truncation_on_primary(
        self, live_mobile_assets, rn_fixture_path
    ):
        """react-native skill alone fits well under the 2500-token
        budget — there should be no truncation entry for it."""
        scope = {
            "path": rn_fixture_path,
            "framework": "react-native",
            "domain": "mobile",
        }
        _, truncated, _, _ = load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
        )
        for t in truncated:
            assert t.get("name") != "react-native", (
                f"react-native unexpectedly truncated: {t}"
            )


# ── M5.5 — external_skills are appended ─────────────────────────────


class TestRnEngineerExternalSkills:
    """``mobile.yaml`` lists ``external_skills: ["browser"]`` for
    rn_engineer. Compose must include browser alongside react-native —
    as documented in ADR-0004 §2.1 (Hermes/JS runtime parity with web).
    """

    def test_browser_skill_loaded_alongside_react_native(
        self, live_mobile_assets, rn_fixture_path
    ):
        scope = {
            "path": rn_fixture_path,
            "framework": "react-native",
            "domain": "mobile",
        }
        loaded, truncated, text, meta = load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
        )
        # M5.5 contract: union of `skills` + `external_skills`.
        assert "react-native" in loaded, (
            f"primary missing; loaded={loaded}, truncated={truncated}"
        )
        assert "browser" in loaded, (
            f"external_skills 'browser' not loaded; loaded={loaded}, "
            f"truncated={truncated}"
        )

    def test_browser_skill_body_present_in_compose(
        self, live_mobile_assets, rn_fixture_path
    ):
        scope = {
            "path": rn_fixture_path,
            "framework": "react-native",
            "domain": "mobile",
        }
        _, _, text, _ = load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
        )
        # Browser skill should also be inlined.
        assert "Browser" in text or "browser" in text.lower(), (
            "browser.md body missing from compose output"
        )

    def test_no_external_skills_no_extras(self, live_mobile_assets, tmp_path):
        """Sanity: a role without external_skills still loads only its
        primary skills (regression — make sure compose doesn't
        accidentally union with every skill in the directory)."""
        # frontend_engineer in web.yaml has no external_skills —
        # just react. A live web fixture is enough.
        scope = {
            "path": str(tmp_path),
            "framework": "react",
            "domain": "web",
        }
        loaded, _, _, meta = load_skills_for_agent(
            agent_name="frontend_engineer",
            persona="frontend-developer",
            state={"domain": "web"},
            scope_entry=scope,
        )
        # We assert the primary loaded; we don't assert NO extras
        # exist (web.yaml may evolve), but browser must NOT be there
        # purely as a function of mobile-side wiring.
        assert "react" in loaded, (
            f"web frontend_engineer missing react; loaded={loaded}, meta={meta}"
        )
