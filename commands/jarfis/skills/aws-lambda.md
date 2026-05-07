# AWS Lambda Expertise

> Serverless 함수 — cold start, Lambda Web Adapter, timeout/memory, IAM

<!-- jarfis:context7
library_id: /websites/aws_amazon_lambda_dg
query_topics: [handlers, layers, environment variables, triggers, IAM roles]
-->

## Common Pitfalls
- **Cold start 누적**: provisioned concurrency 없으면 VPC 연결 + 큰 node_modules → 1~3s 추가. 핵심 API는 prewarm 또는 Lambda SnapStart(Java/Python).
- **Timeout vs API Gateway 29s 제한**: Lambda는 최대 900s여도 API Gateway 경로는 29s 하드캡. 장시간 작업은 Step Functions 또는 async invoke.
- **Ephemeral /tmp는 512MB~10GB**: 동시 실행 컨테이너 재사용 시 이전 실행 잔여 파일이 보임. 민감 데이터 쓰기 금지 또는 명시적 cleanup.
- **Env var 암호화**: KMS 암호화 + Lambda Extensions으로 런타임 decrypt. `process.env` 평문 저장 피하기.
- **Lambda Web Adapter**: Express/Fastify 앱을 Lambda에 올릴 때 어댑터 없이 `awsgi`/`serverless-http` 쓰면 streaming response 차단됨.

## Decision Heuristics
- Memory 설정 = vCPU 비례 (1769MB = 1 vCPU). 연산 많으면 128→1024 올려 **총 비용 감소**(실행 시간 단축).
- Cold start 민감 API → Node.js > Python > Java > .NET 순으로 빠름. Bundle size 50MB 초과 시 분할.
- Reserved concurrency = 안전장치 (runaway 방지). Provisioned = 성능 보장 (비용 추가).

## Anti-patterns
- **Lambda 안에 배경 작업(setInterval) 실행**: 컨테이너 freeze 시 중단 → CloudWatch Events + EventBridge 사용.
- **DB connection을 handler 안에서 생성**: cold start마다 재연결. **module 스코프**에 두고 재사용 (RDS Proxy 권장).
- **무한 재시도**: Destinations 미설정 시 DLQ 없으면 이벤트 유실. `OnFailure: SQS/SNS` 지정.

## Version & Environment Notes
- Node.js 22.x (AL2023 런타임) 권장. 18.x EOL 2025-07.
- Architecture: `arm64` (Graviton2) 비용 20% ↓ + 성능 유사. 단, native module은 arm64 빌드 필요.
- `AWS_REGION`, `AWS_LAMBDA_FUNCTION_NAME` 등 자동 주입 env var는 로컬 테스트 시 mock 필요.
- **Cost guard 기본값**: 신규 함수는 reserved concurrency (예: 100~500) + AWS Budgets alert 둘 다 설정 — runaway invoke 1건이 월 예산 폭발시키는 일을 막는다.

## Related Skills
- `nodejs` (핸들러 작성), `dynamodb`/`s3`/`cognito` (공통 조합), `serverless`/`sam`/`cdk` (배포 도구)
