"""Domain exceptions for compose module.

All raised errors derive from `ComposeError` so __main__ can catch a single base
and emit a structured JSON error on stderr + exit 1.
"""


class ComposeError(Exception):
    """Base class for all compose-domain errors."""


class ConfigError(ComposeError):
    """agent-composition.yaml schema or semantic violation."""


class AgentNotFoundError(ComposeError):
    """Requested agent name missing from agent-composition.yaml."""


class PersonaNotFoundError(ComposeError):
    """Referenced persona markdown file not found."""


class ScopeIndexError(ComposeError):
    """scope_index missing for per-project agent or out of range."""


class OrgNotRegisteredError(ComposeError):
    """state.org is null while org/org_wiki base is requested.

    Usually not raised (optional skip). Reserved for strict mode callers.
    """
