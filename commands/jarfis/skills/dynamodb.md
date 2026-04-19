# DynamoDB Expertise

> NoSQL key-value — partition key 설계, GSI, query vs scan, 1MB limit

## Common Pitfalls
- **Hot partition**: 동일 partition key에 집중 → 특정 파티션만 throttled. 접두 hash 또는 composite PK(예: `userId#YYYYMMDD`)로 분산.
- **1MB query 응답 제한**: 페이지네이션(`LastEvaluatedKey`) 누락 시 결과 누락. 클라이언트는 반드시 루프.
- **Scan은 전체 테이블 RCU 소비**: 운영 환경 금지. GSI 또는 추가 PK 설계.
- **Strong vs Eventually Consistent**: 기본 eventually. `ConsistentRead: true` 지정 시 latency ↑ + cost ×2.
- **Empty string / null**: 과거엔 금지, 이제 허용. 하지만 null vs absent 구분은 app 레벨 규약 필요.

## Decision Heuristics
- 단일 access pattern당 GSI 1개까지 — 5+ GSI는 다른 DB 검토 신호.
- `BatchWriteItem`은 25개/call 하드캡. 대량 삽입은 parallelism + 재시도 로직.
- Provisioned vs On-Demand: 트래픽 예측 가능 → Provisioned + Auto Scaling. 버스트 → On-Demand.
- GSI PK 선정: 쿼리 access pattern 역산. "어떤 필드로 검색?" → 그게 PK.

## Anti-patterns
- **DynamoDB를 RDBMS처럼 쓰기**: JOIN 없음. Denormalize 필수.
- **Large attribute (>400KB)**: item 최대 400KB. 큰 페이로드는 S3 + DynamoDB에 포인터.
- **Transaction 남용**: `TransactWriteItems`는 2×RCU/WCU 소비. 정합성 필수 경로만.

## Version & Environment Notes
- PartiQL 지원 (2020+) — SQL 익숙하면 유용하지만 native API보다 latency 약간 ↑.
- Streams + Lambda trigger: batch size, maximum batching window, 실패 시 bisect-on-error 설정.
- DAX (in-memory cache): read-heavy일 때만 효과. write-through 아님.

## Related Skills
- `aws-lambda` (Streams trigger), `s3` (large blob offload), `nodejs` (AWS SDK v3)
