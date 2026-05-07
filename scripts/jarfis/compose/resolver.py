"""Resolve base+path pairs into absolute filesystem paths.

The five `base` kinds map to different roots within `state`:
    project       scope[scope_index].path               (per-project only)
    all-projects  [scope[i].path for all i]             (work-wide only)
    docs          state.work.docsDir                    (any scope)
    org           state.org.root                        (any; None if org==null)
    org_wiki      state.org.root / .jarfis-org/wiki     (any; None if org==null)

`resolve_working_dir` follows the same per-project/work-wide split (M11).

`all-projects` walk-up (monorepo SSOT, v4.2):
    When `path` starts with `.jarfis-project/`, the resolver probes each
    `scope[i].path` for the requested file; if absent, it walks parent
    directories one step at a time until a match is found or a boundary
    is hit. Boundaries (most restrictive first):
        1. `state.org.root` — never cross above the registered org root.
        2. Nearest ancestor `.git/` — VCS root sentinel.
        3. Hard depth limit = 3 parent moves — final guard.
    Resolved paths are deduped; when 2+ scopes share an SSOT, the entry
    records all originating scope indices via `from_scope_indices`.

    Return shape for `.jarfis-project/` paths is `list[dict]` with keys
    `{path, from_scope_indices}`. For other paths the legacy `list[str]`
    is preserved (caller distinguishes by element type).
"""

import os

from .errors import ScopeIndexError


ORG_WIKI_SUBDIR = os.path.join(".jarfis-org", "wiki")
_WALKUP_PREFIX = ".jarfis-project" + os.sep
_WALKUP_DEPTH_LIMIT = 3


def resolve_path(base, path, state, scope_index):
    """Resolve one (base, path) pair to absolute filesystem target(s).

    Returns:
        str           absolute path (project / docs / org / org_wiki)
        list[str]     list of absolute paths (all-projects, non-walkup paths)
        list[dict]    list of {path, from_scope_indices} entries
                      (all-projects, .jarfis-project/ paths — supports
                      monorepo SSOT walk-up + dedupe)
        None          when state lacks the needed root (org=null)

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
        if _is_walkup_path(path):
            return _resolve_all_projects_walkup(path, scope, state)
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


# ── Walk-up helpers (monorepo SSOT) ──────────────────────────────────


def _is_walkup_path(path):
    """True iff `path` is gated for walk-up resolution (.jarfis-project/...).

    Accepts both POSIX (`/`) and OS-native separators so YAML configs that
    hard-code `/` work on every platform.
    """
    return path.startswith(".jarfis-project/") or path.startswith(_WALKUP_PREFIX)


def _resolve_all_projects_walkup(path, scope, state):
    """Walk-up resolver for `.jarfis-project/`-prefixed paths.

    Returns list[dict] with deduped {path, from_scope_indices} entries.
    Falls back to the original probe path when no SSOT is reachable
    within the boundary (so reader.read_and_extract can mark file_not_found).
    """
    org_root = _safe_get(state, "org", "root")

    # Map abs_path → first-seen index in result list (for dedupe).
    by_path = {}
    result = []

    for i, entry in enumerate(scope):
        scope_path = entry["path"]
        resolved, _boundary, _steps = _walkup_for_scope(
            scope_path, path, org_root
        )
        abs_resolved = os.path.abspath(resolved)
        if abs_resolved in by_path:
            result[by_path[abs_resolved]]["from_scope_indices"].append(i)
        else:
            by_path[abs_resolved] = len(result)
            result.append({"path": resolved, "from_scope_indices": [i]})

        _emit_trace(i, scope_path, path, resolved, _steps, _boundary, by_path)

    return result


def _walkup_for_scope(scope_path, rel_path, org_root):
    """Walk parents of `scope_path` looking for `rel_path`.

    Returns (resolved_path, boundary_hit, steps).
        resolved_path  — absolute path of found file, or original probe
                         (`scope_path/rel_path`) when not found.
        boundary_hit   — "found" | "org_root" | "git_ancestor" | "depth_limit"
        steps          — number of parent moves (0 if found at scope_path).

    Boundary precedence (each checked at the *current* candidate dir
    BEFORE probing — so the candidate itself never crosses the boundary):
        1. org_root — if set and current dir is at-or-above org_root,
           but we already moved up past org_root → stop.
        2. .git ancestor — if current dir contains a .git, stop after probing.
        3. depth limit (3 parent moves) — hard guard.

    The candidate dir at step k is reached by moving up k times from
    scope_path. We probe at each candidate (including step 0). After a
    successful probe we return immediately (`found`). We refuse to move
    above org_root or above a .git directory.
    """
    org_root_abs = os.path.abspath(org_root) if org_root else None
    candidate = os.path.abspath(scope_path)
    probe_path = os.path.join(scope_path, rel_path)

    for steps in range(_WALKUP_DEPTH_LIMIT + 1):
        target = os.path.join(candidate, rel_path)
        if os.path.isfile(target):
            return target, "found", steps

        # Decide whether to move up further.
        if steps == _WALKUP_DEPTH_LIMIT:
            return probe_path, "depth_limit", steps

        # .git boundary: if candidate has a .git dir/file, do not climb past it.
        # (We probed the candidate above; refuse to move above it.)
        if os.path.exists(os.path.join(candidate, ".git")):
            return probe_path, "git_ancestor", steps

        parent = os.path.dirname(candidate)
        if parent == candidate:
            # filesystem root — cannot climb further.
            return probe_path, "depth_limit", steps

        # org_root boundary: refuse to move above org_root.
        # (If candidate IS org_root, parent would be above it.)
        if org_root_abs is not None and candidate == org_root_abs:
            return probe_path, "org_root", steps

        candidate = parent

    return probe_path, "depth_limit", _WALKUP_DEPTH_LIMIT


def _emit_trace(scope_index, scope_path, requested_rel, resolved, steps,
                boundary, by_path):
    """Best-effort JARFIS_TRACE emission for compose_walkup_resolved.

    Failure is silent — trace must never break compose.
    """
    try:
        from jarfis import trace
        trace.log_event("compose_walkup_resolved", {
            "scope_index": scope_index,
            "scope_path": scope_path,
            "requested_path": requested_rel,
            "resolved_path": resolved,
            "walkup_steps": steps,
            "boundary_hit": boundary,
            "shared_with": [
                # All scopes that have already resolved here (excluding self).
                # `by_path` is keyed by abs_path → result-list index; we
                # cannot recover scope-index lists from it without extra
                # state, so trace just records the count.
            ],
        })
    except Exception:
        pass


# ── Internal ────────────────────────────────────────────────────────


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
