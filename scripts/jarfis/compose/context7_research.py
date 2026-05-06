"""Context7 research helper — skill-hint parsing + 3-tier disambiguation.

This module is a *logic helper* for the Phase 4 implement sub-agent flow
described in ``commands/jarfis/rules/context7-research.md`` (B15, v4.1.1).
It does NOT itself invoke MCP tools — those are reachable only from the
agent harness. Instead, the agent calls this module's pure-Python helpers
to:

  1. Parse a skill's ``<!-- jarfis:context7 ... -->`` hint to obtain a
     pre-pinned ``library_id`` (Tier 1 of the 3-tier disambiguation).
  2. Apply the autonomous decision tree to a list of candidate libraries
     returned by ``mcp__context7__resolve-library-id`` (Tier 3).
  3. Track per-invocation cost-guard counter + ``(library_id, query)``
     cache via :class:`ResearchSession`, so the agent can decide whether
     to issue a real MCP call, return a cached docstring, or refuse.
  4. Emit ``context7_query_emitted`` telemetry events through
     :mod:`jarfis.trace`.

ADR-0005 (v4.1.1) drives the design. Tests in
``scripts/tests/test_context7_integration.py`` cover all branches.
"""

import os
import re

from .. import trace


# ── Constants ──────────────────────────────────────────────────────────

DEFAULT_COST_GUARD = 5  # ADR-0005 §2.4 — 잠정값, v4.1.2 testbed 후 조정.

#: Recognized official maintainers for Tier 3 step 2. Library IDs are
#: typically of the form ``/<org>/<project>`` or ``/websites/<host>``;
#: any candidate whose first path segment is in this set is preferred
#: over generic mirrors / archives.
OFFICIAL_ORG_ALLOWLIST = frozenset({
    "facebook",
    "vercel",
    "vuejs",
    "reactjs",
    "nodejs",
    "expressjs",
    "postgres",
    "redis",
    "rust-lang",
    "rust-lang-nursery",
    "tauri-apps",
    "biomejs",
    "awsdocs",
    "microsoft",
    "mdn",
})

#: Tokens that mark a stale or non-canonical library ID.
_BAD_TOKENS = ("archive", "old", "deprecated")

#: Minimum benchmark score required for autonomous selection.
_MIN_BENCHMARK_SCORE = 60


# ── Skill hint parsing (Tier 1) ────────────────────────────────────────


_HINT_BLOCK_PATTERN = re.compile(
    r"<!--\s*jarfis:context7\s*\n(.*?)\n\s*-->",
    re.DOTALL,
)
_LIBRARY_ID_KEY = re.compile(r"^\s*library_id\s*:\s*(\S+)\s*$", re.MULTILINE)
_QUERY_TOPICS_KEY = re.compile(
    r"^\s*query_topics\s*:\s*\[(.*?)\]\s*$", re.MULTILINE
)


def parse_skill_hint(skill_path):
    """Extract the ``jarfis:context7`` HTML-comment hint from a skill .md.

    Format expected::

        <!-- jarfis:context7
        library_id: /facebook/react-native-website
        query_topics: [navigation, native modules, gradle]
        -->

    The first hint block in the file wins; subsequent blocks are
    ignored. ``library_id`` is mandatory; ``query_topics`` is optional
    and tolerates either a bracketed list or a plain comma-separated
    line. Whitespace is forgiving.

    Args:
        skill_path: absolute path to the skill .md file.

    Returns:
        dict with ``library_id`` (str) and ``query_topics`` (list[str])
        keys, or ``None`` when the file is missing, has no hint block,
        or the block lacks ``library_id``.
    """
    if not skill_path or not os.path.isfile(skill_path):
        return None
    try:
        with open(skill_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None

    block_match = _HINT_BLOCK_PATTERN.search(text)
    if not block_match:
        return None

    body = block_match.group(1)

    lib_match = _LIBRARY_ID_KEY.search(body)
    if not lib_match:
        return None
    library_id = lib_match.group(1).strip()
    if not library_id:
        return None

    topics = []
    topics_match = _QUERY_TOPICS_KEY.search(body)
    if topics_match:
        raw = topics_match.group(1)
        topics = [t.strip() for t in raw.split(",") if t.strip()]

    return {"library_id": library_id, "query_topics": topics}


# ── Autonomous decision tree (Tier 2/3) ────────────────────────────────


def _is_official_org(library_id, allowlist):
    if not library_id or not library_id.startswith("/"):
        return False
    parts = library_id.split("/")
    if len(parts) < 3:
        return False
    return parts[1] in allowlist


def _has_bad_token(library_id):
    lid = (library_id or "").lower()
    return any(t in lid for t in _BAD_TOKENS)


def _versioned_id(base_id, versions, scope_version):
    """Tier 2 — return a versioned form of ``base_id`` when ``scope_version``
    matches one of the candidate's known versions.

    Match rules:
        * ``"0.74.0"`` matches ``"v0.74.0"`` (leading-v normalization).
        * Exact match preferred; partial prefix match (``"0.74"`` →
          ``"v0.74.0"``) accepted as fallback.
        * No match → return ``base_id`` (latest).
    """
    if not scope_version or not versions:
        return base_id

    target = scope_version.lstrip("v")
    for v in versions:
        candidate = v.lstrip("v")
        if candidate == target:
            return f"{base_id}/{v}"
    # prefix fallback
    for v in versions:
        candidate = v.lstrip("v")
        if candidate.startswith(target):
            return f"{base_id}/{v}"
    return base_id


def select_library_id(candidates, *, scope_version=None, allowlist=None):
    """Apply the Tier 3 autonomous decision tree to a candidate list.

    Decision steps (ADR-0005 §2.3):
        1. ``source_reputation == "High"`` only.
        2. Prefer official-org allowlist; fall back to all High when none.
        3. Drop ``library_id`` containing ``archive``/``old``/``deprecated``.
        4. ``benchmark_score >= 60`` only.
        5. Tie-break by ``code_snippets`` desc, then ``benchmark_score`` desc.
        6. Tier 2: if ``scope_version`` provided and the chosen candidate
           publishes versions, return the closest versioned ID; else the
           base ID.
        7. Empty pool at any step → return ``None``.

    Args:
        candidates: list of dicts with at least ``library_id``,
            ``source_reputation``, ``benchmark_score`` keys; optional
            ``code_snippets`` (int) and ``versions`` (list[str]).
        scope_version: optional semver-ish string from project Tech Stack.
        allowlist: optional override for :data:`OFFICIAL_ORG_ALLOWLIST`.

    Returns:
        Selected ``library_id`` (possibly versioned), or ``None`` when no
        candidate passes the tree.
    """
    if not candidates:
        return None

    allow = allowlist if allowlist is not None else OFFICIAL_ORG_ALLOWLIST

    # 1: High reputation only
    pool = [c for c in candidates if c.get("source_reputation") == "High"]
    if not pool:
        return None

    # 2: official-org preference
    official = [c for c in pool if _is_official_org(c.get("library_id"), allow)]
    if official:
        pool = official

    # 3: drop bad tokens
    pool = [c for c in pool if not _has_bad_token(c.get("library_id"))]
    if not pool:
        return None

    # 4: benchmark score gate
    pool = [c for c in pool if (c.get("benchmark_score") or 0) >= _MIN_BENCHMARK_SCORE]
    if not pool:
        return None

    # 5: tie-break
    pool.sort(
        key=lambda c: (
            -(c.get("code_snippets") or 0),
            -(c.get("benchmark_score") or 0),
        )
    )
    chosen = pool[0]
    base_id = chosen.get("library_id")
    if not base_id:
        return None

    # 6: Tier 2 versioning
    return _versioned_id(base_id, chosen.get("versions") or [], scope_version)


# ── Per-invocation session state ───────────────────────────────────────


class CostGuardExceeded(Exception):
    """Raised when a query would exceed the session's cost guard."""


class ResearchSession:
    """Per-sub-agent-invocation state for cost guard + cache + telemetry.

    The :attr:`cost_guard` counts only *real* MCP ``query-docs`` calls
    that the agent issues — cache hits and pre-checked skips do not
    count. Each session is local to one Phase 4 implement run; a fresh
    session is constructed at the start of work.

    Typical agent loop::

        session = ResearchSession()
        for q in identified_queries:
            status = session.can_query(library_id, q)
            if status == "blocked":
                continue                # cost guard exhausted
            if status == "skill_blocked":
                continue                # skill anti-pattern wins
            if status == "cache":
                docs = session.cached(library_id, q)
            else:
                docs = mcp.query_docs(library_id, q)   # agent-side MCP call
                session.record(library_id, q, docs)
            apply(docs)
    """

    def __init__(self, cost_guard=None, telemetry=None):
        self.cost_guard = (
            cost_guard if cost_guard is not None else DEFAULT_COST_GUARD
        )
        self._cache = {}
        self._calls_made = 0
        # Tests substitute this with a callable; production path uses
        # :func:`jarfis.trace.log_event`.
        self._telemetry = telemetry

    # ---- inspection ----

    @property
    def calls_made(self):
        return self._calls_made

    @property
    def remaining(self):
        return max(0, self.cost_guard - self._calls_made)

    def cached(self, library_id, query):
        """Return the cached docs string for ``(library_id, query)`` or None."""
        return self._cache.get((library_id, query))

    def can_query(self, library_id, query, *, skill_blocked=False):
        """Classify the next query without mutating session state.

        Returns one of:
            ``"skill_blocked"`` — anti-pattern domain; agent must skip
            ``"cache"``         — already cached, no MCP call needed
            ``"blocked"``       — cost guard exhausted
            ``"ok"``            — fresh, MCP call permitted
        """
        if skill_blocked:
            return "skill_blocked"
        if (library_id, query) in self._cache:
            return "cache"
        if self._calls_made >= self.cost_guard:
            return "blocked"
        return "ok"

    # ---- mutation ----

    def record(self, library_id, query, result):
        """Record the result of a real MCP ``query-docs`` call.

        Increments the counter only for first-time entries. Subsequent
        calls with the same key overwrite the cached result without
        affecting the cost guard.

        Raises:
            CostGuardExceeded: when recording a *new* (uncached) entry
                would exceed :attr:`cost_guard`.
        """
        key = (library_id, query)
        if key not in self._cache:
            if self._calls_made >= self.cost_guard:
                raise CostGuardExceeded(
                    f"cost guard {self.cost_guard} exceeded"
                )
            self._calls_made += 1
        self._cache[key] = result
        return result

    # ---- telemetry ----

    def emit(self, *, library_id, query, source, tier_used,
             cache_hit=False, skill_pre_check_blocked=False):
        """Emit a ``context7_query_emitted`` event (ADR-0005 §2.7).

        Routes to the injected telemetry callable when set; otherwise
        falls back to :func:`jarfis.trace.log_event` (no-op when
        ``JARFIS_TRACE`` is unset).
        """
        attrs = {
            "library_id": library_id,
            "query": query,
            "source": source,
            "tier_used": tier_used,
            "cache_hit": bool(cache_hit),
            "skill_pre_check_blocked": bool(skill_pre_check_blocked),
        }
        if self._telemetry is not None:
            try:
                self._telemetry(attrs)
            except Exception:
                pass
            return
        try:
            trace.log_event("context7_query_emitted", attrs)
        except Exception:
            pass
