"""Frozen data models for compose module.

Immutable config (ContextEntry, AgentConfig, ScopeEntry) protects validated
state after load. ComposeResult is mutable: __main__ incrementally fills meta.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextEntry:
    """A single `context[]` entry under an agent in agent-composition.yaml.

    importance (system-spec §5.5):
        "required"     — missing blocks proper agent operation (loud warning)
        "recommended"  — nice to have (silent meta record)
        "optional"     — informational (meta may omit)
    """

    base: str
    path: str
    sections: tuple[str, ...] | None = None
    optional: bool = True
    importance: str = "recommended"


@dataclass(frozen=True)
class AgentConfig:
    """A single agent entry from `agents.<name>` in agent-composition.yaml."""

    name: str
    persona: str
    scope: str
    model: str | None = None
    skills_from_domain: bool = False
    context: tuple[ContextEntry, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScopeEntry:
    """One entry from `state.workspace.scope[]`."""

    name: str
    type: str
    path: str
    framework: str
    languages: tuple[str, ...] = field(default_factory=tuple)
    branch: str = ""
    baseCommit: str = ""


@dataclass
class ComposeResult:
    """Final output assembled by __main__.

    Standardized meta keys (kept in sync with m2-test-results.md):
        scope_entry          — dict snapshot of workspace.scope[i]
                               (name/type/framework/languages/branch/baseCommit).
                               Present only for per-project agents.
        skills_loaded        — list[str] of skill identifiers actually loaded.
                               Empty when skills_from_domain is false or
                               domain/role mapping is missing.
        truncated_skills     — list[{name, reason}] of skills omitted
                               (token_budget_exceeded / file_not_found / file_too_large).
        skills_meta          — dict from compose/skills.py. Keys among:
                               no_domain / no_role_mapping / domain / role /
                               domain_fallback / domain_fallback_reason.
                               Omitted when skills_from_domain is false.
        context_files        — list of per-entry records:
                               {path, importance, sections?, injected,
                                reason?, missing_sections?}.
                               importance ∈ {required, recommended, optional}
                               matches ContextEntry.importance verbatim so
                               downstream callers classify without lookup.
        locale_fallback      — bool, true when state.locale was missing and
                               assembler defaulted to "ko".
        working_dir_warning  — str, present when work-wide agent received
                               --scope-index (value is ignored).
    """

    subagent_type: str
    model: str | None
    prompt: str
    working_dir: str
    meta: dict
