"""`python3 -m jarfis.compose ...` — CLI entry point.

Used by jarfis-foreman to hydrate a sub-agent invocation.
stdout: JSON (ComposeResult). stderr (on error): JSON {error, type, details}.
Exit 0 on success, 1 on any ComposeError, 1 on unexpected exception.
"""

import argparse
import json
import os
import sys
import time
import traceback

from .. import trace
from .assembler import assemble_prompt
from .config import load_composition, load_extra_skills_by_framework
from .errors import (
    AgentNotFoundError,
    ComposeError,
    PersonaNotFoundError,
)
from .reader import read_and_extract
from .resolver import resolve_path, resolve_working_dir
from .skills import load_skills_for_agent
from .validate import validate as validate_composition_file


DEFAULT_COMPOSITION = os.path.expanduser(
    "~/.claude/commands/jarfis/agent-composition.yaml"
)
PERSONAS_DIR = os.path.expanduser("~/.claude/agents/jarfis/personas")


def main(argv=None):
    args = _parse_args(argv)

    if args.validate:
        report = validate_composition_file(args.composition, args.personas_dir)
        sys.stdout.write(json.dumps(report, ensure_ascii=False) + "\n")
        sys.exit(0 if report["valid"] else 1)

    # M6.3 (T2) — dry-run dispatch.
    if args.dry_run:
        if not args.persona and not args.agent:
            sys.stderr.write(json.dumps({
                "error": "--dry-run requires --persona <stem> (or --agent <name>)",
            }) + "\n")
            sys.exit(1)
        try:
            output = _dry_run(args)
        except ComposeError as e:
            _emit_error(e, type(e).__name__)
            sys.exit(1)
        except Exception as e:  # pragma: no cover — safety net
            sys.stderr.write(json.dumps({
                "error": "internal",
                "type": type(e).__name__,
                "message": str(e),
                "trace": traceback.format_exc(),
            }) + "\n")
            sys.exit(1)
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
        sys.exit(0)

    if not args.agent or not args.state:
        sys.stderr.write(json.dumps({
            "error": "--agent and --state are required unless --validate is set",
        }) + "\n")
        sys.exit(1)

    try:
        result = _compose(args)
    except ComposeError as e:
        _emit_error(e, type(e).__name__)
        sys.exit(1)
    except Exception as e:  # pragma: no cover — safety net
        sys.stderr.write(json.dumps({
            "error": "internal",
            "type": type(e).__name__,
            "message": str(e),
            "trace": traceback.format_exc(),
        }) + "\n")
        sys.exit(1)

    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    sys.exit(0)


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="jarfis_cli.py compose",
        description="Compose an agent invocation (persona + skills + context).",
        # M6.3 (T2): disable argparse abbreviation so the new --scope flag
        # doesn't conflict with the older --scope-index by prefix match.
        allow_abbrev=False,
    )
    parser.add_argument("--agent", default=None,
                        help="Agent name (key in agents: of composition yaml)")
    parser.add_argument("--scope-index", type=int, default=None,
                        help="0-based index into state.workspace.scope[] "
                             "(required for per-project agents)")
    parser.add_argument("--state", default=None,
                        help="Path to .jarfis-state.json")
    parser.add_argument("--composition", default=DEFAULT_COMPOSITION,
                        help="Path to agent-composition.yaml (default: global)")
    parser.add_argument("--personas-dir", default=PERSONAS_DIR,
                        help="Persona directory (default: "
                             "~/.claude/agents/jarfis/personas)")
    parser.add_argument("--validate", action="store_true",
                        help="Validate composition.yaml (schema + persona + "
                             "skill existence + importance stats). No --agent "
                             "or --state needed in this mode.")
    # M6.3 — Testbed dry-run (ADR/roadmap §5 T2)
    parser.add_argument("--dry-run", action="store_true",
                        help="Render the composition (persona + skills + "
                             "context) to stdout without invoking any phase "
                             "or writing to state. Pair with --persona/--scope "
                             "for direct on-disk inspection, or with the "
                             "regular --agent/--state for a markdown view of "
                             "what jarfis-foreman would have received.")
    parser.add_argument("--persona", default=None,
                        help="Persona stem (filename under personas-dir, "
                             "without .md). Used together with --scope for "
                             "dry-run mode against an arbitrary project on "
                             "disk.")
    parser.add_argument("--scope", default=None,
                        help="Path to a scope (project) directory. With "
                             "--dry-run + --persona, the domain is auto-"
                             "detected from on-disk indicators unless "
                             "--domain is also supplied.")
    parser.add_argument("--domain", default=None,
                        help="Override the detected domain in dry-run mode. "
                             "Useful when a project has weak indicators or "
                             "the testbed wants to force a specific pack.")
    parser.add_argument("--format", default="markdown",
                        choices=("markdown", "json"),
                        help="Dry-run output format. `markdown` (default) is "
                             "human-readable; `json` is machine-readable for "
                             "further tooling.")
    return parser.parse_args(argv)


def _compose(args):
    start = time.monotonic()
    try:
        if trace.is_enabled():
            trace.log_event(
                "compose_start",
                {"agent": args.agent, "scope_index": args.scope_index},
            )
    except Exception:
        pass

    state = _load_state(args.state)

    composition = load_composition(args.composition)
    agent = composition.get(args.agent)
    if agent is None:
        raise AgentNotFoundError(
            f"agent `{args.agent}` not found in {args.composition} "
            f"(known: {sorted(composition.keys())})"
        )
    extra_skills_map = load_extra_skills_by_framework(args.composition)

    meta = {}

    if agent.scope == "work-wide" and args.scope_index is not None:
        meta["working_dir_warning"] = (
            f"scope_index={args.scope_index} ignored for work-wide agent"
        )

    working_dir = resolve_working_dir(agent.scope, state, args.scope_index)

    if agent.scope == "per-project":
        scope_entry = state["workspace"]["scope"][args.scope_index]
        meta["scope_entry"] = _snapshot_scope_entry(scope_entry)

    # Skills
    scope_entry_obj = None
    if agent.scope == "per-project":
        scope_entry_obj = state["workspace"]["scope"][args.scope_index]

    if agent.skills_from_domain:
        loaded_skills, truncated_skills, skills_text, skills_meta = (
            load_skills_for_agent(
                agent.name, agent.persona, state, scope_entry_obj,
                extra_skills_by_framework=extra_skills_map,
            )
        )
        meta["skills_loaded"] = loaded_skills
        meta["truncated_skills"] = truncated_skills
        if skills_meta:
            meta["skills_meta"] = skills_meta
    else:
        skills_text = ""
        meta["skills_loaded"] = []
        meta["truncated_skills"] = []

    # Context blocks
    context_blocks = []
    context_files_meta = []
    for entry in agent.context:
        block_meta = {"path": entry.path, "importance": entry.importance}
        if entry.sections:
            block_meta["sections"] = list(entry.sections)

        try:
            target = resolve_path(entry.base, entry.path, state, args.scope_index)
        except ComposeError as e:
            block_meta.update({"injected": False, "reason": str(e)})
            context_files_meta.append(block_meta)
            continue

        if target is None:
            block_meta.update({"injected": False, "reason": "org_not_registered"})
            context_files_meta.append(block_meta)
            continue

        if isinstance(target, list):
            joined_parts = []
            any_injected = False
            scope_list = state["workspace"]["scope"]
            for idx, target_item in enumerate(target):
                if isinstance(target_item, dict):
                    # Walk-up dedupe entry: shared SSOT across N scope indices.
                    sub_target = target_item["path"]
                    scope_indices = target_item["from_scope_indices"]
                    scope_names = [
                        scope_list[i].get("name", f"idx{i}")
                        for i in scope_indices
                    ]
                    if len(scope_names) == 1:
                        label = f"### ({scope_names[0]})"
                    else:
                        label = (
                            "### (monorepo SSOT shared by: "
                            + ", ".join(scope_names) + ")"
                        )
                else:
                    # Legacy list[str] (non-walkup paths).
                    sub_target = target_item
                    scope_name = scope_list[idx].get("name", f"idx{idx}")
                    label = f"### ({scope_name})"
                rr = read_and_extract(sub_target, entry.sections, optional=entry.optional)
                if rr.text:
                    joined_parts.append(f"{label}\n{rr.text.strip()}")
                    any_injected = True
            content = "\n\n".join(joined_parts) if joined_parts else None
            block_meta["injected"] = any_injected
            if not any_injected:
                block_meta["reason"] = "file_not_found"
            context_files_meta.append(block_meta)
            if content:
                context_blocks.append((entry.path, content))
        else:
            rr = read_and_extract(target, entry.sections, optional=entry.optional)
            block_meta["injected"] = rr.meta.get("injected", False)
            if not block_meta["injected"]:
                block_meta["reason"] = rr.meta.get("reason", "unknown")
            if rr.meta.get("missing_sections"):
                block_meta["missing_sections"] = rr.meta["missing_sections"]
            context_files_meta.append(block_meta)
            if rr.text:
                context_blocks.append((entry.path, rr.text))

    meta["context_files"] = context_files_meta

    _emit_missing_sections_warnings(args.agent, context_files_meta)

    # Persona
    persona_path = os.path.join(args.personas_dir, f"{agent.persona}.md")
    if not os.path.isfile(persona_path):
        raise PersonaNotFoundError(
            f"persona file not found: {persona_path}"
        )
    with open(persona_path, encoding="utf-8") as f:
        persona_text = f.read()

    # Assemble
    locale = state.get("locale")
    prompt, assembly_meta = assemble_prompt(
        locale, persona_text, skills_text, context_blocks, task_instruction=None
    )
    meta.update(assembly_meta)

    payload = {
        "subagent_type": agent.persona,
        "prompt": prompt,
        "working_dir": working_dir,
        "meta": meta,
    }
    if agent.model is not None:
        payload["model"] = agent.model

    try:
        if trace.is_enabled():
            trace.log_event(
                "compose_end",
                {"agent": args.agent,
                 "context_files": len(context_files_meta),
                 "injected_files": sum(
                     1 for b in context_files_meta if b.get("injected")
                 ),
                 "skills_count": len(meta.get("skills_loaded", [])),
                 "prompt_chars": len(prompt),
                 "duration_ms": int((time.monotonic() - start) * 1000)},
            )
    except Exception:
        pass

    return payload


def _load_state(path):
    if not os.path.isfile(path):
        raise ComposeError(f"state file not found: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ComposeError(f"state file JSON parse error: {e}") from e


def _snapshot_scope_entry(entry):
    """Only fields useful to downstream agents end up in meta."""
    keys = ("name", "type", "framework", "languages", "branch", "baseCommit")
    return {k: entry.get(k) for k in keys if k in entry}


def _emit_error(exc, type_name):
    sys.stderr.write(json.dumps({
        "error": str(exc),
        "type": type_name,
    }) + "\n")


def _emit_missing_sections_warnings(agent_name, context_files_meta):
    """Emit a stderr warning line per block whose requested sections were absent.

    Non-fatal — keeps stdout JSON clean so jarfis-foreman's downstream parse is
    unaffected. Intent: when a project-profile.md is renamed or a composition
    entry references a stale section title, the human running compose sees
    the mismatch immediately instead of it being silently dropped to meta only.
    """
    for block in context_files_meta:
        missing = block.get("missing_sections")
        if not missing:
            continue
        sys.stderr.write(
            f"[compose warning] agent={agent_name} path={block.get('path')} "
            f"missing_sections={list(missing)}\n"
        )


def _dry_run(args):
    """Render a composition for inspection without phase execution.

    Two input shapes:
        (a) ``--agent <name> --state <path>`` — full agent-composition
            flow, but the result is rendered as markdown/JSON instead
            of being handed to jarfis-foreman.
        (b) ``--persona <stem> --scope <path>`` — synthesize a minimal
            state with one scope at the supplied path. Domain is
            auto-detected from on-disk indicators unless ``--domain``
            is supplied.

    Output:
        markdown (default) or JSON. The state file passed via
        ``--state`` is read but never mutated; in the synthetic case
        nothing is written under ``--scope`` either (smoke-checked by
        ``test_dry_run_does_not_create_state_file``).

    Returns the rendered string. Telemetry breadcrumbs:
        ``compose_dry_run_start`` / ``compose_dry_run_end`` (M6.4).
    """
    start = time.monotonic()
    try:
        if trace.is_enabled():
            trace.log_event(
                "compose_dry_run_start",
                {
                    "persona": args.persona,
                    "agent": args.agent,
                    "scope": args.scope,
                    "domain": args.domain,
                    "format": args.format,
                },
            )
    except Exception:
        pass

    # ── Branch (b): persona + scope synthetic state ─────────────────
    if args.persona and not args.agent:
        persona = args.persona
        scope_path = os.path.abspath(args.scope) if args.scope else os.getcwd()
        domain = args.domain or _auto_detect_domain(scope_path)

        if not domain:
            raise ComposeError(
                f"could not auto-detect a domain under {scope_path}; "
                "rerun with --domain <name>"
            )

        scope_entry = {
            "name": os.path.basename(scope_path.rstrip(os.sep)) or "scope",
            "path": scope_path,
            "domain": domain,
            "type": _infer_scope_type(domain),
        }
        # Best-effort framework hint for the 4-stage skill chain.
        framework = _infer_framework(scope_path, domain)
        if framework:
            scope_entry["framework"] = framework

        state = {
            "domain": domain,
            "workspace": {"scope": [scope_entry]},
        }

        from .skills import load_skills_for_agent

        loaded, truncated, skills_text, meta = load_skills_for_agent(
            agent_name=persona,
            persona=persona,
            state=state,
            scope_entry=scope_entry,
        )

        persona_path = os.path.join(args.personas_dir, f"{persona}.md")
        if not os.path.isfile(persona_path):
            raise PersonaNotFoundError(
                f"persona file not found: {persona_path}"
            )
        with open(persona_path, encoding="utf-8") as f:
            persona_text = f.read()

        # Assemble a prompt-shaped composition string so testbed
        # tooling can grep the same way it does for the agent-state
        # branch (see `composition` in the agent-state payload).
        composition = persona_text.rstrip()
        if skills_text:
            composition = (
                composition + "\n\n"
                "## Skills\n\n" + skills_text.rstrip()
            )

        payload = {
            "dry_run": True,
            "mode": "persona-scope",
            "persona": persona,
            "scope": scope_path,
            "domain": domain,
            "skills_loaded": list(loaded),
            "skills_truncated": list(truncated),
            "skills_text": skills_text,
            "persona_text": persona_text,
            "prompt": composition,
            "composition": composition,
            "meta": meta,
        }

    # ── Branch (a): full agent + state, but rendered for humans ─────
    else:
        if not args.state:
            raise ComposeError(
                "--dry-run with --agent requires --state <path>"
            )
        result = _compose(args)
        payload = {
            "dry_run": True,
            "mode": "agent-state",
            "persona": result.get("subagent_type"),
            "agent": args.agent,
            "scope": args.scope,
            "domain": result.get("meta", {}).get("scope_entry", {}).get("domain")
                or _load_state(args.state).get("domain"),
            "skills_loaded": list(result.get("meta", {}).get("skills_loaded", [])),
            "skills_truncated": list(result.get("meta", {}).get("truncated_skills", [])),
            "prompt": result.get("prompt"),
            "working_dir": result.get("working_dir"),
            "meta": result.get("meta", {}),
        }
        # Reconstruct the building blocks for the markdown layout.
        # `prompt` already contains persona + skills + context — we
        # surface it under "Composition" and keep meta separately.
        payload["composition"] = result.get("prompt")

    rendered = _render_dry_run(payload, args.format)

    try:
        if trace.is_enabled():
            trace.log_event(
                "compose_dry_run_end",
                {
                    "persona": payload.get("persona"),
                    "domain": payload.get("domain"),
                    "skills_count": len(payload.get("skills_loaded", [])),
                    "format": args.format,
                    "duration_ms": int((time.monotonic() - start) * 1000),
                },
            )
    except Exception:
        pass

    return rendered


def _auto_detect_domain(scope_path):
    """Return the top-1 domain for ``scope_path`` or None on greenfield."""
    try:
        from ..domain import detect
    except Exception:
        return None
    try:
        result = detect(scope_path)
    except Exception:
        return None
    matches = result.get("matches") or []
    if not matches:
        return None
    return matches[0].get("domain")


def _infer_scope_type(domain):
    """Default scope.type for a domain — best effort, surfaced as meta."""
    return {
        "web": "frontend",
        "desktop": "desktop",
        "mobile": "mobile",
    }.get(domain, "frontend")


def _infer_framework(scope_path, domain):
    """Cheap framework guess based on package.json hints. Used only in
    dry-run synthesis so step-3 (extra_skills_by_framework) and
    step-2 (Tech Stack) can fire when the user hasn't configured a real
    project profile."""
    pkg_path = os.path.join(scope_path, "package.json")
    if not os.path.isfile(pkg_path):
        return None
    try:
        with open(pkg_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    deps = {}
    for section in ("dependencies", "devDependencies"):
        deps.update(data.get(section, {}))
    if domain == "mobile" and "react-native" in deps:
        return "react-native"
    if domain == "desktop" and any(k.startswith("@tauri-apps/") for k in deps):
        return "tauri"
    if domain == "web":
        if "next" in deps:
            return "next"
        if "vue" in deps:
            return "vue"
        if "react" in deps:
            return "react"
    return None


def _render_dry_run(payload, fmt):
    """Render a dry-run payload as markdown or JSON."""
    if fmt == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)

    # Markdown layout — stable section headers so testbed checklists
    # can grep ## Persona / ## Skills / ## Meta.
    lines = []
    lines.append("# Compose Dry-Run")
    lines.append("")
    persona = payload.get("persona") or "(unknown)"
    domain = payload.get("domain") or "(unset)"
    scope = payload.get("scope") or "(none)"
    mode = payload.get("mode", "")
    lines.append(f"- mode: `{mode}`")
    lines.append(f"- persona: `{persona}`")
    lines.append(f"- domain: `{domain}`")
    lines.append(f"- scope: `{scope}`")
    skills = payload.get("skills_loaded") or []
    lines.append(f"- skills_loaded: {skills}")
    truncated = payload.get("skills_truncated") or []
    if truncated:
        lines.append(f"- skills_truncated: {truncated}")
    lines.append("")

    lines.append("## Persona")
    lines.append("")
    persona_text = payload.get("persona_text")
    if persona_text:
        lines.append(persona_text.rstrip())
    elif payload.get("composition"):
        # agent-state mode — persona body is embedded inside the
        # assembled prompt; just point at the Composition section.
        lines.append("_See `## Composition` below — persona body is "
                     "already merged into the assembled prompt._")
    else:
        lines.append("_(persona body unavailable)_")
    lines.append("")

    lines.append("## Skills")
    lines.append("")
    skills_text = payload.get("skills_text")
    if skills_text:
        lines.append(skills_text.rstrip())
    elif skills:
        lines.append(f"Loaded skills: {', '.join(skills)}")
    else:
        lines.append("_(no skills loaded — see `## Meta` for diagnosis)_")
    lines.append("")

    composition = payload.get("composition")
    if composition:
        lines.append("## Composition")
        lines.append("")
        lines.append(composition.rstrip())
        lines.append("")

    lines.append("## Meta")
    lines.append("")
    meta = payload.get("meta") or {}
    lines.append("```json")
    lines.append(json.dumps(meta, ensure_ascii=False, indent=2))
    lines.append("```")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
