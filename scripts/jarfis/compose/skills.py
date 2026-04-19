"""Bridge from v4 compose to v3 `domain.load_skills_for_role` (옵션 D).

v4.0 strategy:
    * agent_name → role_name via hardcoded table below (system-spec §5.5 step 4).
    * If state.domain is None, skip skill loading entirely.
    * If agent has no mapping (e.g. work-wide agents like technical-architect),
      skip as well — meta records the reason so __main__ can surface it.
    * Actual loading delegates to v3 `domain.load_skills_for_role` (옵션 D),
      so token budget / W1-1 / W1-3 rules stay identical.
    * Step 3 of the 4-stage fallback chain (system-spec §5.5): if
      `scope_entry.framework` is a key of `extra_skills_by_framework`,
      those skill names are appended after the domain.yaml-provided list,
      sharing the same token budget. Flat skill directory lookup via v3
      `_resolve_skill_path` (옵션 E).

v4.1 backlog: externalize PERSONA_TO_ROLE into agent-composition.yaml
`domain_role` field; wire steps 1/2 (project-profile Active Skills / Tech Stack).
"""

import os

import yaml

from ..domain import (
    MAX_SKILL_FILE_SIZE,
    _resolve_skill_path,
    estimate_tokens,
    load_skills_for_role,
)


PERSONA_TO_ROLE = {
    "backend-developer": "backend_engineer",
    "frontend-developer": "frontend_engineer",
    "devops-engineer": "devops_engineer",
    "security-engineer": "security_engineer",
    "qa-engineer": "qa_engineer",
}


def load_skills_for_agent(agent_name, persona, state, scope_entry=None,
                          extra_skills_by_framework=None,
                          max_skill_tokens=None):
    """Load skills for a v4 agent via the 4-stage fallback chain.

    Order (system-spec §5.5):
        1. project-profile.md `## Active Skills` bullets (per-project only)
           → replaces steps 2/3/4 entirely when present and non-empty.
        2. project-profile.md `## Tech Stack` auto-match (not wired in v4.0
           — reserved for v4.1; Tech Stack lives in composition.yaml's
           `extra_skills_by_framework` keyed by scope.framework today).
        3. `extra_skills_by_framework[framework]` — appended after step 4.
        4. v3 `domain.yaml roles[].skills` — baseline.

    Mapping uses `persona` (the persona file stem) instead of the raw
    agent name so dummy agents (e.g. `test-fe-dev` with persona
    `frontend-developer`) and the real M4 composition (where agent name
    happens to equal persona) both resolve correctly.

    Args:
        agent_name: AgentConfig.name — retained for meta reporting.
        persona:    AgentConfig.persona stem — drives step 4 mapping.
        state:      full jarfis-state.json dict. Only state["domain"] used.
        scope_entry: dict | None — scope[i]. `framework` key drives step 3,
                    `path` key drives step 1 project-profile lookup.
        extra_skills_by_framework: dict[str, tuple[str, ...]] | None
            — framework → skill name list. From agent-composition.yaml.
        max_skill_tokens: int | None — budget override (forwarded to
            domain.load_skills_for_role; steps 1/3 use remaining budget).

    Returns:
        (loaded_skills, truncated_skills, skills_text, meta)
        meta keys (one or more):
            no_domain       — True when state.domain is None
            no_role_mapping — persona (str) when persona has no role
            domain          — domain name actually used
            role            — role name actually used
            domain_fallback — True when v3 helper raised (graceful)
            framework_extras — {"framework", "appended", "truncated"} when step 3 fires
            active_skills_override — {"source", "skills", "truncated"} when step 1 fires
    """
    del agent_name   # currently unused; kept for v4.1 `domain_role` override

    meta = {}

    domain = state.get("domain") if isinstance(state, dict) else None
    if not domain:
        meta["no_domain"] = True
        return [], [], "", meta

    # Step 1: project-profile `## Active Skills` override (per-project only)
    active_skills = _read_active_skills_section(scope_entry)
    if active_skills:
        budget = _resolve_token_budget(domain, max_skill_tokens)
        loaded, truncated, skills_text = _load_skills_from_flat(
            domain, active_skills, budget
        )
        meta["active_skills_override"] = {
            "source": ".jarfis-project/project-profile.md#Active Skills",
            "skills": loaded,
            "truncated": truncated,
        }
        # PERSONA_TO_ROLE is still reported for context even when overridden.
        role_name = PERSONA_TO_ROLE.get(persona)
        if role_name:
            meta["role"] = role_name
        meta["domain"] = domain
        return loaded, truncated, skills_text, meta

    role_name = PERSONA_TO_ROLE.get(persona)
    if not role_name:
        meta["no_role_mapping"] = persona
        return [], [], "", meta

    try:
        loaded, truncated, skills_text = load_skills_for_role(
            domain, role_name, max_skill_tokens=max_skill_tokens
        )
    except (FileNotFoundError, yaml.YAMLError, KeyError, ValueError) as e:
        meta["domain"] = domain
        meta["role"] = role_name
        meta["domain_fallback"] = True
        meta["domain_fallback_reason"] = f"{type(e).__name__}: {e}"
        return [], [], "", meta

    meta["domain"] = domain
    meta["role"] = role_name

    loaded = list(loaded)
    truncated = list(truncated)

    # Step 3: framework-based extras (system-spec §5.5)
    framework = (scope_entry or {}).get("framework") if isinstance(scope_entry, dict) else None
    extras_map = extra_skills_by_framework or {}
    extras = extras_map.get(framework) if framework else None
    if extras:
        budget = _resolve_token_budget(domain, max_skill_tokens)
        token_used = estimate_tokens(skills_text)
        appended = []
        ext_truncated = []
        for skill_name in extras:
            if skill_name in loaded:
                ext_truncated.append({"name": skill_name, "reason": "already_loaded"})
                continue
            try:
                skill_path = _resolve_skill_path(domain, skill_name)
            except ValueError as e:
                ext_truncated.append({"name": skill_name, "reason": f"invalid_name: {e}"})
                continue
            if not os.path.isfile(skill_path):
                ext_truncated.append({"name": skill_name, "reason": "file_not_found"})
                continue
            if os.path.getsize(skill_path) > MAX_SKILL_FILE_SIZE:
                ext_truncated.append({"name": skill_name, "reason": "file_too_large"})
                continue
            with open(skill_path, encoding="utf-8") as f:
                skill_text = f.read()
            skill_tokens = estimate_tokens(skill_text)
            if token_used + skill_tokens > budget:
                ext_truncated.append({"name": skill_name, "reason": "token_budget_exceeded"})
                continue
            skills_text += f"\n{skill_text}\n"
            token_used += skill_tokens
            loaded.append(skill_name)
            appended.append(skill_name)

        truncated.extend(ext_truncated)
        if appended or ext_truncated:
            meta["framework_extras"] = {
                "framework": framework,
                "appended": appended,
                "truncated": ext_truncated,
            }

    return loaded, truncated, skills_text, meta


def _resolve_token_budget(domain, max_skill_tokens):
    """Pick token budget used by steps 1/3 (same as v3 domain default)."""
    if max_skill_tokens is not None:
        return max_skill_tokens
    try:
        from ..domain import _load_domain_yaml
        config = _load_domain_yaml(domain)
        return config.get("max_skill_tokens", 2500)
    except Exception:
        return 2500


def _read_active_skills_section(scope_entry):
    """Parse `## Active Skills` bullets from project-profile.md (step 1).

    Only fires when scope_entry represents a per-project scope with a
    discoverable project-profile.md. Returns a list[str] of skill names
    (unique, order preserved). Empty list means step 1 does not apply.
    """
    if not isinstance(scope_entry, dict):
        return []
    project_path = scope_entry.get("path")
    if not project_path:
        return []
    profile_path = os.path.join(
        project_path, ".jarfis-project", "project-profile.md"
    )
    if not os.path.isfile(profile_path):
        return []

    try:
        with open(profile_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []

    # Extract `## Active Skills` section (up to next `## ` or EOF).
    lines = text.splitlines()
    section_start = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## active skills"):
            section_start = i + 1
            break
    if section_start is None:
        return []

    skills = []
    for line in lines[section_start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            candidate = stripped[2:].strip()
            # Strip trailing comments like "- react (Recommended)" and
            # skip placeholder bullets wrapped in parentheses only.
            if candidate.startswith("(") and candidate.endswith(")"):
                continue
            # Take first token if the bullet contains descriptive trailing text.
            candidate = candidate.split()[0] if candidate else ""
            if candidate and candidate not in skills:
                skills.append(candidate)
    return skills


def _load_skills_from_flat(domain, skill_names, budget):
    """Load given skill names from the flat skills dir with shared budget.

    Budget is applied per v3 W1-1 (first skill always loads). Returns
    (loaded_skills, truncated_skills, skills_text) with the same shape as
    `domain.load_skills_for_role` so callers can reuse meta handling.
    """
    loaded = []
    truncated = []
    skills_content = ""
    token_used = 0
    for i, name in enumerate(skill_names):
        try:
            skill_path = _resolve_skill_path(domain, name)
        except ValueError as e:
            truncated.append({"name": name, "reason": f"invalid_name: {e}"})
            continue
        if not os.path.isfile(skill_path):
            truncated.append({"name": name, "reason": "file_not_found"})
            continue
        if os.path.getsize(skill_path) > MAX_SKILL_FILE_SIZE:
            truncated.append({"name": name, "reason": "file_too_large"})
            continue
        with open(skill_path, encoding="utf-8") as f:
            skill_text = f.read()
        skill_tokens = estimate_tokens(skill_text)
        if token_used + skill_tokens > budget and (i != 0 or loaded):
            truncated.append({"name": name, "reason": "token_budget_exceeded"})
            continue
        skills_content += f"\n{skill_text}\n"
        token_used += skill_tokens
        loaded.append(name)
    return loaded, truncated, skills_content
