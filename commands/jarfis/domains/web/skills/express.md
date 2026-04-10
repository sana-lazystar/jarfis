# Express / NestJS Backend Framework Expertise

## Express Patterns
- **Middleware Chain**: req → middleware1 → middleware2 → route handler → res
- **Error Middleware**: 4-argument signature `(err, req, res, next)` — 반드시 마지막에 등록
- **Router 분리**: express.Router()로 도메인별 라우팅 모듈화
- **CORS**: cors() 미들웨어, origin 화이트리스트, credentials 설정

## NestJS Patterns
- **Module Architecture**: 도메인별 모듈 분리, forRoot/forFeature
- **Guards/Interceptors/Pipes**: 인증(Guard) → 변환(Pipe) → 실행 → 로깅(Interceptor)
- **DTO Validation**: class-validator + class-transformer
- **Microservices**: Transport layer 추상화 (TCP, Redis, NATS, Kafka)

## API Design
- **REST**: 리소스 중심 URL, 적절한 HTTP 메서드, 상태 코드 의미 준수
- **GraphQL**: 스키마 퍼스트 vs 코드 퍼스트, N+1 해결 (DataLoader), 쿼리 복잡도 제한
- **Rate Limiting**: 고정 윈도우 vs 슬라이딩 윈도우 vs 토큰 버킷

## Common Pitfalls
- 미들웨어 순서: body-parser → cors → auth → routes → error handler
- async route handler에서 에러 미전파 → express-async-errors 또는 수동 try-catch
- 응답 후 next() 호출 → "headers already sent" 에러
