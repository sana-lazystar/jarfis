# JARFIS Init — 프로젝트 프로필 생성

현재 디렉토리의 프로젝트를 분석하여 `./.jarfis/project-profile.md`를 생성합니다.
이 프로필은 `/jarfis:work` 실행 시 서브에이전트에게 주입되어 코드베이스 탐색 토큰을 절약하고 프로젝트 컨벤션에 맞는 코드를 생성하게 합니다.

사용자 요청: $ARGUMENTS

---

## Depth 설정

`$ARGUMENTS`에서 `--depth` 플래그를 파싱하세요:
- `--depth basic` → **basic**
- `--depth medium` → **medium**
- `--depth deep` 또는 **플래그 없음** → **deep** (기본값)

---

## 실행 흐름

### Step 0: 프로젝트 감지

현재 디렉토리에서 프로젝트 유형을 감지하세요:

1. 프로젝트 매니페스트 파일 탐색:
   - `package.json` → Node.js (FE 또는 BE)
   - `pom.xml` / `build.gradle` / `build.gradle.kts` → Java/Kotlin (BE)
   - `requirements.txt` / `pyproject.toml` / `Pipfile` → Python (BE)
   - `go.mod` → Go (BE)
   - `Cargo.toml` → Rust (BE)
   - `pubspec.yaml` → Flutter/Dart (FE)
   - `Gemfile` → Ruby (BE)

2. 프레임워크 감지 (매니페스트의 dependencies 기반):
   - **FE 프레임워크**: react, vue, angular, svelte, next (pages/app 라우터), nuxt, astro, solid
   - **BE 프레임워크**: express, fastify, nestjs, koa, hono, spring, django, flask, fastapi, gin, echo, fiber
   - **풀스택**: next.js(api routes 존재), nuxt(server/ 존재), remix, sveltekit

3. 감지 실패 시 사용자에게 질문:
   ```
   프로젝트 유형을 자동 감지하지 못했습니다.
   이 프로젝트의 유형과 기술 스택을 알려주세요.
   ```

감지 결과를 표시하세요:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Init — 프로젝트 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 경로: (현재 디렉토리)
🔍 유형: BE / FE / Fullstack
⚙️ 깊이: basic / medium / deep
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 1: Basic 분석 (모든 depth에서 실행)

다음 항목을 분석하세요:

**1-1. 기술 스택 식별**
- 언어 및 버전 (tsconfig.json, .nvmrc, .python-version 등 참조)
- 프레임워크 및 버전
- 패키지 매니저 (npm, yarn, pnpm, bun 등)
- 런타임 (Node.js, Deno, Bun 등)

**1-2. 디렉토리 구조**
- 최상위 3레벨까지의 디렉토리 트리 생성
- 각 주요 디렉토리의 역할 한줄 설명

**1-3. 주요 의존성**
- 핵심 프레임워크/라이브러리 (devDependencies 제외)
- 각 의존성의 역할 한줄 설명

**1-4. 스크립트 및 커맨드**
- 개발 서버 실행, 빌드, 테스트, 린트 커맨드
- 환경 변수 파일 (.env.example 등) 확인

**1-5. 설정 파일 요약**
- ESLint, Prettier, TypeScript, 빌드 도구 등의 핵심 설정값
- 설정 파일 전체를 복사하지 말고, 중요한 옵션만 요약

> **basic depth는 여기서 완료 → Step 4로 이동**

### Step 2: Medium 분석 (medium, deep에서 실행)

**2-1. 코딩 컨벤션 감지**
- 파일 네이밍 패턴: kebab-case, camelCase, PascalCase 등 (실제 파일명 샘플링)
- 컴포넌트/모듈 구조 패턴: barrel exports, co-location, feature-based 등
- Import 컨벤션: 절대 경로, 경로 별칭 (@/, ~/), 정렬 규칙
- 타입 정의 방식: interface vs type, 파일 분리 여부
- 에러 핸들링 패턴: try-catch, Result 타입, 커스텀 에러 클래스 등

**2-2. API 라우트 / 페이지 목록**
- BE: 라우트 파일을 탐색하여 엔드포인트 목록 (Method + Path + 핸들러 위치)
- FE: 페이지/라우트 목록 (경로 + 컴포넌트 위치)

**2-3. 데이터 모델 / 스키마**
- DB 모델 파일 탐색 (Prisma schema, Mongoose models, TypeORM entities, Drizzle schema 등)
- 모델명 + 주요 필드 목록 (전체 스키마를 복사하지 말고 요약)

**2-4. 모듈 관계 맵**
- 주요 모듈 간 의존 관계 (어떤 모듈이 어떤 모듈을 import하는지)
- 공유 모듈/유틸리티 식별

> **medium depth는 여기서 완료 → Step 4로 이동**

### Step 3: Deep 분석 (deep에서만 실행)

**3-1. 아키텍처 패턴 분석**
- 레이어 구조 식별: Controller-Service-Repository, MVC, 헥사고날 등
- 미들웨어 체인 / 플러그인 구조
- 상태 관리 패턴 (FE): Redux, Zustand, Recoil, Context 등의 사용 방식
- 인증/인가 구현 방식

**3-2. 핵심 비즈니스 로직 요약**
- 주요 서비스/유즈케이스 모듈을 식별하고 각각의 책임을 1-2문장으로 요약
- 복잡한 비즈니스 규칙이 있는 모듈 표시
- ⚠️ 코드를 그대로 복사하지 말고, 역할과 로직 흐름만 서술

**3-3. 재사용 가능 컴포넌트 카탈로그**
- FE: 공통 UI 컴포넌트 목록 (이름, props 요약, 사용처)
- BE: 공통 유틸리티/헬퍼 목록 (이름, 기능 요약, 사용처)
- 공유 타입/인터페이스 목록

**3-4. 기술적 특이사항 및 주의점**
- 알려진 workaround나 hack 코드 (TODO/FIXME/HACK 주석 탐색)
- 사용되지 않는 코드나 deprecated 패턴
- 성능 관련 특이사항 (캐싱, 메모이제이션, 지연 로딩 등)

> **deep depth 완료 → Step 4로 이동**

### Step 4: 프로필 문서 생성

분석 결과를 `./.jarfis/project-profile.md`에 저장하세요.

> 📄 템플릿: `templates/project-profile.md`를 읽어서 산출물 양식으로 사용한다.

**작성 원칙:**
- 토큰 효율이 최우선: 코드를 그대로 복사하지 말고, 구조와 패턴을 **서술**
- 해당 depth에서 분석하지 않은 섹션은 포함하지 말 것 (빈 섹션 금지)
- 모든 파일 경로는 프로젝트 루트 기준 상대경로로 표기

### Step 5: 결과 보고

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Init 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 프로젝트: [프로젝트명]
🔍 유형: [BE/FE/Fullstack]
📊 깊이: [basic/medium/deep]
📄 산출물: ./.jarfis/project-profile.md

이 프로필은 /jarfis:work 실행 시 자동으로 참조됩니다.
프로젝트 구조가 크게 변경되면 /jarfis:project-init 을 다시 실행하세요.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
