# .jarfis-state.json Schema

> **v4.1 (M2.11, ADR-0002)**: ``cmd_init`` emits the v4 nested shape only.
> v3 flat keys (``project_name`` / ``work_name`` / ``work_input`` /
> ``docs_dir`` / ``branch`` / ``branches`` / ``source_meeting``) are no
> longer written when a new state file is created. The legacy section at
> the bottom of this document is retained for archival reference and for
> validators that still accept pre-v4.1 state files as input.

## v4 Nested Schema (current — emitted by ``cmd_init``)

The v4 shape splits identity (``work``), orchestration flags
(``sessionKey`` / ``locale`` / ``org`` / ``domain`` / ``design`` /
``responsive`` / ``api`` / ``devops`` / ``po_extras``), and phase
lifecycle (``status`` / ``current_phase`` / ``phases`` /
``key_decisions`` / ``last_checkpoint``).

```json
{
  "sessionKey": "jf-1a2b3c4d",
  "locale": "ko",
  "org": null,
  "domain": "web",
  "design": { "mode": null, "figmaPages": [] },
  "responsive": null,
  "api": { "mode": null },
  "devops": false,
  "po_extras": [],
  "work": {
    "name": "20250101-feat-TICKET-123",
    "input": "feat/TICKET-123",
    "docsDir": "{JARFIS_SOURCE}/.personal/orgs/{org_name}/works/20250101-feat-TICKET-123",
    "startedAt": "2025-01-01T00:00:00Z",
    "meetings": [],
    "projectName": "Summary of planning content"
  },
  "status": "in-progress",
  "key_decisions": ["REST over GraphQL — existing team experience", "PostgreSQL — leverage existing infrastructure"],
  "started_at": "2025-01-01T00:00:00Z",
  "current_phase": 1,
  "workspace": {
    // NOTE: This "workspace" represents the project structure (monorepo/multi-project),
    // and is separate from the v2 "Organization (Org)" concept. Org is managed via org-profile.md.
    "structure": "monorepo | multi-project",
    "scope": [
      // v4.1 (M4.2, ADR-0003 §2.1): scope[] is the per-project array
      // populated in Phase 0 step 5. Phase 0 step 7 fills `domain` per
      // entry; downstream Phase 4 implement uses scope[i].domain to
      // dispatch the correct role (rust_engineer / rn_engineer / ...).
      {
        "name": "tauri-shell",
        "path": "/abs/path/to/shell",
        "type": "frontend | backend | mobile | desktop",
        "framework": "tauri | react | react-native | ...",
        "languages": ["ts", "rust"],
        "domain": "desktop",          // ← v4.1 per-scope domain (M4.2)
        "branch": "20260101-feature",
        "baseCommit": "abc123"
      },
      {
        "name": "mobile-app",
        "path": "/abs/path/to/app",
        "type": "mobile",
        "framework": "react-native",
        "domain": "mobile",
        "branch": "20260101-feature",
        "baseCommit": "def456"
      }
    ]
  },
  "phases": {
    "0": { "status": "completed" },
    "1": {
      "status": "completed",
      "gate": "approved"
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
  "tddEnabled": false,
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

### tddEnabled
**Location: top-level (`state.tddEnabled`)** — v4.0.2 OBS-4 canonicalized here. The v4 runtime (`prompts/phase4.md`, `prompts/phase5.md`, `work.md`) reads and writes this flag at the top level; nested `phases.4.tdd_enabled` is deprecated. The main session sets it after phase4.md sub-agent reports `meta.tddEnabled` in phase-results.

Whether Step 4-0.5 TDD test-first writing is enabled. When `true`, QA (Opus) has pre-written test code based on test-strategy.md. Used as a lightweight hint during Phase 5 QA review and as the gating flag for `phases.4.ratchet`.

### phases.4.ratchet.phase4_tests
Phase 4 TDD code quality ratchet state. Only created when `state.tddEnabled: true`. Based on the AutoResearch ratchet pattern.
- `baseline_pass_rate`: Best test pass rate achieved so far (0.0-1.0). Initially set after Step 4-0.5 completion
- `test_command`: Project's test execution command (extracted from project-profile scripts)
- `task_index`: Number of tasks that have passed the ratchet so far
- `test_modifications`: Array of records where the implementation agent modified test files. Each entry: `file` (path), `task` (task ID), `reason` (commit message). Subject to validation during Phase 5 QA
- `history`: Per-task ratchet decision history. `task`: task ID, `pass_rate`: pass rate at decision time, `action`: `accept` (pass rate maintained/improved), `reject` (pass rate declined, retry required), `skipped_after_max_retries` (2 failures, proceed anyway), `attempt`: attempt number on retry

### workspace.scope[i].domain (v4.1 — M4.2, ADR-0003)

Per-scope domain assignment. Populated by Phase 0 step 7 of work.md
(dispatch matrix — high-conf single / tie / low-conf / greenfield /
multi-domain monorepo / user override). Allowed values: ``"web"``,
``"desktop"``, ``"mobile"``. Multi-domain monorepos (Tauri shell +
RN app, etc.) end up with different values per scope.

**Forward compatibility**: v4.0.x state files used a single
top-level ``state.domain`` for the whole workflow. v4.1 readers
(``compose``, ``validate``, ``list-workflows``) automatically run
``migrate_v40_to_v41(state)`` to backfill ``scope[i].domain`` from
``state.domain`` when the per-scope field is absent. ``state.domain``
itself is preserved untouched so legacy callers keep working.

**Resolution order** in compose (``get_scope_domain(scope, state)``):

1. ``scope[i].domain``    — v4.1 source of truth.
2. ``state.domain``       — v4.0.x legacy single domain (fallback).
3. ``None``               — caller (work.md Phase 0 step 7) MUST
   trigger detect / AskUserQuestion before invoking compose.

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
Created at: Phase 6 Step 6-2.5 (work.md)
Design rationale: AutoResearch results.tsv pattern — quantitative learning loop across workflows

TSV header (tab-separated):
```
workflow_id	project	started_at	completed_at	review_iterations	learning_candidates_count	skipped_phases	follow_up_mode	follow_up_iteration
```

| Column | Type | Description | Extraction Path |
|------|------|------|-----------|
| workflow_id | string | Workflow identifier | `work_name` |
| project | string | Project name | `project_name` |
| started_at | ISO8601 | Start time | `started_at` |
| completed_at | ISO8601 | Completion time | Current time at recording |
| review_iterations | int | Number of Phase 5 re-reviews | Extracted from phases.5 info |
| learning_candidates_count | int | Number of learning candidates | Length of `learning_candidates` array |
| skipped_phases | string | Skipped Phase numbers (comma-separated) | Phases with status="skipped" |
| follow_up_mode | string | Follow-up work mode | "" (main workflow) / "fix" / "extend" |
| follow_up_iteration | int | Follow-up work iteration count | `follow_up.iteration` (empty if absent) |

---

## follow_up.ratchet

Test ratchet state for Fix mode (legacy). A lightweight version of Unit 3 (Phase 4 TDD ratchet).
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

---

## Legacy v3 Flat Keys (Removed in v4.1)

> **참고용. v4.1 에서 ``cmd_init`` 은 더 이상 emit 하지 않음.**
>
> 아래 키들은 v3 ``work-legacy.md`` 가 사용하던 평탄 표현. ADR-0002 에 따라
> ``work-legacy.md`` 가 v4.1 에서 제거되면서 dual-emit 의 근거가 사라졌다.
> ``cmd_validate`` / ``cmd_list_workflows`` 는 backward-compat 차원에서
> 기존 v3 state 파일 읽기는 계속 허용하지만, 신규 state 는 v4 nested
> 셰이프만 작성된다.

| v3 Flat Key | v4 Replacement | Notes |
|-------------|---------------|-------|
| ``project_name`` | ``work.projectName`` | Human-readable label |
| ``work_name`` | ``work.name`` | Identifier (``YYYYMMDD-…``) |
| ``work_input`` | ``work.input`` | Branch/topic input |
| ``docs_dir`` | ``work.docsDir`` | Workspace dir |
| ``branch`` | (n/a — derive from ``work.input``) | v3 single-branch field |
| ``branches`` | (n/a — multi-project covered by ``workspace.projects``) | v3 per-role branch map |
| ``source_meeting`` | (n/a) | v3 meeting hand-off field |

> ``state.py:cmd_validate`` accepts state files lacking ``work.*`` if the
> v3 flat keys are present (transition shim). Once all in-flight workflows
> have rotated through v4.1+, the v3 fallback can be deleted.
