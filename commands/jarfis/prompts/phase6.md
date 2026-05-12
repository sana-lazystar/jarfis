# Phase 6: Retrospective + Wiki Sync

> Executed by **jarfis-foreman** inside tmux. jarfis-foreman is the **orchestrator**:
>   - Spawns tech-lead-strategist via Task — the sub-agent produces retrospective.md AND performs Wiki Track A (text wiki extraction + merge) in a single run, because both require reading $DOCS_DIR/ artifacts.
>   - Runs small orchestrator-only steps: workflow metrics TSV append (state only), Track B (`rsync` + templated `_index.html`), **INDEX.md auto-rebuild via `jarfis_cli.py wiki rebuild-index`**, Track C (CLI), Wiki Update Summary append (writes only).
>   - **Acquires an org-level `wiki.lock` flock** around the entire Wiki update (Track A/B/INDEX-rebuild/C) to prevent concurrent `/jarfis:work` races.
> It does NOT read $DOCS_DIR source artifacts itself.
> All sub-agent artifacts in English. User-facing messages in $LOCALE.

**Execution context**:
- `$DOCS_DIR` = tmux workspace
- `$STATE_FILE` = `$DOCS_DIR/.jarfis-state.json`

### jarfis-foreman precompute (from $STATE_FILE)

- `$ORG_ROOT` = `state.org.root` (empty when org not registered — Step 2 metrics + Step 3/4/5 wiki sync fully skip)
- `$SCOPE` = `state.workspace.scope[]`
- `$HAS_FRONTEND` = "true" if any `scope[].type == "frontend"`, else "false"
- `$LEARNING_CANDIDATES_JSON` = `state.learning_candidates` (carried over from Phase 5 meta; `"[]"` if empty)
- `$WORK_NAME` = `state.work.name`
- `$PROJECTS_JSON` = compact JSON array of `{name}` from scope[] (used for Track B project loop)

## Required Inputs (consumed by tech-lead-strategist sub-agent)

- `$DOCS_DIR/discovery/prd.md`
- `$DOCS_DIR/planning/architecture.md`
- `$DOCS_DIR/planning/tasks.md`
- `$DOCS_DIR/review/review.md`
- `$DOCS_DIR/discovery/ia/manifest.json` + `$DOCS_DIR/discovery/ia/pages/` — work IA (Stage 6a TASK B-2 의 work-side input)
- `$DOCS_DIR/discovery/ia/.baseline/manifest.json` + `.baseline/pages/` — Phase 1b 의 baseline snapshot (Stage 6a TASK B-2 의 baseline-side input)

## Conditional Inputs (consumed by tech-lead-strategist sub-agent)

- `$DOCS_DIR/review/diagnosis.md` — when Phase 5 diagnosed issues
- `$ORG_ROOT/.jarfis-org/wiki/INDEX.md` + section `_index.md` + existing wiki files — when `$ORG_ROOT` non-empty (Track A merge target)
- `$ORG_ROOT/.jarfis-org/wiki/PO/projects/{project_slug}/ia/` — Org IA current state (Stage 6a TASK B-2 의 current-side input)

---

## Wiki lock (orchestrator step — wraps Step 1 through Step 6 when `$ORG_ROOT` is non-empty)

Skip this lock entirely when `$ORG_ROOT` is empty.

Before Step 1 (any wiki-touching work), acquire an org-level flock so concurrent `/jarfis:work` runs cannot corrupt INDEX.md / `_index.md` / search index:

```bash
LOCK_FILE="$ORG_ROOT/.jarfis-org/.wiki.lock"
mkdir -p "$(dirname "$LOCK_FILE")"
exec 200>"$LOCK_FILE"
if ! flock -w 300 200; then
  # 5-minute timeout reached — another /jarfis:work is holding the wiki lock.
  # Emit error via atomic + sentinel (tmux-claude-completion-signal-v1).
  mkdir -p $DOCS_DIR/phase-results/phase6
  RESULT=$DOCS_DIR/phase-results/phase6/attempt{K}.json
  cat > $RESULT.tmp <<EOF
{"status":"error","reason":"wiki_lock_timeout","reasonDetail":"Another /jarfis:work run is holding $LOCK_FILE. Retry after it completes."}
EOF
  mv $RESULT.tmp $RESULT && touch $RESULT.done
  exit 1
fi
# Critical section (Step 1 ~ Step 6) runs below while fd 200 is held.
# Lock auto-releases when jarfis-foreman exits (fd 200 closes).
```

When `$ORG_ROOT` is empty, Steps 1 through 6 still run — only the wiki-update substeps inside each Step are skipped (as noted per Step).

The lock releases automatically when jarfis-foreman exits or explicitly via `flock -u 200`. All subsequent orchestrator-only wiki work (Tracks B / INDEX-rebuild / Track C / summary fill-in) runs inside this critical section.

---

## Step 1 — Retrospective + Wiki Track A (tech-lead-strategist, work-wide, 1 spawn)

This single spawn covers two tasks that both require reading $DOCS_DIR/ artifacts: the workflow retrospective AND the Wiki Track A text-wiki extraction.

### Compose invocation (jarfis-foreman executes)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent tech-lead-strategist --state $STATE_FILE)
# Task spawn with the prompt below.
```

### Sub-agent task prompt (jarfis-foreman injects verbatim, with variables substituted)

```
You are the tech-lead strategist. You have TWO tasks in a single run:
  A. Produce the workflow retrospective at $DOCS_DIR/retrospective.md.
  B. Perform Wiki Track A (text wiki extraction + merge) — ONLY when org is registered.

Orchestrator-provided context:
  work_name:            <work_name>
  org_root:             <org_root>          (empty string when org is not registered)
  learning_candidates:  <learning_candidates_json>
  projects:             <projects_json>      (array of {name} from scope[])
  today:                <today_iso8601_date>

═══════════════════════════════════════════════
TASK B-2 — IA 3-way merge (Stage 6a — Org IA promotion; runs FIRST)
═══════════════════════════════════════════════

SKIP this task entirely when ANY of the following is true:
  - org_root is empty (no org registered).
  - $DOCS_DIR/discovery/ia/manifest.json does NOT exist (this work did not
    produce a work-IA).

Otherwise, perform the 3-way merge BEFORE writing retrospective.md so
TASK A can cite the resulting change set.

Path definitions:
  baseline_path = $DOCS_DIR/discovery/ia/.baseline          (snapshot taken at Phase 1b)
  current_path  = $ORG_ROOT/.jarfis-org/wiki/PO/projects/{project_slug}/ia   (Org IA live state)
  work_path     = $DOCS_DIR/discovery/ia                    (work IA produced by PO this run)

  {project_slug} resolves from state.workspace.scope[0].name. monorepo
  (multi-scope) work is out-of-scope for Stage 6a — if state.workspace.scope[]
  has more than one entry, SKIP this task and record
  `meta.ia_merge.skipped_reason = "multi_scope_deferred_6b"` in the attempt JSON.

Procedure:
  1. Compose the three paths above using the precompute variables.
  2. Run the dry-run merge:
       python3 ~/.claude/scripts/jarfis_cli.py ia merge \
         --baseline <baseline_path> \
         --current  <current_path> \
         --work     <work_path> \
         --dry-run
     Capture stdout JSON as $IA_MERGE_DRY.
  3. Parse $IA_MERGE_DRY:
       - `changes[]`        — pure-add / pure-modify / pure-delete entries.
       - `conflicts[]`      — slugs modified in BOTH current and work since baseline.
       - `applied`          — false in dry-run mode (always).
  4. If `conflicts[]` is non-empty:
       - Emit `meta.ia_merge.conflicts[]` (slug + detail) to the phase-results
         attempt JSON so the main session can yield D12 confirm via
         AskUserQuestion. Do NOT proceed to --apply autonomously.
       - Cite the conflicts in TASK A's "What to Improve" section so the
         retrospective records the merge tension.
  5. If `conflicts[]` is empty AND the user has pre-confirmed (D12 already
     resolved upstream — the main session passes `--apply` intent via the
     phase prompt substitution; default is dry-run only), re-run with:
       python3 ~/.claude/scripts/jarfis_cli.py ia merge \
         --baseline <baseline_path> \
         --current  <current_path> \
         --work     <work_path> \
         --apply --dest <current_path>
     Record `meta.ia_merge.applied = true` and the merged dest_dir in
     the attempt JSON. The Org IA live state now reflects the merge.
  6. If `conflicts[]` is empty but no apply intent is supplied, leave Org IA
     untouched; record `meta.ia_merge.applied = false` and the proposed
     changes[] so the main session can present them for user review.

Capture for retrospective citation:
  - Summary line: "IA merge: +{adds} adds, ~{mods} mods, -{dels} dels,
    {conflicts} conflicts ({applied|dry-run})".
  - Include this line in TASK A's "Project-Specific Learnings" section so
    retrospective.md reflects the IA promotion outcome.

═══════════════════════════════════════════════
TASK A — Retrospective (ALWAYS run)
═══════════════════════════════════════════════

Inputs to read:
- $DOCS_DIR/discovery/prd.md
- $DOCS_DIR/planning/architecture.md
- $DOCS_DIR/planning/tasks.md
- $DOCS_DIR/review/review.md
- $DOCS_DIR/review/diagnosis.md            (only if it exists)
- Any additional artifacts under $DOCS_DIR/ relevant to the retrospective.

Produce $DOCS_DIR/retrospective.md with exactly these sections:

## Workflow Retrospective

### What Went Well (Keep)
- Efficient agents / phases
- Good role skip / execution decisions

### What to Improve (Improve)
- Bottleneck areas
- Unnecessary steps
- Missing considerations

### Action Items for Next Time
- Concrete JARFIS workflow improvements (only if applicable)

### Project-Specific Learnings
- Patterns, conventions, caveats discovered in this codebase
- Reusable components / modules
- Frequently referenced file paths

### Learning Classification
Tag EACH learning item with a scope:
- [universal]: principles / techniques / tool usage valid across other projects
- [project]:  patterns specific to this codebase / team / config

Classification guidelines:
- Mentions specific file paths / directory structures → [project]
- Depends on specific framework version / configuration → [project]
- Qualifiers like "in this project" → [project]
- General tool usage / engineering principles → [universal]

### Suggested Learnings (INCLUDE this section ONLY when learning_candidates is non-empty)

Based on recurring patterns detected by Phase 5, propose learnable rules:

| Category | Occurrences | Example | Suggested Learning |
|----------|-------------|---------|--------------------|

(One row per learning_candidates item. Propose a specific, actionable rule.
The user will decide whether to promote via /jarfis:sys-upgrade.)

If learning_candidates is empty, OMIT this section entirely.

═══════════════════════════════════════════════
TASK B — Wiki Track A (ONLY when org_root is non-empty)
═══════════════════════════════════════════════

If org_root is empty, SKIP this entire task. Stop after Task A completes.

Principle:
- "learning" = JARFIS agent/workflow improvements (Task A output).
- "wiki"     = Org accumulated knowledge (this task).
Different purposes — do NOT mix.

Inputs to read additionally:
- $ORG_ROOT/.jarfis-org/wiki/INDEX.md              (org wiki structure + summaries)
- $ORG_ROOT/.jarfis-org/wiki/PO/_index.md, TA/_index.md, QA/_index.md
- Existing wiki files referenced by the _index.md (only the ones you actually need to merge into)

Extraction procedure:
1. Scan the same $DOCS_DIR/ artifacts you read for Task A. Identify items matching:
   - Accumulate: business rules, ADRs (architecture.md), API contracts (api-spec.md),
                 data models, design tokens, policy changes, architecture decisions.
   - Exclude:    schedule, implementation details, review comments, progress status,
                 inter-agent discussions.

2. Apply the 6-month test to EVERY candidate:
   "Will this still be useful in 6 months?" → if No, exclude.

3. Match against existing org wiki files via the INDEX.md Summary — MERGE into the
   existing file when a conceptual match exists, otherwise CREATE a new file.

4. Update the relevant wiki files AND their section `_index.md`.
   **Do NOT edit $ORG_ROOT/.jarfis-org/wiki/INDEX.md directly.** The orchestrator
   regenerates INDEX.md automatically from your `_index.md` edits via
   `jarfis_cli.py wiki rebuild-index` after your run completes. Editing INDEX.md
   yourself would be overwritten.

Wiki file frontmatter (for new or modified files — KEEP existing fields as-is; only
update the last_updated / last_updated_by pair on a modification):

---
owner: {PO | TA | QA}
projects: [<projects[*].name, comma-joined>]
created: <today_iso8601_date>             # only on creation
created_by: <work_name>                    # only on creation
last_updated: <today_iso8601_date>
last_updated_by: <work_name>
status: active
---

Counting:
While performing Track A, COUNT your changes per owner bucket and include them at
the end of $DOCS_DIR/retrospective.md in the format below. This is the ONLY place
the count appears — jarfis-foreman does NOT re-read wiki to recount.

**Important**: If you SKIPPED Task B because org_root is empty, do NOT append the
`## Wiki Update Summary` section at all. jarfis-foreman's Step 6 fill-in is also
skipped in that case, so any placeholders you leave would remain unsubstituted.

## Wiki Update Summary
Track A (Text):
  - PO/: +{new} new, {updated} updated
  - TA/: +{new} new, {updated} updated
  - QA/: +{new} new, {updated} updated
Track B (DESIGN):
  - pages/{project}/: (jarfis-foreman fills this)
Track C (Index):
  - wiki:  (jarfis-foreman fills this)
  - works: (jarfis-foreman fills this)

Leave the Track B and Track C rows as literal placeholders "(jarfis-foreman fills this)".
jarfis-foreman will overwrite those lines with real results after your run completes.

═══════════════════════════════════════════════

Report format when done:
- If Task B was skipped (no org): report [TASK_A_DONE]
- Otherwise: report [TASK_A_DONE][TASK_B_DONE] with a one-line summary of wiki counts.
```

jarfis-foreman fills substitutions before injection:
- `<work_name>`, `<org_root>`, `<learning_candidates_json>`, `<projects_json>`, `<today_iso8601_date>`.

---

## Step 2 — Workflow metrics TSV (orchestrator step — jarfis-foreman executes directly, best-effort)

Skip this step entirely when `$ORG_ROOT` is empty.

Append one TSV row to `$ORG_ROOT/workflow-metrics.tsv`. Create the header if the file does not exist.

Header (literal — keep columns in this exact order):

```
workflow_id	project	started_at	completed_at	review_iterations	learning_candidates_count	skipped_phases	follow_up_mode	follow_up_iteration
```

Field mapping (`$STATE_FILE` → column):

| Column                      | Source                                                             |
|-----------------------------|--------------------------------------------------------------------|
| workflow_id                 | `state.work.name` (REQUIRED — skip recording entirely if absent)  |
| project                     | `state.workspace.scope[0].name` (or "")                           |
| started_at                  | `state.started_at`                                                |
| completed_at                | current ISO8601 timestamp                                         |
| review_iterations           | `state.phases.5.meta.review_rounds` (or "0")                      |
| learning_candidates_count   | length of `state.learning_candidates` (or "0")                    |
| skipped_phases              | comma-joined phase_ids with `state.phases.*.status == "skipped"` |
| follow_up_mode              | "" (reserved for v4.1)                                            |
| follow_up_iteration         | "" (reserved for v4.1)                                            |

All fields come from `$STATE_FILE` (small JSON) — no $DOCS_DIR reading required.

On any failure (permission / disk / parse): log a warning and CONTINUE. Do NOT fail the phase.

---

## Step 3 — Wiki Track B — DESIGN HTML sync (orchestrator step — jarfis-foreman executes directly)

Skip this step entirely when `$ORG_ROOT` is empty OR `$HAS_FRONTEND == "false"`.

For each project in `$PROJECTS_JSON` that has `$DOCS_DIR/design/` output:

1. Ensure the target directory exists:
   ```bash
   mkdir -p $ORG_ROOT/.jarfis-org/wiki/DESIGN/pages/{project_name}
   ```

2. Copy design files — overwrite existing, add new, PRESERVE wiki-only files:
   ```bash
   cp -Rn …   # no, we want overwrite for conflicts and add for new — use rsync:
   rsync -a --ignore-errors \
     $DOCS_DIR/design/ \
     $ORG_ROOT/.jarfis-org/wiki/DESIGN/pages/{project_name}/
   ```
   This adds new files and overwrites existing ones but does NOT delete wiki-only files.

3. Regenerate the project's ToC `_index.html` using `ls` + a fixed template:
   ```bash
   cd $ORG_ROOT/.jarfis-org/wiki/DESIGN/pages/{project_name}
   cat > _index.html <<'HEADER'
   <!doctype html><html><head><meta charset="utf-8">
   <title>Design Index — {project_name}</title></head><body>
   <h1>{project_name}</h1><ul>
   HEADER
   for f in $(ls -1 */index.html 2>/dev/null); do
     echo "<li><a href=\"$f\">${f%/*}</a></li>" >> _index.html
   done
   echo '</ul></body></html>' >> _index.html
   ```
   This writes the ToC using only filenames — no HTML content is read into jarfis-foreman's context.

4. Update `$ORG_ROOT/.jarfis-org/wiki/DESIGN/_index.md` using a similar `ls`-based template: one bullet per project directory. Do NOT read existing _index.md content.

5. Update `$ORG_ROOT/.jarfis-org/wiki/INDEX.md` → append a line under the DESIGN section with the updated timestamp. Use `sed -i` to update a single marker line (no full file read):
   ```bash
   sed -i '' "s|^<!-- DESIGN_LAST_UPDATED -->.*|<!-- DESIGN_LAST_UPDATED --> {today}|" \
     $ORG_ROOT/.jarfis-org/wiki/INDEX.md
   ```
   (Requires INDEX.md to contain the marker line. If absent, skip this update silently.)

Record counts per project for Step 5 summary append:
- `{project_name}: {N} files synced` where N = `rsync` file transfer count.

> **Supplied 모드 한정 동기화 항목** (`state.design.mode == "supplied"`):
>   - `pages/{slug}/sitemap.md` (시안 동봉 시) → `wiki/DESIGN/pages/{project}/sitemap.md`
>   - `pages/{slug}/ia.json`    (시안 동봉 시) → `wiki/DESIGN/pages/{project}/ia.json`
>   - `assets/`                                → `wiki/DESIGN/pages/{project}/assets/`
>   - 시안에 없는 항목은 **자동 생성하지 않는다** (SSOT — Critic blocker #3 흡수).
>     `rsync -a` 가 시안 전체를 그대로 sync 하므로 동봉본만 wiki 에 도달한다.

---

## Step 4 — INDEX.md auto-rebuild (orchestrator step — jarfis-foreman executes directly)

Skip when `$ORG_ROOT` is empty.

The tech-lead-strategist (Step 1) edited individual wiki files and section `_index.md` files but is forbidden from touching `INDEX.md` directly. jarfis-foreman now regenerates `INDEX.md` deterministically from the updated `_index.md` files:

```bash
REBUILD_JSON=$(python3 ~/.claude/scripts/jarfis_cli.py wiki rebuild-index $ORG_ROOT)
# stdout JSON example:
# {"status":"ok","sections":{"PO":2,"DESIGN":0,"TA":1,"QA":0},"total_entries":3,
#  "index_path":"...","design_marker_preserved":true}

REBUILD_OK=$(echo "$REBUILD_JSON" | jq -r '.status')
```

The rebuild CLI:
- Parses each `{section}/_index.md` 4-column markdown table (file, summary, projects, updated). Placeholder rows ("(none)") are skipped.
- Regenerates `INDEX.md` with counts + per-section Key (top-3 most recently updated file names) + Directory Map.
- Preserves any existing `<!-- DESIGN_LAST_UPDATED -->` marker line so Track B's `sed`-based update target remains intact.

If `$REBUILD_OK != "ok"`, record the error in phase-results meta but continue (Track C still useful for any prior changes).

---

## Step 5 — Wiki Track C — Semantic search index (orchestrator step, best-effort)

Skip when `$ORG_ROOT` is empty.

```bash
python3 ~/.claude/scripts/jarfis_cli.py search index wiki
WIKI_RC=$?
python3 ~/.claude/scripts/jarfis_cli.py search index works
WORKS_RC=$?
```

Record for Step 5 summary append:
- `wiki:  OK`  if `WIKI_RC == 0` else `FAILED: <short reason from stderr>`
- `works: OK`  if `WORKS_RC == 0` else `FAILED: <short reason from stderr>`

On failure containing `memory_insufficient` in stderr: use the literal message "Update later with /jarfis:search-index --current." as the reason.

Do NOT halt the phase on failure.

---

## Step 6 — Summary line fill-in (orchestrator step — jarfis-foreman executes directly)

Skip when `$ORG_ROOT` is empty (retrospective.md has no Wiki Update Summary section in that case).

The tech-lead-strategist in Step 1 wrote the Wiki Update Summary skeleton with literal placeholders:

```
Track B (DESIGN):
  - pages/{project}/: (jarfis-foreman fills this)
Track C (Index):
  - wiki:  (jarfis-foreman fills this)
  - works: (jarfis-foreman fills this)
```

Replace those placeholder lines with real counts / statuses using `sed`:

```bash
# For Track B — one line per project with sync counts:
sed -i '' "/^  - pages\/{project}\/: (jarfis-foreman fills this)$/c\\
  - pages/{project_name}/: {N} files synced" $DOCS_DIR/retrospective.md

# For Track C — wiki + works:
sed -i '' "s|^  - wiki:  (jarfis-foreman fills this)$|  - wiki:  {WIKI_STATUS}|" $DOCS_DIR/retrospective.md
sed -i '' "s|^  - works: (jarfis-foreman fills this)$|  - works: {WORKS_STATUS}|" $DOCS_DIR/retrospective.md
```

These are `sed` substitutions on single lines — jarfis-foreman does NOT read the full retrospective.md content.

---

## Completion Protocol

At phase completion, perform the following in order:

1. **Produce spec artifacts**:
   - `$DOCS_DIR/retrospective.md` (4 sections + Wiki Update Summary when org registered)
   - Wiki updates (Track A via sub-agent + Track B via rsync + INDEX.md auto-rebuild + Track C via CLI) — only when `$ORG_ROOT` non-empty, all serialized under `.wiki.lock`
   - `$ORG_ROOT/workflow-metrics.tsv` append (best-effort)
2. **(Optional) Handoff document**
3. **Write phase-results/phase6/attempt{K}.json** (last step — atomic + sentinel, tmux-claude-completion-signal-v1):
   ```bash
   mkdir -p $DOCS_DIR/phase-results/phase6
   RESULT=$DOCS_DIR/phase-results/phase6/attempt{K}.json
   cat > $RESULT.tmp <<EOF
   {
     "status": "completed",
     "reason": "",
     "reasonDetail": "",
     "meta": {
       "wiki_rebuild_index": ${REBUILD_OK:-skipped},
       "wiki_search_index_wiki": ${WIKI_RC_STATUS:-skipped},
       "wiki_search_index_works": ${WORKS_RC_STATUS:-skipped}
     }
   }
   EOF
   mv $RESULT.tmp $RESULT          # atomic publish
   touch $RESULT.done              # sentinel — wakes parent poll()
   # Error: same emit pattern with status=error
   ```
4. **Release wiki lock**: `flock -u 200` (automatic on jarfis-foreman exit, but explicit release preferred).

**Strict order**: artifacts → (handoff) → phase-results JSON.
Do NOT write to `.jarfis-state.json` (the main Claude owns it).
`{K}` is substituted with the actual attempt number by the main session when generating the prompt file.
