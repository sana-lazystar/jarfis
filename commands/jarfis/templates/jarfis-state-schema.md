# .jarfis-state.json Schema

Full structure example of the workflow state file:

```json
{
  "project_name": "Summary of planning content",
  "work_name": "20250101-feat-TICKET-123",
  "work_input": "feat/TICKET-123",
  "docs_dir": "{JARFIS_SOURCE}/.personal/orgs/{org_name}/works/20250101-feat-TICKET-123",
  "branch": "feat/TICKET-123",
  "status": "in-progress",
  "locale": "ko",
  "key_decisions": ["REST over GraphQL — existing team experience", "PostgreSQL — leverage existing infrastructure"],
  "branches": {
    "backend": "feat/TICKET-123",
    "frontend": "feat/TICKET-123"
  },
  "source_meeting": "20250101-payment-system-renewal",
  "started_at": "2025-01-01T00:00:00Z",
  "current_phase": 1,
  "workspace": {
    // NOTE: This "workspace" represents the project structure (monorepo/multi-project),
    // and is separate from the v2 "Organization (Org)" concept. Org is managed via org-profile.md.
    "type": "monorepo | multi-project",
    "projects": {
      "backend": { "path": ".", "framework": "next.js" },
      "frontend": { "path": ".", "framework": "next.js" }
    }
  },
  "phases": {
    "0": { "status": "completed" },
    "1": {
      "status": "completed",
      "gate": "approved",
      "ratchet": {
        "prd_score": 9,
        "items": {"ambiguity": 2, "kpi": 2, "perf_budget": 1, "roles_rationale": 2, "scope_boundary": 2},
        "passed_items": ["ambiguity", "kpi", "roles_rationale", "scope_boundary"],
        "attempts": 1,
        "history": [{"score": 9, "passed": ["ambiguity", "kpi", "roles_rationale", "scope_boundary"], "action": "accept"}]
      }
    },
    "2": {
      "status": "completed",
      "handoff": {
        "key_decisions": ["REST over GraphQL — existing team experience"],
        "warnings": ["Rate limiting not implemented, required in Phase 4"],
        "unresolved": ["Cache strategy undecided"]
      }
    },
    "3": {
      "status": "skipped",
      "reason": "UX Designer not needed",
      "has_designer": null,
      "mode": "text | figma",
      "figma_pages": [
        {"title": "Page title", "url": "https://figma.com/design/...?node-id=123-456"}
      ],
      "figma_url": "(Legacy — for single URL backward compatibility)",
      "figma_node_id": "(Legacy — for single node ID backward compatibility)",
      "common_components_skip": ["(In figma mode) List of common component names to skip"],
      "token_map_generated": false,
      "figma_iterations": 0,
      "figma_max_iterations": 20
    },
    "4": {
      "status": "in_progress",
      "tdd_enabled": false,
      "ratchet": {
        "phase4_tests": {
          "baseline_pass_rate": 0.95,
          "test_command": "npm test",
          "task_index": 3,
          "test_modifications": [
            {"file": "tests/auth.test.ts", "task": "BE-2", "reason": "Mock update due to API response schema change"}
          ],
          "history": [
            {"task": "BE-1", "pass_rate": 0.95, "action": "accept"},
            {"task": "BE-2", "pass_rate": 0.90, "action": "reject", "attempt": 1},
            {"task": "BE-2", "pass_rate": 0.97, "action": "accept"}
          ]
        }
      }
    },
    "4.5": { "status": "pending" },
    "5": { "status": "pending" },
    "6": { "status": "pending" }
  },
  "required_roles": {
    "backend": true,
    "frontend": false,
    "ux_designer": false,
    "devops": true
  },
  "api_spec_required": false,
  "phase2_agents": {
    "impact_analysis": "completed",
    "architect": "completed",
    "api_spec": "skipped",
    "tech_lead_tasks": "completed",
    "qa_test_strategy": "completed"
  },
  "phase4_agents": {
    "security_review": "completed",
    "backend": "in_progress",
    "frontend": "skipped",
    "devops": "pending"
  },
  "phase4_5_agents": {
    "deployment_plan": "pending"
  },
  "phase5_agents": {
    "api_contract_check": "pending",
    "tech_lead": "pending",
    "qa": "pending",
    "security": "pending",
    "diagnosis": "pending",
    "fix_implementation": "pending"
  },
  "phase6_agents": {
    "retrospective": "pending",
    "learnings_update": "pending"
  },
  "gate_results": {
    "gate1": { "decision": "approved", "feedback": "" },
    "gate2": { "decision": "approved", "feedback": "" },
    "gate3": { "decision": "pending" }
  },
  "last_checkpoint": {
    "timestamp": "2025-01-01T01:30:00Z",
    "phase": 4,
    "summary": "BE-1~3 completed, FE in progress"
  }
}
```

## Field Descriptions

### phases.1.ratchet
Ratchet state for Phase 1 PRD Completeness Check. Based on the AutoResearch ratchet pattern.
- `prd_score`: Current total score (0-10)
- `items`: Score per each of the 5 criteria (0-2). Keys: `ambiguity`, `kpi`, `perf_budget`, `roles_rationale`, `scope_boundary`
- `passed_items`: Array of criteria names currently passing (score of 2). Used for ratchet validation: if a previously passing criterion changes to fail, it is a ratchet violation
- `attempts`: Number of PO rewrite attempts (max 2)
- `history`: Scoring history. `score`: total score at that point, `passed`: passing criteria, `action`: `accept` (score maintained/improved) or `ratchet_violation` (pass-to-fail detected)

### phases.4.tdd_enabled
Whether Step 4-0.5 TDD test-first writing is enabled. When `true`, it means QA (Opus) has pre-written test code based on test-strategy.md. Used as a lightweight hint during Phase 5 QA review.

### phases.4.ratchet.phase4_tests
Phase 4 TDD code quality ratchet state. Only created when `tdd_enabled: true`. Based on the AutoResearch ratchet pattern.
- `baseline_pass_rate`: Best test pass rate achieved so far (0.0-1.0). Initially set after Step 4-0.5 completion
- `test_command`: Project's test execution command (extracted from project-profile scripts)
- `task_index`: Number of tasks that have passed the ratchet so far
- `test_modifications`: Array of records where the implementation agent modified test files. Each entry: `file` (path), `task` (task ID), `reason` (commit message). Subject to validation during Phase 5 QA
- `history`: Per-task ratchet decision history. `task`: task ID, `pass_rate`: pass rate at decision time, `action`: `accept` (pass rate maintained/improved), `reject` (pass rate declined, retry required), `skipped_after_max_retries` (2 failures, proceed anyway), `attempt`: attempt number on retry

### locale
User language setting for the workflow. Auto-detected in Phase 0 or explicitly set via `/jarfis:locale`.
- Default: `"ko"`
- Allowed values: `"ko"`, `"en"`, `"ja"` (extensible in the future)
- JARFIS internal reasoning/instructions are always in English. This field only determines the user-facing output language.
- Set as the `$LOCALE` variable in Phase 0, controlling the agent response language across all subsequent Phases.

### Top-level status
Represents the overall workflow state.

| Value | Description |
|---|------|
| `in-progress` | Workflow in progress |
| `completed` | All Phases completed |
| `aborted` | Aborted by user |

### key_decisions
Cumulatively records key decisions as gates are passed. Type: `array<string>`.

### Status within phases
Represents the progress state of each Phase.

| Value | Description |
|---|------|
| `pending` | Not yet started |
| `in_progress` | In progress |
| `completed` | Completed |
| `skipped` | Skipped (see reason field) |

---

## workflow-metrics.tsv Format

Location: `$JARFIS_ORG_DIR/workflow-metrics.tsv`
Created at: Phase 6 Step 6-2.5 (work.md) or after Fix/Extend retrospective (work-continue.md)
Design rationale: AutoResearch results.tsv pattern — quantitative learning loop across workflows

TSV header (tab-separated):
```
workflow_id	project	started_at	completed_at	prd_score	review_iterations	learning_candidates_count	skipped_phases	follow_up_mode	follow_up_iteration
```

| Column | Type | Description | Extraction Path |
|------|------|------|-----------|
| workflow_id | string | Workflow identifier | `work_name` |
| project | string | Project name | `project_name` |
| started_at | ISO8601 | Start time | `started_at` |
| completed_at | ISO8601 | Completion time | Current time at recording |
| prd_score | int(0-10) | PRD Completeness score | `phases.1.ratchet.prd_score` (empty if absent) |
| review_iterations | int | Number of Phase 5 re-reviews | Extracted from phases.5 info |
| learning_candidates_count | int | Number of learning candidates | Length of `learning_candidates` array |
| skipped_phases | string | Skipped Phase numbers (comma-separated) | Phases with status="skipped" |
| follow_up_mode | string | Follow-up work mode | "" (main workflow) / "fix" / "extend" |
| follow_up_iteration | int | Follow-up work iteration count | `follow_up.iteration` (empty if absent) |

---

## follow_up.ratchet

Test ratchet state for work-continue Fix mode. A lightweight version of Unit 3 (Phase 4 TDD ratchet).
Compares pass rates before and after Fix implementation in projects with a test runner to prevent fix cascades.

```json
{
  "follow_up": {
    "ratchet": {
      "fix_baseline_pass_rate": 0.95,
      "fix_current_pass_rate": 0.97,
      "action": "accept"
    }
  }
}
```

| Field | Type | Description |
|------|------|------|
| fix_baseline_pass_rate | float(0.0-1.0) | Test pass rate before Fix started |
| fix_current_pass_rate | float(0.0-1.0) | Test pass rate after Fix completed |
| action | string | `accept` (pass rate maintained/improved), `reject` (declined, retry), `user_override` (user forced proceed), `disabled` (no test runner available) |
