# JARFIS Distill — Prompt Distillation (Cleanup/Optimization)

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Analyzes token efficiency of JARFIS prompt files and performs deduplication, template externalization, and rule consolidation.

User request: $ARGUMENTS

---

## Execution Flow

### D-0: Measurement (Before)

0. **Assess System State**
   - First read `~/.claude/commands/jarfis/jarfis-index.md` to understand the current JARFIS file structure.
   - Use the index's "File Structure" and "Command Mapping" to determine exclusion targets.
   - **If new commands have been added to the index**: Check their role to determine whether they are workflow prompts or meta tools, and add meta tools to the exclusion list.

1. **Per-file token cost measurement** — use `jarfis_cli.py measure` (LLM does not read files directly; it only receives measurement results)
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py measure \
     --exclude sys-distill.md,sys-sys-implement.md,jarfis-index.md,sys-health.md,sys-upgrade.md,sys-version.md \
     --index ~/.claude/commands/jarfis/jarfis-index.md \
     --diagnostics
   ```
   - Scan scope: `commands/jarfis/`, `agents/jarfis/`, `commands/jarfis.md` (recursive, `.distill-backup/` excluded)
   - Exclusions: meta tools (`sys-distill.md`, `sys-sys-implement.md`, `jarfis-index.md`, `sys-health.md`, `sys-upgrade.md`, `sys-version.md`)
   - Parse `files[].{name, lines, tokens_est}` + `total` + `index_mismatches` from the output JSON and display as a table
   - If `index_mismatches` exist, output a warning
   - The `--diagnostics` option also collects codeblock/header/prompt pattern info needed for D-1 diagnostics
   - Display results as a table:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       JARFIS Distill — Before Measurement
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     Filename            Lines   Est. Tokens
     work.md              427    4,558
     work-meeting.md           183    1,872
     ...
     ─────────────────────────────────────────
     TOTAL               3330   40,549
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```

2. **Determine target files** (only workflow files remain after excluding the above)
   - If `$ARGUMENTS` is provided: analyze only the specified file (e.g., `work.md`)
   - If `$ARGUMENTS` is empty: suggest the top 3 files by token cost as targets
   - Confirm targets with AskUserQuestion:
     ```
     "The following files will be analyzed for distillation:
      1. work.md (16,527tok)
      2. work-meeting.md (2,972tok)
      Proceed?"
     ```

### D-1: Diagnostics

Perform the following 6 diagnostics for each target file (Diagnostic 6 applies only to agent files).
**Leverage `diagnostics` data collected via the `--diagnostics` option in D-0** — mechanical counting is read from script output while only semantic analysis is performed by the LLM.

#### 1. Inline Template Detection
- Reference `diagnostics.codeblock_lines` and `diagnostics.codeblock_ratio` from the D-0 script output.
- If `codeblock_ratio` exceeds 0.50, warn "excessive inline templates."
- Only read files with high ratios directly to record the position, size, and owning Phase of code blocks.

#### 2. Agent Prompt Detection
- Reference `diagnostics.prompt_patterns` from the D-0 script output. (Line number list of `📄 Prompt:`, `📄 Template:`, `Task prompt:` patterns)
- Only read the surrounding lines of files with prompt patterns to record line count, estimated tokens, and owning Phase.
- Mark prompts of 15+ lines as "externalization candidates."

#### 3. Duplicate Rule Detection (LLM semantic analysis — cannot be replaced by script)
- Find patterns where identical/similar sentences appear 2+ times.
  - Keyword-based: same conceptual terms (e.g., `.jarfis-state.json`, `AskUserQuestion`) appearing N+ times in rule context
  - Rule repetition: similar sentences with patterns like "must always ~", "should ~"
- Record the location and content of each duplicate group.

#### 4. Structural Analysis
- Reference `diagnostics.headers` from the D-0 script output. (Line number + text list of `##`-level headers)
- Classify headers as "workflow rules" or "artifact templates":
  - Phase N, Execution Rules, Workflow Overview, etc. → rules
  - Remaining (artifact format names) → templates
- If both types are mixed at the same level, warn "structural mixing."

#### 5. Expression Density Analysis
- **Excessive output format**: Select files with high code block ratio from `diagnostics.codeblock_lines` → read only those files to check output example ratio. Warn "excessive output examples" if it exceeds 20% of the total.
- **Section compression potential**: Estimate section sizes from line gaps between headers in `diagnostics.headers`. Read only large sections to calculate "rule density" (rules / lines). Mark as "low-density section" if density is below 0.1.
- **No-compress marker**: Exclude sections with `<!-- no-condense -->` comments from compression targets.

#### 6. Agent Abstraction Analysis (`agents/jarfis/*.md` only)
- This diagnostic applies only to agent files under `~/.claude/agents/jarfis/`. Skip workflow files.
- **⚠️ Agent Protection Rule (Whitelist)**: The only section distill may analyze/modify in agent files is **`## Learned Rules`**. All other sections (Core Identity, Mindset & Disposition, Judgment Framework, Escalation Criteria, Behavioral Guidelines, Communication Style, Self-Verification, Output Format, role-specific expert sections, etc.) are **entirely read-only**. Do not condense/restructure/delete/move them.
- **Project-specific rule detection**: Apply upgrade's scope classification criteria to each rule in the `## Learned Rules` section:
  - Mentions specific file paths/component names/project names → `[project]`
  - Specific framework versions/configurations + qualifying expressions → `[project]`
  - General-purpose tools/techniques/principles → `[universal]` (normal)
- **Missing parent pattern detection**: For rules classified as `[project]`, check whether an abstractable parent principle already exists among `[universal]` rules in the same agent. If absent, mark as "parent pattern not registered."
  - Example: `moreden-pcweb commitlint only allows Korean` → parent: "Check the project's commitlint settings before committing" is absent
- **Cross-agent rule duplication**: Check whether rules with the same concept are repeated across multiple agents' Learned Rules. If the same filename/pattern appears in 2+ agents, mark as "cross-agent duplication."

#### Diagnostic Results Output
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Distill — Diagnostic Results: [filename]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Inline Templates: N code blocks, ~X,XXX tokens (XX% of total)
   Externalization candidates: [list]

📊 Agent Prompts: N prompts, ~X,XXX tokens
   Externalization candidates: [list]

📊 Duplicate Rules: N groups
   - [rule summary]: repeated at L123, L456, L789

📊 Structural Mixing: M of N ## headers are artifact templates

📊 Expression Density: N low-density sections, M excessive output examples
   Compression candidates: [list]

📊 Agent Abstraction (agents/ files only):
   [project] N rules — project-specific (migration candidates)
   [universal] M rules — general-purpose (normal)
   Missing parent patterns: K items
   Cross-agent duplication: J items

🎯 Estimated distillation impact: ~XX,XXX tok → ~X,XXX tok (XX% reduction)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### D-2: Develop Distillation Plan

> **⚠️ Command File Protection Rule**: `commands/jarfis/*.md` and `commands/jarfis/prompts/*.md` are **analysis/measurement targets for distill, but not modification targets**. The Step/Phase/Gate structure, banner formats, and execution logic in command files are critical to workflow correctness, so no condensation action (condense-section/compress-expression, etc.) may be applied. If token savings are needed in command files, distill may only suggest changes; actual modifications must be performed through `/jarfis:sys-implement`.

Generate a distillation action list based on the diagnostic results:

| Action Type | Description | Example |
|-------------|-------------|---------|
| `externalize-template` | Extract inline template to a separate file | PRD template → `templates/prd.md` |
| `externalize-prompt` | Extract agent prompt to a separate file | Phase 5 QA prompt → `prompts/phase5-qa.md` |
| `consolidate-rule` | Consolidate duplicate rules to a single location | State management → Execution Rules only |
| `restructure-headers` | Adjust artifact header levels | `##` → inside code block or separate file |
| `condense-section` | Compress verbose low-density sections to essentials only | 42-line expert summoning protocol → 15-line condensed version |
| `compress-expression` | Minimize output format examples | 20-line code block format example → 5-line core structure only |
| `abstract-rule` | Extract parent pattern from project-specific rule + move original | `moreden commitlint Korean` → universal: `check commitlint settings before commit`, project → move to `project-context.md` |
| `deduplicate-agent-rule` | Consolidate cross-agent duplicate rules | `CartWidget` rule in both FE+TL → keep in TL only |

For each action:
- Source location (filename, line range)
- Target location (new file path or consolidation point)
- Reference text to leave in the original (e.g., "Load `templates/prd.md` template for use as artifact format")
- Estimated token savings

Confirm the plan with AskUserQuestion:
```
"The following distillation actions will be performed:

 1. [externalize-template] PRD template → templates/prd.md (~480tok savings)
 2. [externalize-prompt] Phase 5 QA → prompts/phase5-qa.md (~230tok savings)
 3. [consolidate-rule] State management rules in 3 locations → 1 location in Execution Rules (~400tok savings)
 ...
 Total estimated savings: ~X,XXXtok (XX%)

 Proceed?"
```
- Options: "Proceed with all" / "Selective proceed" / "Cancel"
- "Selective proceed" allows individual action selection

### D-2.5: Dialectic Review (Debate Gate)

> Note: The Dialectic Review procedure follows sys-implement.md §Step 1.5 (canonical source).
> **Delta**: In distill, the gate entry is determined by the estimated token reduction rate.

**Gate entry condition**:
- Estimated token reduction rate 30% or higher → run debate
- Below 30% → SKIP debate → move to D-3

**Delta (distill-specific)**:
- Advocate prompt: "Analyze the token savings effectiveness and maintainability improvements of the distillation plan"
- Critic prompt: "Analyze the risk of context loss from externalization and potential for missed agent references"

### D-3: Execute Distillation

Execute approved actions in order:

#### externalize-template execution
1. Extract the target code block/section to a separate `.md` file.
   - Save location: `~/.claude/commands/jarfis/templates/[name].md`
2. Delete the content from the original and replace with a reference:
   ```
   > 📄 Template: Read `templates/[name].md` and use as artifact format.
   ```
3. Add the file path to the agent prompt of the Phase that uses the template in the original file.

#### externalize-prompt execution
1. Extract the agent prompt code block to a separate `.md` file.
   - Save location: `~/.claude/commands/jarfis/prompts/[phase]-[role].md`
2. Delete the prompt from the original and replace with a load directive:
   ```
   > 📄 Prompt: Read `prompts/[phase]-[role].md` and pass to the agent.
   ```

#### consolidate-rule execution
1. Select the most complete version among duplicate rules as the "canonical" version.
2. Delete duplicate content from remaining locations and replace with a canonical reference:
   ```
   > Note: For state management rules, see "Execution Rules > Workflow State Management".
   ```

#### restructure-headers execution
1. Lower the `##` level of artifact template headers to `###` or below, or remove the header entirely if externalized.

#### condense-section execution
1. Analyze the content of low-density sections and **keep only core rules/directives**, removing verbose explanations, excessive examples, and detailed edge case descriptions.
2. Compression principle: Preserve semantics — condense to the minimum directives needed for agents to behave identically.
3. Skip sections with the `<!-- no-condense -->` marker.

#### compress-expression execution
1. In output format example code blocks, **keep only structure (headers, section dividers)** and remove sample data/decorations.
   - Before: 20-line full format example → After: 5-line structure skeleton
2. Minimize as much as possible without making the format's intent unclear.

#### abstract-rule execution
1. Extract the **parent pattern (universal principle)** from rules classified as `[project]`.
   - Example: `moreden-pcweb commitlint only allows Korean` → `Check the project's commitlint/lint settings before committing`
2. Add the extracted parent pattern as a `[universal]` rule to the agent's `## Learned Rules` section.
3. **Remove** the original project-specific rule from the agent and move it to the project's `./.jarfis-project/project-context.md` under the `## Project-Specific Learned Rules` section.
   - If project-context.md or the section does not exist: Use AskUserQuestion to confirm the migration target or decide whether to delete the rule.
4. If the parent pattern already exists in `[universal]` rules: only remove the original (no need to add the parent pattern).

#### deduplicate-agent-rule execution
1. Among rules detected as cross-agent duplicates, keep only in the **most relevant agent** (the primary domain for that rule).
2. Remove the rule from all other agents.

### D-4: Measurement (After) + Report

1. **After measurement** — re-measure with `jarfis_cli.py measure` (same as D-0, `--diagnostics` not needed):
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py measure \
     --exclude sys-distill.md,sys-sys-implement.md,jarfis-index.md,sys-health.md,sys-upgrade.md,sys-version.md \
     --index ~/.claude/commands/jarfis/jarfis-index.md
   ```
   - Compare Before data from D-0 with After data using `files[].{name, tokens_est}`.

2. **Before/After comparison report output**:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     JARFIS Distill Complete
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   📊 Before / After Comparison:
   Filename            Before    After     Reduction
   work.md             16,527    5,800    -65%
   ...
   ─────────────────────────────────────────
   TOTAL               29,234   XX,XXX    -XX%

   ✅ Actions Performed:
      - [externalize-template] N items
      - [externalize-prompt] N items
      - [consolidate-rule] N items

   📂 Files Created:
      - templates/prd.md
      - templates/tasks.md
      - prompts/phase5-qa.md
      ...

   🔄 Index updated

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

3. **Update index**: Update `jarfis-index.md` to reflect the modification results.

4. **Version bump (PATCH)** — use `jarfis_cli.py version`:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py version patch "distill: token optimization (distillation summary)"
   ```
   - The script auto-updates VERSION, .jarfis-version, jarfis-index.md Version, and CHANGELOG.md.
   - Include the `previous`/`new` version from the output JSON in the report.

5. **Repo sync**: You must run the sync script:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py sync
   ```
   If files were deleted, manually delete them from the repo after running the script.

6. **Provide Commit + Push command** (do not execute directly):
   - Check the repo's changed files with `git status` and `git diff --stat`.
   - Explicitly list only changed files in `git add`.
   - Commit message: `distill: [distillation summary] (v{new_version})`
   - If a version bump occurred, include tag + `--tags`
   - Include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
   - Use a double-quoted single-line message instead of heredoc (shell compatibility)

   ```
   📋 Copy and run the command below:

   git add [file1] [file2] ... && git commit -m "distill: [summary] (v{version})

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" && git tag v{version} && git push origin main --tags
   ```

---

## Distillation Principles

1. **Preserve semantics**: Workflow behavior must remain identical before and after distillation. Rules are consolidated/moved, never deleted.
2. **Maintain reference links**: Externalized content must always leave a load directive in the original.
3. **Incremental execution**: The user must be able to review and select each action.
4. **Measurement-driven**: Do not tidy up by intuition; verify effectiveness by measuring actual token costs.
5. **Rollback capable**: Use Git history for rollback (no separate backup needed).
