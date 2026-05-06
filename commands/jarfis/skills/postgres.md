# PostgreSQL Expertise

> 관계형 DB — connection pool, JSONB, MVCC, EXPLAIN, RDS Proxy

<!-- jarfis:context7
library_id: /websites/postgresql_16
query_topics: [SQL syntax, JSONB, indexes, transactions, EXPLAIN]
-->

## Common Pitfalls
- **Connection 고갈**: Lambda × Postgres는 cold start마다 connection 생성 → `max_connections` 초과. **RDS Proxy** 또는 PgBouncer 필수.
- **N+1 쿼리**: ORM lazy loading 남용. `EXPLAIN ANALYZE`로 loop 확인 → JOIN 또는 `IN (...)` 배치.
- **Index 미생성 WHERE 컬럼**: seq scan. 1000+ row 테이블의 조회 컬럼은 무조건 index. `CREATE INDEX CONCURRENTLY` (lock 최소화).
- **VACUUM 누락**: MVCC 튜플 팽창 → bloat. autovacuum 설정 확인, `pg_stat_user_tables` dead tuples 모니터링.
- **JSONB는 schemaless라 믿기**: 인덱스 없으면 검색 느림. `GIN` + `jsonb_path_ops` 사용.

## Decision Heuristics
- Connection pool 크기 = `(vCPU * 2) + effective_spindle_count`. 일반 웹앱 Postgres: **10~30**.
- Transaction isolation: 기본 `READ COMMITTED`. 금융/정합성 → `SERIALIZABLE` (retry 핸들링 필수).
- Partitioning: 단일 테이블 100M+ rows 또는 시계열 → `RANGE` partition (월 단위).
- `EXPLAIN (ANALYZE, BUFFERS)` 실행시간 + 디스크 읽기 동시 확인.

## Anti-patterns
- **`SELECT *` + ORM 엔티티 전체 로드**: 필요한 컬럼만. large text/jsonb는 지연 로드.
- **장시간 idle transaction**: row lock 유지 + VACUUM 방해. `idle_in_transaction_session_timeout` 설정.
- **자동 증가 PK에 `uuid_generate_v4()` 남용**: index fragmentation. `uuid_generate_v7()` (시간순) 또는 `bigint` 검토.

## Version & Environment Notes
- Postgres 16+: logical replication 개선, `pg_stat_io` 추가.
- RDS Aurora Postgres: write forwarding, global DB. Aurora Serverless v2는 ACU 0.5부터 스케일.
- Extension 주의: RDS는 화이트리스트만 설치 가능 (`pg_cron`, `pg_trgm`, `postgis` 등).

## Related Skills
- `aws-lambda` (RDS Proxy 필수), `redis` (read-heavy cache 계층), `nodejs` (`pg`/`postgres.js`/Prisma)
