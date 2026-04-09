# .jarfis-state.json Schema

워크플로우 상태 파일의 전체 구조 예시:

```json
{
  "project_name": "기획 내용 요약",
  "work_name": "20250101-feat-TICKET-123",
  "work_input": "feat/TICKET-123",
  "docs_dir": "{JARFIS_SOURCE}/.personal/orgs/{org_name}/works/20250101-feat-TICKET-123",
  "branch": "feat/TICKET-123",
  "status": "in-progress",
  "key_decisions": ["REST over GraphQL — 기존 팀 경험", "PostgreSQL — 기존 인프라 활용"],
  "branches": {
    "backend": "feat/TICKET-123",
    "frontend": "feat/TICKET-123"
  },
  "source_meeting": "20250101-결제-시스템-리뉴얼",
  "started_at": "2025-01-01T00:00:00Z",
  "current_phase": 1,
  "workspace": {
    // NOTE: 이 "workspace"는 프로젝트 구조(monorepo/multi-project)를 나타내며,
    // v2의 "Organization (Org)" 개념과는 별개이다. Org은 org-profile.md로 관리됨.
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
        "key_decisions": ["REST over GraphQL — 기존 팀 경험"],
        "warnings": ["rate limiting 미구현, Phase 4 필수"],
        "unresolved": ["캐시 전략 미확정"]
      }
    },
    "3": {
      "status": "skipped",
      "reason": "UX Designer 불필요",
      "has_designer": null,
      "mode": "text | figma",
      "figma_pages": [
        {"title": "페이지 제목", "url": "https://figma.com/design/...?node-id=123-456"}
      ],
      "figma_url": "(레거시 — 단일 URL 호환용)",
      "figma_node_id": "(레거시 — 단일 노드 ID 호환용)",
      "common_components_skip": ["(figma 모드 시) 스킵할 공통 컴포넌트 이름 목록"],
      "token_map_generated": false,
      "figma_iterations": 0,
      "figma_max_iterations": 20
    },
    "4": { "status": "in_progress", "tdd_enabled": false },
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
    "summary": "BE-1~3 완료, FE 진행중"
  }
}
```

## 필드 설명

### phases.1.ratchet
Phase 1 PRD Completeness Check의 래칫 상태. AutoResearch 래칫 패턴 기반.
- `prd_score`: 현재 총점 (0-10)
- `items`: 5개 항목별 점수 (0-2). 키: `ambiguity`, `kpi`, `perf_budget`, `roles_rationale`, `scope_boundary`
- `passed_items`: 현재 Pass(2점)인 항목명 배열. 래칫 검증에 사용: 이전에 Pass였던 항목이 Fail로 변경되면 래칫 위반
- `attempts`: PO 재작성 시도 횟수 (최대 2)
- `history`: 채점 이력. `score`: 해당 시점 총점, `passed`: Pass 항목, `action`: `accept`(점수 유지/개선) 또는 `ratchet_violation`(Pass→Fail 감지)

### phases.4.tdd_enabled
Step 4-0.5 TDD 테스트 선행 작성 활성화 여부. `true`이면 QA(Opus)가 test-strategy.md 기반 테스트 코드를 선행 작성했음을 의미. Phase 5 QA 리뷰 시 경량화 힌트로 활용.

### 최상위 status
워크플로우 전체 상태를 나타낸다.

| 값 | 설명 |
|---|------|
| `in-progress` | 워크플로우 진행 중 |
| `completed` | 모든 Phase 완료 |
| `aborted` | 사용자에 의해 중단 |

### key_decisions
Gate 통과 시 핵심 결정사항을 누적 기록한다. `array<string>` 타입.

### phases 내부 status
각 Phase의 진행 상태를 나타낸다.

| 값 | 설명 |
|---|------|
| `pending` | 아직 시작하지 않음 |
| `in_progress` | 진행 중 |
| `completed` | 완료 |
| `skipped` | 건너뜀 (reason 필드 참조) |
