# Phase 4: Implementation (parallel BE/FE/DevOps + security pre-review)

> Executed by **jarfis-foreman** inside tmux. jarfis-foreman is the **orchestrator**: runs compose, spawns sub-agents via Task, monitors TDD Ratchet, records meta. It does NOT read source artifacts itself.
> All sub-agent artifacts and code comments in English. User-facing messages in $LOCALE.

**Execution context**:
- `$DOCS_DIR` = tmux workspace
- `$STATE_FILE` = `$DOCS_DIR/.jarfis-state.json`

### jarfis-foreman precompute (from $STATE_FILE)

- `$SCOPE` = `state.workspace.scope[]` (array; each has `{name, type, path, framework, baseCommit, branch}`)
- `$DEVOPS` = `state.devops` (boolean)
- `$HAS_API_SPEC` = "true" if `$DOCS_DIR/planning/api-spec.md` exists, else "false" (`test -f`)
- `$DESIGN_MODE` = `state.design.mode`
- `$RESPONSIVE` = `state.responsive`
- `$TDD_ENABLED` = `state.tddEnabled` (top-level; v4.0.2 OBS-4 canonicalized — **never read from `state.phases.4.tdd_enabled`, that nested path is deprecated**)

### TDD decision precondition (upstream of this prompt)

`state.tddEnabled` is resolved by the **main session** before it launches this tmux phase. The main session evaluates (via its own shell / a helper CLI) whether test-strategy.md has ≥ 3 P0 scenarios AND each scope has a unit-test framework, and writes the result to `state.tddEnabled` (top-level). jarfis-foreman only reads that flag — it does NOT re-evaluate and does NOT fall back to the deprecated nested `phases.4.tdd_enabled` location.

If `state.tddEnabled` is missing (e.g., the upstream decision step was skipped), treat `$TDD_ENABLED` as `false` and record `meta.tddEnabledFallback: "state_missing"` in phase-results so the main session can surface a warning.

## Required Inputs (consumed by sub-agents)

- `$DOCS_DIR/planning/architecture.md` — consumed by security, QA, FE, BE, DevOps
- `$DOCS_DIR/planning/tasks.md` — consumed by security, QA, FE, BE, DevOps (PRIMARY for implementers)
- `$DOCS_DIR/planning/test-strategy.md` — consumed by QA

## Conditional Inputs (consumed by sub-agents)

- `$DOCS_DIR/planning/api-spec.md` — consumed by BE + by FE (type hints); exists if any `scope[].type == "backend"` OR `state.api.mode == "swagger"`
- `$DOCS_DIR/design/{id}/index.html` + `reference.png` + `token-map.json` (+ `reference-mobile.png` / `reference-tablet.png` per responsive) — consumed by FE when `state.design.mode != null`

---

## Step 1 — Security pre-review (security-engineer, work-wide, 1 spawn)

### Compose invocation (jarfis-foreman executes)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent security-engineer --state $STATE_FILE)
# Task spawn with the prompt below.
```

### Sub-agent task prompt (jarfis-foreman injects verbatim)

```
You are the security engineer doing a pre-implementation review.

Inputs to read:
- $DOCS_DIR/planning/architecture.md
- $DOCS_DIR/planning/tasks.md

Produce $DOCS_DIR/planning/security-guidelines.md with:
- Authentication / authorization implementation guide
- Input validation rules
- Sensitive data handling policy
- API security checklist
- OWASP Top 10 watch-list

BE / FE / DevOps agents will reference this file during implementation, so make it
concrete enough to act on (per feature area, not generic prose).
```

---

## Step 2 — Test-first writing (qa-engineer, per-project) — CONDITIONAL on `$TDD_ENABLED`

Skip this Step entirely when `$TDD_ENABLED == false`.

For each `scope[i]` that has tasks:

### Compose invocation (jarfis-foreman executes, per scope)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent qa-engineer --scope-index $i --state $STATE_FILE)
# Task spawn with the prompt below.
```

### Sub-agent task prompt (jarfis-foreman injects verbatim, per scope)

```
You are the QA engineer writing tests FIRST (TDD red phase) for project scope[$i].

Inputs to read:
- $DOCS_DIR/planning/test-strategy.md       (scenarios to convert)
- $DOCS_DIR/planning/api-spec.md            (only if present — request/response contracts)
- $DOCS_DIR/planning/architecture.md        (data models, business rules — basis for edge cases)
- $DOCS_DIR/planning/tasks.md               (Target Files per task — basis for import paths)
- scope[$i].path/.jarfis-project/project-profile.md
                                             (test framework, directory structure, conventions)

Project directory: scope[$i].path

Procedure:
- Convert every P0 and P1 scenario from test-strategy.md into executable tests
  inside scope[$i].path following project conventions.
- Tests MUST fail (RED) since implementation does not exist, but files MUST be
  syntactically valid — no syntax errors.
- Import paths based on tasks.md Target Files.
  Example: tasks.md Target File "src/services/payment.ts" → import { PaymentService } from '...'
- Actively include edge cases: empty/null/undefined, boundary values, unauthorized access,
  concurrency, timeouts — especially cases inferable from architecture.md business rules
  even when not explicit in test-strategy.md.
- Test behavior via public interfaces, NOT private/internal state.
- Follow existing test patterns in the project (fixtures, naming, etc.).
- Do NOT write tests for parts marked N/A in tasks.md.

Header comment at the top of EVERY test file you create:
  // [JARFIS TDD] Auto-generated in Phase 4 Step 3 — implementation agents must not modify

Commit when complete:
  jarfis(QA-test-{project-name}): pre-write tests based on test-strategy.md
(project-name = scope[$i].name)
```

---

## Step 3 — Implementation (parallel per-scope + optional DevOps)

### Scope loop (jarfis-foreman executes)

For each `scope[i]`, spawn the role matching `scope[i].type` in parallel:

```bash
for i in $(seq 0 $((${#SCOPE[@]}-1))); do
  TYPE=${SCOPE[$i].type}
  case $TYPE in
    frontend)
      COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
        --agent frontend-developer --scope-index $i --state $STATE_FILE)
      # Task(subagent_type=$SUBAGENT, ..., prompt=$PROMPT + common rules + FE injection)
      ;;
    backend)
      COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
        --agent backend-developer --scope-index $i --state $STATE_FILE)
      # Task(subagent_type=$SUBAGENT, ..., prompt=$PROMPT + common rules + BE injection)
      ;;
  esac
done

# DevOps (work-wide, 1 spawn) — only when $DEVOPS == true
if [ "$DEVOPS" = "true" ]; then
  COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
    --agent devops-engineer --state $STATE_FILE)
  # devops-engineer model is opus (from composition.yaml)
  # Task(subagent_type=$SUBAGENT, ..., prompt=$PROMPT + common rules + DevOps injection)
fi
```

### Sub-agent task prompt — Common rules (jarfis-foreman injects into EVERY BE/FE/DevOps spawn)

```
You are an implementation agent for project scope[$i] (name={scope[$i].name}, type={scope[$i].type}).
Your role is {frontend-developer | backend-developer | devops-engineer}.

Project directory: scope[$i].path (this is your working directory)

Inputs to read (in order of authority):
- scope[$i].path/CLAUDE.md                    (HIGHEST AUTHORITY — project-level rules; MUST Read first if present. Claude Code's auto-load runs against your spawn working_dir which is docsDir, not scope[$i].path, so you MUST invoke the Read tool explicitly on scope[$i].path/CLAUDE.md at task start.)
- scope[$i].path/.jarfis-project/project-profile.md  (project conventions — Read if present)
- $DOCS_DIR/planning/tasks.md                 (PRIMARY — your assigned tasks)
- $DOCS_DIR/planning/architecture.md          (data models, API patterns, ADRs)
- $DOCS_DIR/planning/api-spec.md              (if present — API contract)
- $DOCS_DIR/planning/security-guidelines.md   (Phase 4 Step 2 output)
- $DOCS_DIR/discovery/prd.md                  (REFERENCE ONLY — do NOT plan from here)

If scope[$i].path/CLAUDE.md contains a verification marker string (e.g. "M11-..."), echo that marker verbatim in your final report so the orchestrator can confirm you loaded the file.

Work rules:
- Work ONLY on tasks in tasks.md whose role prefix matches your role (FE/BE/DevOps)
  AND whose project-name suffix matches scope[$i].name.
- Follow the 'Target Files' of each task — no unnecessary codebase exploration.
- If project-profile.md exists in scope[$i].path/.jarfis-project/, follow its conventions.
- Satisfy every task's Completion Criteria, Tests, and Security.
- prd.md is REFERENCE ONLY — follow tasks.md as the primary guide.

Scope Guard (BE / FE / DevOps):
- Implement only the scope specified in your tasks.
- No out-of-scope abstraction, generalization, or pre-emptive refactoring.
- Do NOT add error handling / validation for impossible scenarios — trust internal guarantees.
- Only validate at system boundaries (user input, external APIs).

Git auto-commit (per task):
- On task completion: git add <changed files> + commit.
- Commit format: jarfis({TASK_ID}): <one-line summary of completion criteria>
  where {TASK_ID} is from tasks.md (e.g., FE-web-1, BE-api-3, DevOps-api-2).
- On .git/index.lock error: wait 3 s and retry (max 3 attempts).
- Report completion per task: [TASK_DONE: {TASK_ID}]
```

### Sub-agent task prompt — FE injection (jarfis-foreman appends ONLY when `state.design.mode != null` AND role=frontend-developer)

```
Design Contract (Visual Contract):
- $DOCS_DIR/design/{path}/reference.png is the FINAL visual authority.
- token-map.json variables take precedence over raw hex.
- Copy image assets from $DOCS_DIR/design/assets/ into the project
  (public/, assets/, etc.) — follow project conventions.
- Do NOT copy-paste HTML/CSS from the mockup. Reimplement using the project's tech stack
  (Vue, React, SCSS, etc.).
- Responsive: apply breakpoints matching state.responsive:
    pc-only           → desktop only
    pc-mobile         → desktop + mobile (390×844)
    pc-mobile-tablet  → desktop + mobile + tablet (768×1024)

Design Application Checklist (MANDATORY before committing any FE task):
□ Every component has a <style> block (scoped or module)
□ Layout matches the mockup: flex direction, gap, padding, margins
□ Typography matches: font-family, font-size, font-weight, line-height
□ Status badges / pills have correct background + text colors
□ Filter buttons show active / inactive states with correct styling
□ Empty, loading, and error states all have appropriate styling
□ Colors use token-map.json variables where mapped, raw hex for unmapped
If ANY checkbox fails → fix before committing.
Do NOT commit code that works functionally but lacks styling.
```

### Sub-agent task prompt — BE injection (jarfis-foreman appends ONLY when `$HAS_API_SPEC == "true"` AND role=backend-developer)

```
API Contract Compliance:
- Endpoint paths, HTTP methods, and parameters MUST match $DOCS_DIR/planning/api-spec.md exactly.
- Return error-response shapes as defined in api-spec.md (code, errorKey, message).
- Deviations → record rationale in the commit message body.
```

### Sub-agent task prompt — DevOps injection (jarfis-foreman appends when role=devops-engineer)

```
Category handling (from tasks.md):
- Category A (local creation):
    Dockerfile, CI/CD configs, IaC — create directly under the appropriate
    scope[i].path OR $DOCS_DIR if work-wide.
- Category B (cloud operations):
    Do NOT execute cloud changes directly.
    Instead, write a step-by-step runbook to $DOCS_DIR/ops/infra-runbook.md:
    prerequisites, commands with exact arguments, verification, rollback.
```

### Sub-agent task prompt — TDD injection (jarfis-foreman appends to BE/FE spawns ONLY when `$TDD_ENABLED == "true"`)

```
TDD Green Phase + Ratchet:
Test code already exists (written by QA in Step 3) and is in a failing (RED) state.

Per task:
1. Run the relevant tests first and confirm RED (failing) state.
2. Implement the task.
3. Run the full test suite and report in the format:
   [TEST_RESULT: passed={N}, failed={N}, total={N}]
4. If tests do not pass, fix the implementation.

Ratchet rule (orchestrator-enforced):
- The orchestrator tracks the test pass rate (passed/total).
- If the pass rate drops below the previous task's end rate → reimplementation will be ordered.

Test modification policy:
- Do NOT modify [JARFIS TDD] test files except with a justified reason.
- If you believe a test is incorrect: report [TEST_ISSUE: {test_name} — {reason}]
  (do NOT modify). The orchestrator may re-request QA review.
- If you must modify a test file, include in the commit message:
  [TEST_MODIFIED: {filename} — {reason}]
  Phase 5 QA will verify the modification.
```

---

## Step 4 — TDD Ratchet (orchestrator step — jarfis-foreman executes directly, CONDITIONAL on `$TDD_ENABLED == "true"`)

After each BE/FE task reports `[TASK_DONE: {TASK_ID}]`:

1. Run the full test suite in `scope[i].path` (project-defined command: `npm test` / `pytest` / etc.).
2. Parse the result: `passed`, `failed`, `total`.
3. Compare pass rate vs baseline (previous task's end rate).
4. If the pass rate dropped → re-spawn the same agent with a fix directive before proceeding to the next task.
5. Record `[TEST_RESULT: passed={N}, failed={N}, total={N}]` per task in the session log.

---

## Step 5 — Final sanity (orchestrator step — jarfis-foreman executes directly)

- Every task in tasks.md has `[TASK_DONE: {TASK_ID}]` (or is marked N/A upstream).
- If `$TDD_ENABLED == "true"`: final full test-suite pass-rate recorded for phase-results meta.
- No unresolved `[TEST_ISSUE]` without a follow-up re-QA or justified waiver.
- Collect `[TEST_MODIFIED]` entries from commit messages (`git log --grep='\[TEST_MODIFIED:' -E --oneline`; output is short) → populate `meta.testModifications[]`.

---

## Completion Protocol

At phase completion, perform the following in order:

1. **Produce spec artifacts**: code (git commits under each `scope[i].path`) + `$DOCS_DIR/planning/security-guidelines.md` + `$DOCS_DIR/ops/infra-runbook.md` (when devops + Category B tasks exist)
2. **(Optional) Handoff document**
3. **Write phase-results/phase4/attempt{K}.json** (last step — atomic + sentinel, tmux-claude-completion-signal-v1):
   ```bash
   mkdir -p $DOCS_DIR/phase-results/phase4
   RESULT=$DOCS_DIR/phase-results/phase4/attempt{K}.json
   cat > $RESULT.tmp <<EOF
   {
     "status": "completed",
     "reason": "",
     "reasonDetail": "",
     "meta": {
       "tddEnabled": true,
       "testPassRate": {"passed": 42, "failed": 0, "total": 42},
       "testModifications": []
     }
   }
   EOF
   mv $RESULT.tmp $RESULT          # atomic publish
   touch $RESULT.done              # sentinel — wakes parent poll()
   # Error: status=error with reason/reasonDetail (same emit pattern)
   ```

**Strict order**: artifacts → (handoff) → phase-results JSON.
Do NOT write to `.jarfis-state.json` (the main Claude owns it). Propagating `state.tddEnabled` is the main session's responsibility.
`{K}` is substituted with the actual attempt number by the main session when generating the prompt file.
