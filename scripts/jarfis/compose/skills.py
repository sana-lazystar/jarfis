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

# v4.1 (M2.12, ADR-0002): helpers consumed by the compose path live in
# ``compose/skills_lib.py`` so ``domain.py`` can be sliced into
# detect/list/scaffold/install without touching this module again.
from .skills_lib import (
    MAX_SKILL_FILE_SIZE,
    _resolve_skill_path,
    estimate_tokens,
    load_skills_for_role,
)


# PERSONA_TO_ROLE — base persona stem (matches files under
# `agents/jarfis/personas/`) → canonical role identifier used to look up
# skills in `domain.yaml`. v4.1 (M2.6, ADR-0001) completes the table to
# 9/9 so `skills_from_domain: true` never silently degrades with a
# `no_role_mapping` meta entry. The right-hand side is matched against
# `roles.{plan,design,implement,review}[].name` first, then falls back
# to `roles.*[].persona` so plan/design/review entries that omit
# `name:` (the common case in domain.yaml) still resolve.
PERSONA_TO_ROLE = {
    # Implementation roles — canonical names match domain.yaml `name:` keys.
    "backend-developer": "backend_engineer",
    "frontend-developer": "frontend_engineer",
    "devops-engineer": "devops_engineer",
    "security-engineer": "security_engineer",
    "qa-engineer": "qa_engineer",
    # Plan / design / review roles — domain.yaml entries omit `name:`,
    # so these stems are matched against `persona:` instead. The values
    # double as semantic role hints surfaced via meta["role"].
    "tech-lead": "reviewer",
    "ux-designer": "designer",
    "product-owner": "planner",
    "technical-architect": "architect",
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
        extra_skills_by_framework: dict | None
            — keys may be either a plain framework string ``"react"``
            (v4.0 behavior) OR a ``(framework, domain)`` 2-tuple ``("react-native", "mobile")``
            (v4.1 — ADR-0003 §4). Tuple wins on collision. Values are
            lists of flat skill names.
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

    # M4.3 (ADR-0003 §2.1): scope[i].domain wins over the legacy
    # state.domain. Falls through to None when neither is set; the
    # caller (work.md Phase 0 step 7) is responsible for triggering
    # detect / AskUserQuestion before compose runs.
    domain = None
    if isinstance(scope_entry, dict):
        sd = scope_entry.get("domain")
        if sd:
            domain = sd
    if not domain and isinstance(state, dict):
        domain = state.get("domain")
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

    # Step 2 (M2.5): project-profile `## Tech Stack` auto-match.
    # Fires when step 1 is absent. Bullets are normalized and matched
    # against the flat `skills/` directory; unmatched bullets are dropped.
    tech_skills = _extract_tech_stack_skills(_resolve_profile_path(scope_entry))
    if tech_skills:
        budget = _resolve_token_budget(domain, max_skill_tokens)
        loaded, truncated, skills_text = _load_skills_from_flat(
            domain, tech_skills, budget
        )
        meta["tech_stack_match"] = {
            "source": ".jarfis-project/project-profile.md#Tech Stack",
            "candidates": tech_skills,
            "loaded": loaded,
            "truncated": truncated,
        }
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
        # Fallback for plan/design/review personas (M2.6): domain.yaml
        # entries in those phases omit `name:`, so `_find_role` raises
        # KeyError. Try a phase-agnostic lookup keyed on `persona`.
        try:
            loaded, truncated, skills_text = _load_skills_for_persona(
                domain, persona, max_skill_tokens=max_skill_tokens
            )
            meta["domain"] = domain
            meta["role"] = role_name
            meta["role_lookup"] = "persona-match"
        except (FileNotFoundError, yaml.YAMLError, KeyError, ValueError) as e2:
            meta["domain"] = domain
            meta["role"] = role_name
            meta["domain_fallback"] = True
            meta["domain_fallback_reason"] = f"{type(e2).__name__}: {e2}"
            return [], [], "", meta
    else:
        meta["domain"] = domain
        meta["role"] = role_name

    loaded = list(loaded)
    truncated = list(truncated)

    # Step 3: framework-based extras (system-spec §5.5).
    # M4.4 (ADR-0003 §4): keys may be either a plain framework string
    # OR a (framework, domain) 2-tuple. Tuple form wins when both are
    # configured for the same framework, so domain-specific extras
    # (e.g. ``("react-native", "mobile") → ["react-native"]``) cannot
    # leak into other domains.
    framework = (scope_entry or {}).get("framework") if isinstance(scope_entry, dict) else None
    extras_map = extra_skills_by_framework or {}
    extras = None
    if framework:
        extras = extras_map.get((framework, domain))
        if extras is None:
            extras = extras_map.get(framework)
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
        from .skills_lib import _load_domain_yaml
        config = _load_domain_yaml(domain)
        return config.get("max_skill_tokens", 2500)
    except Exception:
        return 2500


def _resolve_profile_path(scope_entry):
    """Return absolute path to ``.jarfis-project/project-profile.md`` for
    a per-project scope entry, or empty string when unavailable."""
    if not isinstance(scope_entry, dict):
        return ""
    project_path = scope_entry.get("path")
    if not project_path:
        return ""
    return os.path.join(project_path, ".jarfis-project", "project-profile.md")


# ── M2.5: Tech Stack normalization (step 2 of the 4-stage chain) ───────

# Maps free-form Tech Stack tokens (lowercased, hyphenated) to flat skill
# stems under ~/.claude/commands/jarfis/skills/. Unlisted tokens are
# dropped silently — the chain falls through to step 3/4.
_TECH_STACK_ALIASES = {
    "node": "nodejs",
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "node-js": "nodejs",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react-native": "react",          # rough match; M5 will introduce dedicated skill
    "vue": "vue",
    "vuejs": "vue",
    "vue.js": "vue",
    "express": "express",
    "expressjs": "express",
    "nestjs": "express",
    "nest.js": "express",
    "postgres": "postgres",
    "postgresql": "postgres",
    "redis": "redis",
    "rust": "rust",
    "tauri": "tauri-backend",
    "s3": "s3",
    "aws-s3": "s3",
    "dynamodb": "dynamodb",
    "cognito": "cognito",
    "aws-lambda": "aws-lambda",
    "lambda": "aws-lambda",
    "biome": "biome-lint",
    "browser": "browser",
    "chrome": "browser",
}


def _normalize_tech_token(raw):
    """Lowercase + hyphenate a Tech Stack bullet, then map via aliases.

    Returns the canonical flat-skill stem, or empty string if the token
    has no known mapping.
    """
    if not raw:
        return ""
    # Strip markdown emphasis and trailing version qualifiers.
    token = raw.strip().strip("*_`")
    # If bullet has a "Label: Value" pattern, take the value side.
    if ":" in token:
        token = token.split(":", 1)[1].strip()
    # Drop leading "**Label**" remnants and surrounding punctuation.
    token = token.strip().strip("*").strip()
    # First word only (e.g. "React 18" → "React"; "PostgreSQL 16" → "PostgreSQL").
    first = token.split()[0] if token.split() else ""
    if not first:
        return ""
    key = first.lower()
    # Hyphenate dotted variants ("Node.js" → "node.js" stays; alias maps it).
    if key in _TECH_STACK_ALIASES:
        return _TECH_STACK_ALIASES[key]
    # Hyphenate spaces (rare for first-word path, kept for safety).
    key_h = key.replace(" ", "-")
    return _TECH_STACK_ALIASES.get(key_h, "")


def _extract_tech_stack_skills(profile_path):
    """Parse ``## Tech Stack`` bullets from ``project-profile.md``.

    Returns a list of canonical flat-skill stems (deduplicated, order
    preserved). Empty list when the file is missing or the section has
    no recognizable tokens. Step 2 of the 4-stage fallback chain.

    Bullet syntax accepted:
        - React 18
        * PostgreSQL 16
        - **Runtime**: Node.js 22
    """
    if not profile_path or not os.path.isfile(profile_path):
        return []
    try:
        with open(profile_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []

    lines = text.splitlines()
    section_start = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## tech stack"):
            section_start = i + 1
            break
    if section_start is None:
        return []

    skills = []
    for line in lines[section_start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped:
            continue
        if not (stripped.startswith("- ") or stripped.startswith("* ")):
            continue
        body = stripped[2:].strip()
        canonical = _normalize_tech_token(body)
        if canonical and canonical not in skills:
            skills.append(canonical)
    return skills


# ── M2.6: phase-agnostic skill loader for plan/design/review roles ─────


def _load_skills_for_persona(domain, persona, max_skill_tokens=None):
    """Locate a role by ``persona`` across all phases of ``domain.yaml``
    and load its skills. Returns the same triple as
    ``domain.load_skills_for_role`` so callers can swap helpers.

    plan/design/review entries in domain.yaml typically omit ``name:``,
    so the implement-only ``_find_role`` from ``domain.py`` cannot match
    them. This helper iterates all phases and matches on ``persona`` —
    the first hit wins (deterministic per yaml ordering).
    """
    from .skills_lib import (
        _load_domain_yaml,
        estimate_tokens,
        _resolve_skill_path,
        MAX_SKILL_FILE_SIZE,
    )

    config = _load_domain_yaml(domain)
    matched_role = None
    for phase in ("implement", "plan", "design", "review"):
        for role in config.get("roles", {}).get(phase, []) or []:
            if role.get("persona") == persona:
                matched_role = role
                break
        if matched_role is not None:
            break

    if matched_role is None:
        raise KeyError(f"No role with persona={persona} in domain {domain}")

    token_budget = (
        max_skill_tokens
        if max_skill_tokens is not None
        else config.get("max_skill_tokens", 2500)
    )

    skill_list = matched_role.get("skills", []) or []
    if isinstance(skill_list, str):
        skill_list = [skill_list]

    loaded = []
    truncated = []
    skills_content = ""
    token_used = 0

    for i, skill_name in enumerate(skill_list):
        try:
            skill_path = _resolve_skill_path(domain, skill_name)
            if not os.path.isfile(skill_path):
                truncated.append({"name": skill_name, "reason": "file_not_found"})
                continue
            if os.path.getsize(skill_path) > MAX_SKILL_FILE_SIZE:
                truncated.append({"name": skill_name, "reason": "file_too_large"})
                continue
            with open(skill_path, encoding="utf-8") as f:
                skill_text = f.read()
        except (FileNotFoundError, ValueError):
            truncated.append({"name": skill_name, "reason": "file_not_found"})
            continue

        skill_tokens = estimate_tokens(skill_text)
        if token_used + skill_tokens > token_budget and (i != 0 or loaded):
            truncated.append({"name": skill_name, "reason": "token_budget_exceeded"})
            continue
        skills_content += f"\n{skill_text}\n"
        loaded.append(skill_name)
        token_used += skill_tokens

    # M5.5 (ADR-0004 §2.1): external_skills for persona-matched roles.
    # Mirrors the bare-name + ``domain/skill`` handling in
    # ``domain.load_skills_for_role`` so the union of
    # ``role.skills + role.external_skills`` lands in `loaded` regardless
    # of which loader path resolved the role.
    for ext_skill in (matched_role.get("external_skills") or []):
        try:
            if "/" in ext_skill:
                parts = ext_skill.split("/")
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    raise ValueError(
                        f"Invalid external_skills format: {ext_skill}"
                    )
                ext_domain, ext_skill_name = parts
            else:
                ext_domain, ext_skill_name = domain, ext_skill

            ext_path = _resolve_skill_path(ext_domain, ext_skill_name)
            if not os.path.isfile(ext_path):
                truncated.append({
                    "name": ext_skill,
                    "reason": "external_not_found",
                })
                continue
            if os.path.getsize(ext_path) > MAX_SKILL_FILE_SIZE:
                truncated.append({
                    "name": ext_skill,
                    "reason": "file_too_large",
                })
                continue
            with open(ext_path, encoding="utf-8") as f:
                ext_text = f.read()
        except (FileNotFoundError, ValueError):
            truncated.append({
                "name": ext_skill,
                "reason": "external_not_found",
            })
            continue

        ext_tokens = estimate_tokens(ext_text)
        if token_used + ext_tokens > token_budget:
            truncated.append({
                "name": ext_skill,
                "reason": "token_budget_exceeded",
            })
            continue
        skills_content += f"\n{ext_text}\n"
        loaded.append(ext_skill)
        token_used += ext_tokens

    return loaded, truncated, skills_content


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
