# Express / NestJS Backend Framework Expertise

## Express Patterns
- **Middleware Chain**: req -> middleware1 -> middleware2 -> route handler -> res
- **Error Middleware**: 4-argument signature `(err, req, res, next)` — Must be registered last
- **Router Separation**: Modularize routing per domain with express.Router()
- **CORS**: cors() middleware, origin whitelist, credentials configuration

## NestJS Patterns
- **Module Architecture**: Separate modules per domain, forRoot/forFeature
- **Guards/Interceptors/Pipes**: Auth (Guard) -> Transform (Pipe) -> Execute -> Logging (Interceptor)
- **DTO Validation**: class-validator + class-transformer
- **Microservices**: Transport layer abstraction (TCP, Redis, NATS, Kafka)

## API Design
- **REST**: Resource-oriented URLs, appropriate HTTP methods, proper status code semantics
- **GraphQL**: Schema-first vs code-first, N+1 resolution (DataLoader), query complexity limits
- **Rate Limiting**: Fixed window vs sliding window vs token bucket

## Common Pitfalls
- Middleware order: body-parser -> cors -> auth -> routes -> error handler
- Unhandled errors in async route handlers -> Use express-async-errors or manual try-catch
- Calling next() after response sent -> "headers already sent" error
