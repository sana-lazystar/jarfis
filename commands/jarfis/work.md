# JARFIS v4 — /jarfis:work

> **Locale**: All user-facing output (banners, messages, AskUserQuestion labels) in `$LOCALE`. Internal reasoning English OK. If `$LOCALE` is unset, read `~/.claude/.jarfis-locale`; otherwise auto-detect from user input and persist it.
> **Spec**: Detailed design in `~/Upscales/jarfis-v4-migration/system-spec.md` §9 (flow chart) + §9.2 (Phase × executor matrix). Required Inputs: §16. state schema: implement-plan.md A.1.
> **Naming**: This file is the v4 orchestrator (`/jarfis:work`). v3 orchestrator is archived at `work-legacy.md` (M7 swap).

User input: `$ARGUMENTS`

---

## Phase Router (flow chart, see system-spec §9.1 for full)

```
T → 0 → 1a → 1b → Gate1 → 2 ∥ 3 → Gate2 → 4 → 4.5 → 5 → Gate3 → 6

Direct (main):   T, 0, 1a, Gate 1/2/3
tmux (foreman):  1b, 2, 3, 4, 4.5, 5, 6
```

Phase 3 runs only when `state.design.mode != null`. Phase 2 + Phase 3 run in parallel (two background tmux sessions, `{sessionKey}-phase2` and `{sessionKey}-phase3` — B1 isolation: `kill_existing_session` matches on exact name only, never on prefix). Phase 4.5 uses `phase_id = "4-5"` (hyphen, per A.3).

**State write rule (architecture §1 principle #6)**: Only the main session writes to `.jarfis-state.json`. tmux sub-agents write exclusively to `phase-results/phase{N}/attempt{K}.json` and Phase output directories (`discovery/`, `planning/`, `design/`, `review/`, `ops/`, etc.). The main session reads sub-agent meta and reflects selected fields into state.

**v4 entry point**: `/jarfis:work` invokes this file. The v3 orchestrator is archived at `~/.claude/commands/jarfis/work-legacy.md` for reference only (M7 swap).

---

## Resume Dispatch (runs before Phase T)

On entry, detect whether a workflow is already in progress:

1. Resolve candidate `docsDir`: prefer `$ARGUMENTS` if it looks like a path, else CWD, else most recent under `$JARFIS_ORG_DIR/works/`.
2. If `{docsDir}/.jarfis-state.json` exists, inspect its top-level keys:
   - `sessionKey` present → **v4 state**. AskUserQuestion (labels in `$LOCALE`): "Resume from current phase" / "Start over" / "Abort". On Resume: load state; skip any Phase whose `phases.{N}.status == "verified"`; re-enter from `state.currentPhase` (verify idempotence first — if the Phase artifacts already pass `phase-verify`, promote to `verified` without re-running).
   - `project_name` present (no `sessionKey`) → **v3 state detected**. Tell the user (in `$LOCALE`): "v3 workflow state detected at this path. Continue with the legacy `/jarfis:work` (v3) for this work; start v4 work in a new directory." Halt — do NOT migrate state silently.
3. No state file → proceed to Phase T with a fresh session.

---

## Phase T — Triage (main, direct)

Classify `$ARGUMENTS` + recent conversation into one of three types (Type B removed in M7):

- **Type A** (new feature / refactor / design request) → proceed automatically to Phase 0.
- **Type C** (simple question / debug / config tweak, not workflow-shaped) → AskUserQuestion: "Handle directly (recommended)" / "Run full workflow anyway" / "Abort". If direct, exit the orchestrator and answer in the main session.
- **Resume** is already dispatched above; if the user explicitly says "continue work X" but no state exists, ask for `docsDir` and re-run Resume Dispatch.

No state writes in Phase T (state is created in Phase 0).

---

## Phase 0 — Pre-flight (main, direct)

Execute these steps in order; each writes to `.jarfis-state.json` via `jarfis_cli.py state set` / `set-nested`:

1. **Locale**: read `~/.claude/.jarfis-locale` → `state.locale`. If absent, auto-detect from user input, persist to the global file, then to state (M12).
2. **Work identity**: AskUserQuestion (or derive from `$ARGUMENTS`) → `state.work = {name, input, docsDir (absolute), startedAt}`. Create `docsDir` if missing.
3. **sessionKey**: `jf-` + uuid4 first 8 chars → `state.sessionKey`.
4. **Org detect**: `python3 ~/.claude/scripts/jarfis_cli.py org detect <project_path>` → `state.org = {name, root}` or `null` (M10 — snapshot once, no re-detection later).
5. **Workspace scope**: AskUserQuestion-driven loop (add project paths). For each path run `jarfis_cli.py detect <path>` to auto-fill `framework` + `languages`. User supplies `name` + `type` (frontend | backend). Result → `state.workspace.scope[]` + `state.workspace.structure` (monorepo | multi-project).
6. **Git branch cut**: for each `scope[i]` run `git -C {path} checkout -b {branch}` then `git -C {path} rev-parse HEAD` → `scope[i].baseCommit` (B2).
7. **Domain detect**: `jarfis_cli.py domain detect` → `state.domain`. If tie, AskUserQuestion.
8. **Meetings**: `jarfis_cli.py search meetings "<query>"` (fallback `jarfis_cli.py meetings 3`). User picks 0..N; record in state/discovery as needed.
9. **Wiki loading** (only when `state.org != null`): follow the 4-step protocol in `~/.claude/commands/jarfis/prompts/wiki-loading.md` → write `{docsDir}/.wiki-cache.md`.
10. **Preflight verify**: `jarfis_cli.py preflight` — exit 0 required before Phase 1a.

---

## Phase 1a — PO Discovery Dialogue (main, direct)

Multi-round AskUserQuestion (one decision per turn, all labels in `$LOCALE`). Write each answer to state immediately; archive the full Q&A to `{docsDir}/discovery/po-qa.json`.

- `design.mode`: figma | text | null (null skips Phase 3).
- `design.figmaPages[]`: JSON array `[{title, url}]` (only when mode = figma).
- `responsive`: pc-only | pc-mobile | pc-mobile-tablet (only when any `scope[].type == "frontend"`).
- `api.mode`: design | swagger | null (only when no backend scope AND at least one frontend scope; swagger → also ask `api.swaggerUrl`).
- `devops`: boolean (DevOps agent needed).
- PO extras (multi-select): `legal-review`, `ux-direction` (affects Phase 1b outputs).

PO sub-agent spawn is deferred to v4.1 — v4.0 handles this dialogue directly from the main session (context cost is small).

---

## tmux Phase Execution (common pattern — applies to 1b, 2, 3, 4, 4.5, 5, 6)

Phase 3 is skipped when `state.design.mode == null`. Phase 2 + Phase 3 are launched in parallel as two background tmux sessions (different `sessionKey-phase{N}`). All other phases are sequential.

For each tmux phase:

0. **Phase-check prerequisites**: `python3 ~/.claude/scripts/jarfis_cli.py phase-check {state_file} {phase_id}` — exit 0 READY, exit 1 BLOCKED. On BLOCKED: report `blockers[]` to user (`$LOCALE`) and return to the prior Phase / Gate to supply the missing inputs (see system-spec §16 Phase Required Inputs Matrix). Do NOT launch tmux while phase-check fails.
1. **Compose the phase prompt**: read `~/.claude/commands/jarfis/prompts/phase{N}.md` (Phase 4.5 → `phase4-5.md`). Substitute `{N}`, `{K} = state.phases[phase_id].attempt || 1`, and — on retry — an explicit "Previous attempt did not produce: <missing[]>. You must create them." block. Append the Completion Protocol (implement-plan A.10). Save to `{docsDir}/phase{phase_id}-prompt-attempt{K}.md`. The prompt itself instructs jarfis-foreman to call `jarfis_cli.py compose --agent <name> [--scope-index i] --state <state>` inside tmux and spawn sub-agents via the Task tool (M6); the main session never calls compose.
2. **Resolve result path**: `{docsDir}/phase-results/phase{phase_id}/attempt{K}.json` (B3 — subdirectory preserves debug history per attempt).
3. **Run tmux isolated** (background bash):
   ```bash
   python3 ~/.claude/scripts/jarfis/tmux_claude.py \
     --name {sessionKey}-phase{phase_id} \
     --prompt {prompt_path} \
     --result {result_path} \
     --workspace {docsDir}
   ```
   Append `--mcp-config ~/.claude/.mcp.json` only if the M6 MCP inheritance check falls back (M1 Step 1.4 Scenario 2 outcome).
4. **Read the result file** when tmux exits. Branch on `status`:
   - `"error"`: report `reason` + `reasonDetail` verbatim (in `$LOCALE`); set `state.phases[phase_id].status = "failed"`. No retry — a Claude-level crash would reproduce the same error.
   - `"completed"`: continue to verify.
5. **Verify**: `python3 ~/.claude/scripts/jarfis_cli.py phase-verify {state_file} {phase_id}` — exit 0 PASS, exit 1 FAIL. Parse stdout JSON (`{verdict, missing, checkedAt}`).
6. **On PASS**:
   - Set `state.phases[phase_id].status = "verified"`.
   - Inspect phase-results meta (read `phase-results/phase{phase_id}/attempt{K}.json`):
     - `importance: required` missing (entries where `injected == false` AND `importance == "required"`) → **soft warning** to user (`$LOCALE`): "Phase {N} complete. Required context missing: `{path}`, ...". Do not block; continue.
     - `importance: recommended` missing → silent (debug log only).
     - Phase 4 only: reflect `meta.tddEnabled` → `state.tddEnabled`.
     - Phase 5 only: preserve `meta.review_rounds` and `meta.pathological_patterns` in state (read at Gate 3).
   - AskUserQuestion (`$LOCALE`): "Phase {N} complete (X/Y artifacts). Proceed?" — Approve / Abort.
7. **On FAIL**:
   - Display `missing[]`.
   - If `attempt < MAX_RETRIES (2)`: bump `state.phases[phase_id].attempt += 1`, set status `"retry"`, return to step 1 with missing items cited explicitly. Silent retry (show one-line note at next Phase start: "Phase {N} retry ({K}/{MAX_RETRIES})").
   - If `attempt >= MAX_RETRIES`: set status `"failed"`. AskUserQuestion (`$LOCALE`): "2 attempts failed. Missing: {missing}. Proceed how?" — Manual completion / Force next Phase / Abort workflow.

### Phase 5 specifics (review_round loop, MAX_REVIEW_ROUNDS = 3)

Phase 5 runs up to 3 internal review rounds inside jarfis-foreman (M3/M8). Each round jarfis-foreman invokes `python3 ~/.claude/scripts/jarfis_cli.py pattern-detect {docsDir}/review/review.md` (stdout JSON `{patterns[], details}`, always exit 0 — main never calls pattern-detect directly). The main session sees a single tmux invocation; the review-round + pattern-detect loop is internal to the phase5 prompt. After verify PASS:

- Read `meta.review_rounds` (int, 1..3) and `meta.pathological_patterns` (string[], values among `"stagnation" | "oscillation" | "regression"`, or `[]`).
- If non-empty patterns were detected, jarfis-foreman has already appended a warning section to `{docsDir}/review/review.md` and written a diagnosis file; main just surfaces this at Gate 3 via the conditional "Re-design Phase 2" option.

---

## Gate Handling (common — Gate 1, 2, 3)

Before presenting any Gate:

1. **Mandatory gate-check**: `python3 ~/.claude/scripts/jarfis_cli.py gate-check {state_file} {1|2|3}` — exit 0 PASS, exit 1 FAIL.
   - FAIL → display `missing[]` to user (`$LOCALE`) and return to the current Phase to produce the missing artifacts. **Do not present the Gate.**
2. **On PASS**: summarize artifacts and ask for approval via AskUserQuestion (labels in `$LOCALE`). Options:
   - **Gate 1** (after Phase 1b): summarize `discovery/{prd.md, working-backwards.md}` + `ux-direction.md` if `design.mode != null`. Options: Approve → Phase 2 (+3 parallel) / Revision → re-run Phase 1b / Abort.
   - **Gate 2** (after Phase 2 + Phase 3): summarize `planning/{architecture, tasks, test-strategy, api-spec?}.md` + `design/` if applicable. Options: Approve → Phase 4 / Revision → re-run Phase 2 or Phase 3 (ask which) / Abort.
   - **Gate 3** (after Phase 5): summarize `review/review.md` + `api-contract-check.md` (if api-spec exists) + `diagnosis-*.md` (if pattern-detect flagged any). Options: Approve → Phase 6 / Re-review → Phase 5 additional round (`state.phases.5.attempt += 1`, max 2) / **Re-design Phase 2** (conditional: only if `meta.pathological_patterns` non-empty — M3 decision) → return to Phase 2 to rewrite architecture/tasks / Abort.
3. **Update state**: `state.gates.{N} = "approved" | "rejected"`. Approved → next Phase. Rejected / Abort → terminate workflow.

---

## Error Handling (global matrix)

| Condition | Action |
|---|---|
| `phase-check` BLOCKED | Display `blockers[]`. Return to prior Phase / Gate. Do NOT launch tmux. |
| `tmux_claude.py` exit 1 (timeout / runtime error) | Report result.json `reason` + `reasonDetail` verbatim in `$LOCALE`. Set `phases.{N}.status = "failed"`. No auto-retry. |
| `gate-check` FAIL | Display `missing[]`. Return to current Phase. Do NOT present the Gate. |
| `phase-verify` FAIL + `attempt < 2` | Auto-retry silently (one-line note at next Phase start: "Phase {N} retry ({K}/{MAX_RETRIES})"). |
| `phase-verify` FAIL + `attempt >= 2` | AskUserQuestion: Manual completion / Force next Phase / Abort workflow. |
| `importance: required` missing (despite verify PASS) | Soft warning in `$LOCALE`. Continue. |
| `importance: recommended` missing | Silent (debug log only). |
| Phase 5 pattern-detect non-empty | jarfis-foreman appends warning to review.md. Main surfaces conditional "Re-design Phase 2" option at Gate 3. |

## User Confirmation (unified)

- **All** user-facing decisions use AskUserQuestion — never free-text responses. Question text and all option labels in `$LOCALE`.
- Option labels follow verb + noun pattern ("Approve and proceed", "Revise and re-run Phase 2", "Abort workflow").

## Anti-Optimization (mini)

- **Do NOT merge Phases** into one tmux session. Parallel Phase 2 + Phase 3 is allowed only as two distinct sessions with different `sessionKey-phase{N}` names.
- **Do NOT skip Steps** except per explicit Skip Rules (`design.mode == null` skips Phase 3; no backend scope and `api.mode == null` skips api-spec).
- **Do NOT bypass `gate-check`** — Gate presentation is forbidden while gate-check returns non-zero.
- Detailed Anti-Optimization rules for agent outputs live in `jarfis-foreman` persona + each `prompts/phase*.md`; this file only enforces orchestrator-level rules.

---

## References

- Flow chart + executor matrix: `~/Upscales/jarfis-v4-migration/system-spec.md` §9
- Required Inputs per Phase: system-spec §16
- verify.py 4 subcommands: system-spec §6
- tmux_claude.py core flow: system-spec §7
- state schema: `~/Upscales/jarfis-v4-migration/implement-plan.md` A.1
- phase-results schema: implement-plan A.3
- Completion Protocol (appended to each phase prompt): implement-plan A.10
- Agent mapping (per Phase): implement-plan A.11
- agent-composition.yaml: `~/.claude/commands/jarfis/agent-composition.yaml`
- Per-phase prompts: `~/.claude/commands/jarfis/prompts/phase{1b,2,3,4,4-5,5,6}.md` (M6)
- Personas: `~/.claude/agents/jarfis/personas/*.md`
- jarfis-foreman (tmux executor): `~/.claude/agents/jarfis/jarfis-foreman.md`
