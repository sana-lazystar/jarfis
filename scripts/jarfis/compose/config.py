"""agent-composition.yaml loader + validator.

Only syntactic + semantic validation happens here. Path resolution,
persona file discovery, and file reads live in resolver/reader/__main__.
"""

import os
import yaml

from .errors import ConfigError
from .models import AgentConfig, ContextEntry


_VALID_SCOPE = frozenset({"per-project", "work-wide"})
_VALID_MODEL = frozenset({"sonnet", "opus", "haiku"})
_VALID_BASE = frozenset({"project", "all-projects", "docs", "org", "org_wiki"})
_VALID_IMPORTANCE = frozenset({"required", "recommended", "optional"})


def load_composition(yaml_path):
    """Load and validate agent-composition.yaml.

    Returns:
        dict[str, AgentConfig] keyed by agent name (order preserved).

    Raises:
        ConfigError: file missing, YAML malformed, or schema violated.
    """
    if not os.path.isfile(yaml_path):
        raise ConfigError(f"agent-composition.yaml not found: {yaml_path}")

    try:
        with open(yaml_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error in {yaml_path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"Top-level must be a mapping: {yaml_path}")

    agents_raw = raw.get("agents")
    if not isinstance(agents_raw, dict) or not agents_raw:
        raise ConfigError(f"Missing or empty `agents:` section: {yaml_path}")

    result = {}
    for name, entry in agents_raw.items():
        if not isinstance(name, str) or not name:
            raise ConfigError(f"Agent name must be non-empty string: {name!r}")
        if not isinstance(entry, dict):
            raise ConfigError(f"Agent `{name}` must be a mapping")
        result[name] = _build_agent_config(name, entry, yaml_path)

    return result


def load_extra_skills_by_framework(yaml_path):
    """Load the optional `extra_skills_by_framework:` section.

    Returns a dict whose keys are either:
        * a plain framework string (``"react"``)        — v4.0 behavior, matches any domain.
        * a ``(framework, domain)`` 2-tuple             — v4.1 (M4.4, ADR-0003 §4),
          domain-specific. Tuple wins over the string fallback when
          both are present for the same framework.

    YAML can't express tuple keys natively, so v4.1 supports an
    ``framework@domain`` string syntax that we normalize to a tuple
    on load. Missing section yields an empty dict. Invalid shape
    raises ConfigError.

    Example::

        extra_skills_by_framework:
          vue:                 [vue]                     # any domain
          react:               [react, browser]          # any domain
          react@web:           [react, browser]          # web-specific
          react-native@mobile: [react-native]            # mobile-specific
          tauri@desktop:       [tauri-backend, rust]     # desktop-specific

    Used by ``compose/skills.py`` as step 3 of the 4-stage fallback chain
    (system-spec §5.5). Step 4 delegates to v3 ``domain.yaml roles[].skills``.
    """
    if not os.path.isfile(yaml_path):
        raise ConfigError(f"agent-composition.yaml not found: {yaml_path}")

    try:
        with open(yaml_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error in {yaml_path}: {e}") from e

    section = (raw or {}).get("extra_skills_by_framework")
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ConfigError(
            f"`extra_skills_by_framework` must be a mapping "
            f"(got {type(section).__name__}) [{yaml_path}]"
        )

    result = {}
    for fw, skills in section.items():
        if not isinstance(fw, str) or not fw:
            raise ConfigError(
                f"extra_skills_by_framework: framework name must be non-empty "
                f"string (got {fw!r}) [{yaml_path}]"
            )
        if not isinstance(skills, list) or not all(
            isinstance(s, str) and s for s in skills
        ):
            raise ConfigError(
                f"extra_skills_by_framework[{fw}]: must be list[str] "
                f"(got {skills!r}) [{yaml_path}]"
            )
        # M4.4: ``framework@domain`` syntax → 2-tuple key.
        if "@" in fw:
            parts = fw.split("@", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ConfigError(
                    f"extra_skills_by_framework: malformed key {fw!r} — "
                    f"expected `framework@domain` [{yaml_path}]"
                )
            key = (parts[0], parts[1])
        else:
            key = fw
        result[key] = tuple(skills)
    return result


def validate_composition(raw):
    """Validate a pre-loaded mapping. Raises ConfigError on any violation.

    Used by tests that want to inject yaml dict directly.
    """
    if not isinstance(raw, dict):
        raise ConfigError("Top-level must be a mapping")
    agents_raw = raw.get("agents")
    if not isinstance(agents_raw, dict) or not agents_raw:
        raise ConfigError("Missing or empty `agents:` section")
    for name, entry in agents_raw.items():
        _build_agent_config(name, entry, "<memory>")


def _build_agent_config(name, entry, yaml_path):
    """Build a validated AgentConfig (raises ConfigError on violation)."""
    persona = entry.get("persona")
    if not isinstance(persona, str) or not persona:
        raise ConfigError(
            f"agent `{name}`: `persona` is required (string) [{yaml_path}]"
        )

    scope = entry.get("scope")
    if scope not in _VALID_SCOPE:
        raise ConfigError(
            f"agent `{name}`: `scope` must be one of {sorted(_VALID_SCOPE)} "
            f"(got {scope!r}) [{yaml_path}]"
        )

    model = entry.get("model")
    if model is not None and model not in _VALID_MODEL:
        raise ConfigError(
            f"agent `{name}`: `model` must be one of {sorted(_VALID_MODEL)} "
            f"or omitted (got {model!r}) [{yaml_path}]"
        )

    skills_from_domain = entry.get("skills_from_domain", False)
    if not isinstance(skills_from_domain, bool):
        raise ConfigError(
            f"agent `{name}`: `skills_from_domain` must be bool "
            f"(got {type(skills_from_domain).__name__}) [{yaml_path}]"
        )

    context_raw = entry.get("context", []) or []
    if not isinstance(context_raw, list):
        raise ConfigError(
            f"agent `{name}`: `context` must be a list (got "
            f"{type(context_raw).__name__}) [{yaml_path}]"
        )

    context_entries = []
    for idx, ctx in enumerate(context_raw):
        context_entries.append(_build_context_entry(name, idx, ctx, scope, yaml_path))

    return AgentConfig(
        name=name,
        persona=persona,
        scope=scope,
        model=model,
        skills_from_domain=skills_from_domain,
        context=tuple(context_entries),
    )


def _build_context_entry(agent_name, idx, ctx, scope, yaml_path):
    """Build a validated ContextEntry, checking scope↔base semantic rules."""
    if not isinstance(ctx, dict):
        raise ConfigError(
            f"agent `{agent_name}` context[{idx}]: must be a mapping "
            f"[{yaml_path}]"
        )

    base = ctx.get("base")
    if base not in _VALID_BASE:
        raise ConfigError(
            f"agent `{agent_name}` context[{idx}]: `base` must be one of "
            f"{sorted(_VALID_BASE)} (got {base!r}) [{yaml_path}]"
        )

    path = ctx.get("path")
    if not isinstance(path, str) or not path:
        raise ConfigError(
            f"agent `{agent_name}` context[{idx}]: `path` is required (string) "
            f"[{yaml_path}]"
        )

    sections = ctx.get("sections")
    if sections is not None:
        if not isinstance(sections, list) or not all(
            isinstance(s, str) and s for s in sections
        ):
            raise ConfigError(
                f"agent `{agent_name}` context[{idx}]: `sections` must be "
                f"list[str] or omitted [{yaml_path}]"
            )

    optional = ctx.get("optional", True)
    if not isinstance(optional, bool):
        raise ConfigError(
            f"agent `{agent_name}` context[{idx}]: `optional` must be bool "
            f"[{yaml_path}]"
        )

    importance = ctx.get("importance", "recommended")
    if importance not in _VALID_IMPORTANCE:
        raise ConfigError(
            f"agent `{agent_name}` context[{idx}]: `importance` must be one "
            f"of {sorted(_VALID_IMPORTANCE)} (got {importance!r}) [{yaml_path}]"
        )

    # Semantic scope ↔ base compatibility
    if scope == "per-project" and base == "all-projects":
        raise ConfigError(
            f"agent `{agent_name}` context[{idx}]: per-project scope cannot "
            f"use base=all-projects (logical conflict) [{yaml_path}]"
        )
    if scope == "work-wide" and base == "project":
        raise ConfigError(
            f"agent `{agent_name}` context[{idx}]: work-wide scope cannot "
            f"use base=project (logical conflict — use all-projects) "
            f"[{yaml_path}]"
        )

    return ContextEntry(
        base=base,
        path=path,
        sections=tuple(sections) if sections else None,
        optional=optional,
        importance=importance,
    )
