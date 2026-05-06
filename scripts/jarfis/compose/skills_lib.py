"""Compose skill loading primitives — extracted from ``jarfis.domain``.

v4.1 (M2.12, ADR-0002): the helpers below are the v4 canonical entry
points for compose-time skill resolution. ``compose/skills.py`` and the
new tests should import from here instead of ``jarfis.domain``. For
backward compatibility ``jarfis.domain`` continues to re-export the
same names so external callers (e.g. ``jarfis_cli.py domain compose``)
keep working without touching call sites.

The functions are thin re-exports today; once ``domain.py`` is split
into ``detect/list/scaffold/install`` slices (M3+), the implementation
will migrate here verbatim and ``domain.py`` will become the consumer.
"""

# NOTE: Importing from ``jarfis.domain`` directly creates a cycle when
# ``compose.skills`` is first reached during package init via
# ``jarfis.domain``-side compose() calls. Use lazy module-attr access
# at call time to avoid the cycle while still presenting a stable
# import surface to downstream callers.

from .. import domain as _domain  # noqa: E402  (needed for re-export)


# ── Constants ─────────────────────────────────────────────────────────

MAX_SKILL_FILE_SIZE = _domain.MAX_SKILL_FILE_SIZE
DOMAIN_NAME_RE = _domain.DOMAIN_NAME_RE
SKILL_NAME_RE = _domain.SKILL_NAME_RE


# ── Public API (v4 compose path) ──────────────────────────────────────

def estimate_tokens(text):
    """CJK-aware token estimator (delegates to v3 bridge — to be inlined
    in a future cleanup)."""
    return _domain.estimate_tokens(text)


def resolve_skill_path(domain_name, skill_name, domains_dir=None):
    """Public alias for the validated flat-first skill path resolver."""
    return _domain._resolve_skill_path(domain_name, skill_name, domains_dir)


def load_skills_for_role(domain_name, role_name, domains_dir=None,
                         max_skill_tokens=None):
    """Compose-time skill loader for a single role. Emits the same
    triple ``(loaded, truncated, skills_text)`` that the v3 bridge
    used to expose."""
    return _domain.load_skills_for_role(
        domain_name, role_name, domains_dir, max_skill_tokens
    )


def load_domain_yaml(domain_name, domains_dir=None):
    """Public alias for ``_load_domain_yaml`` — useful when callers
    need to inspect ``max_skill_tokens`` or roles directly."""
    return _domain._load_domain_yaml(domain_name, domains_dir)


# Internal alias kept private (leading underscore) for ``compose.skills``
# which previously imported it from ``..domain``.
_resolve_skill_path = resolve_skill_path
_load_domain_yaml = load_domain_yaml


__all__ = [
    "MAX_SKILL_FILE_SIZE",
    "DOMAIN_NAME_RE",
    "SKILL_NAME_RE",
    "estimate_tokens",
    "resolve_skill_path",
    "load_skills_for_role",
    "load_domain_yaml",
]
