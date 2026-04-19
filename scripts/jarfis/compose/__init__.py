"""JARFIS Compose — Deterministic agent composition for v4.

Entry: `python3 -m jarfis.compose --agent <name> [--scope-index N] --state <path>`

Responsibilities (system-spec §5.6):
    models      — frozen dataclasses (AgentConfig, ContextEntry, ScopeEntry, ComposeResult)
    errors      — domain exceptions
    config      — agent-composition.yaml load + validation
    resolver    — base 5 kinds → absolute path + working_dir
    reader      — Markdown read + section extraction
    skills      — delegate to v3 domain.load_skills_for_role
    assembler   — locale + persona + skills + context + task → final prompt
    __main__    — argparse + orchestration + JSON stdout
"""
