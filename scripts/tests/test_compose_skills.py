"""Tests for ``jarfis.compose.skills`` — M2.5 (Tech Stack auto-match) + M2.6
(PERSONA_TO_ROLE 9/9 mapping completion).

These tests cover the 4-stage fallback chain advertised by
``compose/skills.py``:

    1. project-profile.md ``## Active Skills`` bullets
    2. project-profile.md ``## Tech Stack`` auto-match  ← M2.5 (newly wired)
    3. ``extra_skills_by_framework[framework]``
    4. ``domain.yaml roles[].skills``

and the persona → role mapping table that gates step 4.
"""

import os
import textwrap

import pytest
import yaml

from jarfis.compose import skills as skills_mod
from jarfis.compose.skills import (
    PERSONA_TO_ROLE,
    _extract_tech_stack_skills,
    load_skills_for_agent,
)
# M2.12: skills_lib must expose the same primitives the compose path
# previously fetched from jarfis.domain.
from jarfis.compose import skills_lib as compose_skills_lib


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def domain_env(tmp_path, monkeypatch):
    """Build a minimal v4 layout under ``tmp_path``::

        tmp_path/.claude/commands/jarfis/domains/web.yaml
        tmp_path/.claude/commands/jarfis/domains/web/skills/{react,nodejs}.md
        tmp_path/.claude/commands/jarfis/skills/{react,nodejs,postgres}.md  (flat)

    Returns the ``commands/jarfis`` directory so callers can derive paths.
    """
    base = tmp_path / ".claude"
    domains_dir = base / "commands" / "jarfis" / "domains"
    domains_dir.mkdir(parents=True)

    # Flat skill dir (v4 preferred)
    flat_skills = base / "commands" / "jarfis" / "skills"
    flat_skills.mkdir(parents=True)
    for skill_name in ("react", "nodejs", "postgres", "express", "browser"):
        (flat_skills / f"{skill_name}.md").write_text(
            f"# {skill_name}\n{skill_name} expertise.\n"
        )

    # web.yaml — 9 personas covered across phases
    web_yaml = {
        "schema_version": 2,
        "min_core_version": "3.0.0",
        "domain": {"name": "web", "display_name": "Web"},
        "roles": {
            "plan": [
                {"persona": "product-owner", "skills": [], "model": "opus"},
                {"persona": "technical-architect", "skills": [], "model": "opus"},
            ],
            "design": [
                {"persona": "technical-architect", "skills": [], "model": "opus"},
                {"persona": "tech-lead", "skills": [], "model": "opus"},
                {"persona": "ux-designer", "skills": [], "model": "opus"},
            ],
            "implement": [
                {
                    "name": "backend_engineer",
                    "persona": "backend-developer",
                    "skills": ["nodejs"],
                    "model": "sonnet",
                    "commit_prefix": "BE",
                    "required": True,
                },
                {
                    "name": "frontend_engineer",
                    "persona": "frontend-developer",
                    "skills": ["react"],
                    "model": "sonnet",
                    "commit_prefix": "FE",
                    "required": True,
                },
                {
                    "name": "devops_engineer",
                    "persona": "devops-engineer",
                    "skills": ["nodejs"],
                    "model": "sonnet",
                    "commit_prefix": "Dev",
                    "required": False,
                },
            ],
            "review": [
                {"persona": "tech-lead", "skills": [], "model": "opus"},
                {"persona": "qa-engineer", "skills": [], "model": "opus"},
                {"persona": "security-engineer", "skills": [], "model": "opus"},
            ],
        },
        "max_skill_tokens": 2500,
        "rules": {"filter_by_tags": True, "always_include_untagged": True},
        "detect": {"indicators": []},
    }
    (domains_dir / "web.yaml").write_text(yaml.dump(web_yaml, allow_unicode=True))

    # Make `_get_domains_dir()` resolve to our tmp tree
    monkeypatch.setenv("CLAUDE_DIR", str(base))
    monkeypatch.setattr(
        "jarfis.utils.get_claude_dir", lambda: str(base)
    )

    return str(base / "commands" / "jarfis")


def _write_profile(scope_path, body):
    """Helper: write project-profile.md under ``<scope_path>/.jarfis-project/``."""
    proj_dir = os.path.join(scope_path, ".jarfis-project")
    os.makedirs(proj_dir, exist_ok=True)
    profile = os.path.join(proj_dir, "project-profile.md")
    with open(profile, "w", encoding="utf-8") as f:
        f.write(body)
    return profile


# ── M2.5 — Tech Stack auto-match (step 2) ─────────────────────────────


class TestExtractTechStackSkills:
    """``_extract_tech_stack_skills`` parses ``## Tech Stack`` bullets and
    normalizes them to skill stems matching the flat ``skills/`` dir."""

    def test_basic_react_postgres_match(self, tmp_path, domain_env):
        scope = str(tmp_path)
        _write_profile(scope, textwrap.dedent("""\
            # Project Profile

            ## Tech Stack
            - React 18
            - Vite
            - TypeScript
            - PostgreSQL

            ## Active Skills
            (none)
            """))
        profile = os.path.join(scope, ".jarfis-project", "project-profile.md")
        result = _extract_tech_stack_skills(profile)
        # React + PostgreSQL → react + postgres (Vite/TS have no flat skills)
        assert "react" in result
        assert "postgres" in result
        assert "vite" not in result
        assert "typescript" not in result

    def test_nodejs_normalization(self, tmp_path, domain_env):
        """``Node.js`` should normalize to ``nodejs`` (one of our skills)."""
        scope = str(tmp_path)
        _write_profile(scope, textwrap.dedent("""\
            ## Tech Stack
            - Node.js 22
            """))
        profile = os.path.join(scope, ".jarfis-project", "project-profile.md")
        result = _extract_tech_stack_skills(profile)
        assert "nodejs" in result

    def test_skips_unknown_technologies(self, tmp_path, domain_env):
        """Bullets not matching any flat skill must be silently dropped
        (not error out, not partial-match)."""
        scope = str(tmp_path)
        _write_profile(scope, textwrap.dedent("""\
            ## Tech Stack
            - Tailwind CSS
            - SomethingExotic 9.x
            """))
        profile = os.path.join(scope, ".jarfis-project", "project-profile.md")
        result = _extract_tech_stack_skills(profile)
        assert result == []  # neither has a flat skill

    def test_recognizes_asterisk_bullets(self, tmp_path, domain_env):
        """Both ``-`` and ``*`` bullets accepted."""
        scope = str(tmp_path)
        _write_profile(scope, textwrap.dedent("""\
            ## Tech Stack
            * React
            * PostgreSQL
            """))
        profile = os.path.join(scope, ".jarfis-project", "project-profile.md")
        result = _extract_tech_stack_skills(profile)
        assert "react" in result
        assert "postgres" in result

    def test_ignores_field_label_prefix(self, tmp_path, domain_env):
        """Bullets like ``- **Language**: TypeScript`` should still match
        on the value side (post-colon)."""
        scope = str(tmp_path)
        _write_profile(scope, textwrap.dedent("""\
            ## Tech Stack
            - **Runtime**: Node.js 22
            - **Database**: PostgreSQL 16
            - **Frontend**: React 18
            """))
        profile = os.path.join(scope, ".jarfis-project", "project-profile.md")
        result = _extract_tech_stack_skills(profile)
        assert "nodejs" in result
        assert "postgres" in result
        assert "react" in result

    def test_missing_section_returns_empty(self, tmp_path, domain_env):
        scope = str(tmp_path)
        _write_profile(scope, "# Empty profile\n")
        profile = os.path.join(scope, ".jarfis-project", "project-profile.md")
        assert _extract_tech_stack_skills(profile) == []

    def test_missing_file_returns_empty(self, tmp_path, domain_env):
        bogus = os.path.join(str(tmp_path), "nope.md")
        assert _extract_tech_stack_skills(bogus) == []


class TestStep2TechStackIntegration:
    """Step 2 fires only when step 1 (``## Active Skills``) is absent/empty.
    When step 2 produces hits they must be loaded with the same budget
    semantics as step 1."""

    def test_step2_loads_when_active_skills_empty(self, tmp_path, domain_env):
        scope = str(tmp_path)
        _write_profile(scope, textwrap.dedent("""\
            ## Tech Stack
            - PostgreSQL 16
            - Node.js 22
            """))

        loaded, truncated, text, meta = load_skills_for_agent(
            agent_name="backend_engineer",
            persona="backend-developer",
            state={"domain": "web"},
            scope_entry={"path": scope},
        )
        # Step 2 fires → loaded includes postgres (from Tech Stack)
        assert "tech_stack_match" in meta or "active_skills_override" in meta or loaded
        assert "postgres" in loaded
        assert "nodejs" in loaded

    def test_step1_takes_precedence_over_step2(self, tmp_path, domain_env):
        """When ``## Active Skills`` is present, step 2 must not fire."""
        scope = str(tmp_path)
        _write_profile(scope, textwrap.dedent("""\
            ## Tech Stack
            - PostgreSQL 16

            ## Active Skills
            - react
            """))

        loaded, truncated, text, meta = load_skills_for_agent(
            agent_name="frontend_engineer",
            persona="frontend-developer",
            state={"domain": "web"},
            scope_entry={"path": scope},
        )
        assert "active_skills_override" in meta
        assert "react" in loaded
        # Tech Stack postgres must NOT leak in when step 1 wins
        assert "postgres" not in loaded


# ── M2.6 — PERSONA_TO_ROLE 9/9 completion ─────────────────────────────


class TestPersonaToRoleMapping:
    EXPECTED_PERSONAS = {
        "product-owner",
        "technical-architect",
        "tech-lead",
        "ux-designer",
        "qa-engineer",
        "security-engineer",
        "devops-engineer",
        "frontend-developer",
        "backend-developer",
    }

    def test_all_nine_personas_mapped(self):
        """Every base persona under ``agents/jarfis/personas/`` must have a
        ``PERSONA_TO_ROLE`` entry so ``skills_from_domain: true`` paths
        never silently degrade with ``no_role_mapping``."""
        missing = self.EXPECTED_PERSONAS - set(PERSONA_TO_ROLE.keys())
        assert not missing, f"PERSONA_TO_ROLE missing personas: {missing}"

    def test_mapping_values_are_strings(self):
        for persona, role in PERSONA_TO_ROLE.items():
            assert isinstance(role, str) and role, \
                f"Mapping for {persona} must be a non-empty string"

    def test_no_role_mapping_meta_never_set_for_known_personas(
        self, tmp_path, domain_env
    ):
        """For each of the 9 base personas, ``load_skills_for_agent`` must
        not return ``meta['no_role_mapping']`` when domain is set."""
        for persona in self.EXPECTED_PERSONAS:
            _, _, _, meta = load_skills_for_agent(
                agent_name=persona,
                persona=persona,
                state={"domain": "web"},
                scope_entry={"path": str(tmp_path)},
            )
            assert "no_role_mapping" not in meta, \
                f"{persona} unexpectedly has no_role_mapping in meta"


# ── M2.12 — compose/skills_lib import surface ─────────────────────────


class TestComposeSkillsLib:
    """M2.12: ``compose/skills_lib.py`` is the canonical module the
    compose path imports v3-bridge helpers from. ``domain.py`` keeps
    those names exported for backward compat, but new code paths must
    not import from ``jarfis.domain`` directly."""

    def test_exports_token_helpers(self):
        assert hasattr(compose_skills_lib, "estimate_tokens")
        assert callable(compose_skills_lib.estimate_tokens)
        assert compose_skills_lib.estimate_tokens("hello world") > 0

    def test_exports_path_resolver(self):
        assert hasattr(compose_skills_lib, "resolve_skill_path")
        assert hasattr(compose_skills_lib, "_resolve_skill_path")
        # Public alias is the same callable as the underscore alias.
        assert (
            compose_skills_lib.resolve_skill_path
            is compose_skills_lib._resolve_skill_path
        )

    def test_exports_skill_loader(self):
        assert hasattr(compose_skills_lib, "load_skills_for_role")
        assert callable(compose_skills_lib.load_skills_for_role)

    def test_exports_constants(self):
        assert isinstance(compose_skills_lib.MAX_SKILL_FILE_SIZE, int)
        assert compose_skills_lib.MAX_SKILL_FILE_SIZE > 0
        assert compose_skills_lib.DOMAIN_NAME_RE is not None
        assert compose_skills_lib.SKILL_NAME_RE is not None

    def test_compose_skills_imports_from_skills_lib(self):
        """``compose/skills.py`` must source the v3-bridge primitives
        from ``skills_lib``, not from ``jarfis.domain`` directly. We
        assert this structurally by checking the resolved module of
        the imported names."""
        from jarfis.compose import skills as compose_skills_mod
        # The names the compose path uses are aliased into the module
        # namespace at import time. If they came from ``skills_lib``,
        # the underlying objects are identical to the lib's exports.
        assert (
            compose_skills_mod.estimate_tokens
            is compose_skills_lib.estimate_tokens
        )
        assert (
            compose_skills_mod._resolve_skill_path
            is compose_skills_lib._resolve_skill_path
        )
        assert (
            compose_skills_mod.load_skills_for_role
            is compose_skills_lib.load_skills_for_role
        )
