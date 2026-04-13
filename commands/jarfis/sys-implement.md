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

### Step 0: Assess System State

1. Read `~/.claude/commands/jarfis/jarfis-index.md` to understand the current JARFIS system structure.
2. Based on what you read, determine which files are affected by the user's request.
3. **Minimize exploration**: If the index already provides sufficient information, do not explore further.
4. **Check Git repo**: Read `~/.claude/.jarfis-source` to find the JARFIS Git repo path. If absent, default to `~/repos/jarfis`.

> ⚠️ **Sync direction**: JARFIS active files live in `~/.claude/`.
> Always make modifications in `~/.claude/`, then sync to the repo via `jarfis_cli.py sync` in Step 4.
> Directly modifying the repo will not be reflected in the active system.

→ Proceed to Step 1

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

→ Proceed to Step 1.5

### Step 1.5: Dialectic Review (Ratchet Convergence)

A ratchet gate that iteratively verifies the proposed change to converge toward a better outcome.
Rather than compromising between pro/con opinions, it runs a verify → log → improve → re-verify loop.

**Gate entry condition**:
1. If `$ARGUMENTS` contains a review flag, follow it:
   - `--review=major` → ratchet required
   - `--review=minor` → run ratchet
   - `--review=patch` → skip ratchet → move to Step 2
2. If no flag is present, JARFIS determines the change magnitude:
   - 1 or fewer files to modify & content-only change (no structural change) → AskUserQuestion:
     ```
     question: "This looks like a lightweight update. Would you like to run a Dialectic Review?"
     header: "Review"
     options:
       - label: "Skip (Recommended)"
         description: "Proceed directly without the ratchet"
       - label: "Run Ratchet"
         description: "Converge the proposal through verification ratchet"
     ```
   - 2 or more files to modify, or structural change → run ratchet

**Ratchet convergence flow** (when ratchet is executed):

**0. Initialization**

```
$REVIEW_LOG = []          # Cumulative per-round issue history
$ROUND = 0
$MAX_ROUNDS = 3           # major: 3, minor: 2
$CHANGE_PROPOSAL = original   # Current proposal (improved each round)
```

- **Collect external ratchet history**: If `$ARGUMENTS` references plan.md, brainstorm.md, etc. with items already marked ACCEPT/REJECT/DEFER, compile them into `$PRIOR_RATCHET`. Otherwise, leave empty.

**1. Round Loop** (Round 0 ~ $MAX_ROUNDS-1)

For each round:

**1a. Analysis** (Agent tool, subagent_type: `jarfis-advocate`):
- prompt:
  ```
  Analyze the following JARFIS change proposal: [$CHANGE_PROPOSAL].
  Current system state: [index summary].

  [Round 1+ only:]
  ## Previous Round History
  $REVIEW_LOG

  Verify that previous issues have been properly addressed,
  and analyze the strengths and further improvement potential of the proposal.
  ```

**1b. Verification** (Agent tool, subagent_type: `jarfis-critic`):
- prompt:
  ```
  Verify the following JARFIS change proposal: [$CHANGE_PROPOSAL].
  Analysis results: [advocate results].

  [Round 1+ only:]
  ## Previous Round History (re-litigation of resolved items is prohibited)
  $REVIEW_LOG

  [$PRIOR_RATCHET exists only:]
  ## External Ratchet History (re-litigation prohibited)
  $PRIOR_RATCHET

  For each issue, provide a verdict in the following format:
  - [ID] Issue description → ACCEPT(current plan is sufficient) / IMPROVE(provide specific improvement) / REJECT(fundamental redesign needed)
  Do not re-raise items that were ACCEPTed in previous rounds.
  ```

**1c. Orchestrator Verdict** (performed directly):
- Review each issue from the Critic's results:
  - Issue already answered in `$PRIOR_RATCHET` → **ratchet violation — ignore** (log as "RATCHET_VIOLATION")
  - Re-litigation of previously ACCEPTed item → **ratchet violation — ignore**
  - New ACCEPT → log (no improvement needed)
  - New IMPROVE → log + add to list of changes to apply to proposal
  - New REJECT → log + request user decision

- Append to `$REVIEW_LOG`:
  ```
  Round N: {issues: [{id, verdict, description, resolution}], improve_count, accept_count}
  ```

**1d. Convergence Check**:
- 0 IMPROVE & 0 REJECT → **converged** → exit loop
- IMPROVE only → orchestrator **applies improvements to $CHANGE_PROPOSAL** → next round
- REJECT present → present issues + alternatives to user → AskUserQuestion (continue/pivot/abort)
- `$ROUND >= $MAX_ROUNDS` reached → summarize remaining issues for user + AskUserQuestion

**2. Display Convergence Results**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Dialectic Review — Converged
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Proposal: [final converged proposal summary]
🔄 Rounds: Converged after [N] verification rounds

┌─ Ratchet History ─────────────────────┐
│ Round 0: [N issues] → ACCEPT M, IMPROVE K │
│ Round 1: [N issues] → ACCEPT M, IMPROVE K │
│ ...                                     │
│ Round N: [0 issues] → Converged         │
└─────────────────────────────────────────┘

✅ Converged Decisions:
   - [Summary of ACCEPTed items]
🔧 Applied Improvements:
   - [Summary of IMPROVE → applied items]
🔒 Ratchet Protection:
   - [Items ignored as RATCHET_VIOLATION (if any)]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

After convergence or user approval → Proceed to Step 2

### Step 2: Execute Modifications

> ⚠️ **Modification location**: Always modify files at the `~/.claude/` path.
> Do not directly modify `~/repos/jarfis/` (Git repo). The repo is auto-synced in Step 4.

> 🧪 **Python TDD Rule**: When modifying `~/.claude/scripts/jarfis/*.py` or `jarfis_cli.py`, you must follow **Test-Driven Development**:
> 1. **Tests first**: Write failing tests in `tests/test_*.py` first, or modify existing tests
> 2. **Code change**: Modify production code until tests pass
> 3. **Full run**: Verify all tests pass with `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`
> 4. When adding new functions/subcommands → corresponding tests are mandatory
> 5. This rule does not apply to non-Python modifications (prompts, templates, etc.)

1. Read and modify only the necessary files.
2. Follow the "Modification Checklist" in the index.
3. When adding/deleting/renaming commands, you must also update `jarfis.md` (main helper).
4. **Note the externalized prompt structure**: Agent prompts in work.md are externalized to `prompts/*.md`.
   - To modify Phase-specific workflow **flow/rules** in work.md → edit work.md directly
   - To modify **task prompt content** sent to Phase-specific agents → edit `prompts/phase{N}.md`
   - Verify that `> 📄 Prompt:` references in work.md match the actual content in prompts/ files

→ After completing modifications, you must proceed to Step 3 (do not stop here)

### Step 3: Update Index

You **must** update `~/.claude/commands/jarfis/jarfis-index.md` to reflect the modifications:

- Update the file structure tree (include line counts for added/deleted/renamed files)
- Update the command mapping table
- Update artifacts/data files (if new data files were created)
- Update internal reference relationships
- Change the `Last updated` date to today

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
