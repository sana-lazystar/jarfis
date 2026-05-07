# Phase 5: Review & QA (review_round loop + pattern-detect)

> Executed by **jarfis-foreman** inside tmux. jarfis-foreman is the **orchestrator**: runs the review_round loop, spawns reviewer sub-agents per round (parallel), calls pattern-detect, concatenates reviewer temp files into review.md, spawns diagnosis + fix.
> It does NOT read source artifacts itself. Each reviewer writes its output to a per-role temp file; jarfis-foreman merges via `cat` (shell concatenation — no content read into foreman context).
> The review_round loop (max 3) is INTERNAL to this phase (M3/M8). The main session sees a single tmux invocation.
> All sub-agent artifacts in English. User-facing messages in $LOCALE.

**Execution context**:
- `$DOCS_DIR` = tmux workspace
- `$STATE_FILE` = `$DOCS_DIR/.jarfis-state.json`
- `$MAX_REVIEW_ROUNDS` = 3 (M8)

### jarfis-foreman precompute (from $STATE_FILE)

- `$SCOPE` = `state.workspace.scope[]` (array)
- `$HAS_API_SPEC` = "true" if `$DOCS_DIR/planning/api-spec.md` exists, else "false" (`test -f`)
- `$DESIGN_MODE` = `state.design.mode` (string or null)
- `$TDD_ENABLED` = `state.tddEnabled`
- `$TEST_MODS_JSON` = `state.phase4_tests.test_modifications` (array or `"[]"`)
- For each `scope[i]`: `$DIFF_CMD[i]` = `git -C {scope[i].path} diff {scope[i].baseCommit}..HEAD`

## Required Inputs (consumed by reviewer sub-agents)

- `$DOCS_DIR/planning/tasks.md` — TL, QA
- `$DOCS_DIR/planning/architecture.md` — TL, Security
- `$DOCS_DIR/planning/test-strategy.md` — QA
- **git diff** per scope — each sub-agent runs its `$DIFF_CMD[i]` inside its spawn

## Conditional Inputs (consumed by reviewer sub-agents)

- `$DOCS_DIR/planning/api-spec.md` — TL in Step 5-0 (API contract check) when `$HAS_API_SPEC == "true"`
- `$DOCS_DIR/planning/security-guidelines.md` — Security (Phase 4 Step 1 output)
- `$DOCS_DIR/ops/deployment-plan.md` — TL (Phase 4.5 output)
- `$DOCS_DIR/design/{id}/index.html` + `reference*.png` — UX when `$DESIGN_MODE != null`

---

## review_round loop (orchestrator logic — jarfis-foreman executes)

```
mkdir -p $DOCS_DIR/review/tmp

round = 1
while round <= $MAX_REVIEW_ROUNDS:
  mkdir -p $DOCS_DIR/review/tmp/round-$round

  if round == 1 AND $HAS_API_SPEC == "true":
    Step 5-0 — per BE scope, spawn tech-lead-reviewer for API contract check

  Step 5-1 — per scope[i], spawn TL + QA + Security in parallel
             + work-wide UX if $DESIGN_MODE != null
             Each writes to a dedicated temp file in tmp/round-$round/

  Step 5-2 — Merge temp files into review.md (cat only — no content read)

  if round >= 2:
    Step 5-3 — call pattern-detect; append warnings to review.md

  Step 5-4 — Check unresolved issues (reviewer spawn responses indicate PASS/REVISION count)
    if all PASS: break
    else:       spawn TL for diagnosis (which also emits learning_candidates)
                spawn FE/BE for fixes
                round += 1
```

"Check unresolved" method: each reviewer's short final response to the Task tool (summary line like `[SCOPE_REVIEW: scope=api role=qa verdict=REVISION count=2]`) is parsed from Task output by jarfis-foreman. The full output stays in the temp file.

---

## Step 5-0 — API Contract verification (CONDITIONAL, round 1 only)

Runs only when `$HAS_API_SPEC == "true"`. For each `scope[i]` with `type == "backend"`:

### Compose invocation (jarfis-foreman executes, per BE scope)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent tech-lead-reviewer --scope-index $i --state $STATE_FILE)
# Task spawn with the prompt below.
```

### Sub-agent task prompt (jarfis-foreman injects verbatim, per BE scope)

```
You are the tech-lead reviewer verifying API contract compliance for scope[$i].

Inputs to read:
- $DOCS_DIR/planning/api-spec.md
- Actual BE code at scope[$i].path
- Called FE endpoints in the FE project paths listed below (scan these for API calls)

Frontend scope paths: <fe_scope_paths_list>

Verification items:
- Endpoint path + HTTP method match
- Request parameter match
- Response schema compatibility
- Error code match

Write results to $DOCS_DIR/review/api-contract-check.md (create or overwrite).
Use a per-item checklist table. Flag mismatches clearly.

Report the completion line at the end of your final response:
  [API_CONTRACT_CHECK: scope=$i mismatches={N}]
```

jarfis-foreman precomputes `<fe_scope_paths_list>` (comma-separated paths).

---

## Step 5-1 — Parallel review (per-project reviewers + conditional UX)

For EACH round, for EACH `scope[i]`, spawn three sub-agents in PARALLEL.

### Compose invocations (jarfis-foreman executes, per scope per round)

```bash
# tech-lead-reviewer
COMPOSE_TL=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent tech-lead-reviewer --scope-index $i --state $STATE_FILE)
# qa-engineer
COMPOSE_QA=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent qa-engineer --scope-index $i --state $STATE_FILE)
# security-engineer
COMPOSE_SEC=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent security-engineer --scope-index $i --state $STATE_FILE)
# Task spawn all three in parallel.
```

Work-wide (1 spawn per round), CONDITIONAL on `$DESIGN_MODE != null`:

```bash
COMPOSE_UX=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent ux-designer --state $STATE_FILE)
```

### Per-reviewer temp-file contract (shared by all reviewer prompts below)

Each reviewer MUST write its review output to a dedicated temp file so jarfis-foreman can concatenate without reading content:

- TL  per scope:   `$DOCS_DIR/review/tmp/round-{round}/tech-lead-scope-{i}.md`
- QA  per scope:   `$DOCS_DIR/review/tmp/round-{round}/qa-scope-{i}.md`
- Sec per scope:   `$DOCS_DIR/review/tmp/round-{round}/security-scope-{i}.md`
- UX work-wide:    `$DOCS_DIR/review/tmp/round-{round}/ux-workwide.md`

Each file MUST start with a heading structured for later concatenation — the orchestrator relies on this structure:

```markdown
### {scope_name}     ← for per-scope reviewers (TL/QA/Sec)
#### {Role}
- [PASS] | [REVISION] Issue summary
```

For UX (work-wide), start with:
```markdown
### Work-wide
#### UX Design
- [PASS] | [REVISION] /{path}: diff {N}% — description
```

Reviewers must also emit a short summary line in their final response (for jarfis-foreman's "all resolved?" decision):
- `[SCOPE_REVIEW: scope={scope_name} role={role} verdict=PASS|REVISION count={issue_count}]`

### Sub-agent task prompt — tech-lead-reviewer (jarfis-foreman injects, per scope per round)

```
You are the tech-lead reviewer for scope[$i] (name={scope[$i].name}) in round {round}.

Inspect the Phase 4 delta in scope[$i].path by running:
  git -C {scope[$i].path} diff {scope[$i].baseCommit}..HEAD

Inputs to read:
- $DOCS_DIR/planning/tasks.md
- $DOCS_DIR/planning/architecture.md
- $DOCS_DIR/review/api-contract-check.md     (if it exists — prioritize its mismatches)
- $DOCS_DIR/ops/deployment-plan.md            (review deployment appropriateness)
- $DOCS_DIR/planning/security-guidelines.md   (Phase 4 pre-review)

Review criteria:
- Code quality and readability
- Adherence to architecture.md
- API contract compliance (reference api-contract-check.md)
- Appropriateness of design patterns
- Error handling
- Performance — PRD Performance Budget compliance
- Technical debt
- Deployment-plan feasibility

Output file (OVERWRITE if it exists):
  $DOCS_DIR/review/tmp/round-{round}/tech-lead-scope-{i}.md

Content format:
  ### {scope_name}
  #### Tech Lead
  - [PASS] | [REVISION] Issue summary (file:line if applicable)
  - ...

At the end of your final response to the Task tool, also output a single summary line:
  [SCOPE_REVIEW: scope={scope_name} role=tech-lead verdict=PASS|REVISION count={issue_count}]
```

jarfis-foreman fills `{round}`, `{i}`, `{scope_name}` before injection.

### Sub-agent task prompt — qa-engineer (jarfis-foreman injects, per scope per round)

```
You are the QA engineer reviewing scope[$i] (name={scope[$i].name}) in round {round}.

Inspect the Phase 4 delta in scope[$i].path by running:
  git -C {scope[$i].path} diff {scope[$i].baseCommit}..HEAD

Inputs to read:
- $DOCS_DIR/discovery/prd.md                  (Performance Budget + business rules)
- $DOCS_DIR/planning/test-strategy.md         (verify against this)
- $DOCS_DIR/design/                           (HTML mockups — only if present)
- $DOCS_DIR/planning/tasks.md                 (N/A parts — exclude them from review)

tddEnabled mode (applies ONLY when tddEnabled == true):
  <tdd_enabled>
  Tests already cover P0/P1 functional-correctness scenarios.
  Focus your review on:
  - Integration / E2E level issues NOT covered by tests
  - Non-functional: performance (Performance Budget), accessibility
  - Any [TEST_ISSUE] reported by implementation agents during Phase 4
  (Code-quality + architecture-fitness remain the Tech Lead's responsibility — do not duplicate.)

Test modification verification:
  If test_modifications listed below is non-empty:
  <test_modifications_json>
  For each entry:
  - Check the reason in the [TEST_MODIFIED] commit tag.
  - Determine: was the test genuinely buggy, or was the test being circumvented?
  - Unjustified modifications → report as "Test Integrity Violation" issue.

QA items:
- Pass/Fail per scenario in test-strategy.md
- Edge case testing
- Cross-browser / device compatibility (only if Frontend exists)
- Performance — Pass/Fail vs PRD Performance Budget
- Accessibility (only if Frontend exists)

Output file (OVERWRITE if it exists):
  $DOCS_DIR/review/tmp/round-{round}/qa-scope-{i}.md

Content format:
  ### {scope_name}
  #### QA
  - [PASS] | [REVISION] Issue summary

At the end of your final response, emit:
  [SCOPE_REVIEW: scope={scope_name} role=qa verdict=PASS|REVISION count={issue_count}]
```

jarfis-foreman fills `<tdd_enabled>` (literal "true" or "false"), `<test_modifications_json>`, `{round}`, `{i}`, `{scope_name}`.

### Sub-agent task prompt — security-engineer (jarfis-foreman injects, per scope per round)

```
You are the security engineer reviewing scope[$i] (name={scope[$i].name}) in round {round}.

Inspect the Phase 4 delta in scope[$i].path by running:
  git -C {scope[$i].path} diff {scope[$i].baseCommit}..HEAD

Inputs to read:
- $DOCS_DIR/planning/architecture.md
- $DOCS_DIR/planning/security-guidelines.md   (your Phase 4 pre-review — follow it)

Review items:
- OWASP Top 10 assessment
- Authentication / authorization verification
- Input validation and output encoding
- Sensitive data exposure check
- Dependency vulnerability check
- Security headers + CORS (only when applicable)

Output file (OVERWRITE if it exists):
  $DOCS_DIR/review/tmp/round-{round}/security-scope-{i}.md

Content format:
  ### {scope_name}
  #### Security
  - [PASS] | [REVISION] Issue summary

At the end of your final response, emit:
  [SCOPE_REVIEW: scope={scope_name} role=security verdict=PASS|REVISION count={issue_count}]
```

### Sub-agent task prompt — ux-designer (jarfis-foreman injects, work-wide per round, when `$DESIGN_MODE != null`)

```
You are the UX designer comparing FE implementations against the design baseline (round {round}).

Orchestrator-provided:
  dev_server_url: <dev_server_url>

Inputs to read:
- $DOCS_DIR/design/{path}/reference.png       (primary authority — Figma OR text-mode OR supplied)
- $DOCS_DIR/design/{path}/index.html          (supplementary reference)
- $DOCS_DIR/design/section-map.json           (figma mode only — for problem section identification)

Comparison procedure (dual):

Primary comparison — reference.png vs FE implementation:
1. Check that $DOCS_DIR/design/{path}/reference.png exists.
2. Take a FE screenshot at {dev_server_url} via mcp__playwright__browser_take_screenshot
   (fullPage=true).
3. Pixel-diff via mcp__design-comparison__compare_design:
     design_path:          reference.png
     implementation_path:  FE screenshot
     output_diff_path:     $DOCS_DIR/design/{path}/review-diff-p5.png
4. Decide per page:
     ≤ 5%    → PASS
     5–15%   → MINOR_REVISION (identify differing areas)
     > 15%   → MAJOR_REVISION (possible structural issues)

Secondary comparison (supplementary) — HTML mockup vs FE:
5. Take a screenshot of $DOCS_DIR/design/{path}/index.html via Playwright.
6. Visually compare with the FE screenshot (layout, component placement).
7. If HTML and FE differ, and one is closer to reference.png — the closer one is correct.

Responsive verification (per state.responsive):
8. Capture + compare each viewport:
     pc-only          → 1920×1080
     pc-mobile        → + 390×844
     pc-mobile-tablet → + 768×1024

Fallback when reference.png is absent (legacy workflow):
- Primary comparison becomes HTML mockup vs FE only.
- If compare_design is unavailable, fall back to visual judgment.

Output file (OVERWRITE if it exists):
  $DOCS_DIR/review/tmp/round-{round}/ux-workwide.md

Content format:
  ### Work-wide
  #### UX Design
  ### reference.png Comparison (Primary)
  - /{path}: [PASS] | [REVISION] — diff: {N}% — description
  ### HTML Mockup Comparison (Supplementary)
  - /{path}: [PASS] | [REVISION] description
  ### Viewport: PC (1920×1080)
  - /{path}: [PASS] | [REVISION] description
  ### Viewport: Mobile (390×844) (if applicable)
  - /{path}: [PASS] | [REVISION] description
  ### Viewport: Tablet (768×1024) (if applicable)
  - /{path}: [PASS] | [REVISION] description

At the end of your final response, emit:
  [SCOPE_REVIEW: scope=work-wide role=ux verdict=PASS|REVISION count={issue_count}]
```

jarfis-foreman fills `<dev_server_url>` from state / runtime detection and `{round}`.

---

## Step 5-2 — Merge temp files into review.md (orchestrator step — jarfis-foreman executes directly)

Each reviewer has written to a per-role temp file. jarfis-foreman concatenates (no content read):

```bash
ROUND_DIR=$DOCS_DIR/review/tmp/round-$round

# Round header written directly
echo ""                  >> $DOCS_DIR/review/review.md
echo "## Round $round"   >> $DOCS_DIR/review/review.md
echo ""                  >> $DOCS_DIR/review/review.md

# Per scope: concatenate TL + QA + Security for that scope
for i in $(seq 0 $((${#SCOPE[@]}-1))); do
  for role in tech-lead qa security; do
    F=$ROUND_DIR/${role}-scope-${i}.md
    if [ -f "$F" ]; then
      cat "$F"           >> $DOCS_DIR/review/review.md
      echo ""            >> $DOCS_DIR/review/review.md
    fi
  done
done

# Work-wide: UX (if present)
if [ -f "$ROUND_DIR/ux-workwide.md" ]; then
  cat "$ROUND_DIR/ux-workwide.md" >> $DOCS_DIR/review/review.md
fi
```

Per-round append (do NOT overwrite earlier rounds). Temp files remain on disk for debugging.

---

## Step 5-3 — pattern-detect (orchestrator step, only when `round >= 2`)

```bash
PATTERNS_JSON=$(python3 ~/.claude/scripts/jarfis_cli.py pattern-detect \
  $DOCS_DIR/review/review.md)
# stdout JSON: {"patterns": [...], "details": {...}}
# Always exit 0 (never blocks).

PATTERNS=$(echo "$PATTERNS_JSON" | jq -r '.patterns | join(",")')
```

Pattern semantics:
- `stagnation`  — same issue ≥ 2 consecutive rounds → "may be unsolvable within current design"
- `regression`  — new issue not present before → "fix caused a regression"
- `oscillation` — (round 3+) round N issues == round N-2 issues → "oscillation pattern"

If `$PATTERNS` non-empty, append warnings to review.md:

```bash
echo ""                                                                >> $DOCS_DIR/review/review.md
echo "## Round $round — Pattern Warnings"                              >> $DOCS_DIR/review/review.md
echo "$PATTERNS_JSON" | jq -r '.patterns[] | "- \(.)"'                 >> $DOCS_DIR/review/review.md
```

Record `$PATTERNS_JSON` for phase-results meta (`meta.pathological_patterns` + `meta.pattern_details`).

---

## Step 5-4 — Diagnosis + fix (when any `[SCOPE_REVIEW: verdict=REVISION]` was reported)

### Diagnosis spawn (orchestrator step)

```bash
# tech-lead-reviewer is per-project; anchor on scope-index 0 for the work-wide diagnosis pass.
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent tech-lead-reviewer --scope-index 0 --state $STATE_FILE)
# Task spawn with the diagnosis prompt below.
```

### Sub-agent task prompt — diagnosis (jarfis-foreman injects)

```
You are the tech-lead reviewer producing a root-cause diagnosis for round {round}.

Inputs to read:
- $DOCS_DIR/review/review.md               (all rounds so far — ALL reviewer outputs concatenated)
- $DOCS_DIR/review/api-contract-check.md   (if present)
- $DOCS_DIR/planning/architecture.md        (verify original design intent)
- $DOCS_DIR/planning/tasks.md               (verify original requirements)

Procedure:
1. List all issues across reviewers and scopes.
2. Group issues with common causes (correlate across reviewers).
   Example: "API 500 error" (QA) + "auth token validation missing" (Security)
            → middleware registration order error.
3. For each group, identify the root cause at code level (file path, line, logic).
4. Write a fix directive per group:
     assignee role (FE / BE / DevOps) + scope-index
     target file + line
     fix direction
     caveats (what NOT to change)
5. Propose regression-prevention tests or structural improvements.

Output to $DOCS_DIR/review/diagnosis.md using this format:

## Issue Summary ({N} items)

### Issue Group 1: {Common Cause Summary}
Related Issues:
- [QA]        ...
- [Security]  ...
- [Tech Lead] ...

Root Cause: {code-level analysis}
Impact Scope: {files / features affected}

Fix Directive:
| Assignee       | File                  | Fix Description | Priority |
|----------------|-----------------------|-----------------|----------|
| BE scope-idx 0 | src/auth.ts:42        | ...             | P0       |
| FE scope-idx 1 | src/pages/login.vue:88| ...             | P1       |

Regression Prevention: {tests to add or structural improvements}

(repeat per group)

## Fix Priority Summary
| Rank | Issue Group   | Assignee  | Estimated Difficulty |
|------|---------------|-----------|----------------------|

═══════════════════════════════════════════════
Learning-candidate extraction (include in your FINAL RESPONSE to the Task tool)
═══════════════════════════════════════════════

After diagnosis.md is fully written, ALSO analyze the issue groups across all rounds
(they are all in review.md + diagnosis.md you just wrote). Identify categories where
the same pattern appears in ≥ 2 issue groups (e.g., "input-validation" ×3,
"error-handling" ×2).

Emit the list in your FINAL RESPONSE wrapped in the exact tags below so the
orchestrator can extract it without reading diagnosis.md:

<LEARNING_CANDIDATES>
[
  {"category": "input-validation", "count": 3, "examples": ["BE-api-2 parameter", "FE-web-1 form"]},
  {"category": "error-handling",   "count": 2, "examples": ["BE-api-4 error response", "FE-web-3 boundary"]}
]
</LEARNING_CANDIDATES>

If no category repeats ≥ 2 times, emit:
<LEARNING_CANDIDATES>
[]
</LEARNING_CANDIDATES>
```

### Extract learning_candidates (orchestrator step)

From the Task tool's returned response, jarfis-foreman extracts the JSON between the `<LEARNING_CANDIDATES>` tags (shell-level pattern match — not a content read of diagnosis.md):

```bash
LC_JSON=$(echo "$DIAGNOSIS_RESPONSE" | \
  sed -n '/<LEARNING_CANDIDATES>/,/<\/LEARNING_CANDIDATES>/p' | \
  sed '1d;$d')
# Store $LC_JSON for phase-results meta (see Completion Protocol).
```

### Fix spawns (orchestrator step — jarfis-foreman executes, per unique (role, scope-index) in diagnosis.md)

jarfis-foreman cannot read diagnosis.md to discover (role, scope-index) tuples. Instead, the diagnosis sub-agent ALSO emits a compact directive map in its final response for the orchestrator to parse:

```
Amend the diagnosis task prompt with:

At the VERY END of your final response (AFTER the LEARNING_CANDIDATES block), also emit
the list of fix directives as compact JSON wrapped in the tags below:

<FIX_DIRECTIVES>
[
  {"role": "backend-developer",  "scope_index": 0, "group": "Issue Group 1"},
  {"role": "frontend-developer", "scope_index": 1, "group": "Issue Group 2"}
]
</FIX_DIRECTIVES>

The diagnosis.md file is the source of truth for the actual fix content;
this JSON is only a spawn directory for the orchestrator.
```

(The above block is part of the diagnosis task prompt — jarfis-foreman includes it when injecting.)

Then jarfis-foreman spawns fix agents based on the extracted JSON:

```bash
FIX_DIRECTIVES_JSON=$(echo "$DIAGNOSIS_RESPONSE" | \
  sed -n '/<FIX_DIRECTIVES>/,/<\/FIX_DIRECTIVES>/p' | \
  sed '1d;$d')

# For each unique (role, scope_index) in FIX_DIRECTIVES_JSON:
echo "$FIX_DIRECTIVES_JSON" | \
  jq -c '[ .[] | {role, scope_index} ] | unique | .[]' | \
while read -r D; do
  ROLE=$(echo "$D" | jq -r .role)
  SI=$(echo   "$D" | jq -r .scope_index)
  COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
    --agent "$ROLE" --scope-index $SI --state $STATE_FILE)
  # Task spawn with the fix prompt below.
done
```

### Sub-agent task prompt — fix (jarfis-foreman injects, per unique fix agent)

```
You are an implementation agent applying fixes from diagnosis.md for scope[$i].
Role: {frontend-developer | backend-developer}
Project directory: scope[$i].path

Inputs to read (in order of authority):
- scope[$i].path/CLAUDE.md                    (HIGHEST AUTHORITY — project-level rules; MUST Read first if present. Claude Code's auto-load does NOT cover scope[$i].path when your spawn working_dir is docsDir, so invoke Read explicitly at task start. Echo any verification marker string present.)
- scope[$i].path/.jarfis-project/project-profile.md  (project conventions — Read if present)
- $DOCS_DIR/review/diagnosis.md       (PRIMARY — your assigned directives ONLY)
- $DOCS_DIR/planning/architecture.md  (verify original design intent)
- $DOCS_DIR/planning/tasks.md         (verify original task requirements)

Procedure per directive assigned to you (role + scope-index match):
1. Check the specified file and line.
2. Apply the fix referencing the root-cause analysis.
3. Add the tests specified in Regression Prevention.
4. Verify behavior before/after the fix.

Conflict rule:
- If a directive conflicts with architecture.md design principles:
  follow the diagnosis.md directive BUT record the conflict in the commit message.

Scope Guard:
- Modify ONLY within the scope specified in diagnosis.md.
- Do NOT refactor outside that scope.

Git auto-commit (per issue group):
- Commit format: jarfis(fix/{TASK_ID}): <issue summary>
- On .git/index.lock error: wait 3 s, retry (max 3 attempts).

Report completion in your final response:
  [FIX_DONE: role={role} scope={i}]
```

---

## Completion Protocol

At phase completion, perform the following in order:

1. **Produce spec artifacts**:
   - `$DOCS_DIR/review/review.md` (concatenated across all rounds)
   - `$DOCS_DIR/review/api-contract-check.md` (when `api-spec.md` exists)
   - `$DOCS_DIR/review/diagnosis.md` (when issues were found)
   - Fix commits (under each `scope[i].path`)
   - Temp files remain at `$DOCS_DIR/review/tmp/round-{N}/*.md` for debugging
2. **(Optional) Handoff document**
3. **Write phase-results/phase5/attempt{K}.json** (last step):
   ```bash
   mkdir -p $DOCS_DIR/phase-results/phase5
   cat > $DOCS_DIR/phase-results/phase5/attempt{K}.json <<EOF
   {
     "status": "completed",
     "reason": "",
     "reasonDetail": "",
     "meta": {
       "review_rounds": $round,
       "unresolved_issues": 0,
       "pathological_patterns": $(echo "$PATTERNS_JSON" | jq -c '.patterns // []'),
       "pattern_details":       $(echo "$PATTERNS_JSON" | jq -c '.details  // {}'),
       "learning_candidates":   $LC_JSON,
       "design_source":         "$(jq -r '.design.mode // ""' $STATE_FILE)"
     }
   }
   EOF
   # Error: status=error with reason/reasonDetail
   ```

**Strict order**: artifacts → (handoff) → phase-results JSON.
Do NOT write to `.jarfis-state.json` (the main Claude owns it). At Gate 3 the main session reads this meta and conditionally surfaces the "Re-design Phase 2" option.
`{K}` is substituted with the actual attempt number by the main session when generating the prompt file.
