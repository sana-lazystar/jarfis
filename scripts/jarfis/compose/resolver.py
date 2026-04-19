"""Resolve base+path pairs into absolute filesystem paths.

The five `base` kinds map to different roots within `state`:
    project       scope[scope_index].path               (per-project only)
    all-projects  [scope[i].path for all i]             (work-wide only)
    docs          state.work.docsDir                    (any scope)
    org           state.org.root                        (any; None if org==null)
    org_wiki      state.org.root / .jarfis-org/wiki     (any; None if org==null)

`resolve_working_dir` follows the same per-project/work-wide split (M11).
"""

import os

from .errors import ScopeIndexError


ORG_WIKI_SUBDIR = os.path.join(".jarfis-org", "wiki")


def resolve_path(base, path, state, scope_index):
    """Resolve one (base, path) pair to absolute filesystem target(s).

    Returns:
        str         absolute path (project / docs / org / org_wiki)
        list[str]   list of absolute paths (all-projects)
        None        when state lacks the needed root (org=null)

    Raises:
        ScopeIndexError — scope_index missing or out of range for project base.
    """
    if base == "project":
        scope = _require_scope(state)
        if scope_index is None:
            raise ScopeIndexError(
                "base=project requires scope_index (per-project agent)"
            )
        if scope_index < 0 or scope_index >= len(scope):
            raise ScopeIndexError(
                f"scope_index={scope_index} out of range (scope has "
                f"{len(scope)} entries)"
            )
        return os.path.join(scope[scope_index]["path"], path)

    if base == "all-projects":
        scope = _require_scope(state)
        return [os.path.join(entry["path"], path) for entry in scope]

    if base == "docs":
        docs_dir = _safe_get(state, "work", "docsDir")
        if not docs_dir:
            raise ScopeIndexError("state.work.docsDir missing for base=docs")
        return os.path.join(docs_dir, path)

    if base == "org":
        org = state.get("org")
        if not org:
            return None
        return os.path.join(org["root"], path)

    if base == "org_wiki":
        org = state.get("org")
        if not org:
            return None
        return os.path.join(org["root"], ORG_WIKI_SUBDIR, path)

    raise ScopeIndexError(f"Unknown base: {base!r}")


def resolve_working_dir(scope, state, scope_index):
    """Return the working directory for the sub-agent spawn (M11).

    - per-project → scope[scope_index].path
    - work-wide   → state.work.docsDir
    """
    if scope == "per-project":
        scopes = _require_scope(state)
        if scope_index is None:
            raise ScopeIndexError(
                "per-project agent requires --scope-index"
            )
        if scope_index < 0 or scope_index >= len(scopes):
            raise ScopeIndexError(
                f"scope_index={scope_index} out of range (scope has "
                f"{len(scopes)} entries)"
            )
        return scopes[scope_index]["path"]

    if scope == "work-wide":
        docs_dir = _safe_get(state, "work", "docsDir")
        if not docs_dir:
            raise ScopeIndexError("state.work.docsDir missing for work-wide scope")
        return docs_dir

    raise ScopeIndexError(f"Unknown scope: {scope!r}")


def _require_scope(state):
    scope = _safe_get(state, "workspace", "scope")
    if not isinstance(scope, list) or not scope:
        raise ScopeIndexError("state.workspace.scope missing or empty")
    return scope


def _safe_get(mapping, *keys):
    cur = mapping
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur
