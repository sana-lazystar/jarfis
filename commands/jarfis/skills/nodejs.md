# Node.js / TypeScript Backend Expertise

<!-- jarfis:context7
library_id: /nodejs/node
query_topics: [streams, fs, child_process, net, cluster, worker_threads]
-->

## Runtime Understanding
- **Event Loop**: Microtasks (Promise) -> Macrotasks (setTimeout) ordering
- **V8 Optimization**: Hidden classes, inline caching — Maintain consistent object shapes
- **Clustering**: Utilize CPU cores with the cluster module. Process management via PM2/forever
- **Async Patterns**: async/await, Promise.all/allSettled, streams

## TypeScript Patterns
- Strict mode required (strict: true)
- Leverage generics: Type-safe utility functions
- Discriminated unions: State machine modeling
- Zod/Valibot: Runtime schema validation + type inference simultaneously

## Error Handling
- Custom error class hierarchy: AppError -> NotFoundError, ValidationError
- Prevent unhandled rejections: process.on('unhandledRejection')
- Graceful shutdown: SIGTERM/SIGINT handling

## Database Patterns
- Connection pooling: Appropriate pool size (CPU cores * 2 + 1 rule of thumb)
- N+1 prevention: Eager loading, DataLoader pattern
- Migrations: Schema changes must always go through migration files

## Common Pitfalls
- `require()` vs `import`: __dirname undefined when mixing ESM/CJS -> Use import.meta.url
- Memory leaks: Unreleased event listeners, closures capturing large scopes
- Always wrap mutateAsync in try-catch (prevent unhandled rejections)
