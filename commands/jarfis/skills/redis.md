# Redis Expertise

> In-memory key-value — TTL, eviction, pipeline, pub/sub, ElastiCache 운영

## Common Pitfalls
- **TTL 미설정 cache**: 메모리 누수. 모든 cache 키에 EXPIRE 또는 TTL 정책 필수.
- **KEYS 명령 프로덕션 사용**: O(N) 블로킹. 대신 `SCAN` (cursor 기반 non-blocking).
- **Connection pool 미활용**: 매 요청 new connection → latency + FD exhaustion. Node `ioredis` 또는 pool lib 사용.
- **Large value (>1MB)**: 단일 키 MB 이상은 memory 단편화 + latency spike. 분할 또는 S3로 이동.
- **Pub/Sub는 fire-and-forget**: 구독자 부재 시 메시지 소실. durable 메시지는 Streams 또는 SQS.

## Decision Heuristics
- Eviction policy: 세션 cache → `allkeys-lru`, rate-limit → `volatile-lru`, DB 대체 → `noeviction`.
- Pipeline: 10+ 연속 명령 → `MULTI`/`EXEC` 또는 pipeline으로 RTT 1회 축소.
- Cluster mode vs Single: 데이터셋 < 100GB + 쓰기 단일 노드 가능 → Single. 그 이상 → Cluster + hash tag로 cross-slot 작업 묶기.

## Anti-patterns
- **Redis를 primary DB로 사용**: persistence(AOF/RDB) 있어도 crash 시 최대 수초 데이터 손실.
- **Lua script 긴 실행**: 단일 스레드 블로킹. 50ms 이상이면 분할 또는 Redis Functions.
- **Hot key 없는 분산 lock**: `SET key val NX EX` + Redlock 검토. 단일 노드 lock은 failover 시 실패.

## Version & Environment Notes
- Redis 7.x: Functions, Sharded Pub/Sub 추가. ACL 세밀화.
- ElastiCache Serverless (2023+): capacity 자동 스케일 + AZ 다중화 기본. 기존 노드형보다 예측 가능.
- `CLUSTER` mode: `{hash_tag}` 없으면 cross-slot ops 실패. Pipeline 작성 시 주의.

## Related Skills
- `postgres`/`dynamodb` (primary DB와 cache 계층), `nodejs` (`ioredis`/`redis-node-v4`), `aws-lambda` (VPC ENI cold start 주의)
