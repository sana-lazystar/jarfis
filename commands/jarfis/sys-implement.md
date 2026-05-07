# JARFIS Implement — Self-Modification of JARFIS System

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

A dedicated command for modifying or adding commands, structures, and features of the JARFIS system.

User request: $ARGUMENTS

---

> **🔒 Mandatory Step Execution Rule**
>
> **All Steps in this workflow must be executed in order.** No Step may be skipped or bypassed.
> After completing coding (Step 2), you must execute Step 3 → 3.5 → 4 → 5.
> Explicitly proceed to the next Step upon completing each one.

---

## Execution Flow

### Step 0: Assess System State + Workspace Init (ADR-0003)

> **v4.2+ (ADR-0003)**: every sys-implement run produces a workspace at
> `{JARFIS_SOURCE}/.personal/sys-implements/{plan-name}/`. Step 0 creates it.

#### Step 0.1 — Decide plan-name

Derive a kebab-case slug from `$ARGUMENTS` keywords (e.g.
"add cloudflare skill" → `cloudflare-skill-v1`). Then AskUserQuestion:

```
question: "Plan name for this work? (proposed: {slug})"
header: "Plan name"
options:
  - label: "{slug} (Recommended)"
    description: "Use the auto-derived name"
  - label: "Other"
    description: "Type a custom kebab-case name (e.g. rag-integration-v1)"
```

If the user picks "Other", validate the input matches `^[a-z][a-z0-9-]*$`
and length ≤ 40. On collision (workspace already exists):

```
question: "Workspace `{plan-name}` already exists. How to proceed?"
options:
  - label: "Resume from current state"  → `jarfis_cli.py implement resume {plan-name}` and continue from `currentState`.
  - label: "New plan with -v2 suffix"   → re-run §0.1 with `{plan-name}-v2`.
  - label: "Abort"                       → exit immediately.
```

#### Step 0.2 — Initialize workspace

```bash
python3 ~/.claude/scripts/jarfis_cli.py implement init {plan-name} "{request}"
```

This creates `manifest.json`, `state.json`, `RESUME.md`, `README.md`,
`log/0000-init.json`, and the `artifacts/`, `log/`, `compensation/` trees.
The `currentState` starts at `step0` (in_progress).

After init succeeds, capture the returned `planDir` for use by subsequent
steps. All later step outputs go under `{planDir}/artifacts/step{N}/`.

#### Step 0.3 — Read system structure

1. Read `~/.claude/commands/jarfis/jarfis-index.md` to understand the current JARFIS system structure.
2. Based on what you read, determine which files are affected by the user's request.
3. **Minimize exploration**: If the index already provides sufficient information, do not explore further.
4. **Check Git repo**: Read `~/.claude/.jarfis-source` to find the JARFIS Git repo path. If absent, default to `~/repos/jarfis`.

> ⚠️ **Sync direction**: JARFIS active files live in `~/.claude/`.
> Always make modifications in `~/.claude/`, then sync to the repo via `jarfis_cli.py sync` in Step 4.
> Directly modifying the repo will not be reflected in the active system.

#### Step 0.4 — Persist Step 0 artifact

Write a brief summary of the affected JARFIS surface to
`{planDir}/artifacts/step0/jarfis-state-snapshot.md` — this is the
input for Step 1's Impact Scope Analysis.

Then mark Step 0 complete:

```bash
python3 ~/.claude/scripts/jarfis_cli.py implement state {plan-name} --set-nested steps.step0.status completed
python3 ~/.claude/scripts/jarfis_cli.py implement log {plan-name} append '{"event":"step.completed","step":"step0","details":{"artifact":"artifacts/step0/jarfis-state-snapshot.md"}}'
python3 ~/.claude/scripts/jarfis_cli.py implement state {plan-name} --set-nested currentState step1
```

→ Proceed to Step 1

### 📋 Workspace Update Snippet (apply at the end of every Step from Step 1 onward — ADR-0003)

After completing a step's substantive work, you must:

1. **Write the step artifact** to `{planDir}/artifacts/step{N}/...` (each Step below specifies the exact filenames).
2. **Mark the step completed**:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py implement state {plan-name} --set-nested steps.step{N}.status completed
   python3 ~/.claude/scripts/jarfis_cli.py implement log {plan-name} append '{"event":"step.completed","step":"step{N}","details":{"artifact":"artifacts/step{N}/"}}'
   ```
3. **Advance currentState** to the next step:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py implement state {plan-name} --set-nested currentState step{M}
   ```

If the step is **skipped** (e.g. Step 1.5 patch-mode skip, or Step 2~5 when user picks "Skip Step 2" at Step 1.7), use `--set-nested steps.step{N}.status skipped` instead. If it **failed**, use `failed` and add `failure_reason` field via `--set-nested steps.step{N}.failure_reason "<msg>"`.

### Step 1: Impact Scope Analysis

Analyze the user's request and determine the following:

| Task Type | Affected Targets |
|-----------|-----------------|
| Command rename | Rename the file + all referencing files + `jarfis.md` |
| New command | Create new md file + add to `jarfis.md` listing |
| Modify existing command | The relevant md file |
| Delete command | Delete file + remove references + remove from `jarfis.md` listing |
| Structural change | Identify affected files using "Internal Reference Map" in the index |
| Agent prompt modification | `prompts/*.md` (Phase-specific prompts externalized from work.md) |
| Agent role modification | `~/.claude/agents/jarfis/*.md` (Role prompts for Agent tool) |

**🔒 Required**: You must display the banner below before proceeding to the next Step. Do not move to Step 2 without the banner.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Implement — Impact Scope
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Request: [summary]
📂 Files to modify: [file list]
🔗 References to update: [affected file list]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Step 1 artifact**: write the banner content + `files_affected[]` + `references_to_update[]` to `{planDir}/artifacts/step1/impact-scope.md`.

→ Apply Workspace Update Snippet (step=1, next=step1.5)
→ Proceed to Step 1.5

### Step 1.5: Dialectic Review (Force-Acknowledge — ADR-0005)

A **single-round** dialectic that converges only when one side concedes via stronger
file:line evidence. Otherwise → **UNRESOLVED** → user Confirm. The orchestrator
runs `validate_citations()` (decided by form, not by content).

**Gate entry condition** (unchanged from prior pattern):
1. If `$ARGUMENTS` contains a review flag, follow it:
   - `--review=major` → run dialectic (mandatory)
   - `--review=minor` → run dialectic
   - `--review=patch` → skip → move to Step 1.7
2. If no flag is present:
   - 1 or fewer files to modify & content-only change → AskUserQuestion:
     ```
     question: "This looks like a lightweight update. Run Dialectic Review?"
     header: "Review"
     options:
       - label: "Skip (Recommended)"
         description: "Proceed directly without the dialectic"
       - label: "Run dialectic"
         description: "Force-acknowledge gate (ADR-0005)"
     ```
   - 2 or more files to modify, or structural change → run dialectic

**External ratchet protection** (unchanged): if `$ARGUMENTS` references plan.md /
brainstorm.md items already marked ACCEPT / REJECT / DEFER, compile them into
`$PRIOR_RATCHET`. Both advocate and critic must NOT re-litigate those items —
re-raising = formal violation, ignored by the orchestrator.

#### Single-round flow

**1a. Advocate spawn** (Agent tool, `subagent_type: jarfis-advocate`):
- Prompt:
  ```
  Defend the following JARFIS change proposal: $CHANGE_PROPOSAL
  Current system state (RAG): [top-5 chunks from `jarfis_cli.py search jarfis "<keywords>"`]

  [If $PRIOR_RATCHET exists:]
  ## External Ratchet History (re-litigation prohibited)
  $PRIOR_RATCHET

  Output per `~/.claude/agents/jarfis/jarfis-advocate.md` Output Format.
  Every claim must include a `path:LNN` citation. No citation = no claim.
  ```

**1b. Critic spawn** (Agent tool, `subagent_type: jarfis-critic`):
- Prompt: same as 1a, but the critic reads the advocate's output FIRST.
- Critic must cite `path:LNN` for every "Blocked" failure scenario.

**1c. (optional) Advocate rebuttal** — at most 1 turn. Spawn the advocate again
only when the critic's challenge contains a citation that you (orchestrator) cannot
immediately verify as obviously refuted by the advocate's first turn. Otherwise,
skip the rebuttal — the orchestrator's verdict is final after 1b.

**1d. Orchestrator verdict** (performed directly via `implement.py`):

```python
from jarfis.implement import classify_verdict
verdict = classify_verdict(advocate_output, critic_output, advocate_rebuttal_or_empty)
# verdict.status ∈ {"ACKNOWLEDGED-advocate-wins", "ACKNOWLEDGED-critic-wins", "UNRESOLVED"}
# verdict.advocate_citations / .critic_citations contain Citation objects with status="valid"|"invalid_path"|"invalid_line"
```

The orchestrator does **not** judge content. The verdict is decided by citation form alone:

- **No valid citation from critic** → `ACKNOWLEDGED-advocate-wins` (formal violation by critic).
- **Valid critic, no valid advocate** → `ACKNOWLEDGED-critic-wins` (advocate concedes by absence).
- **Both valid** → `UNRESOLVED` → present Pros/Cons banner + AskUserQuestion.

#### UNRESOLVED handling (user Confirm)

Display the banner and ask the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dialectic UNRESOLVED — User Confirm
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Issue: [orchestrator's 1-line summary]

✅ Pros (Advocate):
  - [verdict text]
  - 증거: `path:LNN` — "[exact line content]"

❌ Cons (Critic):
  - [verdict text]
  - 증거: `path:LNN` — "[exact line content]"

⚖️ 형식 검사만 통과. 내용 판단은 사용자 책임 (LLM 자동 판단 X).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
question: "Resolve this UNRESOLVED issue?"
options:
  - "Confirm Advocate" — proceed with the proposal as-is
  - "Confirm Critic"   — apply Critic's required fix or abort
  - "Pivot"             — type a new alternative (free text)
  - "Abort"             — terminate this sys-implement run
```

Persist the user's choice to `{planDir}/artifacts/step1.5/unresolved.md`.

#### Convergence display (ACKNOWLEDGED)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Dialectic — {ACKNOWLEDGED-advocate-wins | ACKNOWLEDGED-critic-wins}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Proposal: [summary]
✅ Outcome: {advocate / critic} carried by formal evidence.
   - {winning side}: {valid citation count} citations
   - {losing side}: {none | invalid count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Step 1.5 artifacts**: write `{planDir}/artifacts/step1.5/{advocate.md, critic.md, verdict.json}`. If UNRESOLVED, also write `unresolved.md` with the user's chosen option. If the gate is skipped (patch mode), record only `verdict.json = {"status": "skipped"}`.

→ Apply Workspace Update Snippet (step=1.5, next=step1.7; status=`skipped` if patch mode skipped the dialectic)
→ Proceed to Step 1.7

### Step 1.7: Execution Mode Dispatch (ADR-0004)

Decide whether Step 2 / Step 3 run **single** (main Claude direct) or **tmux**
(jarfis-engineer Mode B in a dedicated tmux session). Auto-recommend based on
impact_scope, then defer to the user via AskUserQuestion.

#### 1.7.1 — Auto-recommend

```python
from jarfis.implement import recommend_execution_mode
mode, reason = recommend_execution_mode({
    "files_affected": [...from Step 1...],
    "change_type": "<content|structural|new-command|agent-prompt|agent-role>",
})
# mode ∈ {"single", "tmux"}; reason is a $LOCALE-friendly short string
```

#### 1.7.2 — Argument override

If `$ARGUMENTS` contains `--mode=single` or `--mode=tmux`, honor it directly and
SKIP the AskUserQuestion below. If a force-tmux condition is active
(file_count ≥ 6 OR change_type=structural) AND the user passed `--mode=single`,
ask once more for explicit confirmation:

```
question: "강제 tmux 조건인데 --mode=single 을 시도했습니다. 정말 단일 모드로 진행할까요? (메인 컨텍스트 폭발 위험)"
options:
  - "Yes, force single"  → execution_mode = "single" with `forced=true`
  - "No, switch to tmux" → execution_mode = "tmux"
```

#### 1.7.3 — AskUserQuestion (default path)

```
question: "이번 변경의 실행 모드는? (자동 추천: {mode} — {reason})"
header: "Execution mode"
options:
  - label: "{mode} (Recommended)"
    description: "{reason}"
  - label: "{the other mode}"
    description: "{비교 짧게 — single = 메인 직접 / tmux = jarfis-engineer Mode B 격리}"
  - label: "Skip Step 2 (분석만)"
    description: "Step 2 이후 모두 skip. 본 plan 은 reference 용으로만 보존."
```

If the user picks "Skip Step 2", set `executionMode = "skip"` and mark Step 2 ~ Step 5 as `skipped`. Step 4.5 still runs (RAG would otherwise stale-warn).

#### 1.7.4 — Persist + state

Write the decision to `{planDir}/artifacts/step1.7/mode-decision.json`:
```json
{
  "mode": "single" | "tmux" | "skip",
  "reason": "<recommend_execution_mode reason or user override>",
  "auto_recommendation": {"mode": "...", "reason": "..."},
  "user_choice": "<one of the AskUserQuestion options>",
  "argument_override": null | "--mode=single" | "--mode=tmux",
  "decided_at": "<ISO8601>"
}
```

Update state:
```bash
python3 ~/.claude/scripts/jarfis_cli.py implement state {plan-name} --set executionMode=<single|tmux|skip>
```

→ Apply Workspace Update Snippet (step=1.7, next=step2)
→ Proceed to Step 2 (executionMode-aware)

### Step 2: Execute Modifications

> ⚠️ **Modification location**: Always modify files at the `~/.claude/` path.
> Do not directly modify `~/repos/jarfis/` (Git repo). The repo is auto-synced in Step 4.

> 🧪 **Python TDD Rule**: When modifying `~/.claude/scripts/jarfis/*.py` or `jarfis_cli.py`, you must follow **Test-Driven Development**:
> 1. **Tests first**: Write failing tests in `tests/test_*.py` first, or modify existing tests
> 2. **Code change**: Modify production code until tests pass
> 3. **Full run**: Verify all tests pass with `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`
> 4. When adding new functions/subcommands → corresponding tests are mandatory
> 5. This rule does not apply to non-Python modifications (prompts, templates, etc.)

#### Branch on `executionMode` (set in Step 1.7 — ADR-0004)

##### single mode — main Claude executes directly

1. Read and modify only the necessary files.
2. Follow the "Modification Checklist" in the index.
3. When adding/deleting/renaming commands, you must also update `jarfis.md` (main helper).
4. **Note the externalized prompt structure**: Agent prompts in work.md are externalized to `prompts/*.md`.
   - To modify Phase-specific workflow **flow/rules** in work.md → edit work.md directly
   - To modify **task prompt content** sent to Phase-specific agents → edit `prompts/phase{N}.md`
   - Verify that `> 📄 Prompt:` references in work.md match the actual content in prompts/ files

##### tmux mode — jarfis-engineer Mode B in dedicated tmux session

1. Compose the step prompt: write `{planDir}/step2-prompt.md` with the full instruction set (subset of this Step 2 body, customized to the impact_scope) plus a Completion Protocol footer (per ADR-0001 §Mode B).
2. Launch tmux:
   ```bash
   python3 ~/.claude/scripts/jarfis/tmux_claude.py \
     --name {plan-name}-step2 \
     --prompt {planDir}/step2-prompt.md \
     --result {planDir}/phase-results/step2/attempt{K}.json \
     --workspace $(cat ~/.claude/.jarfis-source) \
     --save-pane {planDir}/phase-results/step2/attempt{K}.pane.log
   ```
   Inside tmux, jarfis-engineer (Mode B) spawns and:
   - RAG-searches the affected files
   - Applies edits to `~/.claude/`
   - Runs Python TDD if scripts/ touched
   - Writes `attempt{K}.json` with `{status, artifacts[], files_modified[], tdd_results, missing[], notes}`
3. Read the `attempt{K}.json` from main and branch on `status`:
   - `completed` → proceed
   - `needs_retry` → AskUserQuestion (retry / debug / abort) → `K += 1`, max 3 retries
   - `blocked` → surface `notes` to user + AskUserQuestion (continue with manual fix / abort)
4. On 3 retries failing → `state.json.steps.step2.status = "failed"` + `failure_reason` from `notes`. Stop and report.

##### skip mode — set in Step 1.7 (analysis-only plan)

Mark Step 2 status `skipped`. Skip Step 3 / 3.5 / 4 / 4.5 / 5 (all `skipped`). Plan ends as reference-only artifacts.

#### Step 2 artifacts (both modes)

For each modified file, snapshot the pre-edit content into `{planDir}/artifacts/step2/before/<relative-path>` and the post-edit content into `{planDir}/artifacts/step2/after/<relative-path>`. Write a unified diff to `{planDir}/artifacts/step2/diff.patch`. If Python TDD ran, also write `{planDir}/artifacts/step2/tdd-results.json` with `{passed, failed, skipped, duration_ms}`. In tmux mode, the engineer Mode B writes these directly; main reads `attempt{K}.json` to verify presence.

→ Apply Workspace Update Snippet (step=2, next=step3; or `skipped` for skip mode)
→ After completing modifications, you must proceed to Step 3 (do not stop here)

### Step 3: Update Index

You **must** update `~/.claude/commands/jarfis/jarfis-index.md` to reflect the modifications.

**Branch on `executionMode`** (same as Step 2):
- **single** → main Claude updates the index directly (substeps below).
- **tmux** → main Claude composes `{planDir}/step3-prompt.md` and re-spawns `jarfis-engineer` via tmux, identical pattern to Step 2 (`{plan-name}-step3` session, `attempt{K}.json` result, retry up to 3).
- **skip** → mark Step 3 status `skipped` and proceed (Step 3.5 also skipped).

Substeps (always — single mode does these directly; tmux mode delegates):
- Update the file structure tree (include line counts for added/deleted/renamed files)
- Update the command mapping table
- Update artifacts/data files (if new data files were created)
- Update internal reference relationships
- Change the `Last updated` date to today

**Step 3 artifact**: write the `jarfis-index.md` before/after diff to `{planDir}/artifacts/step3/index-update-diff.patch`.

→ Apply Workspace Update Snippet (step=3, next=step3.5)
→ Proceed to Step 3.5

### Step 3.5: Version Bump

After modifications are complete, bump the version. Use AskUserQuestion to let the user choose the bump type:

```
question: "How should the version be bumped? (Current: v{current_version})"
header: "Version"
options:
  - label: "PATCH (Recommended)"
    description: "Prompt/template content change (X.Y.Z+1)"
  - label: "MINOR"
    description: "New command/agent added (X.Y+1.0)"
  - label: "MAJOR"
    description: "Phase structure change/breaking (X+1.0.0)"
  - label: "Skip"
    description: "Skip the version bump"
```

If not "Skip", use `jarfis_cli.py version`:
```bash
python3 ~/.claude/scripts/jarfis_cli.py version <patch|minor|major> "implement: change summary"
```
- The script auto-updates VERSION, .jarfis-version, jarfis-index.md Version, and CHANGELOG.md.
- Include the `previous`/`new` version from the output JSON in the results report.

**Step 3.5 artifact**: write `{planDir}/artifacts/step3.5/version-bump.json` with `{previous, new, type, message}`. If skipped, write `{"status":"skipped"}`.

→ Apply Workspace Update Snippet (step=3.5, next=step4; status=`skipped` if version bump skipped)
→ Proceed to Step 4

### Step 4: Repo Sync (Automatic)

You **must** run the following script to sync `~/.claude/` → `{repo_path}/`:

```bash
python3 ~/.claude/scripts/jarfis_cli.py sync
```

This script:
- Auto-reads the repo path from `~/.claude/.jarfis-source` (defaults to `~/repos/jarfis` if absent)
- Diff-compares commands, agents, hooks, scripts, and statusline, then copies only changes
- Auto-excludes `.distill-backup/` and local-only files
- Auto-reports results

**Note**: This Step is a single script execution. Do not copy manually.
If files were deleted, manually delete them from the repo after running the script.

**Step 4 artifact**: capture the sync command's stdout JSON to `{planDir}/artifacts/step4/sync-result.json` (files_copied[], files_skipped[], duration_ms).

→ Apply Workspace Update Snippet (step=4, next=step4.5)
→ Proceed to Step 4.5

### Step 4.5: RAG Auto-Update (ADR-0002 §2.4)

After the repo sync lands, refresh the JARFIS self-knowledge index so the
next `/jarfis:sys-implement` (or any RAG-using consumer) sees the latest
state. **Best-effort**: if this step fails, do NOT roll back Step 4 —
just log the error and proceed to Step 5. A stale RAG is recoverable;
a half-synced repo is not.

#### 4.5.1 — Extract changed files

```python
from jarfis.implement import extract_changed_files
changed = extract_changed_files(planDir)   # List[str], rel-to-~/.claude/
```

If `changed == []` (e.g. patch-mode skip path with no real edits) → mark
Step 4.5 `skipped` and proceed.

#### 4.5.2 — Run incremental update

```bash
python3 ~/.claude/scripts/jarfis_cli.py search index jarfis \
  --incremental --files "<comma-separated changed paths>"
```

The CLI:
- Re-encodes only the listed files
- Removes their existing chunks from the vector store first (chunks-by-file deletion)
- Appends new chunks
- Updates `total_chunks`, `indexed_at`, and the per-file metadata

If a file in `changed` has been **deleted** (no longer on disk), `cmd_index_jarfis`
detects it as `files_deleted_from_index` and removes its chunks without re-encoding.

#### 4.5.3 — Persist artifact

Capture stdout JSON to `{planDir}/artifacts/step4.5/rag-update.json`:

```json
{
  "status": "indexed",
  "scope": "jarfis",
  "incremental": true,
  "files_processed": N,
  "files_deleted_from_index": M,
  "chunks_added": A,
  "chunks_removed": R,
  "total_chunks": T
}
```

If the CLI errored (e.g. memory_insufficient), capture the error JSON instead and
write `{"status": "failed", "error": "..."}`. Status field on the step is `completed`
regardless — best-effort policy. Surface a one-line warning to the user.

→ Apply Workspace Update Snippet (step=4.5, next=step5; status=`skipped` if no changed files)
→ Proceed to Step 5

### Step 5: Results Report + Commit Command

1. Check changed files with `git status` and `git diff --stat`.
2. Display the results banner:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Implement Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Changes:
   - [Change 1]
   - [Change 2]
📂 Modified files:
   - [file path]: [change summary]
🔄 Index updated
🔄 Repo sync complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

3. **Generate a Commit + Push command and provide it to the user** (do not execute directly):
   - Explicitly list only changed files in `git add`
   - Commit message: `implement: [change summary] (v{new_version})`
   - If a version bump occurred, include tag + `--tags`
   - Include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
   - Use a double-quoted single-line message instead of heredoc (shell compatibility)

```
📋 Copy and run the command below:

git add [file1] [file2] ... && git commit -m "implement: [summary] (v{version})

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" && git tag v{version} && git push origin main --tags
```

**Step 5 artifacts**: write the results banner content to `{planDir}/artifacts/step5/results-banner.md` and the generated commit/push command text to `{planDir}/artifacts/step5/commit-cmd.txt`.

→ Apply Workspace Update Snippet (step=5, next=null — workspace finalized).
→ The plan is complete. Optionally archive via `jarfis_cli.py implement archive {plan-name}` after the user confirms the commit landed.
