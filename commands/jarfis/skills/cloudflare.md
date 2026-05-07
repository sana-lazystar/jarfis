# Cloudflare Workers Expertise

> Edge serverless — V8 isolates, Wrangler, KV/D1/R2, edge runtime constraints

<!-- jarfis:context7
library_id: /websites/developers_cloudflare_workers
query_topics: [bindings, wrangler config, KV/D1/R2, durable objects, compat dates, fetch handler]
-->

## Common Pitfalls
- **Node 호환 미설정**: 기본은 V8 isolate (Node API 제한). `compatibility_flags = ["nodejs_compat"]` + 적절한 `compatibility_date` 미설정 시 `crypto`/`fs`/`buffer` 일부 미작동.
- **CPU time 한도**: Free 10ms / Bundled 50ms / Unbound 30s. 동기 hash/JSON 큰 처리는 한도 초과 → 503. 무거운 작업은 Queues/Workers + Durable Objects 분할.
- **Subrequest 50개 제한**: 한 invoke 당 fetch/KV/D1 합계 50회. 루프 안에서 KV 다건 호출 시 즉시 한도. 배치 read (`KV.get(keys[])`) 또는 D1 `IN` 활용.
- **Local Wrangler ↔ 배포 환경 차이**: `wrangler dev --remote` 안 쓰면 KV namespace ID/binding 이 로컬 mock 으로 동작 — 배포 후 only-prod 버그 빈발. `vars.ENVIRONMENT` 로 분기 + `--remote` smoke.
- **Durable Object migrations 누락**: class 변경 시 `[[migrations]]` 추가 안 하면 deploy 거부. 새 클래스명 = `new_classes`, 삭제 = `deleted_classes`.

## Decision Heuristics
- 글로벌 저지연 read-heavy → KV (eventual consistency, 60s TTL 권장). 강한 consistency → D1 (SQLite, region pinned).
- 큰 blob (이미지/영상) → R2 (S3 호환, egress 무료). 작은 메타 → KV. 트랜잭션 → D1 또는 Durable Object stub.
- 외부 API 호출량 많고 fan-out → Queues + Worker consumer 분리 (CPU time 회피).
- 인증 → Workers + JWT verify 직접 또는 Access (Zero Trust). 세션 → KV TTL 또는 Durable Object.

## Anti-patterns
- **모듈 스코프에서 fetch / DB write**: cold-start 시 무한 retry 위험. 반드시 handler 내부.
- **`crypto.randomUUID()` 가정**: Workers `crypto.randomUUID()` 사용 가능하지만 일부 폴리필 필요 시점 주의 — `compatibility_date` 확인.
- **wrangler.toml 의 `account_id` 하드코딩**: 팀 협업 시 `CLOUDFLARE_ACCOUNT_ID` env 로 분리.

## Version & Environment Notes
- `compatibility_date` 는 신규 prod 배포 시 최근 안정 일자로 핀. 변경 시 release note 확인 필수.
- Wrangler v3+ 권장 (esbuild 기반, v2 EOL). `npx wrangler --version` 로 확인.
- Bindings 종류: `vars`, `kv_namespaces`, `r2_buckets`, `d1_databases`, `queues`, `services`, `durable_objects`, `ai`, `vectorize`. wrangler.toml 또는 `[env.<name>]` 분리.

## Related Skills
- `nodejs` (모듈 작성), `s3` (R2 호환 비교), `aws-lambda` (서버리스 비교 — runtime 가정 다름)
