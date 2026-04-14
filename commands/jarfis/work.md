# JARFIS - IT Team Workflow Orchestration

> **Locale**: All user-facing output (banners, messages, questions) must be presented in $LOCALE language.
> Internal instructions and reasoning: English. If $LOCALE is not set, auto-detect from user input.

The user has requested the following plan: $ARGUMENTS

Execute the workflow below automatically for this plan.

---

## Phase T: Triage (Request Classification — Required Before Workflow Entry)

**This phase runs before Phase 0 and serves as the gate that determines whether to enter the workflow.**

### Goal
Determine whether the user's request is suitable for the full JARFIS workflow (Phase 0–6).
If not, present alternatives and ask for confirmation.

### Classification Criteria

Classify the user's request (`$ARGUMENTS` + conversation context) into one of the following 3 types:

| Type | Criteria | Examples | Workflow Entry |
|------|----------|----------|----------------|
| **A. New plan / feature development** | Tasks requiring new feature implementation, refactoring of existing features, or system design | "Board CRUD + comments", "Payment module refactoring" | ✅ Normal execution from Phase 0 |
| **B. Partial execution of existing work** | Tasks that only need a specific Phase from an already-progressed workflow | "Run QA verification on already-implemented work", "Just do an architecture review" | ⚠️ Execute only the relevant Phase (after user confirmation) |
| **C. Not suitable for workflow** | Simple questions, debugging, configuration changes, etc. that don't fit the workflow structure | "Find the cause of this error", "Fix tsconfig" | ❌ Handle directly without workflow (after user confirmation) |

### Execution Logic

1. Analyze $ARGUMENTS → determine type (A/B/C). If `.jarfis-state.json` exists, type B is more likely.
2. Type A → proceed automatically to Phase 0. Type B → AskUserQuestion (relevant Phase only / full / proceed directly). Type C → AskUserQuestion (recommend direct handling / full execution).

### Type B Mapping Guide

| Request Pattern | Mapped Phase |
|----------------|-------------|
| QA, testing, verification, pre-deployment check | Phase 5 (Review & QA) |
| Code review, security review | Phase 5 (Review & QA) |
| Design review, architecture review | Phase 2 (Architecture & Planning) |
| UX feedback, screen design modification | Phase 3 (UX Design) |
| Additional implementation, bug fix (based on existing PRD) | Phase 4 (Implementation) |
| Deployment strategy, rollback plan | Phase 4.5 (Operational Readiness) |

### Type B Branch Rules
- When continuing existing work, branch from the **original feature branch** rather than `develop` (check the `branch` field in `.jarfis-state.json`).
- Record `base_branch` in `.jarfis-state.json` to track branching history.

---

## Workflow Overview

```
Phase T: Triage → Phase 0: Pre-flight → Phase 1: Discovery 🔒
→ Phase 2&3: Architecture+UX (parallel) 🔒 → Phase 4: Implementation
→ Phase 4.5: Operational Readiness → Phase 5: Review & QA 🔒
→ Phase 6: Retrospective (automatic)
```

## Artifacts (Output File Paths)

### Artifact Directory Rules

Artifacts are stored in `$JARFIS_ORG_DIR/works/{YYYYMMDD}-{type}-{ticket-name}/` directory (`$DOCS_DIR`).
> Note: See "Execution Rules > Org Dir Resolution" for `$JARFIS_ORG_DIR` resolution rules.

- Determine `$DOCS_DIR` at workflow start and store its **absolute path** in the `docs_dir` field of `.jarfis-state.json`.
- **Per-project files** (`project-profile.md`, `project-context.md`) are stored in each project's `.jarfis/`.

| Phase | File | Description | Conditional |
|-------|------|-------------|-------------|
| — | `$DOCS_DIR/.jarfis-state.json` | **Workflow state file (context loss prevention)** | Always |
| 1 | `$DOCS_DIR/press-release.md` | Working Backwards virtual press release + FAQ | Always |
| 1 | `$DOCS_DIR/prd.md` | PRD + feasibility assessment + **required roles determination** + **Performance Budget** | Always |
| 1 | `$DOCS_DIR/ux-direction.md` | UX direction document (IA, Tone & Voice, Pages + interaction patterns) | When UX Designer is needed |
| 2 | `$DOCS_DIR/impact-analysis.md` | Existing codebase impact scope analysis | Always |
| 2 | `$DOCS_DIR/architecture.md` | System architecture design + **ADR (Architecture Decision Records)** | Always |
| 2 | `$DOCS_DIR/api-spec.md` | API specification (endpoints, parameters, response schemas) | When both BE+FE are needed |
| 2 | `$DOCS_DIR/tasks.md` | Task decomposition (unnecessary parts marked N/A) | Always |
| 2 | `$DOCS_DIR/test-strategy.md` | Test strategy (test pyramid, scenarios, performance criteria) | Always |
| 3 | `$DOCS_DIR/design/` | HTML mockup directory (_index.html + per-URL mockups) | When FE + UX Designer are needed |
| 4 | `$DOCS_DIR/infra-runbook.md` | Manual infrastructure setup guide (AWS and other cloud tasks) | When DevOps executes |
| 4.5 | `$DOCS_DIR/deployment-plan.md` | Deployment strategy + rollback plan + operational readiness checklist | Always |
| 5 | `$DOCS_DIR/api-contract-check.md` | BE-FE API contract automated verification results | When api-spec.md exists |
| 5 | `$DOCS_DIR/review.md` | Review results for executed parts only | Always |
| 5 | `$DOCS_DIR/diagnosis.md` | Root cause diagnosis + fix directives | On re-review after fixes |
| 6 | `$DOCS_DIR/retrospective.md` | Workflow retrospective (per-project record) | Always |

### Learning File Paths

| File | Location | Description |
|------|----------|-------------|
| `learnings.md` | `$JARFIS_ORG_DIR/learnings.md` | **Per-Org** — Agent Hints + Workflow Patterns |
| `project-context.md` | `./.jarfis/project-context.md` | **Per-project** — Knowledge specific to this codebase |

---

## Phase 0: Pre-flight (Load Learning Files)

### Goal
Load learnings accumulated from previous workflows and project context to improve agent quality.

### Execution Order

0. **Locale Detection + Work Name Input + Git Branch Setup**

   **0-a-0. Locale Detection (top priority)**

   Determine the language for user-facing output. JARFIS internal reasoning/instructions are always in English.

   1. If `.jarfis-state.json` already exists and has a `locale` field → use that value as `$LOCALE`
   2. If not yet present (new workflow) → detect language from `$ARGUMENTS` text using rule-based detection:
      - Contains 1+ Korean characters (U+AC00~U+D7AF) → `$LOCALE = "ko"`
      - Contains 1+ Japanese characters (Hiragana U+3040~U+309F or Katakana U+30A0~U+30FF) → `$LOCALE = "ja"`
      - Neither of the above → `$LOCALE = "en"`
   3. Record the detected `$LOCALE` in `.jarfis-state.json` after initialization (after state init in Step 0-a):
      ```bash
      python3 ~/.claude/scripts/jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "locale" "$LOCALE"
      ```
   4. `$LOCALE` is used to control the agent's response language in all subsequent Phases.
      Include the following instruction when passing prompts to agents:
      `"Present ALL user-facing output in $LOCALE language."`

   > **Default**: If `$LOCALE` cannot be determined, use `"ko"` (same as existing behavior)
   > **Override**: Can be changed at any time during the workflow via `/jarfis:locale-set <code>`

   **0-a. Work Name Input**
   - Use AskUserQuestion to receive the work name (`$WORK_INPUT`) (e.g., `feat/TICKET-123`, `fix/BUG-456`).
   - `$WORK_DIR_NAME` = `{YYYYMMDD}-{$WORK_INPUT with / replaced by -}` (e.g., `20260311-feat-TICKET-123`)
   - `$BRANCH` = `$WORK_INPUT` (Git branch name preserves original, e.g., `feat/TICKET-123`)
   - `$DOCS_DIR` = `$JARFIS_ORG_DIR/works/$WORK_DIR_NAME` (absolute path). Create directory then initialize state:
     ```bash
     python3 ~/.claude/scripts/jarfis_cli.py state init "$DOCS_DIR/.jarfis-state.json" "$PROJECT_NAME" "$WORK_DIR_NAME" "$DOCS_DIR"
     ```
   - Preserve original input value in state file: `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "work_input" "$WORK_INPUT"`
   - Record branch name: `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "branch" "$BRANCH"`
   > Note: See "Execution Rules > Org Dir Resolution" for `$JARFIS_ORG_DIR` resolution rules.

   **0-a-2. Meeting Selection (semantic search + fallback)**
   - **Semantic search first**: Search for related meetings using the plan content from `$ARGUMENTS`:
     ```bash
     python3 ~/.claude/scripts/jarfis_cli.py search meetings "$ARGUMENTS" --top-k 3
     ```
     - If results exist (results not empty) → display recommendations via AskUserQuestion:
       - Convert each result to an Option: `[{source}] {file_path} (score: {score})`
       - Last Option: `No related meeting`
     - If no results or search fails (including out-of-memory) → display to user: `⚠️ Semantic search is unavailable (out of memory or not installed). Falling back to LLM-based search.` → **fallback** to recent meetings list:
       ```bash
       python3 ~/.claude/scripts/jarfis_cli.py meetings 3
       ```
       - If JSON result is not an empty array → AskUserQuestion: `[{date}] {name} - {summary}` + `No related meeting`
       - If empty array → skip meeting selection
   - If `$ARGUMENTS` contains `--meeting {plan name}` flag → auto-select by matching against script results (skip AskUserQuestion)

   **0-a-3. Meeting Context Load**
   - If a meeting is selected: `$MEETING_PATH` = `$JARFIS_ORG_DIR/{selected meeting path}/`
     - `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "source_meeting" "{selected meeting directory name}"`

     **Known files → existing variable mapping** (only files that exist):
     - `summary.md` → `$MEETING_SUMMARY`
     - `decisions.md` → `$MEETING_DECISIONS`
     - `meeting-notes.md` → `$MEETING_NOTES`
     - `tech-research.md` → `$MEETING_RESEARCH`

     **Additional files dynamic scan** → `$MEETING_EXTRA`:
     - Glob scan all `.md` files in `$MEETING_PATH`
     - Collect remaining files excluding the 4 known files above and hidden files (starting with `.`)
     - Concatenate each file into `$MEETING_EXTRA` with a `## [filename]` header
     - **Cap**: If total additional files exceed 200 lines, truncate and show `(... truncated — original: $MEETING_PATH/{filename})`
     - If no additional files, `$MEETING_EXTRA` = empty string

   - If "No meeting" is selected: `source_meeting` = `null`, all `$MEETING_*` variables = empty string

   **0-a-4. Workspace Detection (Project Structure Check)**

   Use AskUserQuestion to confirm the project structure and immediately record the `workspace` field in `.jarfis-state.json`.

   | Selection | workspace.type | BE path | FE path | Notes |
   |-----------|---------------|---------|---------|-------|
   | Monorepo | monorepo | `.` | `.` | Prompt for path if CWD is not a git repo |
   | Multi-project | multi-project | input | input | Validate each path |
   | FE only | monorepo | `N/A` | `.` or input | — |
   | BE only | monorepo | `.` or input | `N/A` | — |

   - Run framework auto-detection script on each path:
     ```bash
     python3 ~/.claude/scripts/jarfis_cli.py detect "$PROJECT_PATH"
     ```
     Use `frameworks`, `languages`, `project_type` from JSON output to record workspace info in `.jarfis-state.json`.
   - Set `$BACKEND_PROJECT_DIR`, `$FRONTEND_PROJECT_DIR` variables (empty string if `N/A`)

   **0-a-5. Domain Detection** (v3.0)

   Detect Domain Pack for each project path:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py domain detect "$PROJECT_PATH"
   ```
   - Set `$DOMAIN` to `matches[0].domain` from the result JSON
   - If `tie`=true → use AskUserQuestion for user to choose domain
   - If detection fails (exit code != 0, empty matches) → `$DOMAIN` = `null`
   - Record in `.jarfis-state.json`: `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "domain" "$DOMAIN"`
   > Note: If domain is null, falls back to existing hardcoded approach in Phase 4

   **0-b. Git Branch Sync and Creation**

   - **monorepo**: Check git repo → warn about uncommitted changes → pull default branch + develop → `git checkout -b $BRANCH develop` → record `branch` in `.jarfis-state.json`. If develop doesn't exist, ask whether to branch from default branch.
   - **multi-project**: Repeat the same process independently for each BE/FE path. Record `branches: { backend, frontend }` in `.jarfis-state.json`.

1. **System Health Check** — Run `~/.claude/scripts/claude-cleanup.sh` in diagnostic mode if it exists. 5+ zombies → AskUserQuestion, 1–4 → warning, 0 → ignore.
2. **Pre-flight Verification** — Verify profile/learnings/context/Org existence in one call via script:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py preflight --check-meetings
   ```
   Check `has_rule`, `has_context`, `has_profile`, `org_root`, `has_wiki`, `warnings` from JSON output:
   - `has_rule`=true → record `rule_path` for lazy loading (do NOT read content here)
   - `has_context`=true → record `context_path` for lazy loading (do NOT read content here)
   - `has_profile`=true → record `profile_path` for lazy loading (do NOT read content here)
   - `org_root` non-null → set `$ORG_ROOT` variable. Confirm Org name via `org_name`. If `org_auto_registered`=true, output "Org '{org_name}' auto-registered"
   - If `warnings` array is not empty, display warnings to user
   - Substitute empty string for missing files

   **2-1. Incomplete Workflow Detection** (when Org is registered — `$ORG_ROOT` exists)
   - Run `jarfis_cli.py state list-workflows` (auto-scans entire Org workspace)
   - If workflows with `status != "completed"` exist:
     - Display list of incomplete workflows and `key_decisions`
     - AskUserQuestion: "There are incomplete workflows. There may be decisions not yet reflected in the wiki." (Continue / Review before proceeding)

   **2-2. Wiki 4-Step Loading** (when Org is registered — `$ORG_ROOT` exists + `has_wiki`=true)
   > Prompt: Execute the "4-Step Full Loading" procedure from `prompts/wiki-loading.md`.
   - INDEX.md → 4 _index.md files → read up to 5 related files
   - Save loaded wiki content as `$WIKI_CONTEXT`

   **2-3. Cascading Specificity Rule Injection**
   - When Org is registered, inject the following rule into all agent prompts:
   > Information priority: $DOCS_DIR > project/.jarfis > wiki/ > INDEX.md
   > Topics covered by this task: $DOCS_DIR takes precedence. Topics not covered: wiki is authoritative.
3. Load project profiles: `$BACKEND_PROJECT_DIR/.jarfis/project-profile.md` + `$FRONTEND_PROJECT_DIR/.jarfis/project-profile.md` (Phase 4–5) → `$BE_PROJECT_PROFILE`, `$FE_PROJECT_PROFILE`

**Injection Rules (Lazy Loading):**

All context files are read at agent spawn time, NOT pre-loaded in Phase 0.

**Orchestrator injection order** (domain/non-domain 공통):
1. `project-rule.md` — if role is in {BE, FE, DevOps, QA, TL} only
2. Persona — from `domain compose` or hardcoded persona file
3. Skills — from `domain compose` (null if no domain)
4. `project-context.md` — per-agent matrix (see brainstorm-audit.md B-revised)
5. `project-profile.md` — per-agent matrix
6. Phase artifacts — agent reads via tool calls, paths in prompt
7. Scope guard — Phase 4 Step 4-1 only, BE/FE/DevOps only
8. Phase 2 handoff — Phase 4 only (from state `phases.2.handoff`)
9. Phase 4 agent status — Phase 5 only (from state `phase4_agents`)

**Priority**: project-rule(1) > project-context(2) > project-profile(3) > wiki(4)
**$LOCALE**: Injected into ALL agent prompts as cross-cutting directive.
**Cascading Specificity**: When Org is registered, inject priority rules into all Phases.

Substitute empty string if files don't exist.

---

## Phase 1: Discovery

### Goal
Clarify the user's plan intent and simultaneously verify technical feasibility.

### Execution Order

**Step 1-0: PO Wiki Reference** (when Org is registered)
- Inject PO/ wiki context to PO: domain-map.md, policies/, business-rules/, etc.
- Guide to maintain consistency with existing policies/rules

> Prompt: Read the Step 1-0 section from `prompts/phase1.md` and pass to the agent.
> Skip this Step if Org is not registered.

**Step 1-1: PO Reverse Questions** (senior-product-owner)

> **Conditional behavior with meeting reference**: If `$MEETING_REF` exists, inject meeting context (`$MEETING_SUMMARY`, `$MEETING_DECISIONS`, `$MEETING_NOTES`, `$MEETING_RESEARCH` + dynamically scanned `$MEETING_EXTRA`) and only ask about unresolved items.

> Prompt: Read the relevant section from `prompts/phase1.md` and pass to the agent.

> Proceed to the next step once the user answers the reverse questions

**Step 1-1.5: Working Backwards Document** (senior-product-owner)
> Prompt: Read the relevant section from `prompts/phase1.md` and pass to the agent.

**Step 1-2: PRD Writing + Feasibility Assessment** (parallel execution)

PO (senior-product-owner):
> Prompt: Read the relevant section from `prompts/phase1.md` and pass to the agent.

Architect (technical-architect):
> Prompt: Read the relevant section from `prompts/phase1.md` and pass to the agent.

**Step 1-2.5: PRD Completeness Check — Ratchet** (orchestrator executes directly — not an agent)

> Prompt: Read the Step 1-2.5 section from `prompts/phase1.md` and execute directly as the orchestrator.
> Score the PRD on 5 items with Pass/Fail + score (0-2 each), then apply ratchet rules.

**Scoring Criteria** (0-2 points each, 10 points total):

| Item | 0 pts (Fail) | 1 pt (Fail) | 2 pts (Pass) |
|------|-------------|-------------|-------------|
| Ambiguous expressions | 3+ vague terms like "appropriate/fast/sufficient" | 1-2 remaining | All converted to specific numbers |
| KPI measurability | No KPIs or qualitative only | Numbers exist but measurement method unspecified | Both numbers + measurement method specified |
| Performance Budget | Undefined | Only some metrics quantified | All metrics have numbers + measurement method |
| Required Roles rationale | No rationale | Rationale for only some roles | 1+ sentence rationale for every role |
| Scope boundary | Out of Scope undefined | Only inclusion scope defined | Both inclusion + exclusion scope specified |

> Warning: **Immutable Evaluator Principle**: The scoring criteria above are for the orchestrator only. Do NOT include these criteria in the PO agent prompt.

**Ratchet Logic**:
1. On initial PRD creation → score 5 items → record per-item Pass(2pts)/Fail(0-1pts) status + total score
2. All 5 items Pass → proceed to Gate 1
3. Fail items exist → send Fail items + current score to PO, instruct to rewrite only those items
4. After PO rewrite, re-score:
   - **Ratchet verification**: Check whether any previously-Passed item changed to Fail
   - No ratchet violation → apply results, retry within remaining attempts
   - **Ratchet violation detected** → warn PO: "Previously-passed [item name] has now failed. Improve only the Fail items while maintaining quality of that item" and re-instruct
5. If Fail items remain after max 2 attempts → display "PRD Score: X/10, Failed items: [list]" at Gate 1 for user judgment

**State Recording** (`.jarfis-state.json`):
```
jarfis_cli.py state set-nested phases.1.ratchet '{
  "prd_score": <total>,
  "items": {"ambiguity": <0-2>, "kpi": <0-2>, "perf_budget": <0-2>, "roles_rationale": <0-2>, "scope_boundary": <0-2>},
  "passed_items": ["<list of passed items>"],
  "attempts": <attempt count>,
  "history": [{"score": <N>, "passed": ["<items>"], "action": "accept|ratchet_violation"}]
}'
```

### 🔒 Gate 1: User Confirmation
Display a summary of artifacts (`press-release.md`, `prd.md`) + **PRD Completeness Score**, then AskUserQuestion:
```
question: "Review the Phase 1 artifacts. PRD Score: {X}/10 (Pass: {N}/5). How would you like to proceed?"
header: "Gate 1"
options:
  - label: "Approve — proceed to next Phase"
    description: "PRD + Working Backwards document are sufficient"
  - label: "Request revision"
    description: "PO will rewrite incorporating feedback"
  - label: "Abort"
    description: "Terminate the workflow immediately"
```

**Step 1-3: PO Additional Tasks** (after Gate 1 approval, senior-product-owner)

> After passing Gate 1, PO optionally executes additional tasks.

**Step 1-3-pre: Designer Availability Check** (only when UX Designer is ✅ in Required Roles)

> If the PRD determined that a UX Designer is needed, check whether a designer exists on the team.

AskUserQuestion:
```
question: "Does your team have a UX designer?"
header: "Design Path"
options:
  - label: "Yes — we have Figma designs"
    description: "A designer has provided design mockups via Figma"
  - label: "No — AI agent will handle design"
    description: "UX Designer agent will design directly based on ux-direction.md"
```

- If "Yes" is selected:
  - Record `phases.3.has_designer: true` in `.jarfis-state.json`
  - Use AskUserQuestion to receive Figma page list:
    ```
    question: "Please enter the Figma page URLs as a JSON array.\nExample: [{\"title\": \"Benefits Intro\", \"url\": \"https://figma.com/design/...?node-id=123-456\"}, ...]"
    header: "Figma Pages"
    ```
  - Save the input JSON array as `phases.3.figma_pages` in `.jarfis-state.json`
  - Record `phases.3.mode: "figma"`
  - If more than 5 pages, warn: "More than 5 pages may consume significant tokens. Consider reducing based on priority."

- If "No" is selected:
  - Record `phases.3.has_designer: false`, `phases.3.mode: "text"` in `.jarfis-state.json`
  - Record `phases.3.figma_pages: []`

> If UX Designer is marked ⬜ not needed in the PRD, skip this Step and keep `has_designer: null`.

AskUserQuestion:
```
question: "Select PO additional tasks (multiple selection allowed)"
header: "PO Tasks"
multiSelect: true
options:
  - label: "Legal/Compliance check"
    description: "Review personal data collection/processing, terms/payments/refunds, industry regulations, GDPR"
  - label: "Write UX direction document"
    description: "Write ux-direction.md (when UX Designer is needed — IA, Tone, Pages all-in-one)"
```

- **Legal/Compliance**: PO adds legal considerations to prd.md based on the PRD
- **UX Direction**: PO writes `$DOCS_DIR/ux-direction.md` referencing `templates/ux-direction.md`. Interaction patterns must be included.

**Responsive Scope Setting** (when FE is needed — Frontend is ✅ in Required Roles):
AskUserQuestion:
```
question: "Select responsive scope"
header: "Responsive"
options:
  - label: "PC only"
    description: "Desktop viewport only"
  - label: "PC + Mobile"
    description: "Desktop + Mobile (FE effort ~1.3x)"
  - label: "PC + Mobile + Tablet"
    description: "Desktop + Mobile + Tablet (FE effort ~1.5x)"
```
Record the selection in the `responsive` field of `.jarfis-state.json`.

> Prompt: Read the Step 1-3 section from `prompts/phase1.md` and pass to the agent.
> If nothing is selected, skip this Step.

---

## Phase 2: Architecture & Planning + Phase 3: UX Design (Parallel)

Phase 2 and Phase 3 run concurrently.

### Phase 2: Architecture & Planning

**Step 2-(-1): TA/QA Wiki Reference** (when Org is registered)
- TA: Check TA/ wiki for decisions/, api-contracts/, data-models/
- QA: Check QA/ wiki for test-standards.md, regression-checklist.md
> Prompt: Read the Step 2-(-1) section from `prompts/phase2.md` and pass to the agent.
> Skip this Step if Org is not registered.

**Step 2-0: Impact Analysis** (technical-architect)
> Prompt: Read the relevant section from `prompts/phase2.md` and pass to the agent.

**Step 2-1: System Architecture Design** (technical-architect)
> Prompt: Read the relevant section from `prompts/phase2.md` and pass to the agent.

**Step 2-1.5: API Specification** (technical-architect → tech-lead sequential) — **Only when both BE+FE are needed**

> **Execution condition**: Only execute when both Backend Engineer and Frontend Engineer are marked ✅ needed in the PRD's 'Required Roles'.

Architect (technical-architect):
> Prompt: Read the relevant section from `prompts/phase2.md` and pass to the agent.

Tech Lead (tech-lead) — api-spec.md review:
> Prompt: Read the relevant section from `prompts/phase2.md` and pass to the agent.

**Step 2-2: Task Decomposition** (tech-lead)
> Prompt: Read the relevant section from `prompts/phase2.md` and pass to the agent.

**Step 2-3: Test Strategy** (senior-qa-engineer)
> Prompt: Read the relevant section from `prompts/phase2.md` and pass to the agent.

### Phase 3: UX Design (Conditional — Only when FE is included + UX Designer is needed)

> **Skip condition**: Skip all of Phase 3 if Frontend Engineer is '⬜ not needed' or UX Designer is '⬜ not needed' in PRD 'Required Roles'.
> Runs in **parallel** with Phase 2 (intentional parallelism).

**Step 3-(-2): MCP Tool Availability Check** (orchestrator)

> Verify that MCP servers required for Phase 3 execution are installed.
> Required tools vary based on `phases.3.mode` in `.jarfis-state.json`.

```
mode === "figma" required tools:
  [Required] Framelink (get_figma_data, download_figma_images) — Figma data extraction/asset download
  [Required] Playwright (browser_navigate, browser_take_screenshot, etc.) — screenshot capture/verification
  [Recommended] mcp-design-comparison (compare_design) — pixel-diff numerical comparison

mode === "text" required tools:
  [Required] Playwright — reference.png generation + Phase 5 UX Review screenshots
  [Recommended] mcp-design-comparison — Phase 5 pixel-diff comparison
```

Check method: Lightly attempt to call each MCP tool and determine availability by response.
- Framelink: Check if `get_figma_data` tool exists
- Playwright: Check if `browser_take_screenshot` tool exists
- compare_design: Check if `compare_design` tool exists

Handling when missing:
- **Required tool missing** → display installation instructions + AskUserQuestion:
  ```
  question: "MCP servers required for Phase 3 are missing:\n- {missing list}\n\nWould you like to continue after installing?"
  header: "MCP Check"
  options:
    - label: "Installation complete — continue"
      description: "Select this option after installing the MCP server(s)"
    - label: "Proceed without (not recommended)"
      description: "Functionality will be limited (e.g., Figma extraction unavailable)"
  ```
- **Recommended tool (compare_design) missing** → warning only, proceed automatically:
  "⚠️ mcp-design-comparison is not available. Falling back to visual comparison instead of pixel-diff numerical comparison."

**Step 3-(-1): Import Existing Mockups** (orchestrator)
- When Org is registered: Copy `wiki/DESIGN/pages/{project}/` → `$DOCS_DIR/design/`
- If no existing mockups, create empty `$DOCS_DIR/design/` directory

#### 🔀 Branch: Path Selection Based on Designer Availability

> Path is determined by `phases.3.has_designer` and `phases.3.mode` in `.jarfis-state.json`.
> These values were already set in Phase 1 Step 1-3-pre.

`phases.3.mode === "figma"` (designer available, Figma provided) → **Figma-Driven Path** (Step 3-F0~3-F4)
- Execute 3-F0~3-F3 **in parallel for each page** in the `phases.3.figma_pages` array
- Independent directory per page: `design/{title in kebab-case}/` (e.g., `design/benefits-signup/`)
- 3-F4 review covers all pages at once

`phases.3.mode === "text"` (no designer) → **Text Path** (Step 3-0~3-1, existing)

> Figma-Driven Path prompt: Read the entirety of `prompts/phase3-figma.md` and execute in order.

**[Text Path] Step 3-0: HTML Mockup Creation/Modification** (senior-ux-designer)
- Create HTML mockups based on `$DOCS_DIR/ux-direction.md`
- URL → file mapping: `/{path}` → `$DOCS_DIR/design/{path}/index.html` or `{path}.html`
- Insert `templates/design-html-meta.md` meta comment at the top of each HTML file
- Auto-generate `$DOCS_DIR/design/_index.html` (table of contents for all mockups)
> Prompt: Read the Step 3-0 section from `prompts/phase2.md` and pass to the agent.

**[Text Path] Step 3-1: PO ↔ Designer Feedback Loop** (max 3 rounds)
1. PO (senior-product-owner): Review mockups, provide feedback on gaps/inconsistencies vs PRD
2. Designer (senior-ux-designer): Revise mockups incorporating feedback
3. If unresolved after 3 rounds → escalate to user Gate
> Prompt: Read the Step 3-1 section from `prompts/phase2.md` and pass to the agent.

**User Gate**: Open `open $DOCS_DIR/design/_index.html` in browser, then AskUserQuestion:
```
question: "Have you reviewed the HTML mockups? How would you like to proceed?"
header: "UX Gate"
options:
  - label: "Approve — finalize mockups"
    description: "Mockups are consistent with PRD/ux-direction.md"
  - label: "Request revision"
    description: "Enter feedback and Designer will revise"
  - label: "Re-review after Phase 2 completion"
    description: "Review again alongside architecture design"
```

**[Text Path] Step 3-2: reference.png Generation** (auto-executes on approval)

> After mockup approval, generate reference.png files to be used as comparison baselines in Phase 5 UX Review.
> Unified naming with Figma Path's reference.png so Phase 4/5 can reference them identically without path branching.

```
For each design/{path}/index.html:
1. Take screenshot via Playwright MCP (fullPage: true, DPR: 2)
2. Save as design/{path}/reference.png
```

### 🔒 Gate 2: User Confirmation
Display a summary of artifacts (`impact-analysis.md`, `architecture.md`, `api-spec.md`, `tasks.md`, `test-strategy.md`, `design/`) + executed parts, then AskUserQuestion:
```
question: "Review the Phase 2&3 artifacts. How would you like to proceed?"
header: "Gate 2"
options:
  - label: "Approve — proceed to Implementation Phase"
    description: "Design + task decomposition are sufficient"
  - label: "Request revision"
    description: "The relevant agent will rewrite incorporating feedback"
  - label: "Abort"
    description: "Terminate the workflow immediately"
```

---

## Phase 4: Implementation

### Goal
Implement in parallel based on design documents. Security performs a pre-review before implementation.
> Note: See "Execution Rules > Skip Rules" for skip decisions

### Execution Order

**Step 4-0: Security Pre-Review** (senior-security-engineer)
> Prompt: Read the relevant section from `prompts/phase4.md` and pass to the agent.

**Step 4-0.5: Test-First Writing (TDD Red Phase)** (senior-qa-engineer) — **Conditional**
> Execution condition: `$DOCS_DIR/test-strategy.md` exists + 3 or more P0 test scenarios + unit test framework exists in project.
> If enabled, record `phases.4.tdd_enabled: true` in `.jarfis-state.json`.
> If skipped, record `phases.4.tdd_enabled: false`.
> Prompt: Read the Step 4-0.5 section from `prompts/phase4.md` and pass to the agent.

**Step 4-0.5a: TDD Baseline Recording** (orchestrator executes directly, only when `tdd_enabled: true`)

> Immediately after Step 4-0.5 completion, orchestrator runs the full test suite to record the baseline.
> Instruct the implementation agent to "run tests and report passed/failed/total" to obtain results.
> Framework-independent: extract test runner command from the project-profile scripts section.

```
jarfis_cli.py state set-nested "$DOCS_DIR/.jarfis-state.json" "ratchet.phase4_tests" '{
  "baseline_pass_rate": <passed/total>,
  "test_command": "<test command extracted from project-profile>",
  "task_index": 0,
  "test_modifications": [],
  "history": []
}'
```

**Step 4-1: Parallel Implementation — Ratchet Loop** (simultaneously execute only the parts with tasks in tasks.md)
> If TDD was enabled in Step 4-0.5, a TDD Green Phase block is added to each implementation agent.
> Prompt: Read the relevant section from `prompts/phase4.md` and pass to the agent.

**Agent Mapping Branch** (v3.0):

When `$DOMAIN` is not null (domain.yaml based):
1. `jarfis_cli.py domain agents "$DOMAIN" implement` → load role list JSON
2. If domain.yaml has `hooks.phase4.before`, read that file and provide as pre-context
3. For each role:
   a. Call `jarfis_cli.py domain compose "$DOMAIN" "$ROLE_NAME"`
   b. Call Agent tool with returned `{agent_type, prompt_content}` (model from role's model field)
   c. Auto-commit (using commit_prefix: `jarfis({PREFIX}-{N}):`)
4. If domain.yaml has `hooks.phase4.after`, execute it
5. Ratchet check: run tests using domain.yaml's `pipeline.test.runner`

When `$DOMAIN` is null (existing approach — fallback):
- Execute using the hardcoded agent mapping below

Backend (senior-backend-engineer), Frontend (senior-frontend-engineer), DevOps (senior-devops-sre-engineer):
> Prompt: Read the relevant section from `prompts/phase4.md` and pass to the agent.

**TDD Ratchet Rules** (when `tdd_enabled: true`, orchestrator executes after each task completion):

1. After implementation agent completes task + git commit
2. Orchestrator: instruct agent to "run full test suite → report passed/failed/total numbers"
3. current_pass_rate = passed / total
4. **Ratchet judgment**:
   - current_pass_rate >= baseline_pass_rate → **ACCEPT**
     - baseline_pass_rate = current_pass_rate (update)
     - Increment ratchet.phase4_tests.task_index
     - Add `{"task": "BE-N", "pass_rate": X, "action": "accept"}` to history
   - current_pass_rate < baseline_pass_rate → **REJECT**
     - `git stash` to save changes
     - Instruct agent: "Task implementation broke N existing tests. Broken tests: [list]. Run `git stash pop` to restore code, then implement the task while passing all existing tests." Re-instruct
     - Retry (max **2 times** per task)
     - Add `{"task": "BE-N", "pass_rate": X, "action": "reject", "attempt": N}` to history
5. If still failing after 2 retries → `git stash pop` to restore → record warning → move to next task
   - Add `{"task": "BE-N", "pass_rate": X, "action": "skipped_after_max_retries"}` to history
   - Flag this task as a diagnosis target in Phase 5

**Test File Modification Detection** (orchestrator):
- Check whether files in `tests/`, `__tests__/`, `*.test.*`, `*.spec.*` paths were modified in each task commit
- If modification detected: add `{"file": "<path>", "task": "BE-N", "reason": "<commit message>"}` to `ratchet.phase4_tests.test_modifications`
- Flag as post-verification target for modification validity in Phase 5 QA review

> Warning: **Anti-pattern**: Do NOT repeat all of Phase 4 or retry more than 2 times per task. If unresolvable, diagnose in Phase 5.

---

## Phase 4.5: Operational Readiness

### Goal
After implementation is complete and before production deployment, review deployment strategy and operational readiness.

### Execution Order

**Step 4.5-1: Deployment Strategy + Operational Readiness** (tech-lead)
> Prompt: Read the relevant section from `prompts/phase4-5.md` and pass to the agent.

---

## Phase 5: Review & QA

### Goal
Perform code review, QA, and security review **only on code from parts that were actually executed in Phase 4**.
> Note: See "Execution Rules > Skip Rules" for skip decisions

### Execution Order

**Step 5-0: API Contract Automated Verification** — **Only when api-spec.md exists**

Tech Lead (tech-lead):
> Prompt: Read the relevant section from `prompts/phase5.md` and pass to the agent.

**Step 5-1: Parallel Review** (3–4 agents run simultaneously)

Tech Lead (tech-lead), QA (senior-qa-engineer), Security (senior-security-engineer):
> Prompt: Read the relevant section from `prompts/phase5.md` and pass to the agent.

UX Designer (senior-ux-designer) — **Only participates when FE is included + UX Designer is required**:
> **Precondition**: A dev server URL is needed. Request from user via AskUserQuestion:
> ```
> question: "Please provide the dev server URL for UX Design Review (e.g., http://localhost:3000)"
> header: "Dev Server"
> ```
> Once user provides URL, save as `$DEV_SERVER_URL` and record in `dev_server_url` field of `.jarfis-state.json`.
> Prompt: Read the UX Design Review section from `prompts/phase5.md` and pass to the agent.
> Perform visual comparison of HTML mockups vs FE implementation via Playwright

**Result Integration**: Only integrate review results from executed agents into `$DOCS_DIR/review.md`.

### 🔒 Gate 3: Final Confirmation

> **Pathological pattern detection (on 2nd+ re-review)**: Execute the "Step 5-2 Pathological Pattern Detection" procedure from `prompts/phase5.md`.

Display review result summary (code review / API contract / QA / security / deployment / UX Design Review), then AskUserQuestion:
```
question: "Review the Phase 5 results. How would you like to proceed?"
header: "Gate 3"
options:
  - label: "Approve — proceed to Retrospective Phase"
    description: "No review issues or they are acceptable"
  - label: "Fix and re-review"
    description: "Fix issues and re-run from Step 5-0"
  - label: "Abort"
    description: "Terminate the workflow immediately"
```
> If pathological pattern is detected, add a 4th option: `"Re-examine Phase 2 design" — "Cannot resolve through repeated fixes, re-examine from design phase"`

### Step 5-2: Root Cause Diagnosis (when "Fix and re-review" is selected at Gate 3)

Tech Lead (tech-lead):
> Prompt: Read the relevant section from `prompts/phase5.md` and pass to the agent.

### Step 5-3: Fix Implementation (diagnosis-based fixes)

Based on fix directives from diagnosis.md, execute the responsible agent (BE/FE/DevOps). Fix P0 first + regression prevention tests.

Backend/Frontend (only when relevant fix directives exist):
> Prompt: Read the relevant section from `prompts/phase5.md` and pass to the agent.

> After fixes are complete, **re-run** Step 5-0 ~ Step 5-1 → Gate 3.

---

## Phase 6: Retrospective (Automatic)

### Goal
Accumulate learnings from this workflow into the **global learnings file** and **project context file**, and update the **wiki** when Org is registered.

### Execution Order (sequential: extract learnings first → update wiki later)

**Step 6-1: Write Retrospective** (tech-lead)
> Prompt: Read the relevant section from `prompts/phase6.md` and pass to the agent.

**Step 6-2: Update Learning Files** (orchestrator executes directly)

Read retrospective.md and distribute to the following two files:

**1. Global Learnings — `$JARFIS_ORG_DIR/learnings.md`**
> Template: Read `templates/learnings.md` and use as the artifact format.

Management rules: Append to existing file (update if duplicate), remove outdated entries, record dates

**2. Project Context — `./.jarfis/project-context.md`**
> Template: Read `templates/project-context.md` and use as the artifact format.

Management rules: Update existing file (add new information, refresh outdated information)

**Step 6-2.5: Workflow Metrics Recording** (orchestrator executes directly)

> Prompt: Read the Step 6-2.5 section from `prompts/phase6.md` and execute directly as orchestrator.
> Extract key metrics from .jarfis-state.json and record in $JARFIS_ORG_DIR/workflow-metrics.tsv. Best-effort — warn only on failure.

**Step 6-3: Wiki Update** (only when Org is registered, orchestrator)
> Prompt: Read the Step 6-3 section from `prompts/phase6.md` and execute.
- Track A: Text Wiki (PO, TA, QA) — extract accumulated knowledge from artifacts → update wiki
- Track B: DESIGN HTML Sync (only when FE is included) — $DOCS_DIR/design/ → wiki/DESIGN/pages/{project}/
- Display update summary to user

**Step 6-4: Record Workflow Completion Status**
```bash
jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "status" "completed"
```
- Record final key decisions agreed upon at Gate 1/2/3 in the `key_decisions` field

---

## Execution Rules

### Prompt & Template Path Resolution

Base path for relative paths referenced in this document:

| Reference Pattern | Absolute Path |
|-------------------|--------------|
| `prompts/*.md` | `~/.claude/commands/jarfis/prompts/*.md` |
| `templates/*.md` | `~/.claude/commands/jarfis/templates/*.md` |
| `agents/jarfis/*.md` | `~/.claude/agents/jarfis/*.md` |

> Warning: The base is `~/.claude/`, NOT `$JARFIS_SOURCE` (Git repo).
> Always use the absolute paths above when reading prompts/templates.

### Workflow State Management (Context Loss Prevention)

Use **`$DOCS_DIR/.jarfis-state.json`** as the single source of truth (SSOT) for the workflow.

> State file schema and field descriptions: See `templates/jarfis-state-schema.md`.

**State File Management Rules (using jarfis_cli.py state):**
1. Workflow start: `jarfis_cli.py state init "$STATE_FILE" "$PROJECT_NAME" "$WORK_NAME" "$DOCS_DIR"`
2. Phase start/completion: `jarfis_cli.py state set-nested "$STATE_FILE" "phases.{N}.status" "in_progress|completed|skipped"`
3. Agent status: `jarfis_cli.py state set-nested "$STATE_FILE" "phase4_agents.backend" "completed"`
4. Gate results: `jarfis_cli.py state set-nested "$STATE_FILE" "gate_results.gate1.decision" "approved"`
5. Before each Phase starts: `jarfis_cli.py state read "$STATE_FILE"` — do not re-run already completed Phases
6. On every state change: `jarfis_cli.py state set "$STATE_FILE" "current_phase" "{N}"` + update `last_checkpoint`
7. Workflow end: `jarfis_cli.py state set "$STATE_FILE" "current_phase" '"done"'`

**`api_spec_required` determination**: `required_roles.backend == true AND frontend == true` → `true`, otherwise → `false`

### Org Dir Resolution

`$JARFIS_PERSONAL_DIR` = contents of `~/.claude/.jarfis-personal-dir` file (defaults to `{JARFIS_SOURCE}/.personal` if missing). `{JARFIS_SOURCE}` is read from the `~/.claude/.jarfis-source` file.
`$JARFIS_ORG_DIR` = `$JARFIS_PERSONAL_DIR/orgs/{org_name}/` (when Org is detected) or `$JARFIS_PERSONAL_DIR/orgs/_standalone/` (when no Org). Determined from the `org_root` result of `jarfis_cli.py preflight`.

### Agent Mapping
> v3.0: When `$DOMAIN` is set, the `roles` section of domain.yaml replaces this table. The table below is for `$DOMAIN`=null fallback only.

| Role | Agent (subagent_type) | Model |
|------|----------------------|-------|
| Product Owner | senior-product-owner | opus |
| Architect | technical-architect | opus |
| Tech Lead | tech-lead | opus |
| UX Designer | senior-ux-designer | opus |
| Backend Engineer | senior-backend-engineer | sonnet |
| Frontend Engineer | senior-frontend-engineer | sonnet |
| DevOps/SRE | senior-devops-sre-engineer | sonnet |
| QA Engineer | senior-qa-engineer | opus |
| Security Engineer | senior-security-engineer | opus |

### Skip Rules

**Core principle**: Only execute an agent when it has work to do.

**Phase 4 skip**: If a section in `tasks.md` is "N/A", SKIP that agent. However, at least 1 part must always execute (all N/A is not allowed).
**Step 4-0.5 skip**: SKIP if test-strategy.md doesn't exist, or fewer than 3 P0 test scenarios, or no unit test framework in the project. Does not apply to DevOps-only tasks.
**Phase 5 skip**: Parts SKIPped in Phase 4 are also excluded from review. If UX is SKIPped, exclude UI tests.
**Phase 3 skip**: SKIP entirely if UX Designer is '⬜ not needed' in PRD Required Roles
**Phase 2-1.5 skip**: SKIP api-spec.md if both BE+FE are not needed

#### Adaptive Skip Experience Guide
- UX SKIP: When reusing existing design system + no new screens needed. DevOps SKIP: Config changes only + no infrastructure structure changes.
- Phase 4.5 lightweight: If `required_roles.devops == false`, reduce to 5-item checklist. Mongoose `default: null` can substitute for migration.

### Parallel Execution Rules
- Phase 2+3 start simultaneously (Phase 2 only if Phase 3 is SKIPped)
- Phase 2 internal: 2-0 → 2-1 (parallelizable) → 2-1.5 (conditional) → 2-2 → 2-3 (after 2-2 completes)
- Phase 4: Simultaneously execute only parts with tasks among BE/FE/DevOps. Step 4-0 security review goes first.
- Phase 5: Step 5-0 (API Contract) goes first → Step 5-1 (TL/QA/Security simultaneously)
- Phase 4.5, 6 proceed automatically after the previous Phase completes

### Variable Resolution
> Note: `$BACKEND_PROJECT_DIR`, `$FRONTEND_PROJECT_DIR` are resolved from the `workspace` field in `.jarfis-state.json`.
> Note: Source paths and injection rules for learning/profile variables — see "Injection Rules" in Phase 0. Empty string if file doesn't exist.

### File Handoff Protocol
1. Each agent **reads** artifacts from the previous Phase and uses them as context.
2. Artifacts must be saved to the designated file paths.
3. Auto-create `$DOCS_DIR/` directory if it doesn't exist.
4. On file conflicts: the agent writing later preserves existing content and **appends** its own section.

### Gate Point Rules
1. At gates, **summarize artifact contents and present to the user**.
2. **Always use AskUserQuestion** to get an explicit user selection (do not auto-proceed with text output alone).
3. "Revision" → re-run the relevant Phase agent. "Approve" → auto-proceed to next Phase. "Abort" → terminate immediately.

### SuperClaude Integration
When needed: `/sc:brainstorm` (Phase 1), `/sc:design` (Phase 2), `/sc:implement` (Phase 4), `/sc:analyze`/`/sc:test` (Phase 5)

### Progress Display
At the start of each Phase, read `.jarfis-state.json` and display a progress bar + active roles + learning load status.

### Resume After Context Compression
1. Read `$DOCS_DIR/.jarfis-state.json` (if `$DOCS_DIR` is unknown, search for the most recent file in `$JARFIS_ORG_DIR/works/`)
2. Check `docs_dir`, `current_phase`, `last_checkpoint`
3. Resume from the `in_progress` Phase. Never re-run `completed` Phases.
4. **Compact backup**: State file can be recovered from `$DOCS_DIR/.compact-backups/` directory (PreCompact hook integration)
5. Cross-verify actual completion by checking artifact file existence
