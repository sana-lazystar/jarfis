# Continue Extend — Agent Prompts

## PO Prompt (PRD 보강)

```
기존 PRD를 참조하여 확장 요구사항을 추가해주세요.

## 기존 PRD
{$DOCS_DIR/prd.md 내용}

## 확장 요청
{$ARGUMENTS}

$PROJECT_CONTEXT

## 지시사항
1. 기존 PRD의 구조와 스타일을 유지하세요.
2. 새 요구사항을 기존 PRD 뒤에 "## Extension #{iteration}" 섹션으로 추가하세요.
3. 기존 기능과의 의존성/충돌을 분석하세요.
4. 추가 역할이 필요한지 판단하세요 (기존: {required_roles 요약}).
5. Working Backwards는 생략합니다 (기존 press-release.md 참조).
6. 불명확한 점이 있으면 사용자에게 역질문하세요.
```

## Architect Prompt (설계 보강)

```
기존 아키텍처를 기반으로 확장 설계를 추가해주세요.

## 기존 아키텍처
{$DOCS_DIR/architecture.md 내용}

## 확장 PRD
{prd.md의 Extension 섹션}

$PROJECT_CONTEXT
$BE_PROJECT_PROFILE
$FE_PROJECT_PROFILE

## 지시사항
1. 기존 아키텍처에 미치는 영향을 분석하세요.
2. 변경/추가할 컴포넌트를 식별하세요.
3. architecture.md에 "## Extension #{iteration}" 섹션으로 추가하세요.
4. 기존 ADR과 충돌하는 결정이 있으면 새 ADR을 추가하세요.
```

## Tech Lead Prompt (태스크 분해)

```
확장 요구사항에 대한 태스크를 분해해주세요.

## 기존 태스크
{$DOCS_DIR/tasks.md 내용}

## 확장 설계
{architecture.md Extension 섹션}

## 확장 PRD
{prd.md Extension 섹션}

$BE_PROJECT_PROFILE
$FE_PROJECT_PROFILE

## 지시사항
1. tasks.md에 "## Extension Tasks (#N)" 섹션을 추가하세요.
2. 기존 태스크와의 의존성을 명시하세요.
3. 기존과 동일한 형식(BE/FE/DevOps 분류, 체크박스)을 따르세요.
4. 프로젝트 프로필이 존재하면 디렉토리 구조와 컨벤션을 참조하여 대상 파일을 구체적으로 명시하세요.
```
