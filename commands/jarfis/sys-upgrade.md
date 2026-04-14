# JARFIS Upgrade — Learning Item Management and System Application

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Manages learning items in `$JARFIS_ORG_DIR/learnings.md` (Org-aware: `.personal/orgs/{org}/learnings.md`) and applies them to actual agent/workflow prompts.

> **`{JARFIS_SOURCE}` resolution**: Read `~/.claude/.jarfis-source` to find the JARFIS Git repo path. If absent, default to `~/repos/jarfis`.

---

## Execution Flow

### Step 1: Load Learning File

Read the `$JARFIS_ORG_DIR/learnings.md` (Org-aware: `.personal/orgs/{org}/learnings.md`) file.
If the file does not exist, inform the user: "No learning file found yet. Please run the `/jarfis` workflow first." and terminate.

If the file exists, parse it by section and display the current learning list to the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JARFIS Learnings — Current Learning List
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Agent Hints

### Backend Engineer
1. (item content)
2. (item content)

### Frontend Engineer
1. (item content)
...

## Workflow Patterns
1. (item content)
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 2: Select Action

Use AskUserQuestion to let the user choose one of the following:

```
question: "What action would you like to perform?"
header: "Action"
options:
  - label: "Apply Learnings (Recommended)"
    description: "Reflect learning items into agent/workflow prompts"
  - label: "Manage Items"
    description: "Add/edit/delete learning items"
  - label: "Clear All"
    description: "Remove all items from the learning file (structure preserved)"
  - label: "Exit"
    description: "Exit"
```

### Step 3: Action-Specific Processing

---

#### When [Apply Learnings] is selected

The core function that reflects learning items into actual agent prompts and workflows.
Composed of 3 independent blocks; each block can be re-executed from its starting point on failure.

---

##### Block 1: Analysis (Scope Classification + Dialectic Review)

> Input: Learning items from learnings.md
> Output: Each item tagged with `[universal]`/`[project]` scope

**1-1. Target Mapping**

Map learning items to their target files:

| learnings Section | Target File |
|-------------------|-------------|
| `Agent Hints > Frontend Engineer` | `~/.claude/agents/jarfis/senior-frontend-engineer.md` |
| `Agent Hints > Backend Engineer` | `~/.claude/agents/jarfis/senior-backend-engineer.md` |
| `Agent Hints > QA Engineer` | `~/.claude/agents/jarfis/senior-qa-engineer.md` |
| `Agent Hints > Tech Lead` | `~/.claude/agents/jarfis/tech-lead.md` |
| `Agent Hints > Security Engineer` | `~/.claude/agents/jarfis/senior-security-engineer.md` |
| `Agent Hints > DevOps Engineer` | `~/.claude/agents/jarfis/senior-devops-sre-engineer.md` |
| `Agent Hints > UX Designer` | `~/.claude/agents/jarfis/senior-ux-designer.md` |
| `Agent Hints > Product Owner` | `~/.claude/agents/jarfis/senior-product-owner.md` |
| `Agent Hints > Architect` | `~/.claude/agents/jarfis/technical-architect.md` |
| `Workflow Patterns` | Kept in `learnings.md` (not copied to work.md — applied via sys-upgrade only, not loaded at runtime) |

**1-2. Automatic Scope Classification**

Automatically classify each learning item by scope:

- Specific file paths/directories/qualifying expressions ("in this project") → `[project]`
- General-purpose tools/techniques/principles → `[universal]`
- Indeterminate → `[ambiguous]`

Display the classification results to the user.

**1-3. Dialectic Review (ambiguous items only)**

> Note: The Dialectic Review procedure follows sys-implement.md §Step 1.5 (canonical source).
> **Delta**: In upgrade, it is applied only for scope determination of ambiguous items.
> - Advocate prompt: "Argue why this learning item is a universal principle"
> - Critic prompt: "Argue why this learning item is project-specific"
> - If all items are clearly classified → SKIP the debate

---

##### Block 2: Plan (Display Application Plan + Scope Selection)

> Input: Scope classification results from Block 1
> Output: User-approved list of items to apply

**2-1. Display Application Plan**

Show the mapping by scope: Universal application (agent Learned Rules) + Project-Specific application (.jarfis/project-context.md). Workflow Patterns are kept in learnings.md and applied via sys-upgrade only, not loaded at runtime.

**2-2. Select Application Scope**

Use AskUserQuestion to let the user choose "Apply All" or "Selective Apply" (multiSelect: true).

---

##### Block 3: Execution (Apply + Cleanup + Version Bump + Sync)

> Input: Approved item list from Block 2
> Output: Agent/workflow files updated + version bump + repo sync

**3-1. Apply to Agent Files**

> **⚠️ Agent Protection Rule (Whitelist)**: The only section upgrade may modify in agent files is **`## Learned Rules`**. All other sections (Core Identity, Mindset, Judgment, Escalation, Behavioral Guidelines, Output Format, role-specific expert sections, etc.) are **read-only**. Do not insert learning items into or modify the content of other sections.

| Learning Scope | Target |
|---------------|--------|
| `[universal]` Agent Hints | `~/.claude/agents/jarfis/{role}.md` → `## Learned Rules` |
| `[project]` Agent Hints | `./.jarfis/project-context.md` → corresponding role section |

- `[universal]`: Add to the `## Learned Rules` section of the agent file (create if absent). Check for duplicates.
- `[project]`: Add to `.jarfis/project-context.md` (create file/section if absent). Check for duplicates.
- Remove date metadata `(YYYY-MM-DD)` when applying.

**3-2. Apply to Workflow Files**

| Learning Scope | Target |
|---------------|--------|
| `[universal]` Workflow Patterns | Kept in `learnings.md` (not copied to work.md — applied via sys-upgrade only, not loaded at runtime) |
| `[project]` Workflow Patterns | `./.jarfis/project-context.md` → Workflow section |

- Check for duplicates. Remove date/confirmation count metadata.

**3-3. Post-Application Cleanup**

Use AskUserQuestion to choose how to handle the learnings file:
- "Clear applied items only (Recommended)" / "Keep as-is" / "Clear all"
- When clearing: preserve section headers, remove only item lines (lines starting with `-`).

**3-4. Version Bump (PATCH)**

```bash
python3 ~/.claude/scripts/jarfis_cli.py version patch "upgrade: apply learnings (application summary)"
```

**3-5. Repo Sync**

```bash
python3 ~/.claude/scripts/jarfis_cli.py sync
```

Display the application results and return to Step 2.

---

#### When [Manage Items] is selected

Use AskUserQuestion to let the user choose a sub-action:

```
question: "What management action would you like to perform?"
header: "Manage"
options:
  - label: "Delete Items"
    description: "Remove unnecessary learning items"
  - label: "Edit Items"
    description: "Update existing learning content"
  - label: "Add Items"
    description: "Manually enter new learnings"
```

##### [Delete]

1. List all learning items with numbers (grouped by section).
2. Use AskUserQuestion with **multiSelect: true** to let the user select items to delete.
   - Each option label: item number and content summary (e.g., "[FE-1] img tag indentation check")
   - description: full item content
3. Remove the selected items from `$JARFIS_ORG_DIR/learnings.md` (Org-aware: `.personal/orgs/{org}/learnings.md`).
4. Display the deletion results and return to Step 2.

##### [Edit]

1. List all learning items with numbers.
2. Use AskUserQuestion to let the user select **one** item to edit.
3. Show the current content of the selected item and use AskUserQuestion to receive new content.
   - question: "Enter the new content (Current: [current content summary])"
   - Allow free input via "Other"
4. Replace the corresponding item in `$JARFIS_ORG_DIR/learnings.md` (Org-aware: `.personal/orgs/{org}/learnings.md`) with the input.
5. Display the edit results and return to Step 2.

##### [Add]

1. Use AskUserQuestion to let the user select which section to add to:
   ```
   question: "Which section should this be added to?"
   header: "Section"
   options:
     - label: "Backend Engineer"
       description: "Backend development learnings"
     - label: "Frontend Engineer"
       description: "Frontend development learnings"
     - label: "QA Engineer"
       description: "QA/testing learnings"
     - label: "Workflow Patterns"
       description: "Workflow decision patterns"
   ```
   - Other sections (Tech Lead, Security Engineer, etc.) can be entered via "Other"
2. Use AskUserQuestion to receive the learning content.
   - question: "Enter the learning content to add"
   - Allow free input via "Other"
3. Auto-append today's date and add the item to the corresponding section in `$JARFIS_ORG_DIR/learnings.md` (Org-aware: `.personal/orgs/{org}/learnings.md`).
   - Format: `- (input content) (YYYY-MM-DD)`
   - For Workflow Patterns: `- (input content) (YYYY-MM-DD, confirmed 1 time)`
4. Display the addition results and return to Step 2.

---

#### When [Clear All] is selected

1. Confirm with AskUserQuestion:
   ```
   question: "Are you sure you want to clear all learning items? This action cannot be undone."
   header: "Confirm"
   options:
     - label: "Execute Clear"
       description: "Remove all items (section structure preserved)"
     - label: "Cancel"
       description: "Return without doing anything"
   ```
2. If "Execute Clear" is selected: Remove all items (lines starting with `-`) from `$JARFIS_ORG_DIR/learnings.md` (Org-aware: `.personal/orgs/{org}/learnings.md`). Preserve section headers (`#`, `##`, `###`).
3. Display the results and return to Step 2.

---

#### When [Exit] is selected

Display the final change summary and terminate:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JARFIS Upgrade Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Changes:
- Applied: N items (M agent files, K workflow items)
- Deleted: N items
- Edited: N items
- Added: N items
- Learnings cleared: Y/N
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If a version bump was executed, **generate a Commit + Push command and provide it to the user** (do not execute directly):
- Check the repo's changed files with `git status` and `git diff --stat`.
- Explicitly list only changed files in `git add`.
- Commit message: `upgrade: [application summary] (v{new_version})`
- If a version bump occurred, include tag + `--tags`
- Include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- Use a double-quoted single-line message instead of heredoc (shell compatibility)

```
📋 Copy and run the command below:

git add [file1] [file2] ... && git commit -m "upgrade: [summary] (v{version})

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" && git tag v{version} && git push origin main --tags
```

---

## Notes

- Save file modifications immediately after each action completes (to prevent data loss if terminated mid-process).
- If a section does not exist, create it (e.g., if a Security Engineer section is missing but an addition is requested).
- If a section becomes empty after item deletion, preserve the section header but remove only the items.
- Maintain consistency with existing file format (markdown lists, date format, etc.).
- **Duplicate check on apply**: If similar content already exists in the target file's `Learned Rules` section, skip it and inform the user.
- **Remove dates on apply**: Do not include learnings date/confirmation count metadata in prompts.
