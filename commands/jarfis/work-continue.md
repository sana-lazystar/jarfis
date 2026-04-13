# JARFIS Continue — Resume and Follow Up on a Completed Workflow

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

The user has requested the following follow-up work: $ARGUMENTS

This workflow reuses artifacts and branches from a previous workflow to efficiently perform follow-up tasks.

**Flag Options:**
- `--workflow {path}` — Specify the workflow directory directly (e.g., `{JARFIS_SOURCE}/.personal/orgs/Medistream/works/20260310-feat-payment-system`)
- `--mode fix|extend` — Explicitly specify the mode (skips auto-classification and runs the given mode directly)

---

## Step 0: Locate Previous Workflow

**0-0. Parse flags from `$ARGUMENTS`:**
- `--workflow {path}` → Store in `$WORKFLOW_PATH`, remove the flag from `$ARGUMENTS`
- `--mode fix|extend` → Store in `$FORCED_MODE`, remove the flag from `$ARGUMENTS`
- If no flags are present, each value remains empty

**0-1. Workflow Selection:**

If `$WORKFLOW_PATH` is specified:
- Check whether `.jarfis-state.json` exists at that path.
- If it exists, select that workflow (regardless of completion status — the user explicitly specified it).
- If it does not exist: print "No workflow found at the specified path: `{$WORKFLOW_PATH}`" and exit.

If `$WORKFLOW_PATH` is not provided (automatic discovery — using jarfis_cli.py state):

1. Search for completed workflows via script (automatic scan across all Org workspaces):
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py state list-workflows --completed-only
   ```
   From the `workflows` array in the JSON output, examine each workflow's `work_name`, `project_name`, `started_at`, and `docs_dir`.

2. If `count` is 0, print "No completed workflows found" and exit.

3. **1 workflow**: Auto-select
   **2+ workflows**: Select via AskUserQuestion:
   ```
   question: "Which workflow would you like to continue?"
   header: "Workflow"
   options:
     - label: "{work_name_1} ({date})"
       description: "{PRD summary or project_name}"
     - label: "{work_name_2} ({date})"
       description: "{PRD summary or project_name}"
   ```
   **0 workflows**: Print "No completed workflows found. Start a new workflow with `/jarfis:work`." and exit.

4. Restore the following from the selected workflow's state file:
   - `$DOCS_DIR` — Artifacts directory
   - `$WORK_NAME` — Work item name
   - `$BRANCH` — Git branch name
   - `required_roles` — Required roles
   - `workspace` — Project structure

5. Quickly read the previous workflow's key artifacts:
   - `$DOCS_DIR/prd.md` — PRD (planning summary)
   - `$DOCS_DIR/tasks.md` — Task breakdown (check completed items)
   - `$DOCS_DIR/architecture.md` — Architecture (first 50 lines only, for overview purposes)

6. **Pre-flight Validation** — Verify context/profile/Org existence via script:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py preflight
   ```
   From the JSON output, use `has_learnings`, `has_context`, `has_profile`, `org_root`, `has_wiki` to load each file. Same injection rules as work.md Phase 0: `$LEARNINGS`, `$PROJECT_CONTEXT`, `$BE_PROJECT_PROFILE`, `$FE_PROJECT_PROFILE` (empty string if not available)

   **0-0.5. Wiki Loading** (when Org is registered — `org_root` non-null + `has_wiki`=true):
   > See prompt: `prompts/wiki-loading.md`
   - **Fix mode** (`$FORCED_MODE`="fix" or after auto-classification): **2-Step lightweight loading** — INDEX.md + relevant _index.md only
   - **Extend mode** (`$FORCED_MODE`="extend" or after auto-classification): **4-Step full loading** — same as work.md
   - If mode is undetermined: Run wiki loading for the appropriate mode after Step 1 classification

---

## Step 1: Classify Follow-up Work

### When mode is specified via flag

If `$FORCED_MODE` is set, skip auto-classification and proceed directly with that mode.

### Auto-classification (when no flag is provided)

Analyze the user's request (`$ARGUMENTS`) and the previous workflow context to determine the mode.

| Signal | Mode |
|--------|------|
| "fix", "bug", "broken", "error", "not working", "test failing" | **Fix** |
| "add", "feature", "new", "extend", "more", "refactoring" | **Extend** |
| Cannot determine | AskUserQuestion |

### AskUserQuestion when classification is uncertain:
```
question: "What type of follow-up work is this?"
header: "Mode"
options:
  - label: "Fix — Bug fix / Correction"
    description: "Fix issues in the existing implementation. Runs Phase 4→5→6 without design changes"
  - label: "Extend — Add / Expand features"
    description: "Add new features on top of existing design. Runs lightweight Phase 1→2→4→5→6"
```

### Execution Flow Summary by Mode

```
Fix mode:
  Step 2: Prepare fix items → Step 4: Implement → Step 5: Review → Step 6: Retrospective

Extend mode:
  Step 2: Enhance PRD → Step 3: Enhance design → Step 4: Implement → Step 5: Review → Step 6: Retrospective
```

---

## Step 2: Work Preparation

### Git Branch Check

1. Verify the current branch is `$BRANCH`.
   - If not: run `git checkout $BRANCH`
   - If the branch has been deleted or does not exist: create a new branch `$WORK_NAME-follow-up` from the default branch (main/develop)

2. Check for uncommitted changes → warn the user if any exist

### State File Update

Add follow-up information to `.jarfis-state.json`:
```json
{
  "current_phase": "follow-up",
  "follow_up": {
    "mode": "fix|extend",
    "description": "$ARGUMENTS summary",
    "started_at": "ISO8601",
    "iteration": 1
  }
}
```
(`iteration` increments when continue is run repeatedly on the same workflow)

If a `follow_up` field already exists, increment `iteration` by 1.

---

## Execution Rules

### Prompt & Template Path Resolution

| Reference Pattern | Absolute Path |
|-------------------|---------------|
| `prompts/*.md` | `~/.claude/commands/jarfis/prompts/*.md` |
| `templates/*.md` | `~/.claude/commands/jarfis/templates/*.md` |

> Warning: The base path is `~/.claude/`, NOT `$JARFIS_SOURCE` (Git repo).

### Agent Model Routing

> Note: All agent models follow the work.md "Execution Rules > Agent Mapping" table (SSOT).
> Inline model hints in this file are for readability only; in case of conflict, work.md takes precedence.

---

## Step 3: Fix Mode Execution

> **Wiki Reference** (when Org is registered): 2-Step lightweight loading is complete. When making fixes, align with existing decisions in the wiki (ADRs, API contracts, etc.).

### 3-1. Organize Fix Items

Analyze the user's fix request and organize the targets:

Display the Fix mode banner: original plan, fix items, artifacts path, branch.

1. Read `$DOCS_DIR/tasks.md` to understand the existing task structure.
2. Map fix items to existing roles (BE/FE/DevOps) and create fix tasks.
3. **Append** a `## Follow-up Fix (#{iteration})` section to the existing `tasks.md`:
   ```markdown
   ## Follow-up Fix (#1)
   > Request: {fix items summary}

   ### BE Tasks
   - [ ] FIX-BE-1: {fix description}

   ### FE Tasks
   - [ ] FIX-FE-1: {fix description}
   ```

### 3-2. Implementation (Reusing Phase 4) — Fix Test Ratchet

Use work.md's Phase 4 agent prompt (`prompts/phase4.md`) with the following adjustments:

- **Task source**: Execute only the `## Follow-up Fix` section of `tasks.md`
- **Existing code reference**: Code from the previous Phase 4 already exists; make modifications based on that code
- **Commit format**: `jarfis(fix/BE-N):`, `jarfis(fix/FE-N):`

**Fix Test Ratchet** (executed directly by the orchestrator):

**3-2a. Record Baseline** (before implementation begins):
1. Detect the project test runner (refer to project-profile scripts, or the original workflow's `ratchet.phase4_tests.test_command`)
2. If a test runner exists → instruct the agent to run all tests + report `[TEST_RESULT: passed={N}, failed={N}, total={N}]`
   → Record `fix_baseline_pass_rate` = passed/total
3. If no test runner exists → disable ratchet, continue with existing flow

**3-2b. Agent Implementation Execution**:

Run agents (model: **sonnet** — implementation role):
- Execute only roles from `required_roles` that have fix tasks
- Context to pass to each agent:
  - `$DOCS_DIR/prd.md` — Original PRD
  - `$DOCS_DIR/architecture.md` — Architecture
  - `$DOCS_DIR/tasks.md` — Tasks (focus on Follow-up Fix section)
  - `$LEARNINGS` — Agent Hints for the relevant role
  - `$PROJECT_CONTEXT` — Project context
  - `$BE_PROJECT_PROFILE` / `$FE_PROJECT_PROFILE` — Project profile for the relevant role (if available)

**3-2c. Ratchet Verification** (after implementation, only when ratchet is active):
1. Instruct the agent to run all tests + report → measure `fix_current_pass_rate`
2. **Ratchet Decision**:
   - fix_current_pass_rate >= fix_baseline_pass_rate → **ACCEPT** → proceed to 3-3 review
   - fix_current_pass_rate < fix_baseline_pass_rate → **REJECT**:
     - Save changes with `git stash`
     - Re-instruct the agent: "The fix broke N existing tests: [list]. Run `git stash pop` to restore the code, then fix while preserving existing tests."
     - **Maximum 1 retry**
3. If still failing after retry → AskUserQuestion:
   ```
   question: "The fix is breaking existing tests (pass rate: {baseline}% → {current}%). How would you like to proceed?"
   header: "Fix Ratchet"
   options:
     - label: "Continue anyway"
       description: "Accept the test regression and proceed to review"
     - label: "Abort"
       description: "Cancel the fix and revert code changes"
   ```

**State Recording** (`.jarfis-state.json`):
```
jarfis_cli.py state set-nested "$DOCS_DIR/.jarfis-state.json" "follow_up.ratchet" '{
  "fix_baseline_pass_rate": <0.0-1.0>,
  "fix_current_pass_rate": <0.0-1.0>,
  "action": "accept|reject|user_override|disabled"
}'
```

### 3-3. Review (Lightweight Phase 5)

Run work.md's Phase 5 in lightweight mode:

- **Tech Lead review only** (model: **opus** — reasoning/analysis role) (QA/Security are skipped since they already passed in the original)
  - Exception: also run Security (model: **opus**) if the fix involves security-related changes
- Append review results to `$DOCS_DIR/review.md` as a `## Follow-up Review (#N)` section
- If fixes are needed → return to 3-2 for re-implementation (maximum 2 iterations)

### 3-4. Gate: User Confirmation

Display fix summary + review results → AskUserQuestion: Approve (retrospective → complete) / Request additional fixes / Finish without retrospective

### 3-5. Retrospective (Lightweight Phase 6)

Refer to `prompts/phase6.md` (tech-lead, model: **opus**), scoping the retrospective to the fix work:
- "What issues arose during this fix, and how could they have been prevented in the original workflow?"
- Append retrospective results to `$DOCS_DIR/retrospective.md` as a `## Follow-up Retrospective (#N)` section
- If there are learning items, add them to `learnings.md`

**Wiki Update** (when Org is registered): Default is "skip". Only run wiki 2-track update when the user opts in via AskUserQuestion.

**Workflow Metrics Recording** (best-effort):
Append lightweight metrics to `$JARFIS_ORG_DIR/workflow-metrics.tsv`. Follow the TSV format from `prompts/phase6.md` Step 6-2.5, with:
- `follow_up_mode` = `"fix"`
- `follow_up_iteration` = `follow_up.iteration` from `.jarfis-state.json`
- Remaining fields extracted from the original workflow state (blanks are acceptable)

---

## Step 4: Extend Mode Execution

> **Wiki Reference** (when Org is registered): 4-Step full loading is complete. Reference the wiki at the same level as work.md in each Phase.
> Phase 6 retrospective: wiki is **always updated** (2-track, same as work.md).

### 4-1. PRD Enhancement (Lightweight Phase 1)

Display the Extend mode banner: original plan, extension content, artifacts path, branch.

> See prompt: read `prompts/continue-extend.md` and pass it to the PO/Architect/TL agents.

Call PO (senior-product-owner, model: **opus**) with the PO Prompt.
If the PO has clarifying questions, relay them to the user → complete PRD enhancement after answers are received.

### 4-2. Design Enhancement (Lightweight Phase 2)

Call Architect (technical-architect, model: **opus**) with the Architect Prompt.
Call Tech Lead (tech-lead, model: **opus**) with the Tech Lead Prompt.
Call QA (senior-qa-engineer, model: **opus**) with the QA Prompt — only when test-strategy.md exists. Add Extension Test Strategy.

### 4-3. Gate: User Confirmation (Design Review)

Display a summary of extension design artifacts (prd.md Extension, architecture.md Extension, tasks.md Extension Tasks) → AskUserQuestion: Approve / Request changes / Abort

### 4-4. Implementation (Reusing Phase 4)

Same as Fix mode's 3-2, with the following differences:
- **Task source**: `## Extension Tasks` section of `tasks.md`
- **Commit format**: `jarfis(ext/BE-N):`, `jarfis(ext/FE-N):`

### 4-5. Review (Phase 5 Execution)

Run work.md's Phase 5 with the following adjustments:
- Scope the review to Extension tasks
- Run Tech Lead (model: **opus**) + QA (model: **opus**) review (QA is needed since this involves new features)
- Run Security (model: **opus**) only when there are security-related changes
- Append review results to `$DOCS_DIR/review.md` as an `## Extension Review (#N)` section

### 4-6. Gate: Final Confirmation

Same format as Fix mode's 3-4.

### 4-7. Retrospective (Lightweight Phase 6)

Same as Fix mode's 3-5, with the retrospective perspective tailored to extension work:
- "Did the extension integrate well with the existing architecture?"
- "Were any improvement opportunities discovered in the existing design during extension?"

**Workflow Metrics Recording** (best-effort):
Append lightweight metrics to `$JARFIS_ORG_DIR/workflow-metrics.tsv`. Follow the TSV format from `prompts/phase6.md` Step 6-2.5, with:
- `follow_up_mode` = `"extend"`
- `follow_up_iteration` = `follow_up.iteration` from `.jarfis-state.json`
- Remaining fields extracted from the original workflow state (blanks are acceptable)

---

## Step 5: Completion

Display the completion banner: original work item name, mode (Fix/Extend), iteration, change summary, artifacts path, branch.

Update `follow_up.status` in the state file to `"completed"`.
