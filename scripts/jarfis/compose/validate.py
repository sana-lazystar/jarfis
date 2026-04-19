"""`jarfis_cli.py compose --validate` — composition validation.

Verifies agent-composition.yaml against structural + semantic rules
defined in system-spec §5.5 and M4 Step 4.7:

    1. Schema (delegated to config.load_composition — errors out early)
    2. Persona file existence
    3. extra_skills_by_framework skill file existence
    4. scope↔base semantics (already caught by load_composition)
    5. section headings: skipped (work-specific, see Step 4.7 item 5)
    6. importance:required + optional:true → warning
    7. importance missing (defaulted to recommended) → warning
    8. importance statistics

Output is JSON on stdout. Exit 0 when valid (warnings OK), 1 when errors.
"""

import os

import yaml

from ..domain import _resolve_skill_path
from .config import load_composition, load_extra_skills_by_framework
from .errors import ConfigError


def validate(yaml_path, personas_dir):
    """Run all validation checks on a composition yaml.

    Returns a dict with keys: valid, errors, warnings, agents_validated,
    skills_referenced, skills_missing, importance_stats.
    """
    report = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "agents_validated": 0,
        "skills_referenced": 0,
        "skills_missing": [],
        "importance_stats": {"required": 0, "recommended": 0, "optional": 0},
    }

    # Step 1: schema via load_composition (any failure → report as error and stop)
    try:
        composition = load_composition(yaml_path)
    except ConfigError as e:
        report["errors"].append({"type": "schema", "message": str(e)})
        return report

    try:
        extras_map = load_extra_skills_by_framework(yaml_path)
    except ConfigError as e:
        report["errors"].append({"type": "schema", "message": str(e)})
        return report

    # Re-parse raw yaml to detect missing importance fields (warning #7).
    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    raw_agents = raw.get("agents") or {}

    # Step 2: persona files
    for name, agent in composition.items():
        persona_path = os.path.join(personas_dir, f"{agent.persona}.md")
        if not os.path.isfile(persona_path):
            report["errors"].append({
                "type": "persona_not_found",
                "agent": name,
                "persona": agent.persona,
                "path": persona_path,
            })

    # Step 6/7/8: importance semantics + stats
    for name, agent in composition.items():
        raw_ctx = (raw_agents.get(name) or {}).get("context") or []
        for idx, entry in enumerate(agent.context):
            report["importance_stats"][entry.importance] = (
                report["importance_stats"].get(entry.importance, 0) + 1
            )

            # #6: required + optional:true conflict
            if entry.importance == "required" and entry.optional:
                report["warnings"].append({
                    "type": "importance_optional_conflict",
                    "agent": name,
                    "entry": entry.path,
                    "msg": ("importance:required + optional:true — intent unclear "
                            "(required normally implies optional:false)"),
                })

            # #7: importance field missing in raw → default applied
            raw_entry = raw_ctx[idx] if idx < len(raw_ctx) and isinstance(raw_ctx[idx], dict) else {}
            if "importance" not in raw_entry:
                report["warnings"].append({
                    "type": "importance_missing",
                    "agent": name,
                    "entry": entry.path,
                    "msg": ("importance field missing — defaulted to "
                            f"`{entry.importance}` (explicit value recommended)"),
                })

    # Step 3: skill files referenced by extra_skills_by_framework
    seen_skills = set()
    for framework, skills in extras_map.items():
        for skill_name in skills:
            seen_skills.add(skill_name)
            try:
                # Use "web" as the domain-fallback reference; flat wins if present.
                skill_path = _resolve_skill_path("web", skill_name)
            except ValueError as e:
                report["errors"].append({
                    "type": "skill_invalid_name",
                    "framework": framework,
                    "skill": skill_name,
                    "message": str(e),
                })
                continue
            if not os.path.isfile(skill_path):
                report["errors"].append({
                    "type": "skill_not_found",
                    "framework": framework,
                    "skill": skill_name,
                    "path": skill_path,
                })
                report["skills_missing"].append(skill_name)

    report["agents_validated"] = len(composition)
    report["skills_referenced"] = len(seen_skills)
    report["valid"] = not report["errors"]
    return report
