"""M4.3 + M4.4 — compose per-scope domain consumption + tuple keys
in ``extra_skills_by_framework``.

ADR-0003 §2.1 / §2.2:
    * ``load_skills_for_agent`` must consult ``scope_entry["domain"]``
      first, then fall back to ``state.domain`` (legacy v4.0.x), then
      surface ``meta["no_domain"]``.
    * ``extra_skills_by_framework`` keys may be either a plain
      framework string (current v4.0 behavior) OR a ``(framework,
      domain)`` 2-tuple. The tuple form takes precedence when both
      are configured for the same framework. This lets us register
      ``("react-native", "mobile") → ["react-native"]`` without
      polluting plain ``react`` entries.

Both behaviors land in ``compose/skills.py``; the tests here drive the
implementation TDD-style.
"""

import os
import textwrap

import pytest
import yaml

from jarfis.compose import skills as skills_mod
from jarfis.compose.skills import load_skills_for_agent


# ── shared fixture ──────────────────────────────────────────────────


@pytest.fixture
def domain_env(tmp_path, monkeypatch):
    """Build a minimal ``.claude/`` tree with web + mobile yaml + flat
    skill files.  Mobile yaml mirrors the M4.6 production shape so
    ``rn_engineer`` resolves end-to-end."""
    base = tmp_path / ".claude"
    domains_dir = base / "commands" / "jarfis" / "domains"
    domains_dir.mkdir(parents=True)

    flat_skills = base / "commands" / "jarfis" / "skills"
    flat_skills.mkdir(parents=True)
    for skill_name in (
        "react", "nodejs", "browser", "react-native"
    ):
        (flat_skills / f"{skill_name}.md").write_text(
            f"# {skill_name}\n{skill_name} expertise.\n"
        )

    web_yaml = {
        "schema_version": 2,
        "domain": {"name": "web", "display_name": "Web"},
        "roles": {
            "implement": [
                {
                    "name": "frontend_engineer",
                    "persona": "frontend-developer",
                    "skills": ["react"],
                    "model": "sonnet",
                    "commit_prefix": "FE",
                    "required": True,
                },
            ],
        },
    }
    # NOTE: We use ``react`` (not ``react-native``) here because the
    # flat skill loader resolves against the LIVE
    # ``~/.claude/commands/jarfis/skills/`` directory — the fixture's
    # tmp_path skill files are not consulted by ``_resolve_skill_path``.
    # ``react-native.md`` lands in M5, not M4. The substantive coverage
    # (per-scope domain priority + tuple keys) is independent of the
    # specific skill name.
    mobile_yaml = {
        "schema_version": 2,
        "domain": {"name": "mobile", "display_name": "Mobile (RN)"},
        "roles": {
            "implement": [
                {
                    "name": "rn_engineer",
                    "persona": "frontend-developer",
                    "skills": ["react"],          # placeholder until M5
                    "external_skills": ["browser"],
                    "model": "sonnet",
                    "commit_prefix": "RN",
                    "required": True,
                },
            ],
        },
    }
    (domains_dir / "web.yaml").write_text(yaml.dump(web_yaml, allow_unicode=True))
    (domains_dir / "mobile.yaml").write_text(
        yaml.dump(mobile_yaml, allow_unicode=True)
    )

    monkeypatch.setenv("CLAUDE_DIR", str(base))
    monkeypatch.setattr(
        "jarfis.utils.get_claude_dir", lambda: str(base)
    )
    return str(base / "commands" / "jarfis")


# ── M4.3 — per-scope domain consumption ─────────────────────────────


class TestPerScopeDomainPriority:
    def test_scope_domain_overrides_state_domain(self, tmp_path, domain_env):
        """scope[i].domain="mobile" must win over state.domain="web"."""
        scope = {"path": str(tmp_path), "framework": "react-native",
                 "domain": "mobile"}
        loaded, truncated, text, meta = load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "web"},  # legacy fallback should NOT win
            scope_entry=scope,
        )
        # Substantive assertion: scope.domain drove the load to mobile,
        # not state.domain="web". (Whether the actual react-native skill
        # file resolves on disk is M5 territory; here we only certify
        # the dispatch chose the right domain.yaml.)
        assert meta.get("domain") == "mobile", (
            f"Expected scope.domain='mobile' to win, meta={meta}"
        )

    def test_state_domain_fallback_when_scope_missing(self, tmp_path, domain_env):
        """No scope.domain → fall back to state.domain (v4.0.x compat)."""
        scope = {"path": str(tmp_path), "framework": "react"}
        loaded, _, _, meta = load_skills_for_agent(
            agent_name="frontend_engineer",
            persona="frontend-developer",
            state={"domain": "web"},
            scope_entry=scope,
        )
        assert meta.get("domain") == "web", (
            f"state.domain='web' should be used, meta={meta}"
        )

    def test_no_domain_anywhere(self, tmp_path, domain_env):
        """Neither scope.domain nor state.domain → meta.no_domain=True."""
        loaded, _, _, meta = load_skills_for_agent(
            agent_name="frontend_engineer",
            persona="frontend-developer",
            state={},
            scope_entry={"path": str(tmp_path), "framework": "react"},
        )
        assert meta.get("no_domain") is True


# ── M4.4 — extra_skills_by_framework tuple keys ─────────────────────


class TestExtraSkillsByFrameworkTupleKeys:
    """``extra_skills_by_framework`` may be keyed by:

        * ``("react-native", "mobile")`` 2-tuple — most specific.
        * ``"react"``                  — plain string (current v4.0).

    Tuple form takes precedence; framework-only is the fallback. When
    both are absent the agent loads no framework extras.
    """

    def test_tuple_key_matches_framework_and_domain(self, tmp_path, domain_env):
        scope = {"path": str(tmp_path), "framework": "react-native",
                 "domain": "mobile"}
        loaded, truncated, text, meta = load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
            extra_skills_by_framework={
                ("react-native", "mobile"): ["browser"],
            },
        )
        # framework_extras should record the appended browser skill.
        extras = meta.get("framework_extras")
        assert extras is not None, f"No framework_extras meta: {meta}"
        # browser may also be in the role's external_skills, but tuple
        # extras should still register an entry. Our minimal mobile.yaml
        # in this fixture lists external_skills:["browser"], so the
        # tuple extra "browser" will be deduped — ext_truncated records
        # already_loaded. We assert appended OR already_loaded match.
        names_seen = set(extras.get("appended", []))
        for t in extras.get("truncated", []):
            names_seen.add(t.get("name"))
        assert "browser" in names_seen

    def test_string_key_still_works(self, tmp_path, domain_env):
        """Pre-M4.4 string keys must keep working (forward-compat)."""
        scope = {"path": str(tmp_path), "framework": "react"}
        loaded, _, _, meta = load_skills_for_agent(
            agent_name="frontend_engineer",
            persona="frontend-developer",
            state={"domain": "web"},
            scope_entry=scope,
            extra_skills_by_framework={
                "react": ["browser"],  # plain string key
            },
        )
        extras = meta.get("framework_extras")
        assert extras is not None
        assert "browser" in extras.get("appended", []) or any(
            t.get("name") == "browser"
            for t in extras.get("truncated", [])
        )

    def test_tuple_key_takes_precedence_over_string(self, tmp_path, domain_env):
        """When BOTH tuple and string match, tuple wins."""
        scope = {"path": str(tmp_path), "framework": "react-native",
                 "domain": "mobile"}
        loaded, _, _, meta = load_skills_for_agent(
            agent_name="rn_engineer",
            persona="frontend-developer",
            state={"domain": "mobile"},
            scope_entry=scope,
            extra_skills_by_framework={
                ("react-native", "mobile"): ["nodejs"],   # tuple
                "react-native": ["react"],                # string fallback
            },
        )
        extras = meta.get("framework_extras")
        assert extras is not None
        # The tuple value (nodejs) should drive extras, not the string
        # value (react). React is part of role.skills already (no — in
        # this fixture only react-native is in role.skills), so we
        # verify nodejs was the one considered.
        appended_or_truncated = set(extras.get("appended", [])) | {
            t.get("name") for t in extras.get("truncated", [])
        }
        assert "nodejs" in appended_or_truncated, (
            f"tuple key should drive extras, got {extras}"
        )
        # The plain-string value MUST NOT be used when the tuple form
        # matches — react should not appear.
        assert "react" not in appended_or_truncated

    def test_tuple_no_match_falls_back_to_string(self, tmp_path, domain_env):
        """Different domain → tuple miss → string fallback applies."""
        # Tuple registered for ("react", "mobile") but scope has
        # domain="web", so the tuple miss-matches; the plain
        # ``react`` string key wins.
        scope = {"path": str(tmp_path), "framework": "react", "domain": "web"}
        loaded, _, _, meta = load_skills_for_agent(
            agent_name="frontend_engineer",
            persona="frontend-developer",
            state={"domain": "web"},
            scope_entry=scope,
            extra_skills_by_framework={
                ("react", "mobile"): ["nodejs"],   # mismatched domain
                "react": ["browser"],              # this should win
            },
        )
        extras = meta.get("framework_extras")
        assert extras is not None
        appended_or_truncated = set(extras.get("appended", [])) | {
            t.get("name") for t in extras.get("truncated", [])
        }
        assert "browser" in appended_or_truncated
        assert "nodejs" not in appended_or_truncated

    def test_no_framework_no_extras(self, tmp_path, domain_env):
        scope = {"path": str(tmp_path), "domain": "web"}  # no framework
        loaded, _, _, meta = load_skills_for_agent(
            agent_name="frontend_engineer",
            persona="frontend-developer",
            state={"domain": "web"},
            scope_entry=scope,
            extra_skills_by_framework={"react": ["browser"]},
        )
        # No framework on scope → no extras to apply
        assert "framework_extras" not in meta


# ── M4.4 — YAML `framework@domain` syntax → tuple key ───────────────


class TestExtraSkillsLoaderTupleSyntax:
    """``load_extra_skills_by_framework`` must accept the v4.1
    ``framework@domain`` string syntax and normalize it to a tuple
    key in the returned dict, while keeping plain framework strings
    untouched (forward-compat with v4.0 yaml)."""

    def test_plain_string_keys(self, tmp_path):
        from jarfis.compose.config import load_extra_skills_by_framework
        path = tmp_path / "comp.yaml"
        path.write_text(textwrap.dedent("""\
            agents: {}
            extra_skills_by_framework:
              react: [react, browser]
              vue: [vue]
            """))
        result = load_extra_skills_by_framework(str(path))
        assert result["react"] == ("react", "browser")
        assert result["vue"] == ("vue",)

    def test_tuple_key_via_at_syntax(self, tmp_path):
        from jarfis.compose.config import load_extra_skills_by_framework
        path = tmp_path / "comp.yaml"
        path.write_text(textwrap.dedent("""\
            agents: {}
            extra_skills_by_framework:
              "react-native@mobile": [react-native]
              "tauri@desktop": [tauri-backend, rust]
              react: [react, browser]
            """))
        result = load_extra_skills_by_framework(str(path))
        assert result[("react-native", "mobile")] == ("react-native",)
        assert result[("tauri", "desktop")] == ("tauri-backend", "rust")
        # Plain string keys remain plain.
        assert result["react"] == ("react", "browser")

    def test_malformed_at_syntax_raises(self, tmp_path):
        from jarfis.compose.config import load_extra_skills_by_framework
        from jarfis.compose.errors import ConfigError
        path = tmp_path / "comp.yaml"
        path.write_text(textwrap.dedent("""\
            agents: {}
            extra_skills_by_framework:
              "@mobile": [react-native]
            """))
        with pytest.raises(ConfigError):
            load_extra_skills_by_framework(str(path))
