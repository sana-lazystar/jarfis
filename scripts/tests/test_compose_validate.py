"""Regression test for ``compose --validate`` persona integrity (C1.7).

ADR-0001 §3.4 mandates a build-time gate that fails when any persona
referenced from a domain pack does not match a disk file under
``agents/jarfis/personas/``. This module enforces that gate by walking
all ``commands/jarfis/domains/*.yaml`` files and asserting every
``roles.{plan,design,implement,review}[].persona`` value resolves to
an actual ``.md`` file. Once green, this test permanently blocks the
``senior-*`` dangling-reference regression that motivated v4.1's M2
consolidation pass.

The check runs against the live ``~/.claude`` tree (the same tree that
``jarfis_cli.py compose`` reads) so it catches ad-hoc edits without
needing a fixture mirror. Because the source of truth is the live
filesystem, the test is intentionally read-only.
"""

import os
import re

import pytest
import yaml


CLAUDE_DIR = os.path.expanduser("~/.claude")
DOMAINS_DIR = os.path.join(CLAUDE_DIR, "commands", "jarfis", "domains")
PERSONAS_DIR = os.path.join(CLAUDE_DIR, "agents", "jarfis", "personas")


def _domain_yaml_files():
    """Yield absolute paths to every domain pack yaml (excluding _schema)."""
    if not os.path.isdir(DOMAINS_DIR):
        return []
    out = []
    for fname in sorted(os.listdir(DOMAINS_DIR)):
        if fname.startswith("_") or not fname.endswith(".yaml"):
            continue
        out.append(os.path.join(DOMAINS_DIR, fname))
    return out


def _all_persona_refs(yaml_path):
    """Return a list of ``(phase, persona)`` tuples extracted from a
    single domain pack file. Skips entries with empty/missing persona."""
    with open(yaml_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    refs = []
    for phase in ("plan", "design", "implement", "review"):
        for role in (config.get("roles") or {}).get(phase) or []:
            persona = role.get("persona", "")
            if persona:
                refs.append((phase, persona))
    return refs


def _persona_file_exists(persona):
    return os.path.isfile(os.path.join(PERSONAS_DIR, f"{persona}.md"))


# ── Tests ─────────────────────────────────────────────────────────────


class TestDomainsDirPresent:
    def test_domains_dir_exists(self):
        assert os.path.isdir(DOMAINS_DIR), \
            f"Domains dir missing: {DOMAINS_DIR}"

    def test_personas_dir_exists(self):
        assert os.path.isdir(PERSONAS_DIR), \
            f"Personas dir missing: {PERSONAS_DIR}"

    def test_at_least_one_domain_yaml(self):
        assert len(_domain_yaml_files()) >= 1, \
            "No domain pack yaml files discovered"


class TestNoSeniorReferences:
    """ADR-0001 §3.3: no ``senior-`` persona prefix may remain in any
    domain pack yaml. Failure here means the M2 consolidation pass
    regressed."""

    @pytest.mark.parametrize("yaml_path", _domain_yaml_files())
    def test_yaml_has_no_senior_prefix(self, yaml_path):
        for phase, persona in _all_persona_refs(yaml_path):
            assert not persona.startswith("senior-"), (
                f"{os.path.basename(yaml_path)} roles.{phase} still "
                f"references {persona!r} (senior- prefix removed in v4.1)"
            )


class TestPersonasResolveOnDisk:
    """ADR-0001 §3.4: every persona referenced from a domain pack must
    exist as ``agents/jarfis/personas/{stem}.md``. Without this gate,
    ``jarfis_cli.py compose`` silently degrades when a yaml drifts."""

    @pytest.mark.parametrize("yaml_path", _domain_yaml_files())
    def test_all_personas_have_disk_files(self, yaml_path):
        missing = []
        for phase, persona in _all_persona_refs(yaml_path):
            if not _persona_file_exists(persona):
                missing.append(f"  {phase}: {persona}")
        assert not missing, (
            f"{os.path.basename(yaml_path)} references personas with "
            f"no disk file:\n" + "\n".join(missing)
        )


class TestComposeValidateGate:
    """Sanity check: the personas dir contains the canonical 9 base
    personas (post-M1 absorption). If any of these are missing, the
    parametrized test above will surface the breakage with a precise
    message; this test gives a single-line summary upfront."""

    EXPECTED_BASE_PERSONAS = {
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

    def test_nine_base_personas_present(self):
        present = {
            f[:-3] for f in os.listdir(PERSONAS_DIR) if f.endswith(".md")
        }
        missing = self.EXPECTED_BASE_PERSONAS - present
        assert not missing, f"Base personas missing on disk: {missing}"

    def test_no_lingering_senior_files(self):
        present = [
            f for f in os.listdir(PERSONAS_DIR) if f.startswith("senior-")
        ]
        assert not present, (
            f"Stray senior- persona files under {PERSONAS_DIR}: {present}"
        )
