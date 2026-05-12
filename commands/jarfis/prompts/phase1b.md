# Phase 1b: Discovery Processing (PO + TA artifacts)

> Executed by **jarfis-foreman** inside tmux. jarfis-foreman is the **orchestrator**: it runs compose CLI, spawns sub-agents via the Task tool, and never reads the source artifacts itself. The sub-agents read files and produce outputs.
> All sub-agent artifacts in English. User-facing messages in $LOCALE.
> Phase 1a (PO counter-questions dialogue) is handled directly by the main session and is NOT part of this prompt.

**Execution context** (set before tmux starts):
- `$DOCS_DIR` = tmux workspace (`state.work.docsDir`)
- `$STATE_FILE` = `$DOCS_DIR/.jarfis-state.json`
- `$LOCALE` = global locale (`~/.claude/.jarfis-locale`)

### jarfis-foreman precompute (Org IA snapshot — Stage 4)

```bash
- $ORG_ROOT = state.org.root (empty when org not registered)
- $PROJECT_SLUG = state.workspace.scope[0].name (multi-scope monorepo: out-of-scope for Stage 4 — see audit:114-115; per scope[0] only)
- snapshot Org IA → discovery/ia/.baseline/ (Stage 1 ia.py snapshot subcommand):
    if [ -n "$ORG_ROOT" ] && [ -d "$ORG_ROOT/.jarfis-org/wiki/PO/projects/$PROJECT_SLUG/ia" ]; then
      python3 ~/.claude/scripts/jarfis_cli.py ia snapshot \
        --src "$ORG_ROOT/.jarfis-org/wiki/PO/projects/$PROJECT_SLUG/ia" \
        --dest "$DOCS_DIR/discovery/ia/.baseline" \
        --create-empty-if-missing
    else
      python3 ~/.claude/scripts/jarfis_cli.py ia snapshot \
        --src /dev/null --dest "$DOCS_DIR/discovery/ia/.baseline" \
        --create-empty-if-missing
    fi
```

## Required Inputs (consumed by sub-agents — not by jarfis-foreman)

The sub-agents spawned in this phase MUST read the following. jarfis-foreman's role is to ensure each sub-agent's task prompt tells it which files to read.

- `$DOCS_DIR/discovery/po-qa.json` — Phase 1a Q&A archive (main Claude wrote this) — consumed by PO
- `$DOCS_DIR/.wiki-cache.md` — org wiki cache, if `state.org != null` — consumed by PO
- Every file listed in `state.work.meetings[]` — consumed by PO when the user picked meetings in Phase 0
- `$DOCS_DIR/discovery/prd.md` (just written by PO in Step 1) — consumed by TA in Step 2
- `$DOCS_DIR/discovery/ia/.baseline/manifest.json` — Org IA snapshot at Phase 1b entry (read-only baseline for PO; written by jarfis-foreman precompute above)

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
   - Tone & Voice (overall tone, error message tone, CTA style)
   - Responsive scope: reflect state.responsive (pc-only | pc-mobile | pc-mobile-tablet)
   - Single file — do NOT split.
   - **DO NOT** author an "IA & URL Structure" section or per-page "Pages" details (Stage 8):
     IA 정량 메타데이터 (slug, route, role, parent, depth) 는 #4 의 discovery/ia/manifest.json
     에만 쓴다. Per-page 디테일 (Heading/Content/Requirements/Interaction Patterns) 은 #4 의
     discovery/ia/pages/{slug}.md `## Notes` body 에 흡수된다. ux-direction.md 는 페이지-비특이적
     톤만 담는다 (+ supplied 모드 한정 External Mockup Reference 섹션).

4. $DOCS_DIR/discovery/ia/ — Information Architecture (IA SSOT, ia-as-po-ssot-v2-spine)
   - Read $DOCS_DIR/discovery/ia/.baseline/manifest.json (Org IA snapshot at Phase 1b entry)
   - For each page in scope (derived from PRD; per-page details go into pages/{slug}.md Notes body):
     - Append/merge into $DOCS_DIR/discovery/ia/manifest.json `pages[]` with L0+L1:
       - L0: slug, route, title, role (public|auth|admin), parent (slug or null), depth (int)
       - L1: title (already in L0), and create $DOCS_DIR/discovery/ia/pages/{slug}.md
         with YAML frontmatter containing:
           slug, route, title, role, parent, depth        (mirror manifest entry)
           purpose: "<short page-existence rationale>"
           user_tasks: ["<top user goals as bullets>"]
         and a "## Notes" body for prose details.
     - L2 (data_sources, api_endpoints) / L3 (components, primary_cta) / L4 (shared.json)
       은 후속 phase 가 채운다 — PO 는 L0+L1 만.
   - slug regex: ^[a-z][a-z0-9-]*$ (verify.py R3 강제). 중복 slug/route 금지 (R4/R5).
   - Cold-start: manifest.version = "2.0", project = state.workspace.scope[0].name.
   - Write the manifest sorted by slug for deterministic diff.
   - Validate before completion:
       python3 ~/.claude/scripts/jarfis_cli.py ia validate $DOCS_DIR/discovery/ia
     (exit 2 = validation FAIL → fix before phase-results emission)

5. Supplied design mode (state.design.mode == "supplied") — IA import (D8, Stage 7 alignment):
   - If $SUPPLIED_PATH/ia.json or $SUPPLIED_PATH/pages/ia.json exists, read it as REFERENCE.
   - Import L0+L1 fields into PO's own discovery/ia/manifest.json + pages/{slug}.md.
   - 시안 동봉 ia.json 이 L2/L3 까지 포함하면 그대로 import (PO 가 후속 phase 의 권한을 침해하지 않는 한도 — i.e. PO 는 시안의 components 를 기록만, 의역/추가 X).
   - 시안에 ia.json 없으면 zero-base author (위 #4 와 동일).
   - SSOT: discovery/ia/ — supplied 동봉본은 보조 reference, 자체 manifest 가 진실.
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
   - `$DOCS_DIR/discovery/ia/manifest.json` (always — IA SSOT)
   - `$DOCS_DIR/discovery/ia/pages/{slug}.md` (one per manifest entry)
   - `$DOCS_DIR/discovery/ia/.baseline/manifest.json` (foreman-written; PO does NOT write here)
2. **(Optional) Handoff document**: only when extra data does not fit into spec artifacts
3. **Write phase-results/phase1b/attempt{K}.json** (last step — atomic + sentinel, tmux-claude-completion-signal-v1):
   ```bash
   mkdir -p $DOCS_DIR/phase-results/phase1b
   RESULT=$DOCS_DIR/phase-results/phase1b/attempt{K}.json
   # Success
   echo '{"status":"completed","reason":"","reasonDetail":""}' > $RESULT.tmp
   # OR Error
   # echo '{"status":"error","reason":"...","reasonDetail":"..."}' > $RESULT.tmp
   mv $RESULT.tmp $RESULT          # atomic publish
   touch $RESULT.done              # sentinel — wakes parent poll()
   ```

**Strict order**: artifacts → (handoff) → phase-results JSON.
Do NOT write to `.jarfis-state.json` (the main Claude owns it).
`{K}` is substituted with the actual attempt number by the main session when generating the prompt file.
