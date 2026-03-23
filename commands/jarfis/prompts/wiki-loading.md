# Wiki Loading — 공통 모듈

> 이 파일은 work.md, continue.md, meeting.md에서 참조하는 wiki 로딩 공통 모듈이다.
> Org 등록된 프로젝트에서만 실행한다.

## 전제 조건

- `preflight` JSON의 `org_root`가 non-null
- `{org_root}/.jarfis/wiki/INDEX.md` 존재

## 2-Step 경량 로딩 (Fix 모드, Meeting)

1. **INDEX.md 읽기**: `{org_root}/.jarfis/wiki/INDEX.md`를 읽어 Quick Reference + Directory Map 파악
2. **관련 섹션만 선택적 로딩**: 현재 태스크와 관련된 섹션의 `_index.md`만 읽기
   - 예: FE 버그 수정 → DESIGN/_index.md + QA/_index.md
   - 예: BE API 수정 → TA/_index.md + QA/_index.md

> 2-Step은 INDEX.md + 관련 _index.md 최대 2개만 읽는다. 개별 파일은 읽지 않는다.

## 4-Step 전체 로딩 (Work 모드, Extend 모드)

1. **INDEX.md 읽기**: Quick Reference + Directory Map → 전체 wiki 구조 파악
2. **모든 섹션 _index.md 읽기**: PO, DESIGN, TA, QA 4개 섹션의 `_index.md` 읽기
3. **관련 파일 선택적 읽기**: _index.md의 Summary 기반으로 현재 기획과 관련 높은 파일만 선택하여 읽기
   - 관련성 판단: 기획 키워드, 도메인, 기술 스택 매칭
   - 최대 5개 파일로 제한 (토큰 효율)
4. **Cascading Specificity 적용**: 읽은 wiki 내용과 $DOCS_DIR 산출물 간 충돌 시 $DOCS_DIR 우선

> 4-Step은 INDEX.md → 4개 _index.md → 관련 파일 최대 5개를 읽는다.

## Cascading Specificity 규칙

정보 충돌 시 우선순위:
```
$DOCS_DIR (현재 태스크 산출물) > project/.jarfis (프로젝트 프로필/컨텍스트) > wiki/ (조직 누적 지식) > INDEX.md (목차)
```

- 이번 태스크가 **다루는 주제**: $DOCS_DIR 산출물이 최신이므로 wiki보다 우선
- 이번 태스크가 **다루지 않는 주제**: wiki 내용이 유효 — 참조하여 일관성 유지
