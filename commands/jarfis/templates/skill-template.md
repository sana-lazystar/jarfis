# Skill Template — Checkpoint Style

> **Skill 파일 작성 가이드.** 이 템플릿을 복사하여 `~/.claude/commands/jarfis/skills/{name}.md`에 작성.
>
> **분량**: 1~2KB (~300~500 토큰), 5섹션. token budget (`max_skill_tokens=2500`)에서 5+개 동시 로드 가능.
>
> **목적**: sub-agent가 작업 시 떠올려야 할 **체크포인트** (참고서 X). 공식 문서/팀 컨벤션은 별도 (project-profile.md, MDN 검색).

## 작성 원칙

❌ 공식 문서 요약 (인터넷 검색 가능, 토큰 낭비)
❌ 팀 컨벤션 (`.jarfis-project/project-profile.md`에 있음)
❌ 일반론 ("코드를 깔끔하게 작성하세요")

✅ **흔히 놓치는 함정** (예: nodejs `__dirname` undefined in ESM)
✅ **결정 휴리스틱** (예: "DB connection pool = CPU * 2 + 1")
✅ **반(反)패턴** (예: "이러면 안 됨" + 왜)
✅ **버전/환경 의존 주의사항** (예: "Node 22+ 필요", "macOS만 X")

## 권장 5섹션 구조

~~~markdown
# {기술명} Expertise

> {1줄 요약: 어떤 작업에 쓰이는 skill인가}

## Common Pitfalls
- 함정 1 (왜 + 어떻게 회피)
- 함정 2

## Decision Heuristics
- 휴리스틱 1 (when X → do Y)
- 휴리스틱 2

## Anti-patterns
- 반패턴 1 (X 하지 마, Y 하라)
- 반패턴 2

## Version & Environment Notes
- 버전 의존성, 호환성 주의

## Related Skills
- 같이 쓰면 좋은 skill 또는 충돌 skill (선택)
~~~

## 파일 위치 + 명명

- 위치: `~/.claude/commands/jarfis/skills/{name}.md` (flat 디렉토리)
- 이름: 소문자 + 하이픈 (예: `aws-lambda.md`, `tauri-backend.md`)
- 도메인 분류 X — 기술 단위로만

## 예시 (nodejs.md)

~~~markdown
# Node.js / TypeScript Backend Expertise

> 서버사이드 JS/TS — 이벤트 루프, V8, async 패턴

## Common Pitfalls
- `__dirname` undefined in ESM → `import.meta.url` 사용
- unhandled rejection 누수 → `mutateAsync`는 항상 try-catch
- 메모리 누수: 미해제 event listener, large closure capture

## Decision Heuristics
- DB connection pool = CPU * 2 + 1 (Postgres)
- Microtask (Promise) > Macrotask (setTimeout) ordering

## Anti-patterns
- `require()` + `import` 혼용 → 빌드 시 ESM/CJS 충돌
- async 함수 안에서 try 없이 await — unhandled rejection

## Version & Environment Notes
- Node 18+ 권장 (ESM 안정화)
- macOS/Linux: `process.platform` 분기 시 `darwin` 매칭

## Related Skills
- `express`, `biome-lint` (lint/format), `aws-lambda` (cold start 주의)
~~~
