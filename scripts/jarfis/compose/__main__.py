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
            for idx, sub_target in enumerate(target):
                scope_name = state["workspace"]["scope"][idx].get("name", f"idx{idx}")
                rr = read_and_extract(sub_target, entry.sections, optional=entry.optional)
                if rr.text:
                    joined_parts.append(f"### ({scope_name})\n{rr.text.strip()}")
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


if __name__ == "__main__":
    main()
