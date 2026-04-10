# Node.js / TypeScript Backend Expertise

## Runtime Understanding
- **Event Loop**: 마이크로태스크(Promise) → 매크로태스크(setTimeout) 순서
- **V8 Optimization**: 히든 클래스, 인라인 캐싱 — 객체 형태 일관성 유지
- **Clustering**: cluster 모듈로 CPU 코어 활용. PM2/forever로 프로세스 관리
- **Async Patterns**: async/await, Promise.all/allSettled, 스트림

## TypeScript Patterns
- Strict mode 필수 (strict: true)
- 제네릭 활용: 타입 안전한 유틸리티 함수
- Discriminated unions: 상태 머신 모델링
- Zod/Valibot: 런타임 스키마 검증 + 타입 추론 동시

## Error Handling
- 커스텀 에러 클래스 계층: AppError → NotFoundError, ValidationError
- 미처리 rejection 방지: process.on('unhandledRejection')
- 그레이스풀 셧다운: SIGTERM/SIGINT 핸들링

## Database Patterns
- 커넥션 풀링: 적절한 풀 사이즈 (CPU 코어 * 2 + 1 경험칙)
- N+1 방지: eager loading, DataLoader 패턴
- 마이그레이션: 스키마 변경은 반드시 마이그레이션 파일로

## Common Pitfalls
- `require()` vs `import`: ESM/CJS 혼용 시 __dirname 미정의 → import.meta.url 사용
- 메모리 누수: 이벤트 리스너 미해제, 클로저의 큰 스코프 캡처
- mutateAsync 사용 시 반드시 try-catch (unhandled rejection 방지)
