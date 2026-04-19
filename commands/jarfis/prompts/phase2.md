# Phase 2: Architecture & Planning

> Executed by **jarfis-foreman** inside tmux. jarfis-foreman is the **orchestrator**: runs compose, spawns the TA sub-agent via Task, never reads source artifacts itself.
> All sub-agent artifacts in English. User-facing messages in $LOCALE.

**Execution context**:
- `$DOCS_DIR` = tmux workspace (`state.work.docsDir`)
- `$STATE_FILE` = `$DOCS_DIR/.jarfis-state.json`

## Required Inputs (consumed by TA sub-agent)

- `$DOCS_DIR/discovery/prd.md` — includes the Technical Feasibility section appended in Phase 1b

## Conditional Inputs (consumed by TA sub-agent)

- `$DOCS_DIR/discovery/ux-direction.md` — if `state.design.mode != null`

---

## Step 1 — TA artifacts (technical-architect)

One spawn produces all planning artifacts.

### Compose invocation (jarfis-foreman executes)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent technical-architect --state $STATE_FILE)

SUBAGENT=$(echo "$COMPOSE" | jq -r .subagent_type)
MODEL=$(echo "$COMPOSE" | jq -r .model)
PROMPT=$(echo "$COMPOSE" | jq -r .prompt)
WORKING_DIR=$(echo "$COMPOSE" | jq -r .working_dir)

# Task(subagent_type=$SUBAGENT, model=$MODEL, cwd=$WORKING_DIR,
#      prompt=$PROMPT + "\n\n## Task\n" + <TA Task prompt below verbatim>)
```

### jarfis-foreman precompute (fill placeholders below before injecting)

Before injecting the task prompt, jarfis-foreman must precompute these values from `$STATE_FILE` and substitute them in the prompt:

- `<has_backend>` = "true" if any `state.workspace.scope[].type == "backend"`, else "false"
- `<has_frontend>` = "true" if any `state.workspace.scope[].type == "frontend"`, else "false"
- `<api_mode_swagger>` = "true" if `state.api.mode == "swagger"`, else "false"
- `<api_spec_required>` = `state.api_spec_required` if set, else "true" when `has_backend && has_frontend`, else "false" (v4.0.2 OBS-1: align with verify.py Gate 2 fallback)
- `<design_mode>` = `state.design.mode` (string or "null")
- `<responsive>` = `state.responsive` (string)
- `<scope_json>` = compact JSON of `state.workspace.scope[]` (array of `{name, type, path, framework}`)

### Sub-agent task prompt (jarfis-foreman injects verbatim after substitution)

```
You are the technical architect. Read the files below and produce the listed planning artifacts.

Files to read first:
- $DOCS_DIR/discovery/prd.md
- $DOCS_DIR/discovery/ux-direction.md    (only if it exists — design mode != null)

Workspace context (from state):
- has_backend: <has_backend>
- has_frontend: <has_frontend>
- api_mode_swagger: <api_mode_swagger>
- api_spec_required: <api_spec_required>
- design_mode: <design_mode>
- responsive: <responsive>
- scope: <scope_json>

Produce the following artifacts under $DOCS_DIR/planning/:

1. $DOCS_DIR/planning/architecture.md
   - System architecture diagram (Mermaid)
   - Technology stack selection with rationale
   - Data model design
   - API design (key endpoints — overview only; details belong to api-spec.md when produced)
   - Infrastructure configuration
   - Security architecture
   - Scalability strategy
   - ## Architecture Decision Records — at least 3 ADRs. Required topics:
     tech stack choice, data model structure, key architecture pattern.
     Each ADR format:
       ### ADR-00N: {Decision Title}
       - Status: Approved
       - Context: {problem to solve}
       - Alternatives considered: | Option | Pros | Cons |
       - Decision: {chosen option}
       - Rationale: {trade-off analysis}
       - Impact: {resulting changes or constraints}

2. $DOCS_DIR/planning/api-spec.md — CONDITIONAL
   Generate ONLY when api_spec_required == "true" OR api_mode_swagger == "true".
   Otherwise SKIP this file entirely.
   Note (v4.0.2 OBS-1): api_spec_required follows verify.py Gate 2 fallback rule —
   true when `state.api_spec_required` is set explicitly OR (has_backend && has_frontend).
   BE-only workflows without a frontend consumer skip this artifact unless
   `state.api_spec_required=true` is set in Phase 1a.

   When generated, per endpoint include:
   - ## {METHOD} {path}         (e.g., ## POST /api/v1/boards)
   - Description, Authentication (permissions/roles)
   - Request parameters table: | Parameter | Location | Type | Required | Description |
   - Request Body Example (JSON)
   - Response Example (JSON)
   - Error Responses table: | Code | Error Key | Message | Description |

   Write clearly enough that FE can directly convert this into type definitions.

3. $DOCS_DIR/planning/tasks.md — 2D structure (M2 decision)
   Top-level sections are per project. Heading pattern:
     ## {Type} Tasks — {project.name}
   where {Type} ∈ {Frontend, Backend, DevOps} and {project.name} comes from scope[].name.
   Use "N/A" in the heading body when a role is listed "Not Required" in PRD's Required Roles.

   Each task row includes:
   - Task ID: {role-prefix}-{project-name}-{N}
     role-prefix ∈ {FE, BE, DevOps}
     Example: FE-web-1, BE-api-3, DevOps-api-2.
   - Description
   - Related APIs     (refer to api-spec.md if present)
   - Target files     (new / modified — concrete paths from project-profile)
   - Dependencies
   - Completion criteria
   - Tests            (inline from test-strategy.md; cross-reference by Task ID)
   - Security         (refer to architecture.md security section)
   - Estimated size   (S | M | L)
   - UX reference     (FE only — reference design/{path} when design_mode != "null")
   - Category         (DevOps only — A = local creation | B = cloud operation)
   - References       (optional — related tasks / ADRs / sections.
                       Format: "- References: BE-api-2, ADR-003")

   Add at the end:
   - ## Shared / Cross-cutting Tasks
   - Dependency summary — Mermaid graph of task dependencies.

   Responsive effort (FE only, from responsive):
   - pc-only            → base effort
   - pc-mobile          → FE effort ~1.3x
   - pc-mobile-tablet   → FE effort ~1.5x

4. $DOCS_DIR/planning/test-strategy.md
   - ## Test Pyramid: Unit / Integration / E2E tables
     Each row: target, test items, priority (P0 | P1 | P2)
   - ## Edge Case List — per feature
   - ## Performance Test Criteria — Pass/Fail thresholds referencing PRD Performance Budget
   - Exclude tests for parts marked N/A in tasks.md.
```

---

## Completion Protocol

At phase completion, perform the following in order:

1. **Produce spec artifacts**:
   - `$DOCS_DIR/planning/architecture.md` (Mermaid + 3+ ADRs)
   - `$DOCS_DIR/planning/api-spec.md` (conditional)
   - `$DOCS_DIR/planning/tasks.md` (2D structure + Task ID + References)
   - `$DOCS_DIR/planning/test-strategy.md`
2. **(Optional) Handoff document**
3. **Write phase-results/phase2/attempt{K}.json** (last step):
   ```bash
   mkdir -p $DOCS_DIR/phase-results/phase2
   # Success
   echo '{"status":"completed","reason":"","reasonDetail":""}' \
     > $DOCS_DIR/phase-results/phase2/attempt{K}.json
   # Error
   echo '{"status":"error","reason":"...","reasonDetail":"..."}' \
     > $DOCS_DIR/phase-results/phase2/attempt{K}.json
   ```

**Strict order**: artifacts → (handoff) → phase-results JSON.
Do NOT write to `.jarfis-state.json` (the main Claude owns it).
`{K}` is substituted with the actual attempt number by the main session when generating the prompt file.
