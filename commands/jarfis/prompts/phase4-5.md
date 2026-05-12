# Phase 4.5: Operational Readiness (DevOps-owned)

> Executed by **jarfis-foreman** inside tmux. jarfis-foreman is the **orchestrator**: runs compose, spawns the devops-engineer sub-agent via Task. It does NOT read source artifacts itself.
> DevOps-owned — no tech-lead involvement (M4 decision).
> All sub-agent artifacts in English. User-facing messages in $LOCALE.

**Execution context**:
- `$DOCS_DIR` = tmux workspace
- `$STATE_FILE` = `$DOCS_DIR/.jarfis-state.json`

### jarfis-foreman precompute (from $STATE_FILE)

- `$DEVOPS` = `state.devops` (boolean)

## Required Inputs (consumed by devops-engineer sub-agent)

- `$DOCS_DIR/planning/architecture.md`
- `$DOCS_DIR/planning/tasks.md`
- `$DOCS_DIR/discovery/ia/shared.json` — IA L4 (auth_model + global_state)

## Conditional Inputs (consumed by devops-engineer sub-agent)

- `$DOCS_DIR/ops/infra-runbook.md` — if `$DEVOPS == "true"` AND Phase 4 produced it (Category B tasks)

---

## Step 1 — DevOps artifact (devops-engineer, work-wide, 1 spawn)

### Compose invocation (jarfis-foreman executes)

```bash
COMPOSE=$(python3 ~/.claude/scripts/jarfis_cli.py compose \
  --agent devops-engineer --state $STATE_FILE)
# devops-engineer model is opus (from composition.yaml) — no override needed.
# Task spawn with the prompt below; select the devops_true OR devops_false variant.
```

### Sub-agent task prompt — devops=true variant (jarfis-foreman injects when `$DEVOPS == "true"`)

```
You are the devops/SRE engineer producing a deployment plan.

Inputs to read:
- $DOCS_DIR/planning/architecture.md
- $DOCS_DIR/planning/tasks.md
- $DOCS_DIR/ops/infra-runbook.md   (only if it exists — Category B runbooks from Phase 4)

Produce $DOCS_DIR/ops/deployment-plan.md with the sections below — ALL REQUIRED:

## Deployment Strategy
- Deployment Method: Blue-Green | Canary | Rolling | Big Bang — with rationale
- Feature Flag Plan: per feature (flag name, rollout gates, kill-switch path) OR "N/A" per feature
- Deployment Order: explicit ordering (e.g., DB migration → BE → FE) adjusted per architecture

## Rollback Plan  (REQUIRED — M4 decision: devops=true must have rollback)
- Rollback Trigger Conditions: e.g., error rate > 1%, P95 response time > 500 ms
- Rollback Procedure: step-by-step, per deployed component
- DB Rollback: migration reversibility + procedure; if irreversible, document mitigation

## Operational Readiness Checklist
- [ ] Logging: key operations logged with correlation IDs
- [ ] Monitoring: error rate + response time dashboards exist
- [ ] Alerts: threshold-triggered alerts configured
- [ ] DB migration: safe execution + rollback validated
- [ ] Environment variables: all newly required variables documented + provisioned
- [ ] External dependencies: stability + SLA documented
- [ ] Dev server startup (npm run dev / yarn dev / etc.) works
      — prerequisite for Phase 5 UX review (build errors block that review).
- [ ] IA L4 alignment: $DOCS_DIR/discovery/ia/shared.json `auth_model` 인프라 지원 확인 (Stage 4)
- [ ] IA L4 global_state: 선언된 state stores (redis/dynamodb 등) 가 deployment 에 포함됨

## Research Notes  (Optional — add only when Category B tasks required external research)
- AWS service comparison / new runtime / etc. Use context7, WebSearch, or docs. Cite sources.
```

### Sub-agent task prompt — devops=false variant (jarfis-foreman injects when `$DEVOPS == "false"`)

```
You are the devops/SRE engineer producing a lightweight operational readiness checklist.

Inputs to read:
- $DOCS_DIR/planning/architecture.md
- $DOCS_DIR/planning/tasks.md

Produce $DOCS_DIR/ops/deployment-plan.md with ONLY the lightweight sections below:

## Operational Readiness Checklist (Lightweight)
- [ ] Logging: key operations logged
- [ ] Monitoring: error rate visible
- [ ] Environment variables: all newly required variables documented
- [ ] External dependencies: stability verified
- [ ] Dev server startup works (prerequisite for Phase 5 UX review)
- [ ] IA L4 alignment: $DOCS_DIR/discovery/ia/shared.json `auth_model` 인프라 지원 확인 (Stage 4)
- [ ] IA L4 global_state: 선언된 state stores (redis/dynamodb 등) 가 deployment 에 포함됨

> DevOps role is not required in this workflow (see Required Roles in PRD).
> Deployment Strategy / Rollback Plan sections are OMITTED.
> Apply existing org-level deployment and rollback defaults.

Do NOT produce Deployment Strategy or Rollback Plan sections in this mode.
```

---

## Completion Protocol

At phase completion, perform the following in order:

1. **Produce spec artifacts**: `$DOCS_DIR/ops/deployment-plan.md` (full when devops=true / lightweight when devops=false)
2. **(Optional) Handoff document**
3. **Write phase-results/phase4-5/attempt{K}.json** (last step — atomic + sentinel, tmux-claude-completion-signal-v1):
   ```bash
   mkdir -p $DOCS_DIR/phase-results/phase4-5
   RESULT=$DOCS_DIR/phase-results/phase4-5/attempt{K}.json
   echo '{"status":"completed","reason":"","reasonDetail":""}' > $RESULT.tmp
   mv $RESULT.tmp $RESULT          # atomic publish
   touch $RESULT.done              # sentinel
   # Error: same emit pattern with status=error
   ```

**Strict order**: artifacts → (handoff) → phase-results JSON.
Do NOT write to `.jarfis-state.json` (the main Claude owns it).
`{K}` is substituted with the actual attempt number by the main session when generating the prompt file.
