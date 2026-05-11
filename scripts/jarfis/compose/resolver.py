"""Resolve base+path pairs into absolute filesystem paths.

The five `base` kinds map to different roots within `state`:
    project       scope[scope_index].path               (per-project only)
    all-projects  [scope[i].path for all i]             (work-wide only)
    docs          state.work.docsDir                    (any scope)
    org           state.org.root                        (any; None if org==null)
    org_wiki      state.org.root / .jarfis-org/wiki     (any; None if org==null)

`resolve_working_dir` follows the same per-project/work-wide split (M11).

`all-projects` walk-up (monorepo SSOT, v4.2; depth bumped to 5 in
sys-implement monorepo-ssot-walkup-fix-v1):
    When `path` starts with `.jarfis-project/` or `.jarfis-org/`, the
    resolver probes each `scope[i].path` for the requested file; if
    absent, it walks parent directories one step at a time until a match
    is found or a boundary is hit. Boundaries (most restrictive first):
        1. `state.org.root` — never cross above the registered org root.
        2. Nearest ancestor `.git/` — VCS root sentinel.
        3. Hard depth limit = 5 parent moves — final guard.
    Resolved paths are deduped; when 2+ scopes share an SSOT, the entry
    records all originating scope indices via `from_scope_indices`.

    Return shape for walk-up-gated paths (`.jarfis-project/` and
    `.jarfis-org/`) is `list[dict]` with keys `{path, from_scope_indices}`.
    For other paths the legacy `list[str]` is preserved (caller
    distinguishes by element type).

Placeholder substitution (Stage 6a — ia-spine-stage6a-org-wiki):
    `path` may contain literal `{project_slug}` placeholders. When the
    caller supplies `slug_context={"project_slug": "<name>"}`, every
    occurrence is replaced BEFORE `os.path.join` so the resolved
    filesystem target points at the real per-project directory (e.g.
    `wiki/PO/projects/myproj/ia/manifest.json`). Unknown placeholder
    keys are left literal — the reader will then mark file_not_found
    instead of raising. Supported placeholders for Stage 6a:
        `{project_slug}` — value from `state.workspace.scope[0].name`
                           (single-project work); monorepo multi-scope
                           semantics deferred to Stage 6b+.
"""

import os
import re

from .errors import ScopeIndexError


ORG_WIKI_SUBDIR = os.path.join(".jarfis-org", "wiki")
_WALKUP_PREFIXES = (
    ".jarfis-project" + os.sep,
    ".jarfis-org" + os.sep,
)
_WALKUP_DEPTH_LIMIT = 5  # was 3 — bumped per sys-implement monorepo-ssot-walkup-fix-v1

# Stage 6a — placeholder pattern: `{name}` where name is an identifier.
# Unknown keys are left literal (the file_not_found path remains the caller's
# diagnostic surface — we never raise on missing placeholder data).
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _interpolate_placeholders(path, ctx):
    """Substitute `{key}` placeholders in `path` using `ctx` mapping.

    Args:
        path: path string with optional `{key}` placeholders.
        ctx:  dict mapping placeholder name → value. May be falsy/None
              (no substitution attempted; path returned unchanged).

    Returns:
        str — path with known placeholders replaced; unknown ones left
        literal.

    Stage 6a supported keys: `project_slug` (state.workspace.scope[0].name
    when work has exactly one scope). Missing key in ctx → literal preserved
    (caller's choice — reader will mark file_not_found downstream).
    """
    if not ctx:
        return path

    def _repl(match):
        key = match.group(1)
        if key in ctx and ctx[key] is not None:
            return str(ctx[key])
        return match.group(0)  # leave literal `{key}` when unknown

    return _PLACEHOLDER_RE.sub(_repl, path)


def resolve_path(base, path, state, scope_index, slug_context=None):
    """Resolve one (base, path) pair to absolute filesystem target(s).

    Args:
        base:         one of {project, all-projects, docs, org, org_wiki}.
        path:         relative path from the base, may contain `{key}`
                      placeholders (see Stage 6a docstring).
        state:        loaded `.jarfis-state.json` dict.
        scope_index:  0-based index into `state.workspace.scope[]` (required
                      for `project`).
        slug_context: optional dict for placeholder substitution. None →
                      placeholders pass through untouched (back-compat).

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
    # Stage 6a — substitute placeholders BEFORE joining so the resulting
    # filesystem target is real (e.g. wiki/PO/projects/myproj/ia/manifest.json).
    if slug_context:
        path = _interpolate_placeholders(path, slug_context)

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
    """True iff `path` is gated for walk-up resolution.

    Accepts both POSIX (`/`) and OS-native separators so YAML configs
    hard-coding `/` work on every platform.

    Currently gated prefixes: `.jarfis-project/`, `.jarfis-org/`.
    """
    posix_prefixes = (".jarfis-project/", ".jarfis-org/")
    if any(path.startswith(p) for p in posix_prefixes):
        return True
    return any(path.startswith(p) for p in _WALKUP_PREFIXES)


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
        3. depth limit (5 parent moves) — hard guard.

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
