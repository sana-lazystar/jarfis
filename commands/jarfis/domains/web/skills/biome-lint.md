# Biome Linting & Formatting Expertise

## Overview
Biome는 Prettier + ESLint를 하나로 통합한 도구. Rust로 작성되어 매우 빠름.

## Configuration (biome.json)
- `formatter`: 들여쓰기, 줄 폭, 따옴표 스타일
- `linter`: 규칙 활성화/비활성화, severity 조정
- `organizeImports`: import 자동 정렬

## Key Rules
- **Complexity**: noExcessiveCognitiveComplexity — 함수 복잡도 제한
- **Correctness**: noUnusedVariables, noConstAssign — 실수 방지
- **Suspicious**: noDoubleEquals — 암묵적 형변환 방지
- **Style**: useConst — let 대신 const 선호

## Integration Patterns
- **Pre-commit hook**: lint-staged + biome check
- **CI**: `biome check --write` (자동 수정) vs `biome check` (검증만)
- **IDE**: VSCode Biome 확장 — 저장 시 자동 포맷

## Migration from ESLint/Prettier
- `biome migrate eslint` — ESLint 설정 자동 변환
- 주의: 일부 ESLint 플러그인 규칙은 Biome에 없을 수 있음
- Prettier 호환: 대부분 동일하지만 trailing comma 등 미세 차이
