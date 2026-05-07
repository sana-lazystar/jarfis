"""JARFIS Agent Admin — Skill+persona registry CRUD.

Subcommands:
    skill list                          JSON output of registered skills
    skill add <name> [--library ID]
                    [--bind-framework FW]
                    [--apply]            default dry-run; --apply writes file
    skill update <name>                  locate skill file (caller edits it)
    skill remove <name> [--apply]        default dry-run; show refs first
    persona list                         JSON of agent-composition.yaml agents

Safety: never writes to agent-composition.yaml — only diff suggestions.
        The slash-command layer surfaces those diffs for manual approval.

Env-var overrides (testability):
    JARFIS_SKILLS_DIR        skills directory (default ~/.claude/commands/jarfis/skills)
    JARFIS_TEMPLATE_PATH     template path  (default ~/.claude/commands/jarfis/templates/skill-template.md)
    JARFIS_COMPOSITION_PATH  composition.yaml (default ~/.claude/commands/jarfis/agent-composition.yaml)
    JARFIS_DOMAINS_DIR       domains dir   (default ~/.claude/commands/jarfis/domains)
"""

import argparse
import glob
import json
import os
import re
import sys

import yaml

from .utils import json_error, json_output

_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_NAME_MAX_LEN = 40


# ─────────────────────────────────────────────────────────────────────
# Path resolution (env-var aware for tests)
# ─────────────────────────────────────────────────────────────────────


def _claude_jarfis_dir():
    return os.path.join(os.path.expanduser("~"), ".claude", "commands", "jarfis")


def _skills_dir():
    return os.environ.get(
        "JARFIS_SKILLS_DIR", os.path.join(_claude_jarfis_dir(), "skills")
    )


def _template_path():
    return os.environ.get(
        "JARFIS_TEMPLATE_PATH",
        os.path.join(_claude_jarfis_dir(), "templates", "skill-template.md"),
    )


def _composition_path():
    return os.environ.get(
        "JARFIS_COMPOSITION_PATH",
        os.path.join(_claude_jarfis_dir(), "agent-composition.yaml"),
    )


def _domains_dir():
    return os.environ.get(
        "JARFIS_DOMAINS_DIR", os.path.join(_claude_jarfis_dir(), "domains")
    )


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _validate_name(name):
    """Raise json_error (sys.exit 1) if name is invalid."""
    if not name:
        json_error("Skill name is required.")
    if len(name) > _NAME_MAX_LEN:
        json_error(
            f"Skill name too long: {len(name)} > {_NAME_MAX_LEN} characters."
        )
    if not _NAME_RE.match(name):
        json_error(
            "Invalid skill name. Must match ^[a-z][a-z0-9-]*$ "
            "(lowercase letter start, lowercase/digits/hyphens only)."
        )


def _kebab_to_title(name):
    """Convert 'aws-lambda' → 'Aws Lambda'."""
    return " ".join(part.capitalize() for part in name.split("-"))


def _parse_skill_metadata(path):
    """Return (title, description) extracted from skill .md file.

    title       = first '# ' heading line (stripped of leading '#')
    description = first '> ' quote line (stripped of leading '>')
    """
    title = ""
    description = ""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not title and stripped.startswith("# "):
                    title = stripped[2:].strip()
                    continue
                if not description and stripped.startswith("> "):
                    description = stripped[2:].strip()
                if title and description:
                    break
    except OSError:
        pass
    return title, description


def _read_template_skeleton(name):
    """Read template, extract the 5-section structure, return rendered skeleton."""
    template_path = _template_path()
    if not os.path.isfile(template_path):
        json_error(f"Template not found: {template_path}")

    with open(template_path, encoding="utf-8") as f:
        content = f.read()

    # Find the inner ~~~markdown ... ~~~ block after "## 권장 5섹션 구조".
    # Use the first ~~~ block to be safe.
    m = re.search(r"~~~markdown\n(.*?)\n~~~", content, re.DOTALL)
    if not m:
        # Fallback: build a minimal skeleton ourselves so the module never
        # depends on exact template formatting.
        body = (
            "# {기술명} Expertise\n\n"
            "> {1줄 요약}\n\n"
            "## Common Pitfalls\n- TODO\n\n"
            "## Decision Heuristics\n- TODO\n\n"
            "## Anti-patterns\n- TODO\n\n"
            "## Version & Environment Notes\n- TODO\n\n"
            "## Related Skills\n- TODO\n"
        )
    else:
        body = m.group(1)

    title = _kebab_to_title(name)
    body = body.replace("{기술명}", title)
    # Replace the 1-line summary placeholder with a TODO marker.
    body = re.sub(
        r">\s*\{1줄 요약[^}]*\}",
        "> TODO: 1줄 요약 — Context7 docs 참조 후 작성",
        body,
    )
    # Replace any "함정 1 ... / 휴리스틱 1 ... / etc." sample bullets with `- TODO`.
    # Simpler: strip every existing list bullet and re-emit `- TODO` per section.
    sections = ["Common Pitfalls", "Decision Heuristics", "Anti-patterns",
                "Version & Environment Notes", "Related Skills"]
    rebuilt = []
    current_section = None
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("## "):
            section_name = s[3:].strip()
            rebuilt.append(line)
            if section_name in sections:
                current_section = section_name
                rebuilt.append("- TODO")
            else:
                current_section = None
            continue
        # Skip the original sample bullets inside known sections.
        if current_section and s.startswith("- "):
            continue
        # Skip blank lines that immediately follow our injected TODO until the
        # next non-bullet line — but keep blank-line separators between sections.
        rebuilt.append(line)

    return "\n".join(rebuilt).rstrip() + "\n"


def _grep_yaml_for_name(yaml_path, name):
    """Grep a YAML file for occurrences of `name` (whole-word).

    Returns list of {"file": path, "line": N, "content": str}.
    """
    refs = []
    if not os.path.isfile(yaml_path):
        return refs
    pattern = re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(name) + r"(?![A-Za-z0-9_-])")
    try:
        with open(yaml_path, encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                if pattern.search(line):
                    refs.append(
                        {"file": yaml_path, "line": i, "content": line.rstrip()}
                    )
    except OSError:
        pass
    return refs


def _collect_references(name):
    """Find all references to `name` in composition.yaml + domains/*.yaml."""
    refs = []
    refs.extend(_grep_yaml_for_name(_composition_path(), name))
    domains_dir = _domains_dir()
    if os.path.isdir(domains_dir):
        for path in sorted(glob.glob(os.path.join(domains_dir, "*.yaml"))):
            refs.extend(_grep_yaml_for_name(path, name))
    return refs


# ─────────────────────────────────────────────────────────────────────
# skill list
# ─────────────────────────────────────────────────────────────────────


def cmd_skill_list(args):
    skills_dir = _skills_dir()
    skills = []
    if os.path.isdir(skills_dir):
        for path in sorted(glob.glob(os.path.join(skills_dir, "*.md"))):
            name = os.path.splitext(os.path.basename(path))[0]
            title, description = _parse_skill_metadata(path)
            skills.append(
                {"name": name, "title": title, "description": description}
            )
    json_output({"count": len(skills), "skills": skills})


# ─────────────────────────────────────────────────────────────────────
# skill add
# ─────────────────────────────────────────────────────────────────────


def cmd_skill_add(args):
    parser = argparse.ArgumentParser(prog="jarfis agent skill add", add_help=False)
    parser.add_argument("name")
    parser.add_argument("--library", default=None)
    parser.add_argument("--bind-framework", default=None)
    parser.add_argument("--apply", action="store_true")
    try:
        ns = parser.parse_args(args)
    except SystemExit:
        json_error("Usage: jarfis agent skill add <name> [--library ID] [--bind-framework FW] [--apply]")

    name = ns.name
    _validate_name(name)

    skills_dir = _skills_dir()
    target = os.path.join(skills_dir, f"{name}.md")
    if os.path.exists(target):
        json_error(f"Skill already exists: {target}")

    skeleton = _read_template_skeleton(name)
    if ns.library:
        header = f"<!-- Context7 ID: {ns.library}. After creation, run: mcp__context7__query-docs to flesh out -->\n\n"
        skeleton = header + skeleton

    framework_binding = None
    if ns.bind_framework:
        # Read existing mapping (read-only — never write composition.yaml).
        comp_path = _composition_path()
        existing = []
        if os.path.isfile(comp_path):
            try:
                with open(comp_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                existing = (
                    data.get("extra_skills_by_framework", {})
                    .get(ns.bind_framework, [])
                ) or []
            except yaml.YAMLError:
                existing = []
        merged = list(existing)
        if name not in merged:
            merged.append(name)
        diff = f"  {ns.bind_framework}: {merged}\n"
        framework_binding = {
            "framework": ns.bind_framework,
            "composition_yaml_diff": diff,
            "manual_action_required": True,
            "target_file": comp_path,
        }

    if not ns.apply:
        json_output(
            {
                "status": "dry_run",
                "path": target,
                "preview_first_lines": skeleton.splitlines()[:6],
                "framework_binding": framework_binding,
            }
        )
        return

    os.makedirs(skills_dir, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(skeleton)
    json_output(
        {
            "status": "created",
            "path": target,
            "framework_binding": framework_binding,
        }
    )


# ─────────────────────────────────────────────────────────────────────
# skill update
# ─────────────────────────────────────────────────────────────────────


def cmd_skill_update(args):
    if not args:
        json_error("Usage: jarfis agent skill update <name>")
    name = args[0]
    _validate_name(name)
    target = os.path.join(_skills_dir(), f"{name}.md")
    if not os.path.isfile(target):
        json_error(f"Skill not found: {target}")
    stat = os.stat(target)
    json_output(
        {
            "status": "located",
            "path": target,
            "size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "instruction": (
                "Edit the file directly with your editor or via "
                "/jarfis:agent skill update follow-up MCP calls "
                "(Context7 + Edit, checkpoint style)."
            ),
        }
    )


# ─────────────────────────────────────────────────────────────────────
# skill remove
# ─────────────────────────────────────────────────────────────────────


def cmd_skill_remove(args):
    parser = argparse.ArgumentParser(prog="jarfis agent skill remove", add_help=False)
    parser.add_argument("name")
    parser.add_argument("--apply", action="store_true")
    try:
        ns = parser.parse_args(args)
    except SystemExit:
        json_error("Usage: jarfis agent skill remove <name> [--apply]")

    name = ns.name
    _validate_name(name)

    target = os.path.join(_skills_dir(), f"{name}.md")
    if not os.path.isfile(target):
        json_error(f"Skill not found: {target}")

    refs = _collect_references(name)

    if not ns.apply:
        json_output(
            {
                "status": "dry_run",
                "path": target,
                "references": refs,
            }
        )
        return

    os.remove(target)
    json_output(
        {
            "status": "removed",
            "path": target,
            "manual_cleanup_required": refs,
        }
    )


# ─────────────────────────────────────────────────────────────────────
# persona list
# ─────────────────────────────────────────────────────────────────────


def cmd_persona_list(args):
    comp_path = _composition_path()
    if not os.path.isfile(comp_path):
        json_error(f"agent-composition.yaml not found: {comp_path}")
    try:
        with open(comp_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        json_error(f"Failed to parse YAML: {e}")

    agents_map = data.get("agents", {}) or {}
    agents = []
    for name, cfg in agents_map.items():
        cfg = cfg or {}
        agents.append(
            {
                "name": name,
                "persona": cfg.get("persona", ""),
                "scope": cfg.get("scope", ""),
                "model": cfg.get("model", "sonnet"),
                "skills_from_domain": bool(cfg.get("skills_from_domain", False)),
                "context_count": len(cfg.get("context", []) or []),
            }
        )
    json_output({"count": len(agents), "agents": agents})


# ─────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────


_SKILL_ACTIONS = {
    "list": cmd_skill_list,
    "add": cmd_skill_add,
    "update": cmd_skill_update,
    "remove": cmd_skill_remove,
}

_PERSONA_ACTIONS = {
    "list": cmd_persona_list,
}


def main(args):
    if not args:
        json_error(
            "Usage: jarfis agent <skill|persona> <action> [args...]"
        )
    sub = args[0]
    rest = args[1:]
    if sub == "skill":
        if not rest:
            json_error("Usage: jarfis agent skill <list|add|update|remove> [args...]")
        action = rest[0]
        if action not in _SKILL_ACTIONS:
            json_error(
                f"Unknown skill action: {action}. Use list|add|update|remove."
            )
        _SKILL_ACTIONS[action](rest[1:])
    elif sub == "persona":
        if not rest:
            json_error("Usage: jarfis agent persona <list>")
        action = rest[0]
        if action not in _PERSONA_ACTIONS:
            json_error(f"Unknown persona action: {action}. Use list.")
        _PERSONA_ACTIONS[action](rest[1:])
    else:
        json_error(
            f"Unknown subcommand: {sub}. Use skill|persona."
        )


if __name__ == "__main__":
    main(sys.argv[1:])
