# Phase 1b: Discovery Processing (PO + TA artifacts)

> Executed by **jarfis-foreman** inside tmux. jarfis-foreman is the **orchestrator**: it runs compose CLI, spawns sub-agents via the Task tool, and never reads the source artifacts itself. The sub-agents read files and produce outputs.
> All sub-agent artifacts in English. User-facing messages in $LOCALE.
> Phase 1a (PO counter-questions dialogue) is handled directly by the main session and is NOT part of this prompt.

**Execution context** (set before tmux starts):
- `$DOCS_DIR` = tmux workspace (`state.work.docsDir`)
- `$STATE_FILE` = `$DOCS_DIR/.jarfis-state.json`
- `$LOCALE` = global locale (`~/.claude/.jarfis-locale`)

## Required Inputs (consumed by sub-agents — not by jarfis-foreman)

The sub-agents spawned in this phase MUST read the following. jarfis-foreman's role is to ensure each sub-agent's task prompt tells it which files to read.

- `$DOCS_DIR/discovery/po-qa.json` — Phase 1a Q&A archive (main Claude wrote this) — consumed by PO
- `$DOCS_DIR/.wiki-cache.md` — org wiki cache, if `state.org != null` — consumed by PO
- Every file listed in `state.work.meetings[]` — consumed by PO when the user picked meetings in Phase 0
- `$DOCS_DIR/discovery/prd.md` (just written by PO in Step 1) — consumed by TA in Step 2

## Conditional Inputs

- (none — Phase 1b is the first producing phase)

---

## Step 1 — PO artifacts (product-owner)

### Compose invocation (jarfis-foreman executes)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent product-owner --state $STATE_FILE)

SUBAGENT=$(echo "$COMPOSE" | jq -r .subagent_type)
MODEL=$(echo "$COMPOSE" | jq -r .model)
PROMPT=$(echo "$COMPOSE" | jq -r .prompt)
WORKING_DIR=$(echo "$COMPOSE" | jq -r .working_dir)

# Spawn via the Task tool:
# Task(subagent_type=$SUBAGENT, model=$MODEL, cwd=$WORKING_DIR,
#      prompt=$PROMPT + "\n\n## Task\n" + <PO Task prompt below verbatim>)
```

### Sub-agent task prompt (jarfis-foreman injects this block verbatim into the Task call, appended after the compose `prompt`)

```
You are the product owner for this workflow. Read the files below and produce the listed artifacts.

Files to read first:
- $DOCS_DIR/discovery/po-qa.json    (Phase 1a answers from the user)
- $DOCS_DIR/.wiki-cache.md          (only if it exists — org-level wiki cache)
- Each meeting file path provided to you by the orchestrator (may be empty)

Meeting reference rule (apply ONLY when meeting files are provided):
For each meeting file, extract four buckets before writing any artifact:
- Meeting summary           (overall context: customer problem, solution sketch, goals)
- Meeting decisions         (confirmed | tentative | unresolved items)
- Meeting technical research (architecture notes, stack comparisons, POC results)
- Additional meeting materials (attachments, diagrams, sample data, external refs)

Incorporation policy:
- Confirmed decisions  → inline into the artifact with NO label
- Tentative decisions  → inline with "(tentative)" label
- Unresolved items     → inline with "(unresolved — to be finalized during work)" label
- DO NOT re-discuss or overwrite items already confirmed in the meeting.
  The Phase 1a dialogue (po-qa.json) already respected them; preserve them verbatim.
- If a bucket is empty for a given file, skip that bucket silently.

If no meeting files are provided, skip the meeting reference rule entirely and rely only on
po-qa.json + .wiki-cache.md.

Produce the following artifacts:

1. $DOCS_DIR/discovery/working-backwards.md (6 sections)
   - Hypothetical Press Release: Title, Subtitle, Customer Problem, Solution, Customer Quote, Getting Started
   - FAQ — External: 5 customer-perspective Q/A
   - FAQ — Internal: 5 technical/business-perspective Q/A
   - Meeting incorporation: actively leverage the customer problems, solutions, and FAQ
     material discussed in meetings. Mirror the framing agreed upon in the meeting.

2. $DOCS_DIR/discovery/prd.md (10 sections)
   - Overview
   - Target Users
   - Functional Requirements (user-story format)
   - Non-Functional Requirements
   - Success Metrics (KPIs — each with a number + measurement method)
   - Timeline
   - Risks / Dependencies
   - Required Roles (BE/FE/UX/DevOps ✅/⬜ table + rationale each)
   - Scope (reflect state.workspace.scope verbatim — do NOT re-judge)
   - Performance Budget (metric + target value + measurement method table)
   Heading rule (phase-verify strict): use the section titles above VERBATIM.
   DO NOT prepend numeric prefixes (bad: `## 1. Overview`, `## 3. Functional Requirements`).
   Use `## Overview`, `## Functional Requirements`, `## Success Metrics`, `## Scope`, `## Required Roles` exactly.
   Meeting incorporation:
   - Pre-fold meeting decisions (confirmed/tentative/unresolved) into the relevant sections
     per the policy above.
   - Pre-fold meeting technical research into Risks/Dependencies + Non-Functional Requirements
     (cite the meeting file).
   - Pre-fold additional meeting materials by reference — do NOT duplicate large attachments;
     link or summarize.

3. $DOCS_DIR/discovery/ux-direction.md — ONLY if state.design.mode != null
   - IA & URL Structure
   - Tone & Voice
   - Pages: headings, content structure, requirements, interaction patterns
     (sync/async, loading, error)
   - ID field for each page/section — kebab-case REQUIRED, regex ^[a-z][a-z0-9-]*$
     (invalid IDs cause phase-verify to FAIL).
   - Responsive scope: reflect state.responsive (pc-only | pc-mobile | pc-mobile-tablet)
   - Single file — do NOT split.
```

### Meeting file discovery (jarfis-foreman executes before spawning)

jarfis-foreman resolves meeting file paths by reading `state.work.meetings[]` from `$STATE_FILE` and passes them to the PO sub-agent by appending a line to the task prompt, e.g.:

```
Meeting files: /path/to/meeting-1.md, /path/to/meeting-2.md
```

If the array is empty, append: `Meeting files: (none)`.

---

## Step 2 — TA Feasibility (technical-architect)

Run after Step 1 completes (prd.md exists).

### Compose invocation (jarfis-foreman executes)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent technical-architect --state $STATE_FILE)
# Extract SUBAGENT, MODEL, PROMPT, WORKING_DIR as in Step 1, then Task spawn.
```

### Sub-agent task prompt (jarfis-foreman injects verbatim)

```
You are the technical architect. Read the files below and append a feasibility section to prd.md.

Files to read first:
- $DOCS_DIR/discovery/prd.md    (just written by PO in Step 1)
- project-profile.md is auto-injected via composition.yaml — you will see it in your context already.

Task:
Assess technical feasibility:
- Technical complexity (high | medium | low)
- Core technology stack candidates
- Expected bottlenecks
- Existing-system integration considerations
- Technical risk factors

APPEND a new section titled "## Technical Feasibility" to $DOCS_DIR/discovery/prd.md.
Do NOT create a separate file. Do NOT rewrite the existing prd.md sections.
```

---

## Completion Protocol

At phase completion, perform the following in order:

1. **Produce spec artifacts**: ensure each required artifact exists at its wiki-standard path
   - `$DOCS_DIR/discovery/working-backwards.md`
   - `$DOCS_DIR/discovery/prd.md` (including the Technical Feasibility section)
   - `$DOCS_DIR/discovery/ux-direction.md` (if `state.design.mode != null`)
2. **(Optional) Handoff document**: only when extra data does not fit into spec artifacts
3. **Write phase-results/phase1b/attempt{K}.json** (last step):
   ```bash
   mkdir -p $DOCS_DIR/phase-results/phase1b
   # Success
   echo '{"status":"completed","reason":"","reasonDetail":""}' \
     > $DOCS_DIR/phase-results/phase1b/attempt{K}.json
   # Error
   echo '{"status":"error","reason":"...","reasonDetail":"..."}' \
     > $DOCS_DIR/phase-results/phase1b/attempt{K}.json
   ```

**Strict order**: artifacts → (handoff) → phase-results JSON.
Do NOT write to `.jarfis-state.json` (the main Claude owns it).
`{K}` is substituted with the actual attempt number by the main session when generating the prompt file.
