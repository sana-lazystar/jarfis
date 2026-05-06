# Rule: Context7 MCP Research (proactive pattern)

> **Locale**: All emitted user-facing output respects `$LOCALE`.
> **Status**: Accepted (ADR-0005, v4.1.1).
> **Applies to**: Phase 4 implement sub-agents (`backend-developer`,
> `frontend-developer`, `devops-engineer`, `security-engineer`).

---

## §1 Mission

Skills (`commands/jarfis/skills/*.md`) carry **opinions** — decision
heuristics + anti-patterns + version notes. Context7 MCP carries
**facts** — official docs (API, syntax, version). The two are
*complementary*. This rule defines how the implement sub-agent uses
both.

Hard rule: **skill > context7**. When a skill's anti-pattern covers a
topic, do not call context7 on it. Skills win on conflict.

---

## §2 Trigger — proactive identification

At the start of a Phase 4 implement run, **before writing any code**:

1. Read the work-item description and `state.workspace.scope[i]`.
2. Enumerate the external libraries / APIs the work will touch.
3. For each library:
   a. Look up the matching skill in `commands/jarfis/skills/` (e.g.
      `react-native` for an RN screen, `postgres` for a query change).
   b. Read the skill's **Decision Heuristics** + **Anti-patterns**
      sections. If the skill answers the question, **stop here** —
      do not call context7.
   c. If the skill is silent on the specific API the work needs (or
      no skill exists for the library), continue to §3 disambiguation
      and §4 cost guard.

Reactive trigger ("call when uncertain") is rejected by ADR-0005 §2.2:
self-awareness is unreliable, the path becomes non-deterministic, and
regression tests cannot pin it down.

---

## §3 Library disambiguation (3-tier)

`mcp__context7__resolve-library-id` returns multiple candidates per
library. Apply the tiers below; the first to produce a `library_id`
wins.

### Tier 1 — Skill hint pin

Open the matching skill `.md` and parse the leading HTML-comment
block:

```markdown
<!-- jarfis:context7
library_id: /facebook/react-native-website
query_topics: [navigation, native modules, gradle, hermes, metro]
-->
```

If `library_id` is present, use it directly. **Disambiguation is
already curated.** This is the common path for the 17 v4.1.1 skills.

Helper: `python3 -c "from jarfis.compose.context7_research import parse_skill_hint; print(parse_skill_hint('<path>'))"`

### Tier 2 — Tech Stack versioned ID

Read `.jarfis-project/project-profile.md` `## Tech Stack` for an
explicit version (e.g. `React Native 0.74`, `Postgres 16`). When the
chosen candidate's `versions` list contains a matching entry, pin to
the versioned form `/<org>/<project>/v<X.Y.Z>`. Falls back to base ID
when no match.

### Tier 3 — Autonomous decision tree (no skill hint)

When the library has no skill (or the skill has no hint):

1. Filter to `Source Reputation == High`.
2. Prefer libraries whose first path segment is in the **official-org
   allowlist**: `facebook`, `vercel`, `vuejs`, `reactjs`, `nodejs`,
   `expressjs`, `postgres`, `redis`, `rust-lang`, `tauri-apps`,
   `biomejs`, `awsdocs`, `microsoft`, `mdn`. Falls back to all
   `High` candidates when none match.
3. Drop any candidate whose `library_id` contains `archive`, `old`,
   or `deprecated`.
4. Drop candidates with `Benchmark Score < 60`.
5. Tie-break by code-snippet count desc, then benchmark score desc.
6. Empty pool at any step → **abort context7 for this library**.
   Fall back to the matching skill's heuristics (if any) and/or
   `WebSearch`.

Helper: `select_library_id(candidates, scope_version=...)` from
`jarfis.compose.context7_research`. The Python helper bakes in steps
1–6 so the agent only needs to pass the parsed candidate list.

---

## §4 Cost guard

A single Phase 4 sub-agent invocation may issue at most **5 real
`mcp__context7__query-docs` calls**. The cap is enforced through
`ResearchSession`:

```python
from jarfis.compose.context7_research import ResearchSession
session = ResearchSession()                    # cost_guard=5 default
status = session.can_query(library_id, query)  # "ok"|"cache"|"blocked"|"skill_blocked"
```

* `cache` — already queried in this session; reuse `session.cached(...)`.
* `skill_blocked` — caller asserted that the skill's anti-pattern
  covers this query; record-and-skip.
* `blocked` — guard exhausted; do not call MCP. Document the
  unanswered question and proceed with skill heuristics or
  best-effort.

After a real MCP call, persist the result via `session.record(library_id, query, docs)`.
Recording the same `(library_id, query)` twice does not consume an
extra slot — cache duplicates are free.

The `5` figure is provisional (ADR-0005 §2.4); v4.1.2 may revise it
based on testbed measurement.

---

## §5 Skill priority (anti-pattern wins)

The order of evidence when applying docs to code:

1. **Skill anti-pattern** — overrides anything else. If the skill
   says "do not use `setState` inside `onScroll`", context7 examples
   showing inline `setState` do not legitimize it.
2. **Skill decision heuristic** — preferred when applicable
   (e.g. "use `FlashList` over `FlatList` for 100+ rows").
3. **Context7 docs** — fills the *factual* gap (exact prop name,
   version-specific signature, deprecated alternative).
4. **Model prior knowledge** — last resort; treat as suspect for
   recently-released APIs.

When (1) and (3) conflict, file a comment in the implementation
explaining the deviation, and prefer (1).

---

## §6 Telemetry

Every query (real, cached, or skill-blocked) emits one
`context7_query_emitted` event when `JARFIS_TRACE` is enabled
(ADR-0005 §2.7):

```json
{
  "event": "context7_query_emitted",
  "attrs": {
    "library_id": "/facebook/react-native-website",
    "query": "navigation API",
    "source": "hint" | "autonomous",
    "tier_used": 1 | 2 | 3,
    "cache_hit": false,
    "skill_pre_check_blocked": false
  }
}
```

Helper: `session.emit(library_id=..., query=..., source=...,
tier_used=..., cache_hit=..., skill_pre_check_blocked=...)`.

Telemetry failure never propagates — it is best-effort.

---

## §7 Failure modes (graceful)

| Condition | Behavior |
|-----------|----------|
| MCP tool unavailable | Skip context7 entirely; rely on skills + WebSearch. Log a single warning trace event. |
| `resolve-library-id` returns 0 candidates | Abort for this library; document gap. |
| Tier 3 decision tree empty after filters | Abort; document gap. |
| Cost guard exhausted | Stop calling MCP; finish work with collected facts. |

The implement run **must not fail** because context7 was unavailable
or guard-limited. Skill-only path is the resilient baseline.

---

— end of rule —
